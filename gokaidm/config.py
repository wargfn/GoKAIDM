"""
Configuration loader for GoKAIDM.

Reads config.json from the project root (or a custom path) and merges
with any environment variables that override API keys.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_DEFAULT_CONFIG: dict[str, Any] = {
    "ai": {
        "provider": "anthropic",
        "model": "claude-opus-4-5",
        "api_key_env": "ANTHROPIC_API_KEY",
        "system_prompt": (
            "You are the AI Dungeon Master for Gates of Krystalia, "
            "a solo/group TTRPG. Narrate vividly, adjudicate rules fairly, "
            "and keep the game engaging. Always respond in third-person "
            "narrative style."
        ),
    },
    "image": {
        "provider": "gemini",
        "api_key_env": "GEMINI_API_KEY",
        "firefly_api_key_env": "ADOBE_FIREFLY_API_KEY",
        "firefly_client_id_env": "ADOBE_FIREFLY_CLIENT_ID",
        "default_style": "fantasy digital painting, Gates of Krystalia style",
    },
    "data_dir": "./data",
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from *path* (defaults to ``config.json``).

    Environment variables always take precedence for any ``*_env`` key
    patterns (i.e. the resolved value is fetched from the named env var).
    """
    config_path = Path(path) if path else Path("config.json")

    config: dict[str, Any] = json.loads(json.dumps(_DEFAULT_CONFIG))  # deep copy

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            user_cfg = json.load(fh)
        _deep_merge(config, user_cfg)

    # Resolve env-var keys so callers get the actual secret string
    config["ai"]["api_key"] = os.getenv(config["ai"].get("api_key_env", ""), "")
    config["image"]["api_key"] = os.getenv(
        config["image"].get("api_key_env", ""), ""
    )
    config["image"]["firefly_api_key"] = os.getenv(
        config["image"].get("firefly_api_key_env", ""), ""
    )
    config["image"]["firefly_client_id"] = os.getenv(
        config["image"].get("firefly_client_id_env", ""), ""
    )

    return config


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Recursively merge *override* into *base* in-place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
