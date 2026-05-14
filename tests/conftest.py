"""Shared fixtures for pub-gm-mcp tests."""
import pytest
from pathlib import Path

from pub_gm_mcp.models.adventure import Adventure, Area, NPC, Item, Connection, ThreatLevel
from pub_gm_mcp.models.campaign import Campaign, TravelNode, CampaignConnection
from pub_gm_mcp.models.session import Session
from pub_gm_mcp.models.campaign_session import CampaignSession, CampaignSessionState
from pub_gm_mcp.parser.adventure_parser import AdventureParser
from pub_gm_mcp.narrator.adventure_narrator import AdventureNarrator
from pub_gm_mcp.campaign.campaign_store import CampaignStore
from pub_gm_mcp.campaign.campaign_narrator import CampaignNarrator


# ---------------------------------------------------------------------------
# Area / Adventure
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_area() -> Area:
    return Area(
        id="test_room",
        name="Test Room",
        at_a_glance="A stone room. Smells of damp.",
        details=["A scratch on the wall.", "A loose flagstone.", "A faded inscription."],
        threat_level=ThreatLevel.SUBTLE,
        threat_telltale="Something feels off.",
        items=[
            Item(id="visible_torch", name="Torch", description="A used torch.", hidden=False),
            Item(id="hidden_key", name="Key", description="A small iron key.", hidden=True),
        ],
        npcs=[
            NPC(
                id="visible_guard",
                name="Guard",
                description="A bored guard.",
                first_impression="A guard leans against the wall, half-asleep.",
                telltale="His sword hand is heavily calloused.",
                disposition="neutral",
                hidden=False,
            ),
            NPC(
                id="hidden_spy",
                name="Spy",
                description="A concealed agent.",
                first_impression="A figure watches from the shadows.",
                telltale=None,
                disposition="hostile",
                hidden=True,
            ),
        ],
        connections=[
            Connection(target_area_id="next_room", label="north door", hidden=False, locked=False),
            Connection(target_area_id="secret_room", label="hidden panel", hidden=True, locked=False),
            Connection(target_area_id="locked_room", label="iron door", hidden=False, locked=True,
                       locked_description="Needs a key."),
        ],
    )


@pytest.fixture
def sample_adventure(sample_area) -> Adventure:
    second_area = Area(
        id="next_room",
        name="Next Room",
        at_a_glance="A plain corridor.",
        details=[],
        threat_level=ThreatLevel.NONE,
        threat_telltale=None,
        connections=[
            Connection(target_area_id="test_room", label="south door", hidden=False, locked=False),
        ],
    )
    return Adventure(
        id="test_adventure",
        title="Test Adventure",
        synopsis="A short test adventure.",
        starting_area_id="test_room",
        areas=[sample_area, second_area],
    )


# ---------------------------------------------------------------------------
# Parser / Narrator
# ---------------------------------------------------------------------------

@pytest.fixture
def adventure_parser(tmp_path, sample_adventure) -> AdventureParser:
    p = AdventureParser(tmp_path / "adventures")
    p.save(sample_adventure)
    return p


@pytest.fixture
def session(sample_adventure) -> Session:
    return Session(id="sess_001", adventure_id=sample_adventure.id)


@pytest.fixture
def narrator(tmp_path, adventure_parser) -> AdventureNarrator:
    return AdventureNarrator(tmp_path / "sessions", adventure_parser)


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_travel_node() -> TravelNode:
    return TravelNode(
        id="crossroads",
        name="Crossroads",
        at_a_glance="A muddy crossroads. Signpost rotted away.",
        details=["Old wagon ruts heading east.", "A crow watches from the post."],
        threat_level=ThreatLevel.SUBTLE,
        threat_telltale="The crow hasn't moved since you arrived.",
    )


@pytest.fixture
def sample_campaign(sample_adventure, sample_travel_node) -> Campaign:
    return Campaign(
        id="test_campaign",
        title="Test Campaign",
        synopsis="A test campaign.",
        adventure_ids=[sample_adventure.id],
        travel_nodes=[sample_travel_node],
        connections=[
            CampaignConnection(
                from_id=sample_travel_node.id,
                to_id=sample_adventure.id,
                label="east road to the dungeon",
                travel_time="half a day",
            ),
            CampaignConnection(
                from_id=sample_adventure.id,
                to_id=sample_travel_node.id,
                label="west road back to the crossroads",
                travel_time="half a day",
            ),
            CampaignConnection(
                from_id=sample_travel_node.id,
                to_id="hidden_place",
                label="overgrown trail",
                hidden=True,
            ),
        ],
        starting_node_id=sample_travel_node.id,
    )


@pytest.fixture
def campaign_store(tmp_path, sample_campaign, sample_adventure) -> CampaignStore:
    adv_parser = AdventureParser(tmp_path / "adventures")
    adv_parser.save(sample_adventure)
    store = CampaignStore(tmp_path / "campaigns", tmp_path / "campaign_sessions")
    store.save_campaign(sample_campaign)
    return store


@pytest.fixture
def campaign_session(sample_campaign) -> CampaignSession:
    return CampaignSession(
        id="csess_001",
        campaign_id=sample_campaign.id,
        state=CampaignSessionState(current_node_id=sample_campaign.starting_node_id),
    )


@pytest.fixture
def campaign_narrator(tmp_path, campaign_store, sample_adventure) -> CampaignNarrator:
    adv_parser = AdventureParser(tmp_path / "adventures")
    adv_parser.save(sample_adventure)
    return CampaignNarrator(campaign_store, adv_parser)
