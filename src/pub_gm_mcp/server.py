from __future__ import annotations
import os
import uuid
from pathlib import Path

import mcp.server.stdio
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

from pub_gm_mcp.models.adventure import Adventure, Area, NPC, Item, Connection, ThreatLevel
from pub_gm_mcp.models.session import Session, SessionState, PartyMember
from pub_gm_mcp.parser.adventure_parser import AdventureParser
from pub_gm_mcp.narrator.adventure_narrator import AdventureNarrator, NarrationError

DATA_DIR = Path(os.environ.get("PUB_GM_DATA_DIR", Path.home() / ".pub-gm-mcp"))
ADVENTURES_DIR = DATA_DIR / "adventures"
SESSIONS_DIR = DATA_DIR / "sessions"

server = Server("pub-gm-mcp")
parser = AdventureParser(ADVENTURES_DIR)
narrator = AdventureNarrator(SESSIONS_DIR, parser)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_adventures",
            description="List all available adventure modules.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_sessions",
            description="List all active or past sessions.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="create_session",
            description="Start a new session for a given adventure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "adventure_id": {"type": "string"},
                    "party": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                },
                "required": ["adventure_id"],
            },
        ),
        Tool(
            name="enter_area",
            description=(
                "Move the party into an area and receive an OSR-style at-a-glance narration: "
                "first impression, standing features, and any threat telltale."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "area_id": {"type": "string"},
                },
                "required": ["session_id", "area_id"],
            },
        ),
        Tool(
            name="inspect_area",
            description=(
                "Party takes a careful look around the current area. "
                "Reveals one additional detail not visible at a glance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="look_at_npc",
            description="Focus attention on a specific NPC to learn more about them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "npc_id": {"type": "string"},
                },
                "required": ["session_id", "npc_id"],
            },
        ),
        Tool(
            name="list_exits",
            description="List the visible exits from the party's current location.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="add_gm_note",
            description="Append a freeform GM note to the current session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["session_id", "note"],
            },
        ),
        Tool(
            name="get_session_state",
            description="Return the current session state (location, visited areas, inventory).",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
    except (NarrationError, FileNotFoundError, FileExistsError, ValueError) as exc:
        result = f"Error: {exc}"
    return [TextContent(type="text", text=str(result))]


async def _dispatch(name: str, args: dict) -> str:
    if name == "list_adventures":
        adventures = parser.list_adventures()
        return "\n".join(adventures) if adventures else "No adventures found."

    if name == "list_sessions":
        sessions = narrator.list_sessions()
        return "\n".join(sessions) if sessions else "No sessions found."

    if name == "create_session":
        adventure_id = args["adventure_id"]
        party = [PartyMember(**m) for m in args.get("party", [])]
        session = Session(
            id=str(uuid.uuid4())[:8],
            adventure_id=adventure_id,
            party=party,
        )
        # Set starting area if adventure defines one
        adventure = parser.load(adventure_id)
        if adventure.starting_area_id:
            session.state.current_area_id = adventure.starting_area_id
        narrator.create_session(session)
        return f"Session '{session.id}' created for adventure '{adventure_id}'."

    if name == "enter_area":
        session = narrator.load_session(args["session_id"])
        return narrator.enter_area(session, args["area_id"])

    if name == "inspect_area":
        session = narrator.load_session(args["session_id"])
        return narrator.inspect_area(session)

    if name == "look_at_npc":
        session = narrator.load_session(args["session_id"])
        return narrator.look_at_npc(session, args["npc_id"])

    if name == "list_exits":
        session = narrator.load_session(args["session_id"])
        exits = narrator.list_visible_exits(session)
        if not exits:
            return "No visible exits."
        lines = [f"- {e['label']} → {e['target']}" + (" [locked]" if e["locked"] else "") for e in exits]
        return "\n".join(lines)

    if name == "add_gm_note":
        session = narrator.load_session(args["session_id"])
        session.state.gm_notes.append(args["note"])
        narrator.save_session(session)
        return "Note added."

    if name == "get_session_state":
        session = narrator.load_session(args["session_id"])
        s = session.state
        lines = [
            f"Adventure: {session.adventure_id}",
            f"Current area: {s.current_area_id or 'none'}",
            f"Visited areas: {', '.join(s.area_states.keys()) or 'none'}",
            f"Party inventory: {', '.join(s.party_inventory.keys()) or 'empty'}",
            f"GM notes: {len(s.gm_notes)}",
        ]
        return "\n".join(lines)

    raise ValueError(f"Unknown tool: {name}")


def main() -> None:
    import asyncio

    async def run() -> None:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="pub-gm-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
