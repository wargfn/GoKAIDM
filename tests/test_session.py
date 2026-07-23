"""Tests for session management and solo notation format."""

from __future__ import annotations

from pathlib import Path

import pytest

from gokaidm.session.notation import NotationEntry, NotationLog, EntryType
from gokaidm.session.manager import Session, SessionStore, SessionManager


# ---------------------------------------------------------------------------
# EntryType
# ---------------------------------------------------------------------------


def test_entry_type_values() -> None:
    assert EntryType.SCENE.value == "SCENE"
    assert EntryType.DM.value == "DM"
    assert EntryType.ACTION.value == "ACTION"


# ---------------------------------------------------------------------------
# NotationEntry
# ---------------------------------------------------------------------------


def test_notation_entry_defaults() -> None:
    e = NotationEntry()
    assert e.entry_type == EntryType.NOTE.value
    assert e.actor == ""
    assert e.content == ""


def test_notation_entry_to_text() -> None:
    e = NotationEntry(
        entry_type="DM",
        actor="AI DM",
        content="The goblin lunges forward.",
        timestamp="2025-01-15T10:30:00+00:00",
    )
    text = e.to_text()
    assert "[2025-01-15 10:30]" in text
    assert "DM" in text
    assert "AI DM" in text
    assert "The goblin lunges forward." in text


def test_notation_entry_from_text_roundtrip() -> None:
    e = NotationEntry(
        entry_type="ACTION",
        actor="Aria",
        content="Draws her bow and aims at the wolf.",
        timestamp="2025-06-01T14:05:00+00:00",
    )
    line = e.to_text()
    parsed = NotationEntry.from_text(line)
    assert parsed is not None
    assert parsed.entry_type == "ACTION"
    assert parsed.actor == "Aria"
    assert "Draws her bow" in parsed.content


def test_notation_entry_from_text_invalid() -> None:
    assert NotationEntry.from_text("this is not a valid notation line") is None


def test_notation_entry_round_trip_dict() -> None:
    e = NotationEntry(entry_type="SCENE", actor="DM", content="Scene opens in a tavern.")
    d = e.to_dict()
    e2 = NotationEntry.from_dict(d)
    assert e2.content == "Scene opens in a tavern."


# ---------------------------------------------------------------------------
# NotationLog
# ---------------------------------------------------------------------------


def test_notation_log_add() -> None:
    log = NotationLog()
    log.add(EntryType.SCENE, "We begin in the dungeon.", actor="DM")
    assert len(log) == 1


def test_notation_log_filter_by_type() -> None:
    log = NotationLog()
    log.add(EntryType.DM, "Narration.", actor="DM")
    log.add(EntryType.ACTION, "Player action.", actor="Player")
    log.add(EntryType.DM, "Response.", actor="DM")
    dm_entries = log.filter_by_type(EntryType.DM)
    assert len(dm_entries) == 2


def test_notation_log_last_n() -> None:
    log = NotationLog()
    for i in range(5):
        log.add(EntryType.NOTE, f"Note {i}")
    assert len(log.last_n(3)) == 3


def test_notation_log_to_text() -> None:
    log = NotationLog()
    log.add(EntryType.DM, "Darkness fills the corridor.", actor="AI DM")
    text = log.to_text()
    assert "DM" in text
    assert "Darkness fills the corridor." in text


def test_notation_log_save_load_text(tmp_path: Path) -> None:
    log = NotationLog()
    log.add(EntryType.SCENE, "Session start.", actor="DM")
    log.add(EntryType.ACTION, "Player moves north.", actor="Aria")
    log.add(EntryType.DM, "You arrive at the bridge.", actor="AI DM")

    txt_file = tmp_path / "session.txt"
    log.save_text(txt_file)
    assert txt_file.exists()

    loaded = NotationLog.load_text(txt_file)
    assert len(loaded) == 3
    assert loaded.entries()[0].entry_type == "SCENE"


def test_notation_log_list_round_trip() -> None:
    log = NotationLog()
    log.add(EntryType.ORACLE, "Will the guard fall asleep?", actor="Player")
    log.add(EntryType.DM, "Yes! The guard slumps against the wall.", actor="DM")

    data = log.to_list()
    log2 = NotationLog.from_list(data)
    assert len(log2) == len(log)


# ---------------------------------------------------------------------------
# Session model
# ---------------------------------------------------------------------------


def test_session_defaults() -> None:
    s = Session(campaign_id="c1", title="Session 1")
    assert s.session_type == "solo"
    assert s.scene_count == 0
    assert s.ended_at == ""


def test_session_add_participant() -> None:
    s = Session(campaign_id="c1")
    s.add_participant("persona-1", player_name="Alice")
    assert len(s.participants) == 1
    assert s.participants[0]["player_name"] == "Alice"


