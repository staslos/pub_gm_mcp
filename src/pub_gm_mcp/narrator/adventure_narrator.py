from __future__ import annotations
from pathlib import Path
from pub_gm_mcp.models.adventure import Adventure, Area, ThreatLevel
from pub_gm_mcp.models.session import Session, SessionState
from pub_gm_mcp.parser.adventure_parser import AdventureParser


class NarrationError(Exception):
    pass


class AdventureNarrator:
    """
    OSR-style narration engine.

    Principle: reveal only what strikes the senses immediately. Details surface
    through player action, not GM exposition.
    """

    def __init__(self, session_dir: Path, parser: AdventureParser) -> None:
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.parser = parser

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def load_session(self, session_id: str) -> Session:
        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session '{session_id}' not found")
        return Session.model_validate_json(path.read_text())

    def save_session(self, session: Session) -> None:
        session.touch()
        self._session_path(session.id).write_text(session.model_dump_json(indent=2))

    def list_sessions(self) -> list[str]:
        return [p.stem for p in self.session_dir.glob("*.json")]

    def create_session(self, session: Session) -> None:
        path = self._session_path(session.id)
        if path.exists():
            raise FileExistsError(f"Session '{session.id}' already exists")
        self.save_session(session)

    # ------------------------------------------------------------------
    # Narration primitives
    # ------------------------------------------------------------------

    def enter_area(self, session: Session, area_id: str) -> str:
        """
        Move the party into an area and return the at-a-glance narration.
        Only immediate sensory information — OSR first impression.
        """
        adventure = self.parser.load(session.adventure_id)
        area = adventure.get_area(area_id)
        if area is None:
            raise NarrationError(f"Area '{area_id}' not found in adventure '{adventure.id}'")

        session.state.current_area_id = area_id
        area_state = session.state.get_area_state(area_id)
        first_visit = not area_state.visited   # capture before mutation
        area_state.visited = True
        self.save_session(session)

        return self._format_entry(area, first_visit=first_visit)

    def inspect_area(self, session: Session) -> str:
        """Party takes a careful look around — surfaces one unrevealed detail."""
        adventure = self.parser.load(session.adventure_id)
        area = self._current_area(adventure, session.state)
        area_state = session.state.get_area_state(area.id)

        unrevealed = [
            i for i in range(len(area.details))
            if i not in area_state.revealed_detail_indices
        ]
        if not unrevealed:
            return "You've taken in everything there is to see here."

        idx = unrevealed[0]
        area_state.revealed_detail_indices.append(idx)
        self.save_session(session)
        return area.details[idx]

    def look_at_npc(self, session: Session, npc_id: str) -> str:
        """Party focuses attention on an NPC — returns impression + telltale. Name is never revealed here."""
        adventure = self.parser.load(session.adventure_id)
        area = self._current_area(adventure, session.state)

        npc = next((n for n in area.npcs if n.id == npc_id), None)
        if npc is None:
            raise NarrationError(f"NPC '{npc_id}' not present in current area")

        area_state = session.state.get_area_state(area.id)
        if npc_id not in area_state.revealed_npc_ids:
            area_state.revealed_npc_ids.append(npc_id)
        self.save_session(session)

        parts = [npc.first_impression]
        if npc.telltale:
            parts.append(npc.telltale)
        return " ".join(parts)

    def introduce_npc(self, session: Session, npc_id: str) -> str:
        """
        Record that an NPC has revealed their name in play.
        Returns the name so the GM can use it going forward.
        Call this when an NPC introduces themselves or another character names them.
        """
        adventure = self.parser.load(session.adventure_id)
        area = self._current_area(adventure, session.state)

        npc = next((n for n in area.npcs if n.id == npc_id), None)
        if npc is None:
            raise NarrationError(f"NPC '{npc_id}' not present in current area")

        area_state = session.state.get_area_state(area.id)
        if npc_id not in area_state.named_npc_ids:
            area_state.named_npc_ids.append(npc_id)
        self.save_session(session)

        return npc.name

    def get_npc_name(self, session: Session, npc_id: str) -> str:
        """
        Returns the NPC's name if the party has learned it, otherwise 'unknown'.
        Use this to check before using a name in narration.
        """
        adventure = self.parser.load(session.adventure_id)
        area = self._current_area(adventure, session.state)

        npc = next((n for n in area.npcs if n.id == npc_id), None)
        if npc is None:
            raise NarrationError(f"NPC '{npc_id}' not present in current area")

        area_state = session.state.get_area_state(area.id)
        if npc_id in area_state.named_npc_ids:
            return npc.name
        return "unknown"

    def list_visible_exits(self, session: Session) -> list[dict]:
        """Return connections the party can perceive (non-hidden)."""
        adventure = self.parser.load(session.adventure_id)
        area = self._current_area(adventure, session.state)
        return [
            {"label": c.label, "target": c.target_area_id, "locked": c.locked}
            for c in area.connections
            if not c.hidden
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _current_area(self, adventure: Adventure, state: SessionState) -> Area:
        if state.current_area_id is None:
            raise NarrationError("Party has no current location")
        area = adventure.get_area(state.current_area_id)
        if area is None:
            raise NarrationError(f"Current area '{state.current_area_id}' missing from adventure")
        return area

    def _format_entry(self, area: Area, first_visit: bool) -> str:
        # Revisit: abbreviated opener — party already knows this place
        if not first_visit:
            parts = [f"You return to {area.name}."]
        else:
            parts = [area.at_a_glance]

        # Visible, non-hidden NPCs get a brief mention on entry
        visible_npcs = [n for n in area.npcs if not n.hidden]
        if visible_npcs:
            npc_line = "You notice: " + ", ".join(n.first_impression for n in visible_npcs) + "."
            parts.append(npc_line)

        # Threat telltale — something feels wrong, without spelling out the danger
        if area.threat_level != ThreatLevel.NONE and area.threat_telltale:
            parts.append(area.threat_telltale)

        return "\n\n".join(parts)

    def _session_path(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"
