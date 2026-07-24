"""Tests for the AI DM module (no real API calls)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gokaidm.ai.dm import AIDungeonMaster
from gokaidm.session.notation import NotationLog, EntryType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(provider: str = "anthropic", api_key: str = "sk-test") -> dict:
    return {
        "ai": {
            "provider": provider,
            "model": "claude-opus-4-5",
            "api_key": api_key,
            "system_prompt": "You are a DM.",
        }
    }


@pytest.fixture
def dm() -> AIDungeonMaster:
    return AIDungeonMaster(_make_config())


@pytest.fixture
def dm_no_key() -> AIDungeonMaster:
    return AIDungeonMaster(_make_config(api_key=""))


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def test_dm_init(dm: AIDungeonMaster) -> None:
    assert dm.provider == "anthropic"
    assert dm.model == "claude-opus-4-5"
    assert dm.api_key == "sk-test"


def test_dm_no_key_returns_placeholder(dm_no_key: AIDungeonMaster) -> None:
    result = dm_no_key.narrate("The door creaks open.")
    assert "unavailable" in result.lower() or "no API key" in result


# ---------------------------------------------------------------------------
# Context loading
# ---------------------------------------------------------------------------


def test_load_context_campaign() -> None:
    dm = AIDungeonMaster(_make_config(api_key=""))

    campaign = MagicMock()
    campaign.name = "Test Campaign"
    campaign.description = "A dark world."
    campaign.quests = [{"title": "Find the ring", "status": "active"}]

    dm.load_context(campaign=campaign)
    assert "Test Campaign" in dm._context_block


def test_load_context_location() -> None:
    dm = AIDungeonMaster(_make_config(api_key=""))

    location = MagicMock()
    location.name = "Dark Forest"
    location.location_type = "wilderness"
    location.description = "Thick ancient trees."

    dm.load_context(location=location)
    assert "Dark Forest" in dm._context_block


def test_load_context_persona() -> None:
    dm = AIDungeonMaster(_make_config(api_key=""))

    persona = MagicMock()
    persona.name = "Aria"
    persona.level = 5
    persona.character_class = "Ranger"
    persona.hit_points_current = 30
    persona.hit_points_max = 40
    persona.conditions = ["poisoned"]

    dm.load_context(persona=persona)
    assert "Aria" in dm._context_block
    assert "poisoned" in dm._context_block


def test_load_context_ruleset() -> None:
    dm = AIDungeonMaster(_make_config(api_key=""))

    ruleset = MagicMock()
    ruleset.name = "Core Rules"
    ruleset.version = "1.0"

    dm.load_context(ruleset=ruleset)
    assert "Core Rules" in dm._context_block


# ---------------------------------------------------------------------------
# API calls (mocked)
# ---------------------------------------------------------------------------


def test_narrate_anthropic(dm: AIDungeonMaster) -> None:
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="The door swings open.") as mock_call:
        result = dm.narrate("Open the door.")
    mock_call.assert_called_once()
    assert result == "The door swings open."


def test_narrate_openai() -> None:
    dm = AIDungeonMaster(_make_config(provider="openai"))
    with patch("gokaidm.ai.dm._openai_complete", return_value="The wind howls.") as mock_call:
        result = dm.narrate("Describe the weather.")
    assert result == "The wind howls."


def test_narrate_copilot_without_api_key() -> None:
    dm = AIDungeonMaster(_make_config(provider="copilot", api_key=""))
    with patch(
        "gokaidm.ai.dm._copilot_complete", return_value="The torches flare."
    ) as mock_call:
        result = dm.narrate("Enter the hall.")
    mock_call.assert_called_once()
    assert result == "The torches flare."


def test_describe_scene(dm: AIDungeonMaster) -> None:
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="A cold stone chamber."):
        result = dm.describe_scene("Ancient Temple", atmosphere="eerie")
    assert "cold stone" in result


def test_roll_oracle(dm: AIDungeonMaster) -> None:
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="Yes. The guard dozes off."):
        result = dm.roll_oracle("Is the guard asleep?", likelihood="likely")
    assert "guard" in result


def test_adjudicate(dm: AIDungeonMaster) -> None:
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="You succeed with a DC 12."):
        result = dm.adjudicate("Can I climb this wall with no rope?")
    assert "succeed" in result


def test_generate_npc(dm: AIDungeonMaster) -> None:
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="Mira, a cautious herbalist."):
        result = dm.generate_npc("herbalist shopkeeper")
    assert "Mira" in result


def test_generate_encounter(dm: AIDungeonMaster) -> None:
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="3 goblins ambush the party."):
        result = dm.generate_encounter("forest path", difficulty="easy")
    assert "goblins" in result


def test_summarise_session(dm: AIDungeonMaster) -> None:
    log = NotationLog()
    log.add(EntryType.DM, "Party entered the cave.")
    log.add(EntryType.ACTION, "Aria fought the spider.", actor="Aria")
    log.add(EntryType.DM, "Victory! Treasure found.")

    with patch("gokaidm.ai.dm._anthropic_complete", return_value="Session summary: brave heroes."):
        result = dm.summarise_session(log)
    assert "summary" in result.lower()


def test_suggest_image_prompt(dm: AIDungeonMaster) -> None:
    with patch(
        "gokaidm.ai.dm._anthropic_complete",
        return_value="A dark forest clearing, moonlit, fantasy art.",
    ):
        result = dm.suggest_image_prompt("Moonlit clearing in a dark forest")
    assert "forest" in result.lower()


# ---------------------------------------------------------------------------
# History trimming
# ---------------------------------------------------------------------------


def test_history_trimming() -> None:
    dm = AIDungeonMaster(_make_config())
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="reply"):
        for _ in range(25):
            dm.narrate("prompt")
    assert len(dm._history) <= dm._MAX_HISTORY * 2


def test_clear_history(dm: AIDungeonMaster) -> None:
    with patch("gokaidm.ai.dm._anthropic_complete", return_value="reply"):
        dm.narrate("test")
    assert len(dm._history) > 0
    dm.clear_history()
    assert dm._history == []


# ---------------------------------------------------------------------------
# Unknown provider
# ---------------------------------------------------------------------------


def test_unknown_provider_raises() -> None:
    dm = AIDungeonMaster(_make_config())
    dm.provider = "unknown-provider"
    with pytest.raises(ValueError, match="Unknown AI provider"):
        dm.narrate("test")
