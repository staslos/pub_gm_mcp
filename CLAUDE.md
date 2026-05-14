# pub-gm-mcp

This is a solo TTRPG GM assistant. All adventure sessions are run using the pub-gm-mcp MCP server.

## Running an adventure

When the user asks to run, start, play, or continue an adventure:

1. Call `get_running_guidelines` from pub-gm-mcp first — always, before anything else.
2. Use pub-gm-mcp tools exclusively for all session state: `create_session`, `enter_area`, `inspect_area`, `look_at_npc`, `introduce_npc`, `list_exits`, `add_gm_note`.
3. Never narrate area content from memory or imagination — always call the appropriate tool and narrate what it returns.

## Parsing an adventure

When the user asks to parse or import an adventure from a file or text:

1. Call `get_parsing_guidelines` from pub-gm-mcp first.
2. Use `save_adventure` and `upsert_area` to persist the structured data.
3. Call `get_adventure` to verify the result before starting any session.

## General

- This is a solo game. One player, one main character, followers managed by the GM.
- The pub-gm-mcp server is always the source of truth for adventure content and session state.
