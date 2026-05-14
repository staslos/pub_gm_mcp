from __future__ import annotations
from pub_gm_mcp.models.campaign import Campaign, TravelNode
from pub_gm_mcp.models.campaign_session import CampaignSession
from pub_gm_mcp.models.adventure import ThreatLevel
from pub_gm_mcp.campaign.campaign_store import CampaignStore
from pub_gm_mcp.parser.adventure_parser import AdventureParser


class CampaignNarrationError(Exception):
    pass


class CampaignNarrator:
    def __init__(self, store: CampaignStore, adventure_store: AdventureParser) -> None:
        self.store = store
        self.adventure_store = adventure_store

    def travel_to_node(self, session: CampaignSession, node_id: str) -> str:
        """
        Move the party to a campaign node (adventure site or travel node).
        Returns at-a-glance narration for the destination.
        """
        campaign = self.store.load_campaign(session.campaign_id)

        # Validate node exists
        is_adventure = node_id in campaign.adventure_ids
        travel_node = campaign.get_travel_node(node_id)
        if not is_adventure and travel_node is None:
            raise CampaignNarrationError(f"Node '{node_id}' not found in campaign")

        session.state.current_node_id = node_id
        session.state.in_adventure = False
        session.state.active_session_id = None

        if is_adventure and node_id not in session.state.visited_adventure_ids:
            session.state.visited_adventure_ids.append(node_id)

        if travel_node is not None:
            node_state = session.state.get_travel_node_state(node_id)
            node_state.visited = True

        self.store.save_session(session)

        if travel_node is not None:
            return self._format_travel_node_entry(travel_node)

        # Arriving at an adventure site — give the approach description from the adventure
        adventure = self.adventure_store.load(node_id)
        return f"You arrive at {adventure.title}.\n\n{adventure.synopsis}"

    def inspect_travel_node(self, session: CampaignSession) -> str:
        """Reveal one additional detail at the current travel node."""
        campaign = self.store.load_campaign(session.campaign_id)
        node_id = session.state.current_node_id

        if node_id is None or session.state.in_adventure:
            raise CampaignNarrationError("Party is not at a travel node")

        node = campaign.get_travel_node(node_id)
        if node is None:
            raise CampaignNarrationError(f"Travel node '{node_id}' not found")

        node_state = session.state.get_travel_node_state(node_id)
        unrevealed = [
            i for i in range(len(node.details))
            if i not in node_state.revealed_detail_indices
        ]
        if not unrevealed:
            return "There is nothing more to observe here."

        idx = unrevealed[0]
        node_state.revealed_detail_indices.append(idx)
        self.store.save_session(session)
        return node.details[idx]

    def enter_adventure_site(self, session: CampaignSession, adventure_session_id: str) -> str:
        """Record that the party has entered an adventure site with an active adventure session."""
        node_id = session.state.current_node_id
        if node_id is None:
            raise CampaignNarrationError("Party has no current campaign position")

        campaign = self.store.load_campaign(session.campaign_id)
        if node_id not in campaign.adventure_ids:
            raise CampaignNarrationError(f"Current node '{node_id}' is not an adventure site")

        session.state.in_adventure = True
        session.state.active_session_id = adventure_session_id
        self.store.save_session(session)
        return f"Adventure session '{adventure_session_id}' is now active."

    def leave_adventure_site(self, session: CampaignSession) -> str:
        """Return the party to the campaign map after leaving an adventure site."""
        session.state.in_adventure = False
        session.state.active_session_id = None
        self.store.save_session(session)
        return "The party leaves the site and returns to the open road."

    def list_exits(self, session: CampaignSession) -> list[dict]:
        """List visible connections from the current campaign node."""
        campaign = self.store.load_campaign(session.campaign_id)
        node_id = session.state.current_node_id
        if node_id is None:
            raise CampaignNarrationError("Party has no current campaign position")
        return [
            {
                "label": c.label,
                "to": c.to_id,
                "travel_time": c.travel_time,
            }
            for c in campaign.connections_from(node_id)
        ]

    def _format_travel_node_entry(self, node: TravelNode) -> str:
        parts = [node.at_a_glance]
        if node.threat_level != ThreatLevel.NONE and node.threat_telltale:
            parts.append(node.threat_telltale)
        return "\n\n".join(parts)
