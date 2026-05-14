"""Tests for CampaignNarrator — campaign-level travel and state transitions."""
import pytest
from pub_gm_mcp.campaign.campaign_narrator import CampaignNarrationError
from pub_gm_mcp.models.adventure import ThreatLevel
from pub_gm_mcp.models.campaign import TravelNode


class TestTravelToNode:
    def test_travel_to_travel_node_returns_at_a_glance(
        self, campaign_narrator, campaign_session
    ):
        result = campaign_narrator.travel_to_node(campaign_session, "crossroads")
        assert "muddy crossroads" in result

    def test_travel_to_travel_node_includes_threat_telltale(
        self, campaign_narrator, campaign_session
    ):
        result = campaign_narrator.travel_to_node(campaign_session, "crossroads")
        assert "The crow hasn't moved" in result

    def test_travel_to_adventure_site_returns_title_and_synopsis(
        self, campaign_narrator, campaign_session
    ):
        result = campaign_narrator.travel_to_node(campaign_session, "test_adventure")
        assert "Test Adventure" in result
        assert "A short test adventure." in result

    def test_updates_current_node(self, campaign_narrator, campaign_session):
        campaign_narrator.travel_to_node(campaign_session, "crossroads")
        loaded = campaign_store_session(campaign_narrator, campaign_session.id)
        assert loaded.state.current_node_id == "crossroads"

    def test_clears_in_adventure_flag(self, campaign_narrator, campaign_session):
        campaign_session.state.in_adventure = True
        campaign_narrator.travel_to_node(campaign_session, "crossroads")
        loaded = campaign_store_session(campaign_narrator, campaign_session.id)
        assert loaded.state.in_adventure is False

    def test_adventure_site_appended_to_visited_on_first_visit(
        self, campaign_narrator, campaign_session
    ):
        campaign_narrator.travel_to_node(campaign_session, "test_adventure")
        loaded = campaign_store_session(campaign_narrator, campaign_session.id)
        assert "test_adventure" in loaded.state.visited_adventure_ids

    def test_adventure_site_not_duplicated_on_revisit(
        self, campaign_narrator, campaign_session
    ):
        campaign_narrator.travel_to_node(campaign_session, "test_adventure")
        campaign_session = campaign_store_session(campaign_narrator, campaign_session.id)
        campaign_narrator.travel_to_node(campaign_session, "test_adventure")
        loaded = campaign_store_session(campaign_narrator, campaign_session.id)
        assert loaded.state.visited_adventure_ids.count("test_adventure") == 1

    def test_travel_node_marked_visited(self, campaign_narrator, campaign_session):
        campaign_narrator.travel_to_node(campaign_session, "crossroads")
        loaded = campaign_store_session(campaign_narrator, campaign_session.id)
        assert loaded.state.travel_node_states["crossroads"].visited is True

    def test_unknown_node_raises(self, campaign_narrator, campaign_session):
        with pytest.raises(CampaignNarrationError, match="not found"):
            campaign_narrator.travel_to_node(campaign_session, "nowhere")

    def test_no_threat_telltale_when_threat_none(
        self, campaign_narrator, campaign_session, sample_campaign
    ):
        safe_node = TravelNode(
            id="safe_place",
            name="Safe Place",
            at_a_glance="Nothing to worry about here.",
            threat_level=ThreatLevel.NONE,
            threat_telltale="this should not appear",
        )
        # Add to campaign and re-save
        sample_campaign.travel_nodes.append(safe_node)
        campaign_narrator.store.save_campaign(sample_campaign)
        result = campaign_narrator.travel_to_node(campaign_session, "safe_place")
        assert "this should not appear" not in result


