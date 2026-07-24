"""Tests for ruleset persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from gokaidm.persistence.ruleset import Ruleset, RulesetStore


@pytest.fixture
def store(tmp_path: Path) -> RulesetStore:
    return RulesetStore(data_dir=tmp_path)


# ---------------------------------------------------------------------------
# Ruleset model
# ---------------------------------------------------------------------------


def test_ruleset_defaults() -> None:
    r = Ruleset()
    assert r.name == "Gates of Krystalia Core"
    assert r.version == "1.0"
    assert r.entries == []


def test_ruleset_add_entry() -> None:
    r = Ruleset(name="Core Rules")
    entry = r.add_entry("Combat", "Roll 1d20 + modifier.", category="combat")
    assert entry.title == "Combat"
    assert len(r.entries) == 1
    assert r.entries[0]["category"] == "combat"


def test_ruleset_search_hit() -> None:
    r = Ruleset(name="Core Rules")
    r.add_entry("Stealth", "Dexterity check to hide.", category="skills")
    r.add_entry("Combat", "Roll to attack.", category="combat")
    results = r.search("stealth")
    assert len(results) == 1
    assert results[0]["title"] == "Stealth"


def test_ruleset_search_case_insensitive() -> None:
    r = Ruleset(name="Core Rules")
    r.add_entry("Magic Missile", "Auto-hit spell.", category="spells")
    results = r.search("magic missile")
    assert len(results) == 1


def test_ruleset_search_no_results() -> None:
    r = Ruleset(name="Core Rules")
    r.add_entry("Combat", "Roll to attack.", category="combat")
    assert r.search("nonexistent keyword") == []


def test_ruleset_categories() -> None:
    r = Ruleset(name="Core Rules")
    r.add_entry("A", "text", category="combat")
    r.add_entry("B", "text", category="skills")
    r.add_entry("C", "text", category="combat")
    cats = r.categories()
    assert cats == ["combat", "skills"]


def test_ruleset_round_trip() -> None:
    r = Ruleset(name="Test Ruleset", version="2.0")
    r.add_entry("Spell", "Cast at will.", category="magic")
    d = r.to_dict()
    r2 = Ruleset.from_dict(d)
    assert r2.id == r.id
    assert len(r2.entries) == 1


# ---------------------------------------------------------------------------
# RulesetStore
# ---------------------------------------------------------------------------


def test_store_save_load(store: RulesetStore) -> None:
    r = Ruleset(name="Core Rules")
    store.save(r)
    loaded = store.load(r.id)
    assert loaded.id == r.id
    assert loaded.name == "Core Rules"


def test_store_load_by_name(store: RulesetStore) -> None:
    r = Ruleset(name="Advanced Rules")
    store.save(r)
    loaded = store.load_by_name("Advanced Rules")
    assert loaded.id == r.id


def test_store_load_missing(store: RulesetStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.load("missing-id")


def test_store_delete(store: RulesetStore) -> None:
    r = Ruleset(name="Temp")
    store.save(r)
    assert store.exists(r.id)
    store.delete(r.id)
    assert not store.exists(r.id)


def test_store_list_all(store: RulesetStore) -> None:
    for name in ["Alpha", "Beta"]:
        store.save(Ruleset(name=name))
    rulesets = store.list_all()
    assert len(rulesets) == 2
