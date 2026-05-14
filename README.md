# pub-gm-mcp

An MCP server that turns Claude Desktop into an OSR-style Game Master for published TTRPG adventures.

You provide the adventure text. Claude parses it, persists the structured data, and runs narration during play — following Old School Renaissance principles: information is earned, danger is real, and the GM never volunteers what the players haven't looked for.

---

## How it works

```
Published adventure (PDF/text)
        ↓
   Claude Desktop          ← reads parsing guidelines + schema from MCP resources
        ↓
   MCP write tools         ← save_adventure, upsert_area
        ↓
   JSON on disk            ← data/adventures/<id>.json
        ↓
   MCP narration tools     ← enter_area, inspect_area, look_at_npc, ...
        ↓
   Claude narrates play
```

**Claude is the parser and narrator. The MCP server is storage and rules.**

---

## Architecture

```
src/pub_gm_mcp/
├── server.py               # MCP server — tools and resources
├── models/
│   ├── adventure.py        # Adventure, Area, NPC, Item, Connection
│   ├── session.py          # Session, SessionState, AreaState
│   ├── campaign.py         # Campaign, TravelNode, CampaignConnection
│   └── campaign_session.py # CampaignSession, CampaignSessionState
├── parser/
│   └── adventure_parser.py # Adventure file I/O (load/save JSON)
├── narrator/
│   └── adventure_narrator.py # OSR narration engine
├── campaign/
│   ├── campaign_store.py   # Campaign + campaign session file I/O
│   └── campaign_narrator.py # Campaign-level travel narration
└── resources/
    └── parsing_guidelines.md # OSR parsing rules served as MCP resource
```

### Data hierarchy

```
Campaign
├── adventure_ids           → references to stored Adventures
├── travel_nodes            → wilderness, roads, landmarks between sites
└── connections             → edges between any two nodes

Adventure  (single explorable site)
└── areas
    ├── at_a_glance         → immediate sensory impression (OSR entry)
    ├── details             → revealed one at a time through player action
    ├── npcs                → first_impression + telltale (name gated until introduced)
    ├── items               → hidden items require declared action to find
    └── connections         → doors, passages, exits
```

### Session hierarchy

```
CampaignSession             → position on campaign map, active adventure session
└── Session                 → position inside a single adventure site
    └── AreaState           → what the party has revealed per area
```

---

## Setup

**Requirements:** Python 3.11+

```bash
git clone <repo>
cd pub-gm-mcp
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pub-gm-mcp": {
      "command": "/path/to/pub-gm-mcp/.venv/bin/python",
      "args": ["-m", "pub_gm_mcp.server"],
      "env": {
        "PUB_GM_DATA_DIR": "/path/to/pub-gm-mcp/data"
      }
    }
  }
}
```

Restart Claude Desktop. Check `~/Library/Logs/Claude/mcp-server-pub-gm-mcp.log` if it doesn't connect.

---

## Parsing a new adventure

In a new Claude Desktop conversation, attach your adventure file (PDF or text) and say:

> *"Before parsing, read the resources at `pub-gm://guidelines/parsing` and `pub-gm://schema/adventure` from the pub-gm-mcp server, then parse this adventure and persist it using the MCP tools."*

That one prompt does everything: fetches the OSR rules and schema, reads the file, builds the structured JSON, and persists it.

Claude will:
1. Read the OSR parsing guidelines and adventure schema from the MCP server
2. Parse the adventure text applying OSR information discipline
3. Call `save_adventure` + `upsert_area` to persist it area by area
4. Call `get_adventure` to verify the result

**File format tips:**
- PDF works well for most published adventures
- For large adventures, Claude will parse area by area using `upsert_area` rather than one big `save_adventure` call — that's expected and fine

For a multi-site campaign, also read `pub-gm://schema/campaign` and follow up with `save_campaign`.

---

## Running an adventure

In a new Claude Desktop conversation, just say:

> *"Start a session for the `my_adventure` adventure and narrate it."*

Claude will call `create_session` and `enter_area` on its own. No resource prompts needed for play — those are only required when parsing. For playing, the tools are self-describing enough.

> **Note:** Each new Claude Desktop conversation starts fresh. Claude won't remember a previous session ID — it will create a new one, which is correct behaviour.

### Option A — Single adventure *(recommended for first playthrough)*

```
create_session  adventure_id="my_adventure"  party=[...]
enter_area      session_id="..."  area_id="starting_area"
```

### Option B — Full campaign *(travel between multiple sites)*

```
create_campaign_session  campaign_id="my_campaign"  party=[...]
campaign_travel_to       session_id="..."  node_id="first_site"
create_session           adventure_id="first_site"
campaign_enter_site      campaign_session_id="..."  adventure_session_id="..."
enter_area               session_id="..."  area_id="starting_area"
```

When leaving a site: `campaign_leave_site` → `campaign_travel_to` → repeat.

---

## OSR narration principles

- **`enter_area`** — at-a-glance only: dominant sense, visible NPCs, threat telltale. Nothing hidden.
- **`inspect_area`** — reveals one detail per call. Players must declare they're looking.
- **`look_at_npc`** — first impression + telltale hint. Never reveals the NPC's name.
- **`introduce_npc`** — call when an NPC gives their name in play. Only then is it available.
- **`list_exits`** — visible exits only. Hidden doors stay hidden until found.

The GM never volunteers information. Every detail is earned.

---

## MCP tools reference

| Tool | Purpose |
|------|---------|
| `save_adventure` | Persist a complete adventure (overwrites) |
| `upsert_area` | Add or replace a single area |
| `get_adventure` | Retrieve full adventure JSON |
| `delete_adventure` | Remove an adventure |
| `list_adventures` | List all stored adventure IDs |
| `save_campaign` | Persist a complete campaign |
| `upsert_travel_node` | Add or replace a travel node |
| `get_campaign` | Retrieve full campaign JSON |
| `delete_campaign` | Remove a campaign |
| `list_campaigns` | List all stored campaign IDs |
| `create_session` | Start an adventure session |
| `get_session_state` | Current location, inventory, notes |
| `enter_area` | Move party, get at-a-glance narration |
| `inspect_area` | Reveal next detail in current area |
| `look_at_npc` | Get NPC impression + telltale |
| `introduce_npc` | Record NPC name revealed in play |
| `get_npc_name` | Check if party knows an NPC's name |
| `list_exits` | Visible exits from current area |
| `add_gm_note` | Append note to session log |
| `create_campaign_session` | Start a campaign session |
| `get_campaign_session_state` | Campaign position and status |
| `campaign_travel_to` | Move to a campaign node |
| `campaign_inspect_node` | Reveal detail at travel node |
| `campaign_list_exits` | Visible routes from current node |
| `campaign_enter_site` | Link campaign session to adventure session |
| `campaign_leave_site` | Return to campaign map |
| `campaign_add_gm_note` | Append note to campaign session |

## MCP resources

| URI | Content |
|-----|---------|
| `pub-gm://guidelines/parsing` | OSR parsing rules — read before parsing any adventure |
| `pub-gm://schema/adventure` | Adventure JSON schema |
| `pub-gm://schema/campaign` | Campaign JSON schema |

---

## Data storage

```
data/
├── adventures/         # <adventure_id>.json
├── sessions/           # <session_id>.json  (gitignored)
├── campaigns/          # <campaign_id>.json
└── campaign_sessions/  # <session_id>.json  (gitignored)
```

Adventures and campaigns are version-controlled. Session state is local only.
