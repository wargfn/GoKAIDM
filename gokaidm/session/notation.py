"""
Solo Notation Format for GoKAIDM.

Each entry follows the Solo Oracle Notation (SON) convention:

    [YYYY-MM-DD HH:MM] <TYPE> | <ACTOR> | <CONTENT>

Entry types
-----------
SCENE   – scene description or scene change
ACTION  – a player / character action
ORACLE  – oracle / fate question + answer
DM      – AI DM narration or ruling
NOTE    – meta note (player thought, bookkeeping)
IMAGE   – inline image reference (URL or path)
ROLL    – dice roll result
DIALOGUE – in-character dialogue
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class EntryType(str, Enum):
    SCENE = "SCENE"
    ACTION = "ACTION"
    ORACLE = "ORACLE"
    DM = "DM"
    NOTE = "NOTE"
    IMAGE = "IMAGE"
    ROLL = "ROLL"
    DIALOGUE = "DIALOGUE"


# Regex to parse plain-text notation lines back into structured form
_NOTATION_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\]\s+(?P<etype>[A-Z]+)\s*\|\s*(?P<actor>[^|]*)\|\s*(?P<content>.+)$"
)


@dataclass
class NotationEntry:
    """A single entry in a solo notation log."""

    entry_type: str = EntryType.NOTE.value
    actor: str = ""        # Who is performing the action / speaking
    content: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        """Render as a single-line solo notation string."""
        ts = self._format_ts()
        actor = self.actor or "—"
        content = self.content.replace("\n", " ")
        return f"[{ts}] {self.entry_type} | {actor} | {content}"

    def _format_ts(self) -> str:
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return self.timestamp

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotationEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_text(cls, line: str) -> "NotationEntry | None":
        """Parse a notation line back into a :class:`NotationEntry`.

        Returns ``None`` if the line does not match the expected format.
        """
        m = _NOTATION_RE.match(line.strip())
        if not m:
            return None
        return cls(
            entry_type=m.group("etype"),
            actor=m.group("actor").strip(),
            content=m.group("content").strip(),
            timestamp=m.group("ts").strip(),
        )


class NotationLog:
    """An ordered list of :class:`NotationEntry` objects for a session."""

    def __init__(self) -> None:
        self._entries: list[NotationEntry] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def append(self, entry: NotationEntry) -> None:
        self._entries.append(entry)

    def add(
        self,
        entry_type: str | EntryType,
        content: str,
        actor: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> NotationEntry:
        """Create and append a new entry, returning it."""
        entry = NotationEntry(
            entry_type=EntryType(entry_type).value if isinstance(entry_type, str) else entry_type.value,
            actor=actor,
            content=content,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        return entry

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def entries(self) -> list[NotationEntry]:
        return list(self._entries)

    def filter_by_type(self, entry_type: str | EntryType) -> list[NotationEntry]:
        t = EntryType(entry_type).value if isinstance(entry_type, str) else entry_type.value
        return [e for e in self._entries if e.entry_type == t]

    def last_n(self, n: int) -> list[NotationEntry]:
        return self._entries[-n:]

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Text rendering
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        """Render entire log as a newline-separated notation string."""
        return "\n".join(e.to_text() for e in self._entries)

    def save_text(self, path: str | Path) -> None:
        """Write the plain-text notation log to *path*."""
        Path(path).write_text(self.to_text(), encoding="utf-8")

    @classmethod
    def load_text(cls, path: str | Path) -> "NotationLog":
        """Load a plain-text notation log from *path*."""
        log = cls()
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            entry = NotationEntry.from_text(line)
            if entry is not None:
                log.append(entry)
        return log

    # ------------------------------------------------------------------
    # JSON serialisation (used by SessionStore)
    # ------------------------------------------------------------------

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._entries]

    @classmethod
    def from_list(cls, data: list[dict[str, Any]]) -> "NotationLog":
        log = cls()
        for item in data:
            log.append(NotationEntry.from_dict(item))
        return log
