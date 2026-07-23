"""
Image generation for GoKAIDM via MCP (Model Context Protocol) connections.

Supports two provider backends:
  - ``gemini``   → Google Gemini image generation (Imagen models)
  - ``firefly``  → Adobe Firefly image generation API

Both providers are accessed via HTTP / REST so that the connection can
be treated as an MCP tool call.  When neither provider is configured the
module returns a placeholder result rather than raising an exception, so
the rest of the game can continue unaffected.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ImageResult:
    """The result of an image generation request."""

    prompt: str = ""
    provider: str = ""
    url: str = ""                     # remote URL if returned by provider
    image_data: bytes = field(default_factory=bytes)  # raw bytes if returned inline
    local_path: str = ""              # path after saving to disk
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        """True if image data or a URL was actually generated."""
        return bool(self.url or self.image_data or self.local_path)

    def save(self, path: str | Path) -> str:
        """Save inline *image_data* to *path*. Returns the path string."""
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.image_data:
            dest.write_bytes(self.image_data)
        elif self.url:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            dest.write_bytes(response.content)
        else:
            raise ValueError("ImageResult has no image data or URL to save.")
        self.local_path = str(dest)
        return self.local_path


# ---------------------------------------------------------------------------
# Provider: Google Gemini (Imagen via Generative Language REST API)
# ---------------------------------------------------------------------------


def _gemini_generate(prompt: str, api_key: str, model: str = "imagen-3.0-generate-001") -> ImageResult:
    """Generate an image via the Gemini Imagen REST API."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:predict"
    )
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1},
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    }
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()

    # Extract base64-encoded image from response
    predictions = data.get("predictions", [])
    if not predictions:
        raise RuntimeError("Gemini returned no image predictions.")

    b64 = predictions[0].get("bytesBase64Encoded", "")
    image_bytes = base64.b64decode(b64) if b64 else b""
    return ImageResult(
        prompt=prompt,
        provider="gemini",
        image_data=image_bytes,
        metadata={"model": model},
    )


# ---------------------------------------------------------------------------
# Provider: Adobe Firefly
# ---------------------------------------------------------------------------


def _firefly_get_token(client_id: str, api_key: str) -> str:
    """Obtain a short-lived Firefly access token via the Adobe IMS."""
    token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": api_key,
        "scope": "openid,AdobeID,firefly_api",
    }
    response = requests.post(token_url, data=payload, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _firefly_generate(
    prompt: str,
    client_id: str,
    api_key: str,
    style: str = "",
    width: int = 1024,
    height: int = 1024,
) -> ImageResult:
    """Generate an image via the Adobe Firefly v3 API."""
    access_token = _firefly_get_token(client_id, api_key)
    api_url = "https://firefly-api.adobe.io/v3/images/generate"
    headers = {
        "Authorization": "Bearer " + access_token,
        "x-api-key": client_id,
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "prompt": prompt,
        "size": {"width": width, "height": height},
        "n": 1,
    }
    if style:
        body["style"] = {"preset": style}

    response = requests.post(api_url, json=body, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()

    outputs = data.get("outputs", [])
    if not outputs:
        raise RuntimeError("Firefly returned no image outputs.")

    image_url = outputs[0].get("image", {}).get("url", "")
    return ImageResult(
        prompt=prompt,
        provider="firefly",
        url=image_url,
        metadata={"width": width, "height": height},
    )


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------


class ImageGenerator:
    """Generate images for GoKAIDM via MCP-connected AI image services.

    Usage::

        config = load_config()
        generator = ImageGenerator(config)
        result = generator.generate("A dark ancient temple in the mountains")
        result.save("./data/images/temple.png")
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        img_cfg = config.get("image", {})
        self.provider: str = img_cfg.get("provider", "gemini")
        self.api_key: str = img_cfg.get("api_key", "")
        self.firefly_api_key: str = img_cfg.get("firefly_api_key", "")
        self.firefly_client_id: str = img_cfg.get("firefly_client_id", "")
        self.default_style: str = img_cfg.get(
            "default_style", "fantasy digital painting, Gates of Krystalia style"
        )

    def generate(
        self,
        prompt: str,
        style_suffix: str | None = None,
        save_to: str | Path | None = None,
    ) -> ImageResult:
        """Generate an image from *prompt*.

        Args:
            prompt: Scene or subject description.
            style_suffix: Additional style keywords appended to *prompt*.
                          Defaults to ``config.image.default_style``.
            save_to: If provided, the image is immediately saved to this path.

        Returns:
            An :class:`ImageResult`. If no API key is configured, returns a
            placeholder result so the rest of the game continues unaffected.
        """
        suffix = style_suffix if style_suffix is not None else self.default_style
        full_prompt = f"{prompt}. {suffix}".strip(" .")

        result = self._dispatch(full_prompt)

        if save_to and result.available:
            result.save(save_to)

        return result

    def _dispatch(self, prompt: str) -> ImageResult:
        if self.provider == "gemini":
            if not self.api_key:
                return self._placeholder(prompt, "gemini")
            return _gemini_generate(prompt, self.api_key)

        if self.provider == "firefly":
            if not self.firefly_api_key or not self.firefly_client_id:
                return self._placeholder(prompt, "firefly")
            return _firefly_generate(
                prompt, self.firefly_client_id, self.firefly_api_key
            )

        raise ValueError(f"Unknown image provider: {self.provider!r}")

    @staticmethod
    def _placeholder(prompt: str, provider: str) -> ImageResult:
        """Return a placeholder result when credentials are missing."""
        return ImageResult(
            prompt=prompt,
            provider=provider,
            metadata={"placeholder": True, "reason": "No API key configured"},
        )

    def generate_portrait(self, persona_name: str, description: str) -> ImageResult:
        """Generate a character portrait for a persona."""
        prompt = (
            f"Character portrait of {persona_name}: {description}. "
            "Fantasy RPG portrait, detailed face, dramatic lighting."
        )
        return self.generate(prompt)

    def generate_location(self, location_name: str, description: str) -> ImageResult:
        """Generate a scene illustration for a location."""
        prompt = f"Fantasy landscape scene: {location_name}. {description}."
        return self.generate(prompt)

    def generate_encounter(self, description: str) -> ImageResult:
        """Generate an action scene for a combat or event encounter."""
        prompt = f"Fantasy encounter scene: {description}. Dynamic action composition."
        return self.generate(prompt)
