"""
Persona persistence for GoKAIDM.

Personas represent player characters (PCs) and non-player characters (NPCs).
Each persona tracks stats, inventory, backstory, relationships, and a simple
condition/status block compatible with the Gates of Krystalia ruleset.
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
class Persona:
    """A player character or NPC in a Gates of Krystalia campaign."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    persona_type: str = "pc"          # "pc" | "npc" | "creature"
    race: str = ""
    character_class: str = ""
    level: int = 1
    experience: int = 0

    # Core attribute block – keys follow GoK conventions
    attributes: dict[str, int] = field(default_factory=lambda: {
        "strength": 10,
        "dexterity": 10,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
    })

    # Derived / tracked values
    hit_points_max: int = 10
    hit_points_current: int = 10
    armor_class: int = 10
    speed: int = 30

    # Skills: dict mapping skill name → proficiency level (0 = none, 1 = proficient, 2 = expert)
    skills: dict[str, int] = field(default_factory=dict)

    # Inventory items
    inventory: list[dict[str, Any]] = field(default_factory=list)

    # Conditions / status effects
    conditions: list[str] = field(default_factory=list)

    backstory: str = ""
    notes: str = ""
    portrait_url: str = ""   # URL or file path to generated portrait

    # Relationships: list of {"persona_id": ..., "relationship": "friend/enemy/..."}
    relationships: list[dict[str, Any]] = field(default_factory=list)

    campaign_id: str = ""

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

    def add_inventory_item(
        self,
        name: str,
        quantity: int = 1,
        description: str = "",
        item_type: str = "misc",
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "name": name,
            "quantity": quantity,
            "description": description,
            "type": item_type,
        }
        self.inventory.append(item)
        return item

    def remove_inventory_item(self, item_id: str) -> bool:
        for i, item in enumerate(self.inventory):
            if item.get("id") == item_id:
                self.inventory.pop(i)
                return True
        return False

    def heal(self, amount: int) -> int:
        self.hit_points_current = min(
            self.hit_points_current + amount, self.hit_points_max
        )
        return self.hit_points_current

    def take_damage(self, amount: int) -> int:
        self.hit_points_current = max(self.hit_points_current - amount, 0)
        return self.hit_points_current

    @property
    def is_alive(self) -> bool:
        return self.hit_points_current > 0

    def add_condition(self, condition: str) -> None:
        if condition not in self.conditions:
            self.conditions.append(condition)

    def remove_condition(self, condition: str) -> bool:
        if condition in self.conditions:
            self.conditions.remove(condition)
            return True
        return False

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Persona":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Persistence store
# ---------------------------------------------------------------------------


class PersonaStore:
    """JSON-backed store for :class:`Persona` objects.

    Files live at ``<data_dir>/personas/<id>.json``.
    """

    def __init__(self, data_dir: str | Path = "./data") -> None:
        self.root = Path(data_dir) / "personas"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, persona: Persona) -> None:
        persona.touch()
        path = self.root / f"{persona.id}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(persona.to_dict(), fh, indent=2, ensure_ascii=False)

    def load(self, persona_id: str) -> Persona:
        path = self.root / f"{persona_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Persona '{persona_id}' not found in {self.root}")
        with path.open("r", encoding="utf-8") as fh:
            return Persona.from_dict(json.load(fh))

    def load_by_name(self, name: str) -> Persona:
        for persona in self.list_all():
            if persona.name.lower() == name.lower():
                return persona
        raise FileNotFoundError(f"Persona named '{name}' not found.")

    def delete(self, persona_id: str) -> bool:
        path = self.root / f"{persona_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self, campaign_id: str | None = None) -> list[Persona]:
        """Return personas, optionally filtered by campaign."""
        personas: list[Persona] = []
        for p in self.root.glob("*.json"):
            with p.open("r", encoding="utf-8") as fh:
                try:
                    persona = Persona.from_dict(json.load(fh))
                    if campaign_id is None or persona.campaign_id == campaign_id:
                        personas.append(persona)
                except (KeyError, TypeError):
                    continue
        return sorted(personas, key=lambda p: p.created_at)

    def exists(self, persona_id: str) -> bool:
        return (self.root / f"{persona_id}.json").exists()
