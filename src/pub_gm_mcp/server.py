from __future__ import annotations
import json
import os
import uuid
from pathlib import Path

import mcp.server.stdio
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, Resource, ReadResourceResult, TextResourceContents

from pub_gm_mcp.models.adventure import Adventure, Area
from pub_gm_mcp.models.session import Session, PartyMember
from pub_gm_mcp.parser.adventure_parser import AdventureParser
from pub_gm_mcp.narrator.adventure_narrator import AdventureNarrator, NarrationError

DATA_DIR = Path(os.environ.get("PUB_GM_DATA_DIR", Path.home() / ".pub-gm-mcp"))
ADVENTURES_DIR = DATA_DIR / "adventures"
SESSIONS_DIR = DATA_DIR / "sessions"
RESOURCES_DIR = Path(__file__).parent / "resources"

server = Server("pub-gm-mcp")
store = AdventureParser(ADVENTURES_DIR)
narrator = AdventureNarrator(SESSIONS_DIR, store)


# ---------------------------------------------------------------------------
# Resources — static context Claude reads when connecting
# ---------------------------------------------------------------------------

@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="pub-gm://guidelines/parsing",
            name="Adventure Parsing Guidelines",
            description=(
                "OSR-style rules for converting a published adventure into the "
                "pub-gm-mcp data model. Read this before parsing any adventure."
            ),
            mimeType="text/markdown",
        ),
        Resource(
            uri="pub-gm://schema/adventure",
            name="Adventure JSON Schema",
            description="Full JSON schema for the Adventure data model.",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    if uri == "pub-gm://guidelines/parsing":
        text = (RESOURCES_DIR / "parsing_guidelines.md").read_text()
        return ReadResourceResult(
            contents=[TextResourceContents(uri=uri, mimeType="text/markdown", text=text)]
        )
    if uri == "pub-gm://schema/adventure":
        schema = Adventure.model_json_schema()
        return ReadResourceResult(
            contents=[TextResourceContents(
                uri=uri,
                mimeType="application/json",
                text=json.dumps(schema, indent=2),
            )]
        )
    raise ValueError(f"Unknown resource: {uri}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # -- Adventure authoring (used by Claude when parsing a source text) --
        Tool(
            name="save_adventure",
            description=(
                "Persist a complete adventure. Pass the full adventure object. "
                "Overwrites any existing adventure with the same id. "
                "Use this to create a new adventure or replace one entirely."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "adventure": {
                        "type": "object",
                        "description": "Full Adventure object matching the adventure schema.",
                    }
                },
                "required": ["adventure"],
            },
        ),
        Tool(
            name="upsert_area",
            description=(
                "Add or replace a single area within a stored adventure. "
                "Use this to build an adventure incrementally, one area at a time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "adventure_id": {"type": "string"},
                    "area": {
                        "type": "object",
                        "description": "Full Area object matching the adventure schema.",
                    },
                },
                "required": ["adventure_id", "area"],
            },
        ),
        Tool(
            name="get_adventure",
            description=(
                "Retrieve the full stored adventure JSON. "
                "Use this to review what has been saved before starting a session or continuing parsing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "adventure_id": {"type": "string"},
                },
                "required": ["adventure_id"],
            },
        ),
        Tool(
            name="delete_adventure",
            description="Permanently delete a stored adventure and all its data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "adventure_id": {"type": "string"},
                },
                "required": ["adventure_id"],
            },
        ),
        Tool(
            name="list_adventures",
            description="List all stored adventure IDs.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # -- Session lifecycle --
        Tool(
            name="create_session",
            description="Start a new play session for a stored adventure.",
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
            name="list_sessions",
            description="List all session IDs.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_session_state",
            description="Return current session state: location, visited areas, inventory, note count.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        # -- Narration (used during play) --
        Tool(
            name="enter_area",
            description=(
                "Move the party into an area. Returns OSR at-a-glance narration: "
                "immediate sensory impression, visible NPCs, and threat telltale if present. "
                "Does NOT reveal details, hidden items, or hidden NPCs."
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
                "Party takes a careful look around. Reveals the next unrevealed detail. "
                "Call repeatedly; each call surfaces one more observation."
            ),
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        Tool(
            name="look_at_npc",
            description="Focus attention on a specific NPC. Returns first impression and telltale hint.",
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
            description="List visible exits from the current area.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        Tool(
            name="add_gm_note",
            description="Append a freeform GM note to the session log.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["session_id", "note"],
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
    # -- Adventure authoring --

    if name == "save_adventure":
        adventure = Adventure.model_validate(args["adventure"])
        store.save(adventure)
        area_count = len(adventure.areas)
        return f"Adventure '{adventure.id}' saved ({area_count} area{'s' if area_count != 1 else ''})."

    if name == "upsert_area":
        adventure_id = args["adventure_id"]
        area = Area.model_validate(args["area"])
        adventure = store.load(adventure_id)
        existing = next((i for i, a in enumerate(adventure.areas) if a.id == area.id), None)
        if existing is not None:
            adventure.areas[existing] = area
            action = "updated"
        else:
            adventure.areas.append(area)
            action = "added"
        store.save(adventure)
        return f"Area '{area.id}' {action} in adventure '{adventure_id}'."

    if name == "get_adventure":
        adventure = store.load(args["adventure_id"])
        return adventure.model_dump_json(indent=2)

    if name == "delete_adventure":
        store.delete(args["adventure_id"])
        return f"Adventure '{args['adventure_id']}' deleted."

    if name == "list_adventures":
        adventures = store.list_adventures()
        return "\n".join(adventures) if adventures else "No adventures stored."

    # -- Session lifecycle --

    if name == "create_session":
        adventure_id = args["adventure_id"]
        party = [PartyMember(**m) for m in args.get("party", [])]
        adventure = store.load(adventure_id)
        session = Session(
            id=str(uuid.uuid4())[:8],
            adventure_id=adventure_id,
            party=party,
        )
        if adventure.starting_area_id:
            session.state.current_area_id = adventure.starting_area_id
        narrator.create_session(session)
        return f"Session '{session.id}' created for '{adventure_id}'."

    if name == "list_sessions":
        sessions = narrator.list_sessions()
        return "\n".join(sessions) if sessions else "No sessions found."

    if name == "get_session_state":
        session = narrator.load_session(args["session_id"])
        s = session.state
        lines = [
            f"Adventure: {session.adventure_id}",
            f"Current area: {s.current_area_id or 'none'}",
            f"Visited areas: {', '.join(s.area_states.keys()) or 'none'}",
            f"Inventory: {', '.join(s.party_inventory.keys()) or 'empty'}",
            f"GM notes: {len(s.gm_notes)}",
        ]
        return "\n".join(lines)

    # -- Narration --

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
        lines = [
            f"- {e['label']} → {e['target']}" + (" [locked]" if e["locked"] else "")
            for e in exits
        ]
        return "\n".join(lines)

    if name == "add_gm_note":
        session = narrator.load_session(args["session_id"])
        session.state.gm_notes.append(args["note"])
        narrator.save_session(session)
        return "Note added."

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