def test_session_get_set_log() -> None:
    s = Session(campaign_id="c1")
    log = NotationLog()
    log.add(EntryType.SCENE, "A dark forest.")
    s.set_log(log)
    retrieved = s.get_log()
    assert len(retrieved) == 1


def test_session_end() -> None:
    s = Session(campaign_id="c1")
    s.end_session("The party rested at the inn.")
    assert s.ended_at != ""
    assert "rested" in s.summary


def test_session_round_trip() -> None:
    s = Session(campaign_id="c1", title="Test Session", session_type="group")
    s.add_participant("persona-1")
    d = s.to_dict()
    s2 = Session.from_dict(d)
    assert s2.id == s.id
    assert s2.session_type == "group"
    assert len(s2.participants) == 1


# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------


@pytest.fixture
def session_store(tmp_path: Path) -> SessionStore:
    return SessionStore(data_dir=tmp_path)


def test_session_store_save_load(session_store: SessionStore) -> None:
    s = Session(campaign_id="camp-1", title="First Session")
    log = NotationLog()
    log.add(EntryType.DM, "The adventure begins.")
    s.set_log(log)
    session_store.save(s)

    loaded = session_store.load(s.id)
    assert loaded.id == s.id
    assert len(loaded.get_log()) == 1


def test_session_store_text_file_created(session_store: SessionStore, tmp_path: Path) -> None:
    s = Session(campaign_id="c1")
    log = NotationLog()
    log.add(EntryType.DM, "Test entry.")
    s.set_log(log)
    session_store.save(s)

    txt_path = tmp_path / "sessions" / f"{s.id}.txt"
    assert txt_path.exists()


def test_session_store_delete(session_store: SessionStore) -> None:
    s = Session(campaign_id="c1")
    session_store.save(s)
    assert session_store.exists(s.id)
    session_store.delete(s.id)
    assert not session_store.exists(s.id)


def test_session_store_list_all(session_store: SessionStore) -> None:
    for i in range(3):
        s = Session(campaign_id="c1", session_number=i + 1)
        session_store.save(s)
    sessions = session_store.list_all(campaign_id="c1")
    assert len(sessions) == 3


def test_session_store_list_filtered(session_store: SessionStore) -> None:
    session_store.save(Session(campaign_id="camp-A"))
    session_store.save(Session(campaign_id="camp-B"))
    session_store.save(Session(campaign_id="camp-A"))
    assert len(session_store.list_all(campaign_id="camp-A")) == 2


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


@pytest.fixture
def session_manager(tmp_path: Path) -> SessionManager:
    store = SessionStore(data_dir=tmp_path)
    return SessionManager(store)


def test_manager_start_session(session_manager: SessionManager) -> None:
    s = session_manager.start_session("camp-1", title="Epic Start", session_type="solo")
    assert s.title == "Epic Start"
    assert session_manager.active_session is not None


def test_manager_append_entry(session_manager: SessionManager) -> None:
    session_manager.start_session("camp-1")
    entry = session_manager.append_entry(EntryType.ACTION, "Player draws sword.", actor="Aria")
    assert entry.content == "Player draws sword."


def test_manager_scene_count(session_manager: SessionManager) -> None:
    session_manager.start_session("camp-1")
    assert session_manager.active_session.scene_count == 0
    session_manager.append_entry(EntryType.SCENE, "New scene.")
    assert session_manager.active_session.scene_count == 1


def test_manager_end_session(session_manager: SessionManager) -> None:
    session_manager.start_session("camp-1")
    ended = session_manager.end_session("The party succeeded.")
    assert ended.ended_at != ""
    assert session_manager.active_session is None


def test_manager_no_active_session_raises(session_manager: SessionManager) -> None:
    with pytest.raises(RuntimeError):
        session_manager.append_entry(EntryType.DM, "No session!")


def test_manager_resume_session(session_manager: SessionManager) -> None:
    s = session_manager.start_session("camp-1", title="Original")
    session_id = s.id
    session_manager.end_session()

    resumed = session_manager.resume_session(session_id)
    assert resumed.id == session_id
    assert session_manager.active_session is not None


def test_manager_get_log_text(session_manager: SessionManager) -> None:
    session_manager.start_session("camp-1")
    session_manager.append_entry(EntryType.DM, "You see a dragon!")
    text = session_manager.get_log_text()
    assert "DM" in text
    assert "dragon" in text


def test_manager_get_active_log(session_manager: SessionManager) -> None:
    session_manager.start_session("camp-1")
    session_manager.append_entry(EntryType.DM, "A riddle appears.")
    log = session_manager.get_active_log()
    assert len(log) >= 1
    assert any("riddle" in e.content for e in log.entries())


def test_manager_get_active_log_no_session_raises(session_manager: SessionManager) -> None:
    with pytest.raises(RuntimeError):
        session_manager.get_active_log()
