import json

import pytest

from hermes_cli import models


MODEL = "publisher/model"
BASE_URL = "http://127.0.0.1:1234/v1"


class _JsonResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._body


def _catalog(*, loaded_context=None, loaded_parallel=None, maximum=262_144):
    loaded_instances = []
    if loaded_context is not None:
        config = {"context_length": loaded_context}
        if loaded_parallel is not None:
            config["parallel"] = loaded_parallel
        loaded_instances.append({
            "id": f"{MODEL}:active",
            "config": config,
        })
    return [
        {
            "key": MODEL,
            "max_context_length": maximum,
            "loaded_instances": loaded_instances,
        }
    ]


def _capture_load(monkeypatch, response_payload):
    requests = []

    def fake_open(request, *, timeout):
        requests.append((request, timeout, json.loads(request.data.decode())))
        return _JsonResponse(response_payload)

    monkeypatch.setattr(models, "_urlopen_model_catalog_request", fake_open)
    return requests


def test_missing_echo_refreshes_loaded_state(monkeypatch):
    catalogs = iter([_catalog(), _catalog(loaded_context=88_000)])
    monkeypatch.setattr(
        models, "_lmstudio_fetch_raw_models", lambda **_kwargs: next(catalogs)
    )
    _capture_load(monkeypatch, {"status": "loaded"})

    result = models.ensure_lmstudio_model_loaded(
        MODEL, BASE_URL, api_key="", target_context_length=100_000
    )

    assert result == 88_000


def test_explicit_override_above_known_maximum_rejects_even_when_loaded(monkeypatch):
    monkeypatch.setattr(
        models,
        "_lmstudio_fetch_raw_models",
        lambda **_kwargs: _catalog(loaded_context=64_000, maximum=128_000),
    )
    monkeypatch.setattr(
        models,
        "_urlopen_model_catalog_request",
        lambda *_args, **_kwargs: pytest.fail("invalid override must not be posted"),
    )

    result = models.ensure_lmstudio_model_loaded(
        MODEL,
        BASE_URL,
        api_key="",
        target_context_length=256_000,
        return_load_result=True,
    )

    assert result.context_length is None
    assert result.load_attempted is False
    assert result.rejected is True


def test_explicit_load_forwards_parallel_limit(monkeypatch):
    monkeypatch.setattr(
        models,
        "_lmstudio_fetch_raw_models",
        lambda **_kwargs: _catalog(),
    )
    requests = _capture_load(
        monkeypatch,
        {"load_config": {"context_length": 65_536, "parallel": 1}},
    )

    result = models.ensure_lmstudio_model_loaded(
        MODEL,
        BASE_URL,
        api_key="",
        target_context_length=65_536,
        parallel=1,
        return_load_result=True,
    )

    assert result.context_length == 65_536
    assert result.load_attempted is True
    assert requests[0][2]["parallel"] == 1


def test_invalid_parallel_limit_is_rejected_before_load(monkeypatch):
    monkeypatch.setattr(
        models,
        "_lmstudio_fetch_raw_models",
        lambda **_kwargs: _catalog(),
    )
    monkeypatch.setattr(
        models,
        "_urlopen_model_catalog_request",
        lambda *_args, **_kwargs: pytest.fail(
            "invalid parallel value must not be posted"
        ),
    )

    result = models.ensure_lmstudio_model_loaded(
        MODEL,
        BASE_URL,
        api_key="",
        target_context_length=65_536,
        parallel=0,
        return_load_result=True,
    )

    assert result.context_length is None
    assert result.load_attempted is False
    assert result.rejected is True


def test_loaded_parallel_mismatch_is_reconfigured(monkeypatch):
    monkeypatch.setattr(
        models,
        "_lmstudio_fetch_raw_models",
        lambda **_kwargs: _catalog(loaded_context=65_536, loaded_parallel=4),
    )
    requests = _capture_load(
        monkeypatch,
        {"load_config": {"context_length": 65_536, "parallel": 1}},
    )

    result = models.ensure_lmstudio_model_loaded(
        MODEL,
        BASE_URL,
        api_key="",
        target_context_length=65_536,
        parallel=1,
        return_load_result=True,
    )

    assert result.context_length == 65_536
    assert result.load_attempted is True
    assert requests[0][0].full_url.endswith("/api/v1/models/unload")
    assert requests[0][2] == {"instance_id": f"{MODEL}:active"}
    assert requests[1][0].full_url.endswith("/api/v1/models/load")
    assert requests[1][2]["parallel"] == 1


def test_unload_lmstudio_model_posts_every_loaded_instance(monkeypatch):
    catalog = _catalog(loaded_context=65_536, loaded_parallel=1)
    catalog[0]["loaded_instances"].append({
        "id": f"{MODEL}:second",
        "config": {"context_length": 65_536},
    })
    monkeypatch.setattr(models, "_lmstudio_fetch_raw_models", lambda **_kwargs: catalog)
    requests = _capture_load(monkeypatch, {"status": "unloaded"})

    assert models.unload_lmstudio_model(MODEL, BASE_URL, api_key="") is True
    assert [payload for _request, _timeout, payload in requests] == [
        {"instance_id": f"{MODEL}:active"},
        {"instance_id": f"{MODEL}:second"},
    ]


def test_unload_lmstudio_model_treats_known_idle_model_as_success(monkeypatch):
    monkeypatch.setattr(
        models,
        "_lmstudio_fetch_raw_models",
        lambda **_kwargs: _catalog(),
    )
    monkeypatch.setattr(
        models,
        "_urlopen_model_catalog_request",
        lambda *_args, **_kwargs: pytest.fail("idle model must not post unload"),
    )

    assert models.unload_lmstudio_model(MODEL, BASE_URL, api_key="") is True
