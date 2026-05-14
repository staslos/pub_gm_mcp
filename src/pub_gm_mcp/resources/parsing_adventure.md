# Parsing workflow in a new Claude Desktop conversation

1. Attach your adventure file (PDF or text — Claude Desktop handles both)
2. Start with a prompt like:

> *"Before parsing, read the resources at `pub-gm://guidelines/parsing` and `pub-gm://schema/adventure` from the pub-gm-mcp server, then parse this adventure and persist it using the MCP tools."*

That one prompt does everything: fetches the rules, reads the file, builds the JSON, calls `save_adventure` + `upsert_area`.

**File format tips:**
- PDF works well for most published adventures
- If it's a large adventure, Claude will parse area by area using `upsert_area` rather than one big `save_adventure` call — that's expected and fine

Want to try it now with a file, or is there anything you want to adjust in the parsing guidelines first?