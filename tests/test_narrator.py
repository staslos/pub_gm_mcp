"""Tests for AdventureNarrator — OSR narration correctness."""
import pytest
from pub_gm_mcp.narrator.adventure_narrator import NarrationError


class TestEnterArea:
    def test_returns_at_a_glance(self, narrator, session):
        result = narrator.enter_area(session, "test_room")
        assert "A stone room. Smells of damp." in result

    def test_visible_npc_appears(self, narrator, session):
        result = narrator.enter_area(session, "test_room")
        assert "leans against the wall" in result

    def test_hidden_npc_suppressed(self, narrator, session):
        """Hidden NPCs must never appear in the at-a-glance narration."""
        result = narrator.enter_area(session, "test_room")
        assert "watches from the shadows" not in result

    def test_threat_telltale_included_when_threat_present(self, narrator, session):
        result = narrator.enter_area(session, "test_room")
        assert "Something feels off." in result

    def test_threat_telltale_absent_when_no_threat(self, narrator, session):
        result = narrator.enter_area(session, "next_room")
        # next_room has threat_level=NONE and no telltale
        assert result.count("\n\n") == 0 or "feels off" not in result

    def test_sets_current_area(self, narrator, session):
        narrator.enter_area(session, "test_room")
        loaded = narrator.load_session(session.id)
        assert loaded.state.current_area_id == "test_room"

    def test_marks_area_visited(self, narrator, session):
        narrator.enter_area(session, "test_room")
        loaded = narrator.load_session(session.id)
        assert loaded.state.area_states["test_room"].visited is True

    def test_first_visit_differs_from_revisit(self, narrator, session):
        """First visit and revisit must produce different narration (first-visit bug guard)."""
        first = narrator.enter_area(session, "test_room")
        # reload session so narrator picks up the saved visited=True state
        session = narrator.load_session(session.id)
        revisit = narrator.enter_area(session, "test_room")
        assert first != revisit

    def test_unknown_area_raises(self, narrator, session):
        with pytest.raises(NarrationError, match="not found"):
            narrator.enter_area(session, "nonexistent_area")

    def test_saves_session_on_entry(self, narrator, session):
        narrator.enter_area(session, "test_room")
        loaded = narrator.load_session(session.id)
        assert loaded.state.current_area_id == "test_room"


class TestInspectArea:
    def _enter(self, narrator, session):
        narrator.enter_area(session, "test_room")
        return narrator.load_session(session.id)

    def test_reveals_first_detail(self, narrator, session):
        session = self._enter(narrator, session)
        result = narrator.inspect_area(session)
        assert result == "A scratch on the wall."

    def test_reveals_second_detail_on_second_call(self, narrator, session):
        session = self._enter(narrator, session)
        narrator.inspect_area(session)
        session = narrator.load_session(session.id)
        result = narrator.inspect_area(session)
        assert result == "A loose flagstone."

    def test_exhaustion_message_after_all_details(self, narrator, session):
        session = self._enter(narrator, session)
        for _ in range(3):  # sample_area has 3 details
            narrator.inspect_area(session)
            session = narrator.load_session(session.id)
        result = narrator.inspect_area(session)
        assert "nothing more" in result.lower() or "everything" in result.lower()

    def test_persists_revealed_indices(self, narrator, session):
        session = self._enter(narrator, session)
        narrator.inspect_area(session)
        loaded = narrator.load_session(session.id)
        assert 0 in loaded.state.area_states["test_room"].revealed_detail_indices

    def test_no_details_returns_exhaustion_immediately(self, narrator, session):
        narrator.enter_area(session, "next_room")
        session = narrator.load_session(session.id)
        result = narrator.inspect_area(session)
        assert "nothing more" in result.lower() or "everything" in result.lower()

    def test_no_current_area_raises(self, narrator, session):
        with pytest.raises(NarrationError):
            narrator.inspect_area(session)


class TestLookAtNpc:
    def _enter(self, narrator, session):
        narrator.enter_area(session, "test_room")
        return narrator.load_session(session.id)

    def test_returns_first_impression(self, narrator, session):
        session = self._enter(narrator, session)
        result = narrator.look_at_npc(session, "visible_guard")
        assert "leans against the wall" in result

    def test_returns_telltale_when_present(self, narrator, session):
        session = self._enter(narrator, session)
        result = narrator.look_at_npc(session, "visible_guard")
        assert "calloused" in result

    def test_does_not_reveal_name(self, narrator, session):
        session = self._enter(narrator, session)
        result = narrator.look_at_npc(session, "visible_guard")
        assert "Guard" not in result

    def test_marks_npc_revealed(self, narrator, session):
        session = self._enter(narrator, session)
        narrator.look_at_npc(session, "visible_guard")
        loaded = narrator.load_session(session.id)
        assert "visible_guard" in loaded.state.area_states["test_room"].revealed_npc_ids

    def test_unknown_npc_raises(self, narrator, session):
        session = self._enter(narrator, session)
        with pytest.raises(NarrationError, match="not present"):
            narrator.look_at_npc(session, "nonexistent_npc")


class TestNpcNameGating:
    def _enter(self, narrator, session):
        narrator.enter_area(session, "test_room")
        return narrator.load_session(session.id)

    def test_name_unknown_before_introduction(self, narrator, session):
        session = self._enter(narrator, session)
        result = narrator.get_npc_name(session, "visible_guard")
        assert result == "unknown"

    def test_name_returned_after_introduction(self, narrator, session):
        session = self._enter(narrator, session)
        name = narrator.introduce_npc(session, "visible_guard")
        assert name == "Guard"

    def test_name_accessible_after_introduction(self, narrator, session):
        session = self._enter(narrator, session)
        narrator.introduce_npc(session, "visible_guard")
        session = narrator.load_session(session.id)
        result = narrator.get_npc_name(session, "visible_guard")
        assert result == "Guard"

    def test_introduce_npc_is_idempotent(self, narrator, session):
        session = self._enter(narrator, session)
        narrator.introduce_npc(session, "visible_guard")
        session = narrator.load_session(session.id)
        narrator.introduce_npc(session, "visible_guard")
        session = narrator.load_session(session.id)
        count = session.state.area_states["test_room"].named_npc_ids.count("visible_guard")
        assert count == 1

    def test_unknown_npc_name_raises(self, narrator, session):
        session = self._enter(narrator, session)
        with pytest.raises(NarrationError):
            narrator.get_npc_name(session, "nonexistent")


class TestListVisibleExits:
    def _enter(self, narrator, session):
        narrator.enter_area(session, "test_room")
        return narrator.load_session(session.id)

    def test_visible_exit_included(self, narrator, session):
        session = self._enter(narrator, session)
        exits = narrator.list_visible_exits(session)
        labels = [e["label"] for e in exits]
        assert "north door" in labels

    def test_hidden_exit_excluded(self, narrator, session):
        session = self._enter(narrator, session)
        exits = narrator.list_visible_exits(session)
        labels = [e["label"] for e in exits]
        assert "hidden panel" not in labels

    def test_locked_exit_included_with_flag(self, narrator, session):
        session = self._enter(narrator, session)
        exits = narrator.list_visible_exits(session)
        locked = next(e for e in exits if e["label"] == "iron door")
        assert locked["locked"] is True

    def test_no_current_area_raises(self, narrator, session):
        with pytest.raises(NarrationError):
            narrator.list_visible_exits(session)
