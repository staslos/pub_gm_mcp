from __future__ import annotations
import json
import os
import uuid
from pathlib import Path

import mcp.server.stdio
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import Tool, TextContent, Resource, ReadResourceResult, TextResourceContents

from pub_gm_mcp.models.adventure import Adventure, Area
from pub_gm_mcp.models.campaign import Campaign, TravelNode
from pub_gm_mcp.models.session import Session, PartyMember
from pub_gm_mcp.models.campaign_session import CampaignSession, CampaignSessionState
from pub_gm_mcp.parser.adventure_parser import AdventureParser
from pub_gm_mcp.narrator.adventure_narrator import AdventureNarrator, NarrationError
from pub_gm_mcp.campaign import CampaignStore, CampaignNarrator
from pub_gm_mcp.campaign.campaign_narrator import CampaignNarrationError

DATA_DIR = Path(os.environ.get("PUB_GM_DATA_DIR", Path.home() / ".pub-gm-mcp"))
ADVENTURES_DIR = DATA_DIR / "adventures"
SESSIONS_DIR = DATA_DIR / "sessions"
CAMPAIGNS_DIR = DATA_DIR / "campaigns"
CAMPAIGN_SESSIONS_DIR = DATA_DIR / "campaign_sessions"
RESOURCES_DIR = Path(__file__).parent / "resources"

