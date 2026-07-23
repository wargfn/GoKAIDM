"""
Location persistence for GoKAIDM.

Locations represent places in the world of Gates of Krystalia.
Each location can be connected to other locations and may hold
events, NPCs, items of interest, and secrets.
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
class Location:
    """A world location in a Gates of Krystalia campaign."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    location_type: str = "settlement"   # dungeon, wilderness, settlement, ruin, etc.
    region: str = ""
    description: str = ""
    atmosphere: str = ""                # mood / atmosphere notes

    # Connected location IDs → direction / description
    connections: dict[str, str] = field(default_factory=dict)

    # Notable NPCs present (persona IDs)
    npc_ids: list[str] = field(default_factory=list)

    # Points of interest within this location
    points_of_interest: list[dict[str, Any]] = field(default_factory=list)

    # Events that have occurred here
    events: list[dict[str, Any]] = field(default_factory=list)

    # Secrets / hidden info unlocked by exploration or skill checks
    secrets: list[dict[str, Any]] = field(default_factory=list)

    # Tags for quick filtering (e.g. "dangerous", "market", "dungeon-level-1")
    tags: list[str] = field(default_factory=list)

    image_url: str = ""   # generated scene illustration

    campaign_id: str = ""

    explored: bool = False
    visited_count: int = 0

    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def connect(self, other_location_id: str, description: str = "") -> None:
        """Create a one-way connection to *other_location_id*."""
        self.connections[other_location_id] = description

    def disconnect(self, other_location_id: str) -> bool:
        if other_location_id in self.connections:
            del self.connections[other_location_id]
            return True
        return False

    def add_point_of_interest(
        self, name: str, description: str = "", poi_type: str = "general"
    ) -> dict[str, Any]:
        poi: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "type": poi_type,
            "discovered": False,
        }
        self.points_of_interest.append(poi)
        return poi

    def add_event(self, description: str, event_type: str = "general") -> dict[str, Any]:
        evt: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "description": description,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(evt)
        return evt

    def add_secret(self, description: str, reveal_condition: str = "") -> dict[str, Any]:
        secret: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "description": description,
            "reveal_condition": reveal_condition,
            "revealed": False,
        }
        self.secrets.append(secret)
        return secret

    def visit(self) -> None:
        """Increment visited count and mark as explored."""
        self.visited_count += 1
        if not self.explored:
            self.explored = True

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Location":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Persistence store
# ---------------------------------------------------------------------------


class LocationStore:
    """JSON-backed store for :class:`Location` objects.

    Files live at ``<data_dir>/locations/<id>.json``.
    """

    def __init__(self, data_dir: str | Path = "./data") -> None:
        self.root = Path(data_dir) / "locations"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, location: Location) -> None:
        location.touch()
        path = self.root / f"{location.id}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(location.to_dict(), fh, indent=2, ensure_ascii=False)

    def load(self, location_id: str) -> Location:
        path = self.root / f"{location_id}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"Location '{location_id}' not found in {self.root}"
            )
        with path.open("r", encoding="utf-8") as fh:
            return Location.from_dict(json.load(fh))

    def load_by_name(self, name: str) -> Location:
        for location in self.list_all():
            if location.name.lower() == name.lower():
                return location
        raise FileNotFoundError(f"Location named '{name}' not found.")

    def delete(self, location_id: str) -> bool:
        path = self.root / f"{location_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(
        self,
        campaign_id: str | None = None,
        location_type: str | None = None,
    ) -> list[Location]:
        locations: list[Location] = []
        for p in self.root.glob("*.json"):
            with p.open("r", encoding="utf-8") as fh:
                try:
                    loc = Location.from_dict(json.load(fh))
                    if campaign_id and loc.campaign_id != campaign_id:
                        continue
                    if location_type and loc.location_type != location_type:
                        continue
                    locations.append(loc)
                except (KeyError, TypeError):
                    continue
        return sorted(locations, key=lambda l: l.created_at)

    def exists(self, location_id: str) -> bool:
        return (self.root / f"{location_id}.json").exists()