class TestInspectTravelNode:
    def _travel(self, campaign_narrator, campaign_session):
        campaign_narrator.travel_to_node(campaign_session, "crossroads")
        return campaign_store_session(campaign_narrator, campaign_session.id)

    def test_reveals_first_detail(self, campaign_narrator, campaign_session):
        campaign_session = self._travel(campaign_narrator, campaign_session)
        result = campaign_narrator.inspect_travel_node(campaign_session)
        assert result == "Old wagon ruts heading east."

    def test_reveals_second_detail_on_second_call(
        self, campaign_narrator, campaign_session
    ):
        campaign_session = self._travel(campaign_narrator, campaign_session)
        campaign_narrator.inspect_travel_node(campaign_session)
        campaign_session = campaign_store_session(campaign_narrator, campaign_session.id)
        result = campaign_narrator.inspect_travel_node(campaign_session)
        assert result == "A crow watches from the post."

    def test_exhaustion_after_all_details(self, campaign_narrator, campaign_session):
        campaign_session = self._travel(campaign_narrator, campaign_session)
        for _ in range(2):  # crossroads has 2 details
            campaign_narrator.inspect_travel_node(campaign_session)
            campaign_session = campaign_store_session(campaign_narrator, campaign_session.id)
        result = campaign_narrator.inspect_travel_node(campaign_session)
        assert "nothing more" in result.lower()

    def test_raises_when_in_adventure(self, campaign_narrator, campaign_session):
        campaign_session = self._travel(campaign_narrator, campaign_session)
        campaign_session.state.in_adventure = True
        with pytest.raises(CampaignNarrationError):
            campaign_narrator.inspect_travel_node(campaign_session)

    def test_raises_when_no_current_node(self, campaign_narrator, campaign_session):
        campaign_session.state.current_node_id = None
        with pytest.raises(CampaignNarrationError):
            campaign_narrator.inspect_travel_node(campaign_session)


class TestEnterAdventureSite:
    def _at_site(self, campaign_narrator, campaign_session):
        campaign_narrator.travel_to_node(campaign_session, "test_adventure")
        return campaign_store_session(campaign_narrator, campaign_session.id)

    def test_sets_in_adventure_flag(self, campaign_narrator, campaign_session):
        campaign_session = self._at_site(campaign_narrator, campaign_session)
        campaign_narrator.enter_adventure_site(campaign_session, "adv_sess_001")
        loaded = campaign_store_session(campaign_narrator, campaign_session.id)
        assert loaded.state.in_adventure is True

    def test_sets_active_session_id(self, campaign_narrator, campaign_session):
        campaign_session = self._at_site(campaign_narrator, campaign_session)
        campaign_narrator.enter_adventure_site(campaign_session, "adv_sess_001")
        loaded = campaign_store_session(campaign_narrator, campaign_session.id)
        assert loaded.state.active_session_id == "adv_sess_001"

    def test_raises_when_at_travel_node(self, campaign_narrator, campaign_session):
        campaign_narrator.travel_to_node(campaign_session, "crossroads")
        campaign_session = campaign_store_session(campaign_narrator, campaign_session.id)
        with pytest.raises(CampaignNarrationError):
            campaign_narrator.enter_adventure_site(campaign_session, "adv_sess_001")

    def test_raises_when_no_current_node(self, campaign_narrator, campaign_session):
        campaign_session.state.current_node_id = None
        with pytest.raises(CampaignNarrationError):
            campaign_narrator.enter_adventure_site(campaign_session, "adv_sess_001")


class TestListExits:
    def test_visible_connection_included(self, campaign_narrator, campaign_session):
        campaign_narrator.travel_to_node(campaign_session, "crossroads")
        campaign_session = campaign_store_session(campaign_narrator, campaign_session.id)
        exits = campaign_narrator.list_exits(campaign_session)
        labels = [e["label"] for e in exits]
        assert "east road to the dungeon" in labels

    def test_hidden_connection_excluded(self, campaign_narrator, campaign_session):
        campaign_narrator.travel_to_node(campaign_session, "crossroads")
        campaign_session = campaign_store_session(campaign_narrator, campaign_session.id)
        exits = campaign_narrator.list_exits(campaign_session)
        labels = [e["label"] for e in exits]
        assert "overgrown trail" not in labels

    def test_no_current_node_raises(self, campaign_narrator, campaign_session):
        campaign_session.state.current_node_id = None
        with pytest.raises(CampaignNarrationError):
            campaign_narrator.list_exits(campaign_session)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def campaign_store_session(campaign_narrator, session_id):
    """Reload a campaign session from the store."""
    return campaign_narrator.store.load_session(session_id)
