"""Tests for location persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from gokaidm.persistence.location import Location, LocationStore


@pytest.fixture
def store(tmp_path: Path) -> LocationStore:
    return LocationStore(data_dir=tmp_path)


# ---------------------------------------------------------------------------
# Location model
# ---------------------------------------------------------------------------


def test_location_defaults() -> None:
    loc = Location(name="Ironveil Keep")
    assert loc.name == "Ironveil Keep"
    assert loc.location_type == "settlement"
    assert not loc.explored
    assert loc.visited_count == 0


def test_location_connect_disconnect() -> None:
    loc = Location(name="Keep")
    loc.connect("loc-2", "north gate")
    assert "loc-2" in loc.connections
    assert loc.disconnect("loc-2")
    assert "loc-2" not in loc.connections


def test_location_disconnect_not_found() -> None:
    loc = Location(name="Keep")
    assert not loc.disconnect("nonexistent")


def test_location_add_point_of_interest() -> None:
    loc = Location(name="Keep")
    poi = loc.add_point_of_interest("Throne Room", poi_type="encounter")
    assert poi["name"] == "Throne Room"
    assert len(loc.points_of_interest) == 1
    assert not poi["discovered"]


def test_location_add_event() -> None:
    loc = Location(name="Keep")
    evt = loc.add_event("Goblin raid!", event_type="combat")
    assert evt["type"] == "combat"
    assert len(loc.events) == 1


def test_location_add_secret() -> None:
    loc = Location(name="Keep")
    secret = loc.add_secret("Hidden vault behind bookshelf.", "Perception DC 15")
    assert not secret["revealed"]
    assert len(loc.secrets) == 1


def test_location_visit() -> None:
    loc = Location(name="Keep")
    assert not loc.explored
    loc.visit()
    assert loc.explored
    assert loc.visited_count == 1
    loc.visit()
    assert loc.visited_count == 2


def test_location_round_trip() -> None:
    loc = Location(name="Forest", location_type="wilderness", region="North")
    loc.add_point_of_interest("Ancient Tree")
    loc.connect("village-id", "south path")
    d = loc.to_dict()
    loc2 = Location.from_dict(d)
    assert loc2.id == loc.id
    assert len(loc2.points_of_interest) == 1
    assert "village-id" in loc2.connections


# ---------------------------------------------------------------------------
# LocationStore
# ---------------------------------------------------------------------------


def test_store_save_load(store: LocationStore) -> None:
    loc = Location(name="The Caverns")
    store.save(loc)
    loaded = store.load(loc.id)
    assert loaded.id == loc.id
    assert loaded.name == "The Caverns"


def test_store_load_by_name(store: LocationStore) -> None:
    loc = Location(name="Market Square")
    store.save(loc)
    loaded = store.load_by_name("Market Square")
    assert loaded.id == loc.id


def test_store_load_missing(store: LocationStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.load("missing-id")


def test_store_delete(store: LocationStore) -> None:
    loc = Location(name="Temp")
    store.save(loc)
    store.delete(loc.id)
    assert not store.exists(loc.id)


def test_store_list_all(store: LocationStore) -> None:
    for i in range(3):
        store.save(Location(name=f"Place {i}", campaign_id="camp-1"))
    assert len(store.list_all()) == 3


def test_store_list_filtered_by_campaign(store: LocationStore) -> None:
    store.save(Location(name="Castle", campaign_id="camp-1"))
    store.save(Location(name="Forest", campaign_id="camp-2"))
    store.save(Location(name="Dungeon", campaign_id="camp-1"))
    filtered = store.list_all(campaign_id="camp-1")
    assert len(filtered) == 2


def test_store_list_filtered_by_type(store: LocationStore) -> None:
    store.save(Location(name="Cave", location_type="dungeon"))
    store.save(Location(name="Town", location_type="settlement"))
    dungeons = store.list_all(location_type="dungeon")
    assert len(dungeons) == 1
    assert dungeons[0].name == "Cave"
