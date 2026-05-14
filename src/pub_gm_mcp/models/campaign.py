from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from pub_gm_mcp.models.adventure import ThreatLevel


class TravelNode(BaseModel):
    """A wilderness location, road junction, or named landmark between adventure sites."""
    id: str
    name: str
    # What the party perceives arriving here — OSR at-a-glance rules apply
    at_a_glance: str
    details: list[str] = Field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.NONE
    threat_telltale: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: dict[str, Any] = Field(default_factory=dict)


class CampaignConnection(BaseModel):
    """A traversable link between two campaign nodes (adventures or travel nodes)."""
    from_id: str   # adventure id or travel_node id
    to_id: str     # adventure id or travel_node id
    label: str     # "road south to the village", "trail into the hills"
    travel_time: str | None = None   # "half a day", "three days on foot"
    hidden: bool = False
    notes: dict[str, Any] = Field(default_factory=dict)


class Campaign(BaseModel):
    id: str
    title: str
    synopsis: str
    # IDs of stored Adventure objects that are sites in this campaign
    adventure_ids: list[str] = Field(default_factory=list)
    # Wilderness / travel nodes that exist between adventure sites
    travel_nodes: list[TravelNode] = Field(default_factory=list)
    # Edges connecting adventure sites and travel nodes
    connections: list[CampaignConnection] = Field(default_factory=list)
    # Where a new campaign session starts — adventure_id or travel_node id
    starting_node_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_travel_node(self, node_id: str) -> TravelNode | None:
        return next((n for n in self.travel_nodes if n.id == node_id), None)

    def connections_from(self, node_id: str) -> list[CampaignConnection]:
        return [c for c in self.connections if c.from_id == node_id and not c.hidden]
