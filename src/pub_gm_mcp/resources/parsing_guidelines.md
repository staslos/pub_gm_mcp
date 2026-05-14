# Adventure Parsing Guidelines

You are reading a published TTRPG adventure and converting it into the pub-gm-mcp
adventure schema. Follow these rules precisely.

---

## Core principle: OSR information discipline

Published adventures describe everything the author imagined. Your job is NOT to
preserve that prose — it is to decide **what a party perceives at a glance** versus
**what requires active investigation**.

The GM never volunteers information. Players earn it through declared actions.

---

## Area parsing rules

### `at_a_glance`
Write what hits the senses in the first 2–3 seconds of entering: dominant sight,
smell, sound, temperature. One to three sentences. No adjective stacking.
Do NOT include:
- Things that require looking closely
- Contents of containers
- Hidden objects
- NPC motivations or backstory
- Game-mechanical information

Good: `"A low-ceilinged room smelling of damp stone. A single torch gutters near the far wall. Something has been dragged across the dust."`

Bad: `"A 20×30 dungeon room with 2 hobgoblins guarding a chest containing 300gp and a +1 sword."`

### `details`
Everything that rewards a careful look or a stated action ("I search the room",
"I examine the altar"). Each entry is one discrete discoverable fact. Order from
most to least obvious. Keep hidden items out of here — they go in `items` with
`hidden: true`.

### `threat_level`
- `none` — genuinely safe
- `subtle` — something is wrong but not visible (eerie silence, animals won't enter)
- `present` — signs of danger are visible (blood, weapon marks, dead bodies)
- `immediate` — active threat is visible or about to trigger

### `threat_telltale`
A single sensory observation that signals danger without naming it.
Write it as what a character notices, not a GM warning.

Good: `"The candles here have all burned down to stubs, but there is no wax on the floor."`

Bad: `"Warning: there is a monster here."`

Set to `null` if `threat_level` is `none`.

---

## NPC parsing rules

### `first_impression`
What the party sees when they first lay eyes on this person. Posture, activity,
one physical detail. Written as an observation, present tense.

Good: `"An old man sits with his back to the wall, both hands visible on the table."`

### `telltale`
One subtle observation that hints at the NPC's true nature, role, or danger —
without stating it. May be `null` if the NPC is genuinely unremarkable.

Good: `"His nails are clean but his hands are scarred in a pattern that suggests a lifetime of sword work, not farming."`

### `hidden`
Set to `true` for NPCs that are concealed, disguised, or only present under
specific conditions. Do not include them in `at_a_glance`.

---

## Item parsing rules

### `hidden`
Set to `true` for anything that requires searching, moving furniture, picking
locks, or other declared action. Hidden items must NOT appear in `at_a_glance`
or `details`.

### `description`
Physical description only — what it looks like, feels like, smells like.
No game statistics. No value in gold pieces.

---

## Connection parsing rules

Every door, passage, staircase, or traversable feature gets its own `Connection`.
`label` is the physical description from inside the current area: `"iron door to
the north"`, `"ladder descending into darkness"`.

`hidden: true` for concealed doors and passages.
`locked: true` + `locked_description` for anything that requires a key, force,
or special action to open.

---

## ID conventions

Use lowercase with underscores. Be descriptive and unique within the adventure.

- Areas: `entrance_hall`, `crypt_of_aldric`, `tavern_common_room`
- NPCs: `barkeep_marta`, `ghost_of_aldric`, `suspicious_traveller`
- Items: `iron_key`, `merchants_ledger`, `altar_candle`

---

## What to ignore

- Room dimensions and grid coordinates
- Game-mechanical stats, hit points, armor class
- Read-aloud boxed text — treat it as a starting point, not the final `at_a_glance`
- Author's GM notes about player psychology or "how to run this encounter"
- Treasure values in gold pieces (keep item descriptions, drop the numbers)

---

## Workflow

1. Read the full adventure first to understand scope and connections.
2. Create the adventure shell with `save_adventure` (id, title, synopsis, system).
3. Add areas one at a time with `upsert_area`, working from entrance inward.
4. After all areas are saved, verify connections are bidirectional where appropriate.
5. Call `get_adventure` to review the saved structure before starting a session.
