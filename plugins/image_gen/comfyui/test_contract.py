"""Focused contract tests for the local ComfyUI image_gen provider.

These exercise the real plugin module (not the registry fakes): the provider
surface, the success response shape, and the error paths an agent hits when
the local ComfyUI server is down or rejects the graph.

Run:  python -m pytest test_comfyui_provider_contract.py -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(r"C:\Dev\hermes-agent\.hermes\hermes-agent\plugins\image_gen\comfyui\__init__.py")

_requests = pytest.importorskip("requests")


def _load_plugin(monkeypatch, requests_stub):
    """Import the plugin fresh with `requests` swapped for a stub."""
    monkeypatch.setitem(sys.modules, "requests", requests_stub)
    spec = importlib.util.spec_from_file_location("comfyui_provider_ct", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Resp:
    def __init__(self, status_code=200, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise _requests.exceptions.HTTPError(str(self.status_code))


class _Stub:
    """Minimal stand-in for the `requests` module the provider imports."""

    exceptions = _requests.exceptions

    def __init__(self, *, stats_ok=True, prompt=None, history=None, image=b"PNGDATA"):
        self._stats_ok, self._prompt, self._history, self._image = stats_ok, prompt, history, image
        self.posted = []

    def get(self, url, **kw):
        if url.endswith("/system_stats"):
            return _Resp(200 if self._stats_ok else 503, {})
        if "/history/" in url:
            return _Resp(200, self._history)
        if "/view" in url:
            return _Resp(200, None, content=self._image)
        return _Resp(404, None, text="nope")

    def post(self, url, json=None, **kw):
        if self._prompt is None:
            raise self.exceptions.ConnectionError("refused")
        self.posted.append(json["prompt"])
        return self._prompt


_OK_PROMPT = _Resp(200, {"prompt_id": "pid-1"})
_OK_HISTORY = {
    "pid-1": {
        "outputs": {"9": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}},
        "status": {"status_str": "success"},
    }
}


# ---------------------------------------------------------------- surface -- #

def test_picker_surface(monkeypatch):
    p = _load_plugin(monkeypatch, _Stub()).ComfyUIImageGenProvider()

    assert p.name == "comfyui"
    assert p.display_name == "ComfyUI (local)"
    assert p.default_model() == "flux-2-klein-4b-q4-k-s"
    assert [r["id"] for r in p.list_models()] == ["flux-2-klein-4b-q4-k-s"]

    schema = p.get_setup_schema()
    assert schema["env_vars"] == []  # local backend needs no key
    assert schema["badge"] == "Local"


def test_is_available_true_and_false(monkeypatch):
    assert _load_plugin(monkeypatch, _Stub(stats_ok=True)).ComfyUIImageGenProvider().is_available() is True
    assert _load_plugin(monkeypatch, _Stub(stats_ok=False)).ComfyUIImageGenProvider().is_available() is False


def test_is_available_never_raises(monkeypatch):
    class _Boom(_Stub):
        def get(self, url, **kw):
            raise RuntimeError("kaboom")

    assert _load_plugin(monkeypatch, _Boom()).ComfyUIImageGenProvider().is_available() is False


# --------------------------------------------------------------- generate -- #

def test_generate_success_contract(monkeypatch, tmp_path):
    stub = _Stub(prompt=_OK_PROMPT, history=_OK_HISTORY)
    mod = _load_plugin(monkeypatch, stub)

    saved = {}
    out = tmp_path / "comfyui_saved.png"

    import agent.image_gen_provider as igp

    def _fake_save(b64, *, prefix="image", extension="png"):
        saved.update(b64=b64, prefix=prefix, extension=extension)
        return out

    monkeypatch.setattr(igp, "save_b64_image", _fake_save)

    res = mod.ComfyUIImageGenProvider().generate("a lighthouse at sunset", aspect_ratio="landscape")

    assert res["success"] is True
    assert res["provider"] == "comfyui"
    assert res["modality"] == "text"
    assert res["aspect_ratio"] == "landscape"
    assert (res["width"], res["height"]) == (1024, 768)
    assert res["engine"] == "comfyui"
    assert res["image"] == str(out)
    assert saved == {"b64": "UE5HREFUQQ==", "prefix": "comfyui", "extension": "png"}

    graph = stub.posted[0]
    assert graph["1"]["class_type"] == "UnetLoaderGGUF"
    assert graph["2"]["inputs"]["type"] == "flux2"
    assert graph["4"]["inputs"]["text"] == "a lighthouse at sunset"
    assert graph["7"]["inputs"]["cfg"] == res["guidance"]  # knob is plumbed through


def test_guidance_default_and_override(monkeypatch, tmp_path):
    stub = _Stub(prompt=_OK_PROMPT, history=_OK_HISTORY)
    mod = _load_plugin(monkeypatch, stub)

    import agent.image_gen_provider as igp

    monkeypatch.setattr(igp, "save_b64_image", lambda b64, **kw: tmp_path / "x.png")
    p = mod.ComfyUIImageGenProvider()

    assert p.generate("x")["guidance"] == mod.DEFAULT_GUIDANCE
    assert stub.posted[-1]["7"]["inputs"]["cfg"] == mod.DEFAULT_GUIDANCE

    assert p.generate("x", guidance=1.0)["guidance"] == 1.0
    assert stub.posted[-1]["7"]["inputs"]["cfg"] == 1.0


@pytest.mark.parametrize("aspect,size", [("square", (1024, 1024)), ("portrait", (768, 1024)), ("bogus", (1024, 768))])
def test_aspect_ratio_sizing_and_clamping(monkeypatch, tmp_path, aspect, size):
    stub = _Stub(prompt=_OK_PROMPT, history=_OK_HISTORY)
    mod = _load_plugin(monkeypatch, stub)

    import agent.image_gen_provider as igp

    monkeypatch.setattr(igp, "save_b64_image", lambda b64, **kw: tmp_path / "x.png")

    res = mod.ComfyUIImageGenProvider().generate("x", aspect_ratio=aspect)
    assert (res["width"], res["height"]) == size


def test_generate_empty_prompt_rejected(monkeypatch):
    mod = _load_plugin(monkeypatch, _Stub(prompt=_OK_PROMPT, history=_OK_HISTORY))
    res = mod.ComfyUIImageGenProvider().generate("   ")
    assert res["success"] is False
    assert res["error_type"] == "invalid_argument"


def test_generate_server_down(monkeypatch):
    mod = _load_plugin(monkeypatch, _Stub(prompt=None))
    res = mod.ComfyUIImageGenProvider().generate("anything")
    assert res["success"] is False
    assert res["error_type"] == "connection_error"
    assert "ComfyUI" in res["error"]


def test_generate_http_error_is_api_error(monkeypatch):
    mod = _load_plugin(monkeypatch, _Stub(prompt=_Resp(400, None, text="bad graph")))
    res = mod.ComfyUIImageGenProvider().generate("anything")
    assert res["success"] is False
    assert res["error_type"] == "api_error"


def test_generate_workflow_error_reported(monkeypatch):
    history = {"pid-1": {"outputs": {}, "status": {"status_str": "error"}}}
    mod = _load_plugin(monkeypatch, _Stub(prompt=_OK_PROMPT, history=history))
    res = mod.ComfyUIImageGenProvider().generate("anything", timeout=1)
    assert res["success"] is False
    assert res["error_type"] == "provider_error"


# ----------------------------------------------------------- registration -- #

def test_register_wires_provider(monkeypatch):
    mod = _load_plugin(monkeypatch, _Stub())

    captured = {}

    class _Ctx:
        def register_image_gen_provider(self, provider):
            captured["provider"] = provider

    mod.register(_Ctx())
    assert captured["provider"].name == "comfyui"
