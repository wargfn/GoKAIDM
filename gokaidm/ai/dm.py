"""
AI Dungeon Master for GoKAIDM.

Supports three backends:
  - ``anthropic``  → Claude (default)
  - ``openai``     → OpenAI Chat Completions
    - ``copilot``    → GitHub Copilot SDK

The DM holds recent session context to provide coherent narration, and
exposes helper methods for the CLI (ask, roll_oracle, describe_scene, etc.).
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from gokaidm.session.notation import NotationLog, EntryType


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


def _anthropic_complete(
    messages: list[dict[str, str]],
    system: str,
    model: str,
    api_key: str,
    max_tokens: int = 1024,
) -> str:
    """Call the Anthropic Messages API and return the text response."""
    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "The 'anthropic' package is required. Run: pip install anthropic"
        ) from exc

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _openai_complete(
    messages: list[dict[str, str]],
    system: str,
    model: str,
    api_key: str,
    max_tokens: int = 1024,
) -> str:
    """Call the OpenAI Chat Completions API and return the text response."""
    try:
        import openai  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' package is required. Run: pip install openai"
        ) from exc

    client = openai.OpenAI(api_key=api_key)
    all_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=model,
        messages=all_messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def _copilot_complete(
    messages: list[dict[str, str]],
    system: str,
    model: str,
    max_tokens: int = 1024,
) -> str:
    """Call the GitHub Copilot SDK and return the final assistant response."""
    try:
        from copilot import CopilotClient
        from copilot.session_events import AssistantMessageData, SessionIdleData
    except ImportError as exc:
        raise RuntimeError(
            "The 'github-copilot-sdk' package is required. "
            "Run: pip install github-copilot-sdk"
        ) from exc

    async def complete() -> str:
        reply = ""
        done = asyncio.Event()
        transcript = "\n\n".join(
            f"{message['role'].upper()}: {message['content']}"
            for message in messages
        )

        async with CopilotClient(
            mode="empty", base_directory=os.path.expanduser("~/.copilot")
        ) as client:
            async with await client.create_session(
                model=model,
                system_message={"mode": "append", "content": system},
                infinite_sessions={"enabled": False},
                available_tools=[],
            ) as session:
                def on_event(event: Any) -> None:
                    nonlocal reply
                    if isinstance(event.data, AssistantMessageData):
                        reply = event.data.content
                    elif isinstance(event.data, SessionIdleData):
                        done.set()

                session.on(on_event)
                await session.send(transcript)
                await done.wait()
        return reply

    return asyncio.run(complete())


# ---------------------------------------------------------------------------
# Main DM class
# ---------------------------------------------------------------------------


class AIDungeonMaster:
    """AI-powered Dungeon Master for Gates of Krystalia.

    Usage::

        config = load_config()
        dm = AIDungeonMaster(config)
        dm.load_context(campaign, current_location, active_persona, ruleset)
        response = dm.narrate("The party enters the ancient temple.")
    """

    _MAX_HISTORY = 20  # message pairs kept in rolling context window

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        ai_cfg = config.get("ai", {})
        self.provider: str = ai_cfg.get("provider", "anthropic")
        self.model: str = ai_cfg.get("model", "claude-opus-4-5")
        self.api_key: str = ai_cfg.get("api_key", "")
        self.system_prompt: str = ai_cfg.get(
            "system_prompt",
            "You are the AI Dungeon Master for Gates of Krystalia.",
        )
        self._history: list[dict[str, str]] = []
        self._context_block: str = ""

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def load_context(
        self,
        campaign: Any | None = None,
        location: Any | None = None,
        persona: Any | None = None,
        ruleset: Any | None = None,
        extra: str = "",
    ) -> None:
        """Build a system-level context block from game objects."""
        parts: list[str] = []

        if campaign:
            parts.append(
                f"CAMPAIGN: {campaign.name}\n{campaign.description}\n"
                f"Active quests: {[q['title'] for q in campaign.quests if q.get('status') == 'active']}"
            )
        if location:
            parts.append(
                f"CURRENT LOCATION: {location.name} ({location.location_type})\n"
                f"{location.description}"
            )
        if persona:
            parts.append(
                f"ACTIVE CHARACTER: {persona.name} (Level {persona.level} {persona.character_class})\n"
                f"HP: {persona.hit_points_current}/{persona.hit_points_max}  "
                f"Conditions: {persona.conditions or 'none'}"
            )
        if ruleset:
            parts.append(f"RULESET: {ruleset.name} v{ruleset.version}")
        if extra:
            parts.append(extra)

        self._context_block = "\n\n---\n\n".join(parts)

    def _build_system(self) -> str:
        base = self.system_prompt
        if self._context_block:
            base += f"\n\n=== CURRENT GAME CONTEXT ===\n{self._context_block}"
        return base

    # ------------------------------------------------------------------
    # Core LLM call
    # ------------------------------------------------------------------

    def _complete(self, user_message: str, max_tokens: int = 1024) -> str:
        """Send a message to the configured LLM backend and return the reply."""
        if self.provider != "copilot" and not self.api_key:
            return (
                "[AI DM unavailable – no API key configured. "
                "Set the relevant env variable in config.json.]"
            )

        self._history.append({"role": "user", "content": user_message})

        system = self._build_system()
        if self.provider == "anthropic":
            reply = _anthropic_complete(
                self._history, system, self.model, self.api_key, max_tokens
            )
        elif self.provider == "openai":
            reply = _openai_complete(
                self._history, system, self.model, self.api_key, max_tokens
            )
        elif self.provider == "copilot":
            reply = _copilot_complete(
                self._history, system, self.model, max_tokens
            )
        else:
            raise ValueError(f"Unknown AI provider: {self.provider!r}")

        self._history.append({"role": "assistant", "content": reply})
        # Trim rolling window after both messages are appended so the cap
        # is respected precisely (trimming before the assistant reply would
        # leave history at MAX*2 + 1 entries on every trimmed call).
        if len(self._history) > self._MAX_HISTORY * 2:
            self._history = self._history[-(self._MAX_HISTORY * 2):]
        return reply

    # ------------------------------------------------------------------
    # High-level DM actions
    # ------------------------------------------------------------------

    def narrate(self, prompt: str) -> str:
        """Generate narrative text for a given situation or player action."""
        return self._complete(prompt)

    def describe_scene(self, location_name: str, atmosphere: str = "") -> str:
        """Generate a vivid scene description for the given location."""
        msg = f"Describe the scene as the character arrives at: {location_name}."
        if atmosphere:
            msg += f" Atmosphere: {atmosphere}."
        return self._complete(msg)

    def roll_oracle(self, question: str, likelihood: str = "50/50") -> str:
        """Ask a yes/no fate oracle question and return a DM ruling with narration."""
        msg = (
            f"Solo oracle question ({likelihood} likelihood): {question}\n"
            "Answer yes or no, then briefly narrate what happens."
        )
        return self._complete(msg)

    def adjudicate(self, rule_situation: str) -> str:
        """Adjudicate a rules question in context of the current campaign."""
        return self._complete(
            f"Rules adjudication needed: {rule_situation}\n"
            "Give a fair ruling based on the Gates of Krystalia ruleset."
        )

    def generate_npc(self, role: str, context: str = "") -> str:
        """Generate an NPC with a name, personality, and hook."""
        msg = f"Generate an NPC for the role: {role}."
        if context:
            msg += f" Context: {context}."
        msg += " Include name, appearance, personality, and a plot hook."
        return self._complete(msg)

    def generate_encounter(self, location: str, difficulty: str = "moderate") -> str:
        """Generate a random encounter appropriate for the current situation."""
        return self._complete(
            f"Generate a {difficulty} encounter for: {location}.\n"
            "Include setup, enemies or complication, and suggested outcomes."
        )

    def summarise_session(self, log: NotationLog) -> str:
        """Produce a concise session summary from a notation log."""
        log_text = log.to_text()
        return self._complete(
            f"Write a concise in-world session summary (2-4 paragraphs) based on "
            f"this session log:\n\n{log_text}"
        )

    def suggest_image_prompt(self, scene_description: str) -> str:
        """Generate an image generation prompt for the given scene."""
        return self._complete(
            f"Write a concise image generation prompt (max 200 words) for: "
            f"{scene_description}\n"
            "Style: fantasy digital painting, Gates of Krystalia aesthetic."
        )

    # ------------------------------------------------------------------
    # Context reset
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        """Clear the rolling conversation history."""
        self._history = []
