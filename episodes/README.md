# Story World episodes: "المحرّك" (CEOS Engine)

One world, many episodes. The world (`worlds/ceos-engine/`) is drawn once in code/SVG; an episode is a JSON file
that says what is said, where the camera goes, and what changes on which spoken word.

```
python3 reel.py episode episodes/ep002.json --build   # build only (fast check)
python3 reel.py episode episodes/ep002.json           # build → mix → render → episodes/ep002/exports/vNNN.mp4
```

## Making Episode 002: edit only the JSON

1. Copy `episodes/ep001.json` to `episodes/ep002.json`; set `"episode": "002"`.
2. **Global state** (`data`):
   - `counter`: where the HUD starts (e.g. `137`). Western digits are drawn automatically: `137 / 10,000`.
   - `queue`: brand names already inside, in order (e.g. `["هدوم", "سكين كير"]`). These slots are lit from the start.
   - `drawer135`: `{"state": "sealed", "lines": 0}`. Raise `lines` to show how many lines are written inside
     (amber lines on the drawer face).
   - `handle`: `@CreativeEngineOS`.
3. **Lines** (`lines[]`): each line has
   - `text`: the exact words. The voice reads them as written.
   - `tag` (optional): an unspoken eleven_v3 delivery tag, e.g. `[fast-paced]`, `[whispers]`.
   - `keys`: words shown in lime in the captions.
   - `cam`: `{"shot": "wide|wide_far|module|slot|slot_tray|tray|engine_module|grid_corridor|corridor_start|corridor_end|drawer|drawer_close|drawer_up", "move": "drift|push|pull|travel|cut", "at": "<word>", "until": "<word>" | "dur": s}`.
     A whoosh is added to every move automatically (`"whoosh": false` to skip it).
   - `events`: state changes, each `{"do": ..., "at": "<word in this line>"}` (or `"start"`/`"end"`, plus `"offset"`).
     Use `{"word": "حلقة", "nth": 2}` for a repeated word. Times always come from the voice, never hand-typed seconds.
   - `sfx`: `{"kind": "clunk|ignite|tick|drop|pulse|swoosh", "at": "<word>", "gain": -15}`.
4. Run the build; fix any "no word …" error (the anchor must be a word of that line), then render.

### Event reference (world components)
| do | what | options |
|---|---|---|
| `core.pulse` / `core.active` / `core.idle` | the engine core (always running, never off) | |
| `grid.scan` / `grid.lit` / `grid.dim` | the 10,000 slots: a faint wave, light all, back to dim | `dur` |
| `you.on` / `you.off` | the single "براندك" slot | |
| `bubble.fly` | a comment flies into the slot | `text` |
| `tray.emit` | placeholder ad cards come out (one print tick each) | `n`, `interval` |
| `module.label` / `module.ignite` / `module.off` | the experiment module | |
| `hud.to` | counter animates (log bar 100 / 1K / 10K) | `value`, `dur`, `instant` |
| `hud.pulse` / `hud.line` / `hud.line_off` / `hud.hide` / `hud.show` | HUD accents, a second HUD line | `text` |
| `lights.dim` / `lights.up` / `lights.drop` | screen light | `level`, `dur` |
| `corridor.dark` / `corridor.light` / `corridor.lit` | drawers 001–134 light in sequence | `from`, `to`, `over` or `until` |
| `d135.pulse` / `d135.label` / `d135.label_off` | drawer 135 (amber pulse grows to `level`), its label | `level`, `grow`, `text` |
| `comments.show` / `comments.hide` | mock comment bubbles | `items`, `y`, `interval`, `highlight` |
| `endcard.show` | end card + handle | `lines` (`*word*` = lime) |

### Voice
- Voice: "Mine" (cloned) `uJCHSa1oJ32y5sbQ1hDc`, model `eleven_v3`, seed 7, stability 0.5 (v3 accepts 0 / 0.5 / 1),
  similarity 0.8, style 0.2. eleven_v3 does not take previous/next-line context, so consistency comes from one seed and
  identical settings.
- Generate/re-use takes with `engine/voice.py` (`voice.line`, cached by request, so re-runs are free). Check each take
  with speech-to-text before using it: forced alignment trusts the script, so it won't catch a swallowed or added word.
  Episode 001 caught two: "أصل" swallowed, and an extra "ده".
- `voice.assemble(lines, takes, out, gaps, target=44.6)` joins the takes and time-stretches with pitch kept.
  Episode 001 needed 1.23× (approved: the script read naturally runs ~54 s).

### QA (Episode 001 passed all)
`node engine/world_qa.js episodes/epNNN/build '{"hud": [[t, "100 / 10,000"], …], "keys": [{"line": "L1", "t": …}, …]}'`
checks Arabic shaping (width and, on ties, pixels vs. the same word with joining broken) and the RTL order of every
caption chunk, HUD values at given times, and a visible frame change on each line's key moment. Make a contact sheet
(one frame every 2 s) from the MP4 and look at it.

### Rules
No ad-performance claims, no real brand names or logos (the ad cards are placeholders), script wording never changed:
if a line can't fit, say so.
