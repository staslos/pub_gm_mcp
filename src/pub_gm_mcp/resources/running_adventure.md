For a **new conversation** in Claude Desktop, just say something like:

> *"Start a session for the `a_tiny_rescue` adventure and narrate it."*

Claude will call `create_session` and `enter_area` on its own. No resource prompts needed this time — those are only required when **parsing** a new adventure, so Claude knows the schema and OSR rules. For **playing**, the tools are self-describing enough.

The only thing to be aware of: if it's a fresh Claude Desktop conversation, Claude won't remember the session ID from before. It'll just create a new one — which is correct, that's a new session.

Two options depending on how you want to run it:

---

**Option A — Single adventure** (just dive into one chapter, no campaign map)

1. `create_session` with `adventure_id: "a_tiny_rescue"` — optionally name your party members
2. `enter_area` with the session id and `area_id: "valeys_rest_inn"`
3. Play from there

---

**Option B — Full campaign** (travel between sites, the whole arc)

1. `create_campaign_session` with `campaign_id: "garden_of_death"` — sets you at the starting node
2. When the party reaches an adventure site, `create_session` for that adventure
3. `campaign_enter_site` to link the two sessions together
4. `enter_area` to step inside
5. When they leave, `campaign_leave_site` — back to the campaign map
6. `campaign_travel_to` to move to the next node

---

For a first playthrough, **Option A** is the right call — start with `a_tiny_rescue`, get a feel for the narration, and worry about the campaign layer when the party is actually heading into the Elderwild.

Just say the word and I'll kick it off.