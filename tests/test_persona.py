"""Tests for persona persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from gokaidm.persistence.persona import Persona, PersonaStore


@pytest.fixture
def store(tmp_path: Path) -> PersonaStore:
    return PersonaStore(data_dir=tmp_path)


# ---------------------------------------------------------------------------
# Persona model
# ---------------------------------------------------------------------------


def test_persona_defaults() -> None:
    p = Persona(name="Aria")
    assert p.name == "Aria"
    assert p.persona_type == "pc"
    assert p.hit_points_current == 10
    assert p.level == 1


def test_persona_add_inventory_item() -> None:
    p = Persona(name="Aria")
    item = p.add_inventory_item("Iron Sword", quantity=1, item_type="weapon")
    assert item["name"] == "Iron Sword"
    assert len(p.inventory) == 1


def test_persona_remove_inventory_item() -> None:
    p = Persona(name="Aria")
    item = p.add_inventory_item("Health Potion")
    assert p.remove_inventory_item(item["id"])
    assert len(p.inventory) == 0


def test_persona_remove_inventory_item_not_found() -> None:
    p = Persona(name="Aria")
    assert not p.remove_inventory_item("nonexistent")


def test_persona_heal() -> None:
    p = Persona(name="Aria", hit_points_max=20, hit_points_current=5)
    result = p.heal(10)
    assert result == 15
    assert p.hit_points_current == 15


def test_persona_heal_capped_at_max() -> None:
    p = Persona(name="Aria", hit_points_max=20, hit_points_current=18)
    result = p.heal(10)
    assert result == 20
    assert p.hit_points_current == 20


def test_persona_take_damage() -> None:
    p = Persona(name="Aria", hit_points_max=20, hit_points_current=20)
    result = p.take_damage(7)
    assert result == 13


def test_persona_take_damage_to_zero() -> None:
    p = Persona(name="Aria", hit_points_max=10, hit_points_current=5)
    result = p.take_damage(100)
    assert result == 0
    assert not p.is_alive


def test_persona_is_alive() -> None:
    p = Persona(name="Aria", hit_points_current=1)
    assert p.is_alive


def test_persona_conditions() -> None:
    p = Persona(name="Aria")
    p.add_condition("poisoned")
    p.add_condition("blinded")
    assert "poisoned" in p.conditions
    assert len(p.conditions) == 2
    assert p.remove_condition("poisoned")
    assert "poisoned" not in p.conditions


def test_persona_add_duplicate_condition() -> None:
    p = Persona(name="Aria")
    p.add_condition("stunned")
    p.add_condition("stunned")
    assert len(p.conditions) == 1


def test_persona_round_trip() -> None:
    p = Persona(name="Aria", character_class="Ranger", race="Elf", level=3)
    p.add_inventory_item("Bow", quantity=1)
    d = p.to_dict()
    p2 = Persona.from_dict(d)
    assert p2.id == p.id
    assert p2.name == "Aria"
    assert len(p2.inventory) == 1


# ---------------------------------------------------------------------------
# PersonaStore
# ---------------------------------------------------------------------------


def test_store_save_load(store: PersonaStore) -> None:
    p = Persona(name="Theron", character_class="Warrior")
    store.save(p)
    loaded = store.load(p.id)
    assert loaded.id == p.id
    assert loaded.name == "Theron"


def test_store_load_by_name(store: PersonaStore) -> None:
    p = Persona(name="Zara")
    store.save(p)
    loaded = store.load_by_name("Zara")
    assert loaded.id == p.id


def test_store_load_missing(store: PersonaStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.load("missing-id")


def test_store_delete(store: PersonaStore) -> None:
    p = Persona(name="Temp")
    store.save(p)
    store.delete(p.id)
    assert not store.exists(p.id)


def test_store_list_all(store: PersonaStore) -> None:
    for name in ["A", "B", "C"]:
        store.save(Persona(name=name, campaign_id="camp-1"))
    personas = store.list_all()
    assert len(personas) == 3


def test_store_list_filtered_by_campaign(store: PersonaStore) -> None:
    store.save(Persona(name="PC1", campaign_id="camp-1"))
    store.save(Persona(name="NPC1", campaign_id="camp-2"))
    store.save(Persona(name="PC2", campaign_id="camp-1"))
    camp1 = store.list_all(campaign_id="camp-1")
    assert len(camp1) == 2
    assert all(p.campaign_id == "camp-1" for p in camp1)
