"""Tests for campaign persistence."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from gokaidm.persistence.campaign import Campaign, CampaignStore


@pytest.fixture
def store(tmp_path: Path) -> CampaignStore:
    return CampaignStore(data_dir=tmp_path)


# ---------------------------------------------------------------------------
# Campaign model
# ---------------------------------------------------------------------------


def test_campaign_defaults() -> None:
    c = Campaign(name="Test")
    assert c.name == "Test"
    assert c.id
    assert c.persona_ids == []
    assert c.quests == []


def test_campaign_add_quest() -> None:
    c = Campaign(name="Test")
    q = c.add_quest("Find the artifact", description="Ancient relic", status="active")
    assert q["title"] == "Find the artifact"
    assert len(c.quests) == 1
    assert c.quests[0]["status"] == "active"


def test_campaign_complete_quest() -> None:
    c = Campaign(name="Test")
    q = c.add_quest("Find the artifact")
    assert c.complete_quest(q["id"])
    assert c.quests[0]["status"] == "completed"


def test_campaign_complete_quest_not_found() -> None:
    c = Campaign(name="Test")
    assert not c.complete_quest("nonexistent-id")


def test_campaign_round_trip() -> None:
    c = Campaign(name="Round trip", description="A desc", notes="some notes")
    c.add_quest("Side quest")
    d = c.to_dict()
    c2 = Campaign.from_dict(d)
    assert c2.id == c.id
    assert c2.name == c.name
    assert len(c2.quests) == 1


# ---------------------------------------------------------------------------
# CampaignStore
# ---------------------------------------------------------------------------


def test_store_save_load(store: CampaignStore) -> None:
    c = Campaign(name="Hero's Journey")
    store.save(c)
    loaded = store.load(c.id)
    assert loaded.id == c.id
    assert loaded.name == "Hero's Journey"


def test_store_load_by_name(store: CampaignStore) -> None:
    c = Campaign(name="Krystalia Rising")
    store.save(c)
    loaded = store.load_by_name("Krystalia Rising")
    assert loaded.id == c.id


def test_store_load_by_name_case_insensitive(store: CampaignStore) -> None:
    c = Campaign(name="Krystalia Rising")
    store.save(c)
    loaded = store.load_by_name("krystalia rising")
    assert loaded.id == c.id


def test_store_load_missing(store: CampaignStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.load("does-not-exist")


def test_store_delete(store: CampaignStore) -> None:
    c = Campaign(name="Temp")
    store.save(c)
    assert store.exists(c.id)
    assert store.delete(c.id)
    assert not store.exists(c.id)


def test_store_delete_missing(store: CampaignStore) -> None:
    assert not store.delete("does-not-exist")


def test_store_list_all(store: CampaignStore) -> None:
    names = ["Alpha", "Beta", "Gamma"]
    for n in names:
        store.save(Campaign(name=n))
    all_campaigns = store.list_all()
    assert len(all_campaigns) == 3
    assert {c.name for c in all_campaigns} == set(names)


def test_store_list_all_empty(store: CampaignStore) -> None:
    assert store.list_all() == []


def test_store_exists(store: CampaignStore) -> None:
    c = Campaign(name="Exists")
    store.save(c)
    assert store.exists(c.id)
    assert not store.exists("fake-id")
