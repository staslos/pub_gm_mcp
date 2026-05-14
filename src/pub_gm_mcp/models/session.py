from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class PartyMember(BaseModel):
    name: str
    description: str = ""
    notes: dict[str, Any] = Field(default_factory=dict)


class AreaState(BaseModel):
    """Tracks what the party has revealed in a given area."""
    area_id: str
    visited: bool = False
    revealed_detail_indices: list[int] = Field(default_factory=list)
    revealed_item_ids: list[str] = Field(default_factory=list)
    revealed_npc_ids: list[str] = Field(default_factory=list)
    # NPCs whose names the party has learned through in-play introduction
    named_npc_ids: list[str] = Field(default_factory=list)
    resolved_encounter_ids: list[str] = Field(default_factory=list)


class SessionState(BaseModel):
    current_area_id: str | None = None
    area_states: dict[str, AreaState] = Field(default_factory=dict)
    # Free-form GM notes accumulated during play
    gm_notes: list[str] = Field(default_factory=list)
    # Items the party is carrying (item_id -> source_area_id)
    party_inventory: dict[str, str] = Field(default_factory=dict)

    def get_area_state(self, area_id: str) -> AreaState:
        if area_id not in self.area_states:
            self.area_states[area_id] = AreaState(area_id=area_id)
        return self.area_states[area_id]


class Session(BaseModel):
    id: str
    adventure_id: str
    party: list[PartyMember] = Field(default_factory=list)
    state: SessionState = Field(default_factory=SessionState)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
