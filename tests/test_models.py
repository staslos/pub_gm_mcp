"""Tests for model methods — lookup helpers and lazy state init."""
from pub_gm_mcp.models.adventure import Adventure, Area, ThreatLevel
from pub_gm_mcp.models.campaign import Campaign, TravelNode, CampaignConnection
from pub_gm_mcp.models.campaign_session import CampaignSessionState


class TestAdventureGetArea:
    def test_returns_area_by_id(self, sample_adventure):
        area = sample_adventure.get_area("test_room")
        assert area is not None
        assert area.id == "test_room"

    def test_returns_none_when_not_found(self, sample_adventure):
        assert sample_adventure.get_area("nonexistent") is None

    def test_returns_none_on_empty_areas(self):
        adventure = Adventure(id="empty", title="Empty", synopsis="", areas=[])
        assert adventure.get_area("anything") is None


class TestCampaignGetTravelNode:
    def test_returns_node_by_id(self, sample_campaign):
        node = sample_campaign.get_travel_node("crossroads")
        assert node is not None
        assert node.id == "crossroads"

    def test_returns_none_when_not_found(self, sample_campaign):
        assert sample_campaign.get_travel_node("nonexistent") is None

    def test_returns_none_on_empty_travel_nodes(self):
        campaign = Campaign(id="c", title="C", synopsis="", travel_nodes=[])
        assert campaign.get_travel_node("anything") is None


class TestCampaignConnectionsFrom:
    def test_returns_visible_connections_from_node(self, sample_campaign):
        connections = sample_campaign.connections_from("crossroads")
        # crossroads has 2 connections: one visible to test_adventure, one hidden
        assert any(c.to_id == "test_adventure" for c in connections)

    def test_excludes_hidden_connections(self, sample_campaign):
        connections = sample_campaign.connections_from("crossroads")
        assert not any(c.to_id == "hidden_place" for c in connections)

    def test_returns_empty_for_unknown_node(self, sample_campaign):
        assert sample_campaign.connections_from("nowhere") == []

    def test_returns_empty_when_no_connections(self):
        campaign = Campaign(id="c", title="C", synopsis="", connections=[])
        assert campaign.connections_from("anywhere") == []


class TestCampaignSessionStateLazyInit:
    def test_creates_fresh_node_state(self):
        state = CampaignSessionState()
        node_state = state.get_travel_node_state("crossroads")
        assert node_state.node_id == "crossroads"
        assert node_state.visited is False

    def test_returns_same_state_on_second_call(self):
        state = CampaignSessionState()
        first = state.get_travel_node_state("crossroads")
        first.visited = True
        second = state.get_travel_node_state("crossroads")
        assert second.visited is True

    def test_different_nodes_are_independent(self):
        state = CampaignSessionState()
        a = state.get_travel_node_state("crossroads")
        b = state.get_travel_node_state("forest")
        a.visited = True
        assert b.visited is False
