from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field
from pub_gm_mcp.models.session import PartyMember


class TravelNodeState(BaseModel):
    node_id: str
    visited: bool = False
    revealed_detail_indices: list[int] = Field(default_factory=list)


class CampaignSessionState(BaseModel):
    # Current position: either an adventure_id or a travel_node id
    current_node_id: str | None = None
    # True when the party is inside an adventure site (as opposed to a travel node)
    in_adventure: bool = False
    # The active Adventure session id when in_adventure is True
    active_session_id: str | None = None
    # adventure_ids the party has fully left (not necessarily "won")
    visited_adventure_ids: list[str] = Field(default_factory=list)
    travel_node_states: dict[str, TravelNodeState] = Field(default_factory=dict)
    gm_notes: list[str] = Field(default_factory=list)

    def get_travel_node_state(self, node_id: str) -> TravelNodeState:
        if node_id not in self.travel_node_states:
            self.travel_node_states[node_id] = TravelNodeState(node_id=node_id)
        return self.travel_node_states[node_id]


class CampaignSession(BaseModel):
    id: str
    campaign_id: str
    party: list[PartyMember] = Field(default_factory=list)
    state: CampaignSessionState = Field(default_factory=CampaignSessionState)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
