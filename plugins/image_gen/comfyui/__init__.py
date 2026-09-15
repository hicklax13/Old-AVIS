"""Local ComfyUI image generation backend.

Serves ``image_generate`` from a ComfyUI instance running on this machine
(default ``http://127.0.0.1:8188``), driving a FLUX.2 Klein 4B GGUF graph.
Fully local: no API key, no cloud round-trip.

Selection: ``model`` kwarg → ``image_gen.comfyui.model`` → ``image_gen.model``
(when it names one of our ids) → :data:`DEFAULT_MODEL`. Endpoint override:
``COMFYUI_BASE_URL`` env var → ``image_gen.comfyui.base_url`` → default.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import requests

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    resolve_aspect_ratio,
    success_response,
)
from plugins.image_gen._common import (
    StaticImageGenProvider,
    error_factory,
    load_image_gen_config,
    prompt_required_error,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://127.0.0.1:8188"

# Semantic aspect → (width, height). Kept modest so a 6 GB laptop GPU can
# still finish a render with ComfyUI's --lowvram offloading.
_SIZES: Dict[str, tuple] = {
    "landscape": (1024, 768),
    "square": (1024, 1024),
    "portrait": (768, 1024),
}

DEFAULT_STEPS = 20
DEFAULT_GUIDANCE = 3.5

_MODELS: Dict[str, Dict[str, Any]] = {
    "flux-2-klein-4b-q4-k-s": {
        "display": "FLUX.2 Klein 4B (Q4_K_S GGUF)",
        "speed": "~100s @1024px (measured; needs the LLM unloaded — see docs)",
        "strengths": "Local text-to-image, Apache-2.0, no cloud. Run `lms unload --all` first: "
                     "with a 35B LLM resident, RAM pressure pushes this past 8 minutes.",
        "unet": "flux-2-klein-4b-Q4_K_S.gguf",
        "clip": "qwen_3_4b.safetensors",
        "vae": "flux2-vae.safetensors",
    },
}

DEFAULT_MODEL = "flux-2-klein-4b-q4-k-s"


def _base_url(cfg: Dict[str, Any]) -> str:
    env = (os.environ.get("COMFYUI_BASE_URL") or "").strip()
    if env:
        return env.rstrip("/")
    sub = cfg.get("comfyui") if isinstance(cfg, dict) else None
    if isinstance(sub, dict):
        url = (sub.get("base_url") or "").strip()
        if url:
            return url.rstrip("/")
    return DEFAULT_BASE_URL


def _resolve_model(model_kwarg: Optional[str], cfg: Dict[str, Any]) -> str:
    if isinstance(model_kwarg, str) and model_kwarg in _MODELS:
        return model_kwarg
    sub = cfg.get("comfyui") if isinstance(cfg, dict) else None
    if isinstance(sub, dict):
        m = (sub.get("model") or "").strip()
        if m in _MODELS:
            return m
    top = (cfg.get("model") or "").strip() if isinstance(cfg, dict) else ""
    if top in _MODELS:
        return top
    return DEFAULT_MODEL


def _build_graph(spec: Dict[str, Any], prompt: str, width: int, height: int, seed: int,
                 steps: int, guidance: float) -> Dict[str, Any]:
    """FLUX.2 Klein text-to-image graph (GGUF unet + Qwen3-4B text encoder)."""
    return {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": spec["unet"]},
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": spec["clip"], "type": "flux2"},
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": spec["vae"]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["2", 0]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["2", 0]},
        },
        "6": {
            "class_type": "EmptyFlux2LatentImage",
            "inputs": {"width": int(width), "height": int(height), "batch_size": 1},
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": int(seed),
                "steps": int(steps),
                "cfg": float(guidance),
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["3", 0]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "hermes_comfy"},
        },
    }


class ComfyUIImageGenProvider(StaticImageGenProvider):
    """Local ComfyUI backend — no credentials, talks to ``127.0.0.1:8188``."""

    provider_id = "comfyui"
    label = "ComfyUI (local)"
    models = _MODELS
    default_model_id = DEFAULT_MODEL
    price = "free (local GPU)"
    catalog_fields = ("display", "speed", "strengths")

    def get_setup_schema(self) -> Dict[str, Any]:
        """No credentials — the picker row just points at the local server."""
        return {
            "name": self.label,
            "badge": "Local",
            "tag": "No API key — talks to a ComfyUI server on this machine (default 127.0.0.1:8188)",
            "env_vars": [],
        }

    def is_available(self) -> bool:
        """True when a ComfyUI server answers; never raises."""
        try:
            cfg = load_image_gen_config()
            r = requests.get(f"{_base_url(cfg)}/system_stats", timeout=3)
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        aspect = resolve_aspect_ratio(aspect_ratio)
        cfg = load_image_gen_config()
        model_id = _resolve_model(kwargs.get("model"), cfg)
        spec = _MODELS[model_id]
        fail = error_factory("comfyui", aspect, model=model_id, prompt=prompt or "")

        if not isinstance(prompt, str) or not prompt.strip():
            return prompt_required_error("comfyui", aspect)

        base = _base_url(cfg)
        width, height = _SIZES.get(aspect, _SIZES["square"])
        seed = int(kwargs.get("seed") or time.time_ns() % (2**31))
        steps = int(kwargs.get("steps") or DEFAULT_STEPS)
        guidance = float(kwargs.get("guidance") or DEFAULT_GUIDANCE)

        # Local ComfyUI graph is text-to-image; reference/edit flows are not wired yet.
        if image_url or reference_image_urls:
            logger.info("comfyui: ignoring reference image(s) — text-to-image only for now")

        graph = _build_graph(spec, prompt, width, height, seed, steps, guidance)
        client_id = str(uuid.uuid4())

        try:
            resp = requests.post(
                f"{base}/prompt",
                json={"prompt": graph, "client_id": client_id},
                timeout=30,
            )
        except requests.exceptions.ConnectionError:
            return fail(
                f"Could not reach a ComfyUI server at {base} — is it running?",
                "connection_error",
            )
        except requests.exceptions.RequestException as exc:
            return fail(f"ComfyUI request failed: {exc}", "connection_error")

        if resp.status_code != 200:
            return fail(
                f"ComfyUI rejected the workflow ({resp.status_code}): {resp.text[:400]}",
                "api_error",
            )

        try:
            prompt_id = resp.json().get("prompt_id")
        except ValueError:
            return fail("ComfyUI returned a non-JSON response to /prompt", "invalid_response")
        if not prompt_id:
            return fail("ComfyUI did not return a prompt_id", "invalid_response")

        # Poll history until the render lands (or we give up).
        deadline = time.time() + float(kwargs.get("timeout") or 600)
        images: List[Dict[str, Any]] = []
        while time.time() < deadline:
            time.sleep(2.0)
            try:
                h = requests.get(f"{base}/history/{prompt_id}", timeout=15)
                hist = h.json() if h.status_code == 200 else {}
            except requests.exceptions.RequestException:
                continue
            entry = hist.get(prompt_id) if isinstance(hist, dict) else None
            if isinstance(entry, dict) and entry.get("outputs"):
                for node_out in entry["outputs"].values():
                    if isinstance(node_out, dict) and node_out.get("images"):
                        images.extend(node_out["images"])
                break
            status = (entry or {}).get("status") if isinstance(entry, dict) else None
            if isinstance(status, dict) and status.get("status_str") == "error":
                return fail("ComfyUI reported an execution error", "provider_error")

        if not images:
            return fail(
                "ComfyUI render did not finish before the timeout — the model may still be warming up",
                "timeout",
            )

        first = images[0]
        params = {
            "filename": first.get("filename", ""),
            "subfolder": first.get("subfolder", ""),
            "type": first.get("type", "output"),
        }
        try:
            img = requests.get(f"{base}/view", params=params, timeout=120)
            img.raise_for_status()
        except requests.exceptions.RequestException as exc:
            return fail(f"Could not fetch the rendered image from ComfyUI: {exc}", "io_error")

        try:
            b64 = base64.b64encode(img.content).decode("ascii")
            from agent.image_gen_provider import save_b64_image

            image_ref = str(save_b64_image(b64, prefix="comfyui"))
        except Exception as exc:  # noqa: BLE001
            return fail(f"Could not save the generated image: {exc}", "io_error")

        return success_response(
            image=image_ref,
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
            provider="comfyui",
            modality="text",
            extra={
                "width": width,
                "height": height,
                "seed": seed,
                "steps": steps,
                "guidance": guidance,
                "engine": "comfyui",
                "base_url": base,
                "filename": first.get("filename", ""),
            },
        )


def register(ctx) -> None:
    """Plugin entry point — wire :class:`ComfyUIImageGenProvider` into the registry."""
    ctx.register_image_gen_provider(ComfyUIImageGenProvider())
