from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ThreatLevel(str, Enum):
    NONE = "none"
    SUBTLE = "subtle"      # something feels off
    PRESENT = "present"    # visible danger signs
    IMMEDIATE = "immediate"


class Item(BaseModel):
    id: str
    name: str
    description: str
    hidden: bool = False
    properties: dict[str, Any] = Field(default_factory=dict)


class NPC(BaseModel):
    id: str
    name: str
    description: str
    # What an observant party notices at first glance
    first_impression: str
    # A detail that hints at the NPC's nature or role without revealing it
    telltale: str | None = None
    disposition: str = "neutral"
    hidden: bool = False
    notes: dict[str, Any] = Field(default_factory=dict)


class Encounter(BaseModel):
    id: str
    description: str
    trigger: str | None = None   # what causes it (None = always present)
    repeatable: bool = False
    resolved: bool = False
    notes: dict[str, Any] = Field(default_factory=dict)


class Connection(BaseModel):
    """A traversable link from one area to another."""
    target_area_id: str
    label: str           # "north door", "staircase down", etc.
    hidden: bool = False
    locked: bool = False
    locked_description: str | None = None


class Area(BaseModel):
    id: str
    name: str
    # At-a-glance description (OSR style: what hits the senses immediately)
    at_a_glance: str
    # Details revealed only on inspection or interaction
    details: list[str] = Field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.NONE
    # Hint about danger without spelling it out
    threat_telltale: str | None = None
    items: list[Item] = Field(default_factory=list)
    npcs: list[NPC] = Field(default_factory=list)
    encounters: list[Encounter] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: dict[str, Any] = Field(default_factory=dict)


class Adventure(BaseModel):
    id: str
    title: str
    system: str = "system-agnostic"
    synopsis: str
    areas: list[Area] = Field(default_factory=list)
    starting_area_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_area(self, area_id: str) -> Area | None:
        return next((a for a in self.areas if a.id == area_id), None)
