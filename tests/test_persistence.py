"""Tests for storage layer — round-trips, error paths, state integrity."""
import pytest
from pub_gm_mcp.models.adventure import Adventure, Area, ThreatLevel
from pub_gm_mcp.models.session import Session, SessionState
from pub_gm_mcp.models.campaign import Campaign
from pub_gm_mcp.models.campaign_session import CampaignSession
from pub_gm_mcp.parser.adventure_parser import AdventureParser
from pub_gm_mcp.campaign.campaign_store import CampaignStore


class TestAdventureParserRoundTrip:
    def test_save_and_reload_preserves_fields(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        parser.save(sample_adventure)
        loaded = parser.load(sample_adventure.id)
        assert loaded.id == sample_adventure.id
        assert loaded.title == sample_adventure.title
        assert loaded.synopsis == sample_adventure.synopsis
        assert loaded.starting_area_id == sample_adventure.starting_area_id
        assert len(loaded.areas) == len(sample_adventure.areas)

    def test_round_trip_preserves_nested_npcs(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        parser.save(sample_adventure)
        loaded = parser.load(sample_adventure.id)
        original_npc = sample_adventure.areas[0].npcs[0]
        loaded_npc = loaded.areas[0].npcs[0]
        assert loaded_npc.id == original_npc.id
        assert loaded_npc.first_impression == original_npc.first_impression
        assert loaded_npc.hidden == original_npc.hidden

    def test_round_trip_preserves_connections(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        parser.save(sample_adventure)
        loaded = parser.load(sample_adventure.id)
        original_conn = sample_adventure.areas[0].connections[0]
        loaded_conn = loaded.areas[0].connections[0]
        assert loaded_conn.target_area_id == original_conn.target_area_id
        assert loaded_conn.hidden == original_conn.hidden
        assert loaded_conn.locked == original_conn.locked

    def test_round_trip_preserves_threat_level_enum(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        parser.save(sample_adventure)
        loaded = parser.load(sample_adventure.id)
        assert loaded.areas[0].threat_level == ThreatLevel.SUBTLE
        assert loaded.areas[1].threat_level == ThreatLevel.NONE

    def test_create_raises_on_duplicate(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        parser.create(sample_adventure)
        with pytest.raises(FileExistsError):
            parser.create(sample_adventure)

    def test_load_raises_on_missing(self, tmp_path):
        parser = AdventureParser(tmp_path / "adv")
        with pytest.raises(FileNotFoundError):
            parser.load("does_not_exist")

    def test_delete_removes_file(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        parser.save(sample_adventure)
        parser.delete(sample_adventure.id)
        with pytest.raises(FileNotFoundError):
            parser.load(sample_adventure.id)

    def test_delete_raises_on_missing(self, tmp_path):
        parser = AdventureParser(tmp_path / "adv")
        with pytest.raises(FileNotFoundError):
            parser.delete("does_not_exist")

    def test_list_adventures(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        assert parser.list_adventures() == []
        parser.save(sample_adventure)
        assert sample_adventure.id in parser.list_adventures()

    def test_save_overwrites_existing(self, tmp_path, sample_adventure):
        parser = AdventureParser(tmp_path / "adv")
        parser.save(sample_adventure)
        modified = sample_adventure.model_copy(update={"title": "Modified Title"})
        parser.save(modified)
        loaded = parser.load(sample_adventure.id)
        assert loaded.title == "Modified Title"


class TestCampaignStoreRoundTrip:
    def test_save_and_reload_campaign(self, tmp_path, sample_campaign):
        store = CampaignStore(tmp_path / "campaigns", tmp_path / "csessions")
        store.save_campaign(sample_campaign)
        loaded = store.load_campaign(sample_campaign.id)
        assert loaded.id == sample_campaign.id
        assert loaded.title == sample_campaign.title
        assert loaded.adventure_ids == sample_campaign.adventure_ids
        assert len(loaded.travel_nodes) == len(sample_campaign.travel_nodes)
        assert len(loaded.connections) == len(sample_campaign.connections)

    def test_campaign_session_round_trip(self, tmp_path, campaign_session):
        store = CampaignStore(tmp_path / "campaigns", tmp_path / "csessions")
        store.save_session(campaign_session)
        loaded = store.load_session(campaign_session.id)
        assert loaded.id == campaign_session.id
        assert loaded.campaign_id == campaign_session.campaign_id
        assert loaded.state.current_node_id == campaign_session.state.current_node_id

    def test_touch_updates_updated_at(self, tmp_path, campaign_session):
        store = CampaignStore(tmp_path / "campaigns", tmp_path / "csessions")
        original_time = campaign_session.updated_at
        store.save_session(campaign_session)
        loaded = store.load_session(campaign_session.id)
        assert loaded.updated_at >= original_time

    def test_datetime_timezone_survives_round_trip(self, tmp_path, campaign_session):
        store = CampaignStore(tmp_path / "campaigns", tmp_path / "csessions")
        store.save_session(campaign_session)
        loaded = store.load_session(campaign_session.id)
        assert loaded.created_at.tzinfo is not None
        assert loaded.updated_at.tzinfo is not None

    def test_load_missing_campaign_raises(self, tmp_path):
        store = CampaignStore(tmp_path / "campaigns", tmp_path / "csessions")
        with pytest.raises(FileNotFoundError):
            store.load_campaign("no_such_campaign")

    def test_load_missing_session_raises(self, tmp_path):
        store = CampaignStore(tmp_path / "campaigns", tmp_path / "csessions")
        with pytest.raises(FileNotFoundError):
            store.load_session("no_such_session")

    def test_list_campaigns(self, tmp_path, sample_campaign):
        store = CampaignStore(tmp_path / "campaigns", tmp_path / "csessions")
        assert store.list_campaigns() == []
        store.save_campaign(sample_campaign)
        assert sample_campaign.id in store.list_campaigns()


class TestSessionStateLazyInit:
    def test_get_area_state_creates_fresh_on_first_call(self):
        state = SessionState()
        area_state = state.get_area_state("room_a")
        assert area_state.area_id == "room_a"
        assert area_state.visited is False
        assert area_state.revealed_detail_indices == []

    def test_get_area_state_returns_same_object_on_second_call(self):
        state = SessionState()
        first = state.get_area_state("room_a")
        first.visited = True
        second = state.get_area_state("room_a")
        assert second.visited is True

    def test_different_areas_are_independent(self):
        state = SessionState()
        a = state.get_area_state("room_a")
        b = state.get_area_state("room_b")
        a.visited = True
        assert b.visited is False