server = Server("pub-gm-mcp")
store = AdventureParser(ADVENTURES_DIR)
narrator = AdventureNarrator(SESSIONS_DIR, store)
campaign_store = CampaignStore(CAMPAIGNS_DIR, CAMPAIGN_SESSIONS_DIR)
campaign_narrator = CampaignNarrator(campaign_store, store)


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
            uri="pub-gm://guidelines/running",
            name="Adventure Running Guidelines",
            description=(
                "OSR-style rules for running a solo adventure session as GM. "
                "Read this before starting or resuming any session."
            ),
            mimeType="text/markdown",
        ),
        Resource(
            uri="pub-gm://schema/adventure",
            name="Adventure JSON Schema",
            description="Full JSON schema for the Adventure data model (a single explorable site).",
            mimeType="application/json",
        ),
        Resource(
            uri="pub-gm://schema/campaign",
            name="Campaign JSON Schema",
            description=(
                "Full JSON schema for the Campaign data model. "
                "A campaign links multiple Adventure sites with travel nodes."
            ),
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
    if uri == "pub-gm://guidelines/running":
        text = (RESOURCES_DIR / "running_guidelines.md").read_text()
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
    if uri == "pub-gm://schema/campaign":
        schema = Campaign.model_json_schema()
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
        # -- Guidelines (call these before parsing or running) --
        Tool(
            name="get_running_guidelines",
            description=(
                "Returns GM guidelines for running a solo adventure session. "
                "Call this before create_session or create_campaign_session."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_parsing_guidelines",
            description=(
                "Returns guidelines and adventure schema for parsing a source text into "
                "the pub-gm-mcp data model. Call this before save_adventure or upsert_area."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        # -- Adventure authoring (used by Claude when parsing a source text) --
        Tool(
            name="save_adventure",
            description=(
                "Persist a complete adventure. Pass the full adventure object. "
                "Overwrites any existing adventure with the same id. "
                "Use this to create a new adventure or replace one entirely. "
                "Call get_parsing_guidelines before parsing any adventure."
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
            description=(
                "Start a new play session for a stored adventure. "
                "Call get_running_guidelines before calling this."
            ),
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
            description=(
                "Focus attention on a specific NPC. Returns first impression and telltale hint. "
                "Never reveals the NPC's name — call introduce_npc once they give it."
            ),
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
            name="introduce_npc",
            description=(
                "Record that an NPC has revealed their name in play — call this when an NPC "
                "introduces themselves or another character names them. Returns the name."
            ),
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
            name="get_npc_name",
            description=(
                "Returns the NPC's name if the party has learned it, otherwise 'unknown'. "
                "Use this to check before using a name in narration."
            ),
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
            description="Append a freeform GM note to the adventure session log.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["session_id", "note"],
            },
        ),
        # -- Campaign authoring --
        Tool(
            name="save_campaign",
            description=(
                "Persist a complete campaign. Pass the full campaign object. "
                "Overwrites any existing campaign with the same id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign": {
                        "type": "object",
                        "description": "Full Campaign object matching the campaign schema.",
                    }
                },
                "required": ["campaign"],
            },
        ),
        Tool(
            name="upsert_travel_node",
            description="Add or replace a travel node within a stored campaign.",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                    "travel_node": {
                        "type": "object",
                        "description": "Full TravelNode object.",
                    },
                },
                "required": ["campaign_id", "travel_node"],
            },
        ),
        Tool(
            name="get_campaign",
            description="Retrieve the full stored campaign JSON.",
            inputSchema={
                "type": "object",
                "properties": {"campaign_id": {"type": "string"}},
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="delete_campaign",
            description="Permanently delete a stored campaign.",
            inputSchema={
                "type": "object",
                "properties": {"campaign_id": {"type": "string"}},
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="list_campaigns",
            description="List all stored campaign IDs.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # -- Campaign sessions --
        Tool(
            name="create_campaign_session",
            description=(
                "Start a new campaign session. "
                "Call get_running_guidelines before calling this."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
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
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="get_campaign_session_state",
            description="Return current campaign session state: position, visited nodes, active session.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        # -- Campaign narration --
        Tool(
            name="campaign_travel_to",
            description=(
                "Move the party to a campaign node (adventure site or travel node). "
                "Returns OSR at-a-glance narration for the destination."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "node_id": {"type": "string"},
                },
                "required": ["session_id", "node_id"],
            },
        ),
        Tool(
            name="campaign_inspect_node",
            description=(
                "Party looks around their current travel node. "
                "Reveals one additional detail not visible at a glance. "
                "Only valid when at a travel node, not inside an adventure site."
            ),
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        Tool(
            name="campaign_list_exits",
            description="List visible routes from the party's current campaign position.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        Tool(
            name="campaign_enter_site",
            description=(
                "Record that the party has entered the adventure site at their current position. "
                "Links the campaign session to an adventure session. "
                "Use after create_session to connect the two."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_session_id": {"type": "string"},
                    "adventure_session_id": {"type": "string"},
                },
                "required": ["campaign_session_id", "adventure_session_id"],
            },
        ),
        Tool(
            name="campaign_leave_site",
            description="Record that the party has left the current adventure site and returned to the campaign map.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        Tool(
            name="campaign_add_gm_note",
            description="Append a freeform GM note to the campaign session log.",
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
    except (NarrationError, CampaignNarrationError, FileNotFoundError, FileExistsError, ValueError) as exc:
        result = f"Error: {exc}"
    return [TextContent(type="text", text=str(result))]


async def _dispatch(name: str, args: dict) -> str:
    # -- Guidelines --

    if name == "get_running_guidelines":
        return (RESOURCES_DIR / "running_guidelines.md").read_text()

    if name == "get_parsing_guidelines":
        text = (RESOURCES_DIR / "parsing_guidelines.md").read_text()
        schema = json.dumps(Adventure.model_json_schema(), indent=2)
        return f"{text}\n\n---\n\n## Adventure JSON Schema\n\n```json\n{schema}\n```"

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
        if session.party:
            party_str = ", ".join(
                f"{m.name} ({m.description})" if m.description else m.name
                for m in session.party
            )
        else:
            party_str = "none"
        lines = [
            f"Adventure: {session.adventure_id}",
            f"Party: {party_str}",
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

    if name == "introduce_npc":
        session = narrator.load_session(args["session_id"])
        return narrator.introduce_npc(session, args["npc_id"])

    if name == "get_npc_name":
        session = narrator.load_session(args["session_id"])
        return narrator.get_npc_name(session, args["npc_id"])

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

    # -- Campaign authoring --

    if name == "save_campaign":
        campaign = Campaign.model_validate(args["campaign"])
        campaign_store.save_campaign(campaign)
        node_count = len(campaign.travel_nodes) + len(campaign.adventure_ids)
        return f"Campaign '{campaign.id}' saved ({node_count} nodes)."

    if name == "upsert_travel_node":
        campaign_id = args["campaign_id"]
        node = TravelNode.model_validate(args["travel_node"])
        campaign = campaign_store.load_campaign(campaign_id)
        existing = next((i for i, n in enumerate(campaign.travel_nodes) if n.id == node.id), None)
        if existing is not None:
            campaign.travel_nodes[existing] = node
            action = "updated"
        else:
            campaign.travel_nodes.append(node)
            action = "added"
        campaign_store.save_campaign(campaign)
        return f"Travel node '{node.id}' {action} in campaign '{campaign_id}'."

    if name == "get_campaign":
        campaign = campaign_store.load_campaign(args["campaign_id"])
        return campaign.model_dump_json(indent=2)

    if name == "delete_campaign":
        campaign_store.delete_campaign(args["campaign_id"])
        return f"Campaign '{args['campaign_id']}' deleted."

    if name == "list_campaigns":
        campaigns = campaign_store.list_campaigns()
        return "\n".join(campaigns) if campaigns else "No campaigns stored."

    # -- Campaign sessions --

    if name == "create_campaign_session":
        campaign_id = args["campaign_id"]
        party = [PartyMember(**m) for m in args.get("party", [])]
        campaign = campaign_store.load_campaign(campaign_id)
        session = CampaignSession(
            id=str(uuid.uuid4())[:8],
            campaign_id=campaign_id,
            party=party,
            state=CampaignSessionState(current_node_id=campaign.starting_node_id),
        )
        campaign_store.save_session(session)
        return f"Campaign session '{session.id}' created for '{campaign_id}'."

    if name == "get_campaign_session_state":
        session = campaign_store.load_session(args["session_id"])
        s = session.state
        lines = [
            f"Campaign: {session.campaign_id}",
            f"Current node: {s.current_node_id or 'none'}",
            f"In adventure site: {s.in_adventure}",
            f"Active adventure session: {s.active_session_id or 'none'}",
            f"Visited adventure sites: {', '.join(s.visited_adventure_ids) or 'none'}",
            f"GM notes: {len(s.gm_notes)}",
        ]
        return "\n".join(lines)

    # -- Campaign narration --

    if name == "campaign_travel_to":
        session = campaign_store.load_session(args["session_id"])
        return campaign_narrator.travel_to_node(session, args["node_id"])

    if name == "campaign_inspect_node":
        session = campaign_store.load_session(args["session_id"])
        return campaign_narrator.inspect_travel_node(session)

    if name == "campaign_list_exits":
        session = campaign_store.load_session(args["session_id"])
        exits = campaign_narrator.list_exits(session)
        if not exits:
            return "No visible routes from here."
        lines = [
            f"- {e['label']} → {e['to']}" + (f" ({e['travel_time']})" if e["travel_time"] else "")
            for e in exits
        ]
        return "\n".join(lines)

    if name == "campaign_enter_site":
        session = campaign_store.load_session(args["campaign_session_id"])
        return campaign_narrator.enter_adventure_site(session, args["adventure_session_id"])

    if name == "campaign_leave_site":
        session = campaign_store.load_session(args["session_id"])
        return campaign_narrator.leave_adventure_site(session)

    if name == "campaign_add_gm_note":
        session = campaign_store.load_session(args["session_id"])
        session.state.gm_notes.append(args["note"])
        campaign_store.save_session(session)
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
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
