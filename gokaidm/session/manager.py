"""
Session management for GoKAIDM.

Supports both solo play (single player, solo notation format) and
group play (multiple participants, same underlying notation format).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gokaidm.session.notation import NotationLog, NotationEntry, EntryType


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SessionParticipant:
    """A participant in a session (solo player or group member)."""

    persona_id: str = ""
    player_name: str = ""    # real-world player name; empty for AI-controlled
    is_player_character: bool = True


@dataclass
class Session:
    """A single play session within a campaign."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str = ""
    title: str = ""
    session_type: str = "solo"          # "solo" | "group"
    session_number: int = 1

    participants: list[dict[str, Any]] = field(default_factory=list)

    # Solo notation log – stored as a list of dicts for JSON serialisation
    log: list[dict[str, Any]] = field(default_factory=list)

    # Quick-access fields populated at the start/end of sessions
    scene_count: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: str = ""
    summary: str = ""
    notes: str = ""

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def get_log(self) -> NotationLog:
        """Return the session log as a :class:`NotationLog`."""
        return NotationLog.from_list(self.log)

    def set_log(self, log: NotationLog) -> None:
        self.log = log.to_list()

    def add_participant(self, persona_id: str, player_name: str = "", is_pc: bool = True) -> None:
        participant = SessionParticipant(
            persona_id=persona_id,
            player_name=player_name,
            is_player_character=is_pc,
        )
        self.participants.append(asdict(participant))

    def end_session(self, summary: str = "") -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()
        if summary:
            self.summary = summary

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Persistence store
# ---------------------------------------------------------------------------


class SessionStore:
    """JSON-backed store for :class:`Session` objects.

    Files live at ``<data_dir>/sessions/<id>.json``.
    A plain-text notation log is co-located at ``<data_dir>/sessions/<id>.txt``.
    """

    def __init__(self, data_dir: str | Path = "./data") -> None:
        self.root = Path(data_dir) / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, session: Session) -> None:
        session.touch()
        path = self.root / f"{session.id}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(session.to_dict(), fh, indent=2, ensure_ascii=False)
        # Also write human-readable notation log
        log = session.get_log()
        txt_path = self.root / f"{session.id}.txt"
        log.save_text(txt_path)

    def load(self, session_id: str) -> Session:
        path = self.root / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session '{session_id}' not found in {self.root}")
        with path.open("r", encoding="utf-8") as fh:
            return Session.from_dict(json.load(fh))

    def delete(self, session_id: str) -> bool:
        removed = False
        for ext in (".json", ".txt"):
            path = self.root / f"{session_id}{ext}"
            if path.exists():
                path.unlink()
                removed = True
        return removed

    def list_all(self, campaign_id: str | None = None) -> list[Session]:
        sessions: list[Session] = []
        for p in self.root.glob("*.json"):
            with p.open("r", encoding="utf-8") as fh:
                try:
                    s = Session.from_dict(json.load(fh))
                    if campaign_id is None or s.campaign_id == campaign_id:
                        sessions.append(s)
                except (KeyError, TypeError):
                    continue
        return sorted(sessions, key=lambda s: s.session_number)

    def exists(self, session_id: str) -> bool:
        return (self.root / f"{session_id}.json").exists()


# ---------------------------------------------------------------------------
# Session manager – high-level API used by CLI and AI DM
# ---------------------------------------------------------------------------


class SessionManager:
    """High-level interface for starting, running, and ending sessions.

    Wraps :class:`SessionStore` and :class:`NotationLog` to provide a
    convenient API for the CLI and AI DM components.
    """

    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self._active_session: Session | None = None
        self._active_log: NotationLog | None = None

    @property
    def active_session(self) -> Session | None:
        return self._active_session

    def start_session(
        self,
        campaign_id: str,
        title: str = "",
        session_type: str = "solo",
        session_number: int = 1,
        participants: list[dict[str, Any]] | None = None,
    ) -> Session:
        """Create and activate a new session, returning it."""
        session = Session(
            campaign_id=campaign_id,
            title=title or f"Session {session_number}",
            session_type=session_type,
            session_number=session_number,
            participants=participants or [],
        )
        log = NotationLog()
        log.add(EntryType.SCENE, f"Session '{session.title}' begins.", actor="DM")
        session.set_log(log)
        self.store.save(session)
        self._active_session = session
        self._active_log = log
        return session

    def resume_session(self, session_id: str) -> Session:
        """Load and re-activate an existing session."""
        session = self.store.load(session_id)
        self._active_session = session
        self._active_log = session.get_log()
        return session

    def append_entry(
        self,
        entry_type: str | EntryType,
        content: str,
        actor: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> NotationEntry:
        """Add a notation entry to the active session and auto-save."""
        if self._active_session is None or self._active_log is None:
            raise RuntimeError("No active session. Call start_session() first.")
        entry = self._active_log.add(entry_type, content, actor=actor, metadata=metadata or {})
        if entry_type in (EntryType.SCENE, EntryType.SCENE.value):
            self._active_session.scene_count += 1
        self._active_session.set_log(self._active_log)
        self.store.save(self._active_session)
        return entry

    def end_session(self, summary: str = "") -> Session:
        """End the active session, writing a summary entry."""
        if self._active_session is None or self._active_log is None:
            raise RuntimeError("No active session.")
        self._active_log.add(EntryType.NOTE, f"Session ended. {summary}".strip(), actor="DM")
        self._active_session.set_log(self._active_log)
        self._active_session.end_session(summary)
        self.store.save(self._active_session)
        session = self._active_session
        self._active_session = None
        self._active_log = None
        return session

    def get_log_text(self) -> str:
        """Return the active session's notation log as formatted text."""
        if self._active_log is None:
            raise RuntimeError("No active session.")
        return self._active_log.to_text()

    def get_active_log(self) -> NotationLog:
        """Return the active session's :class:`NotationLog`.

        Raises :exc:`RuntimeError` if no session is currently active.
        """
        if self._active_log is None:
            raise RuntimeError("No active session.")
        return self._active_log
