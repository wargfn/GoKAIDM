"""
Ruleset persistence for GoKAIDM.

A Ruleset holds the rules reference used in a campaign.  Rules can be
loaded from JSON directly or extracted from a PDF via the PDF loader.
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
class RuleEntry:
    """A single rule or lore entry within a Ruleset."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    title: str = ""
    content: str = ""
    source: str = ""   # e.g. "Player's Handbook p.42" or "PDF:filename.pdf:12"
    tags: list[str] = field(default_factory=list)


@dataclass
class Ruleset:
    """A named collection of :class:`RuleEntry` objects."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Gates of Krystalia Core"
    version: str = "1.0"
    description: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Entry helpers
    # ------------------------------------------------------------------

    def add_entry(
        self,
        title: str,
        content: str,
        category: str = "general",
        source: str = "",
        tags: list[str] | None = None,
    ) -> RuleEntry:
        entry = RuleEntry(
            title=title,
            content=content,
            category=category,
            source=source,
            tags=tags or [],
        )
        self.entries.append(asdict(entry))
        return entry

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return entries whose title or content contains *query* (case-insensitive)."""
        q = query.lower()
        return [
            e for e in self.entries
            if q in e.get("title", "").lower() or q in e.get("content", "").lower()
        ]

    def categories(self) -> list[str]:
        """Return a sorted, deduplicated list of categories."""
        return sorted({e.get("category", "") for e in self.entries})

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ruleset":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Persistence store
# ---------------------------------------------------------------------------


class RulesetStore:
    """JSON-backed store for :class:`Ruleset` objects.

    Files live at ``<data_dir>/rulesets/<id>.json``.
    """

    def __init__(self, data_dir: str | Path = "./data") -> None:
        self.root = Path(data_dir) / "rulesets"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, ruleset: Ruleset) -> None:
        ruleset.touch()
        path = self.root / f"{ruleset.id}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(ruleset.to_dict(), fh, indent=2, ensure_ascii=False)

    def load(self, ruleset_id: str) -> Ruleset:
        path = self.root / f"{ruleset_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Ruleset '{ruleset_id}' not found in {self.root}")
        with path.open("r", encoding="utf-8") as fh:
            return Ruleset.from_dict(json.load(fh))

    def load_by_name(self, name: str) -> Ruleset:
        for ruleset in self.list_all():
            if ruleset.name.lower() == name.lower():
                return ruleset
        raise FileNotFoundError(f"Ruleset named '{name}' not found.")

    def delete(self, ruleset_id: str) -> bool:
        path = self.root / f"{ruleset_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> list[Ruleset]:
        rulesets: list[Ruleset] = []
        for p in self.root.glob("*.json"):
            with p.open("r", encoding="utf-8") as fh:
                try:
                    rulesets.append(Ruleset.from_dict(json.load(fh)))
                except (KeyError, TypeError):
                    continue
        return sorted(rulesets, key=lambda r: r.created_at)

    def exists(self, ruleset_id: str) -> bool:
        return (self.root / f"{ruleset_id}.json").exists()
