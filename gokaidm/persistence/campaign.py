"""
Campaign persistence for GoKAIDM.

A Campaign is the top-level container that binds together a Ruleset,
a set of Personas, a set of Locations, and a log of Sessions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Campaign:
    """Represents a single Gates of Krystalia campaign."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    ruleset_id: str = ""
    persona_ids: list[str] = field(default_factory=list)
    location_ids: list[str] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)
    active_location_id: str = ""
    active_persona_id: str = ""
    quests: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Quest helpers
    # ------------------------------------------------------------------

    def add_quest(self, title: str, description: str = "", status: str = "active") -> dict[str, Any]:
        """Add a new quest and return the quest dict."""
        quest: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.quests.append(quest)
        return quest

    def complete_quest(self, quest_id: str) -> bool:
        """Mark a quest as completed. Returns True if found."""
        for quest in self.quests:
            if quest["id"] == quest_id:
                quest["status"] = "completed"
                return True
        return False

    def touch(self) -> None:
        """Update the ``updated_at`` timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Campaign":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Persistence store
# ---------------------------------------------------------------------------


class CampaignStore:
    """JSON-backed store for :class:`Campaign` objects.

    Files live at ``<data_dir>/campaigns/<id>.json``.
    """

    def __init__(self, data_dir: str | Path = "./data") -> None:
        self.root = Path(data_dir) / "campaigns"
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save(self, campaign: Campaign) -> None:
        """Persist a campaign to disk."""
        campaign.touch()
        path = self.root / f"{campaign.id}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(campaign.to_dict(), fh, indent=2, ensure_ascii=False)

    def load(self, campaign_id: str) -> Campaign:
        """Load a campaign by ID. Raises :exc:`FileNotFoundError` if missing."""
        path = self.root / f"{campaign_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Campaign '{campaign_id}' not found in {self.root}")
        with path.open("r", encoding="utf-8") as fh:
            return Campaign.from_dict(json.load(fh))

    def load_by_name(self, name: str) -> Campaign:
        """Load the first campaign whose name matches (case-insensitive)."""
        for campaign in self.list_all():
            if campaign.name.lower() == name.lower():
                return campaign
        raise FileNotFoundError(f"Campaign named '{name}' not found.")

    def delete(self, campaign_id: str) -> bool:
        """Delete a campaign. Returns True if deleted."""
        path = self.root / f"{campaign_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> list[Campaign]:
        """Return all campaigns sorted by creation time (oldest first)."""
        campaigns: list[Campaign] = []
        for p in self.root.glob("*.json"):
            with p.open("r", encoding="utf-8") as fh:
                try:
                    campaigns.append(Campaign.from_dict(json.load(fh)))
                except (KeyError, TypeError):
                    continue
        return sorted(campaigns, key=lambda c: c.created_at)

    def exists(self, campaign_id: str) -> bool:
        return (self.root / f"{campaign_id}.json").exists()
