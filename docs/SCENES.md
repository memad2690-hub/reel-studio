# scenes.json reference

One file per project describes every scene and element. `python3 reel.py build <slug>` turns it into a deterministic page; `storyboard` and `render` use that page. Edit this file to apply feedback, never the generated HTML.

```json
{
  "mode": "A",
  "words": "words.json",
  "audio": "audio/vo.mp3",
  "captions": true,
  "badge": true,
  "scenes": [
    {"id": "hook", "start": null, "elements": [ ... ]},
    {"id": "context", "start": "ليه", "card": "bottom", "elements": [ ... ]}
  ]
}
```

- `words.json`: `[{"text","start","end"}]` on the **final timeline** (Mode A: the voiceover; Mode B: after the cut).
- `audio`: Mode A `audio/vo.mp3`; Mode B `build/cut_audio.m4a` (made by `finalize-cut`).
- Duration comes from the audio. Scene end = next scene start.
- Mode B only: `card` is `top` or `bottom`. Default alternates. Element `y` is measured inside the graphics half (0–820). Add `"space": "canvas"` to place an element on the full 1080×1920 canvas.

## Coordinates

| Mode | Author size | Output | Notes |
|---|---|---|---|
| A cut-out | 720×1280 | 1080×1920 (scale 1.5) | captions at y≈960, keep graphics in y 120–880 |
| B doodle | 1080×1920 | 1080×1920 | card x40, 1000×920; top y130 / bottom y900 |

Every element has `x`, `y` (its centre), optional `rot`, `scale`.

## Timing specs (`start`, `in`, `out`, `fill_end`)

| Spec | Meaning |
|---|---|
| `12.5` | absolute seconds |
| `"كلمة"` | first word **containing** this text, searched from the scene start |
| `"عشان كدة"` | consecutive-word phrase |
| `{"at": "كلمة", "nth": 2, "offset": -0.1, "after": "سابق", "edge": "end"}` | full form |
| `{"rel": 0.4}` | seconds after the scene start |

Arabic words carry attached prefixes (بـ، الـ، و). Anchor on the stem (`"المرتجعات"` matches `والمرتجعات`). Words of 1–2 letters (`ما`, `في`) only match exactly. Missing anchors, and elements whose `in` lands at or after the time they leave (e.g. anchored on a word spoken only in a later scene, so they would never appear), are listed by `build`; `render` refuses to run until they are fixed (or `--force`).

Default `in`: scene start + 0.2s, plus 0.12s per element. Default `out`: scene end.

## Animations (`anim`)

`pop` (default, overshoot scale), `stamp` (1.8→1, for verdicts), `shake` (pop + wobble, for losses or alarms), `fade`, `slide` (rises 50px), `none`.

## Mode A elements (cut-out kit)

| type | key fields |
|---|---|
| `torn` | `text`, `w`, `h`, `size`, `color` (cream), `text_color`, `seed` |
| `label` | `text`, `size`, `color` — taped card that auto-fits its text |
| `person` | `color` (navy/teal/red/…), `h` — silhouette, no face |
| `chair`, `ballot`, `siren` | `color` |
| `building` | `floors`, `color` |
| `money` | `stacks`, `height` |
| `calendar` | `top` (red strip text), `text`, `size` |
| `card` | `title`, `lines[]`, `w`, `h`, `accent` |
| `stamp` | `text`, `size`, `color`, `rot` — rubber-stamp border |
| `seats` | `n`, `cols`, `filled`, `size`, `gap`, `color`, `fill_end` — squares fill one by one |

Palette names: ink, navy, teal, mustard, red, cream, olive, white, grey (or any hex).

## Mode B elements (notebook doodle kit)

| type | key fields |
|---|---|
| `headline` | `pre`, `hl` (on yellow marker), `post`, `size` 76–104 |
| `icon` | `name`: megaphone, cart, box, truck, return, receipt, calculator, chart, scale, chat, check, money, phone, clock, warning, users; `r` |
| `wcard` | `lines[]` or `text`, `size`, `text_color` — white card, hatched shadow, auto-fit |
| `pill` | `text`, `color` red/blue/ink, `size` |
| `cta` | `keyword`, `magnet`, `prompt` |

Palette names: ink, red, blue, yellow, green, grey, white (or any hex).

## Shared elements

| type | key fields |
|---|---|
| `text` | `text`, `size`, `color`, `weight`, `align` (right/left/center) |
| `number` | `text`, `size`, `color`; count-up with `count_to`, `count_from`, `prefix`, `suffix`, `count_dur` |
| `arrow` | `dx`, `dy`, `dashed`, `color` |
| `xmark`, `check` | `size`, `color` |
| `steps` | `items[]` (each an element; default `label` in A, `wcard` in B, each with its own `in`), `gap`, `size` |
| `svg` | `svg`: raw SVG drawn around (0,0) — for one-off shapes |

## RTL rules

- SVG text uses `direction:rtl`; `text-anchor="start"` is the **right** edge (`align: "right"`).
- Never put a minus sign before a number (`-5,000` renders reversed). Write `خسارة 5,000 ج`.
- English terms stay in Latin script inside Arabic text (`الـROAS`, `Break-even`).
- Illustrative numbers get a `مثال` tag. Never invent results.

## V2 — Style 01 Editorial Motion Explainer (Mode B)

Optional keys; projects without them render exactly as before.

### Project-level keys
| key | values |
|---|---|
| `brand` | `media-buying` (current look) · `ceos` (lime #D1FE17 highlighter, black ink). Defined in `studio.config.json → brands`. |
| `caption_style` | `box` (default) · `highlight` (keywords on a highlighter chip) · `clean` (no box, white text with shadow) |
| `caption_keywords` | words to highlight in captions (matched like anchors: `"ROAS"` matches `الـROAS`) |
| `focus` | `[fx, fy]` face point in the frame (0–1). Default comes from the `cuts.json` crop. |

### Talking-head layouts (`scene.layout`)
Needs full-frame card frames: `reel.py finalize-cut <slug> --full-frame` (1080×1920 frames, cropped live per layout).
The card morphs between layouts over 0.45 s; graphics in that scene wait until it lands.

| layout | card | graphics region (element `y` measured from) |
|---|---|---|
| `top` / `bottom` | 1000×920 at y 130 / 900 | y0 1080 / 60, height 820 |
| `hero` | 1000×1300 at y 130 | y0 1460, height 420 |
| `full` | whole screen, no border | y0 1080, height 780 (over the video: use cards, not bare text) |
| `pip-right` / `pip-left` | 350×430 in the top corner | y0 620, height 1200 |

`card: top|bottom` still works (old name for the two original layouts).

### Motion
- `anim`: `pop`, `stamp`, `shake`, `fade`, `slide`/`slide-up`, `slide-down`, `slide-left` (enters from the right, RTL start), `slide-right`, `spring`, `wipe` (reveals right→left), `none`.
- `exit` (last 0.3 s before `out`): `fade` (default), `shrink`, `slide-left`, `slide-right`, `slide-down`, `none`.

### Financial components
- `statcard`: `label`, `value` (number), `unit` (default `ج`, `""` for ratios), `tone` `positive` (green) / `negative` (red) / `neutral`, `count` (count-up, default true), `size`. Negative values are shown as their absolute amount; say "خسارة" in the label.
- `equation`: `rows[]` of `{label, value, op ("+"|"-"), tone, in}` (first row has no op) and `result {label, label_negative, value, tone, in}`. `build` recomputes the total; a wrong `result.value` or a tone that contradicts the sign is a **finance problem** and `render` refuses to run. Operators are drawn as shapes (never a `-` character), the result shows the absolute value with `label_negative` when below zero.
- Illustrative numbers still need a `مثال` pill. Never invent results.

## V2 — Style 04 Data Storytelling (Mode B)

All charts are drawn around their `x`,`y` in the graphics region, read right-to-left (first item on the right),
and animate item by item: give each bar/segment/stage/point its own `in` anchor (else they stagger 0.5 s).
Numbers are checked by `build`; a **finance problem blocks render**. Illustrative numbers need a `مثال` pill.
Gallery of every chart: `python3 scripts/make_gallery.py` → `projects/_demo-data`.

| type | keys | checked |
|---|---|---|
| `bars` | `items[] {label, value, tone, in}`, `unit`, `w`, `h`, optional `ref {value, label, tone, in}` (dashed target line, e.g. break-even) | every value numeric |
| `waterfall` | `rows[] {label, value, op "+"/"-", in}` (first row = start), `result {label, label_negative, value, in}`, `unit`, `w`, `h` | result = start ± rows; negative total shown as `label_negative` + absolute value |
| `donut` | `segments[] {label, value, tone, in}`, optional `total`, `center`, `r`, `thickness` | segments ≥ 0 and sum to `total` |
| `line` | `points[] {label, value, in}`, `unit`, `tone`, `w`, `h` | values numeric; the line reaches each point as it is said |
| `funnel` | `stages[] {label, value, rate?, in}`, `w` | stages never increase; conversion % computed (a given `rate` must match within 0.5 pt) |
| `breakeven` | `margin_pct` **or** `revenue` + `variable_costs`; `expect`, `actual`; `in` (margin), `in_be`, `in_actual` | break-even ROAS = 1 ÷ margin; `expect` must match; verdict (above/below) is computed, never typed |

Tones: `positive` (green), `negative` (red), `neutral` (ink), `blue`, `yellow`, `grey`. Percentages are wrapped in a
left-to-right isolate so `20%` never displays as `%20` inside Arabic text.

## V2 — Styles 02 Kinetic Typography · 07 Split-Screen Battles · 08 Hand-Drawn Whiteboard

Gallery: `python3 scripts/make_gallery.py styles` → `projects/_demo-styles`.

### 02 Kinetic typography
`{"type": "kinetic", "from": "<anchor>", "to": "<anchor>" | "count": N, "emphasis": [...], "intensity": "low|medium|high", "size", "w", "color"}`
Shows the **exact spoken words** in that range (never retyped), each appearing at its own spoken time, wrapped right-to-left
inside `w` and centred. `emphasis` words are 1.35× with a highlighter sweep. Intensity: low = gentle rise, medium = rise + spring,
high = punch-in with a small rotation. Trailing punctuation is hidden. Text *behind* the speaker needs segmentation (milestone 5).

### 07 Split-screen battles
- Layouts `half-top` / `half-bottom`: the video fills one half edge-to-edge, graphics the other (region heights 880).
- `versus`: `a` (shown on the right, read first) and `b`, each `{title, color, in, items[] {text, good, in}, winner_label}`;
  `ratio` (0.5 or e.g. 0.6), `winner` `a|b` + `in_winner` → winner gets a green frame + label, the other side dims.
- `scorecard`: `heads {a, b}`, `rows[] {label, a, b, unit, in}`, `lower_is_better`, `in_winner`. Totals and the winner are
  **computed**; a stated `winner` that disagrees blocks render.
- `beforeafter`: `before`/`after {label, value, in}`, `unit`, `better` `higher|lower`, `in_change`, optional `change_pct`
  (checked). The change is green when it moves in the better direction.

### 08 Hand-drawn whiteboard
Brand `whiteboard` (white board, marker colours). Strokes draw on with deterministic hand-drawn jitter.
- `circle_mark {rx, ry, color, width}` · `underline {w, color}` · `hand_arrow {dx, dy, bend, color}`
- `flow {nodes[] {label, color, in}, direction "down"|"rtl", box_w, box_h, gap}`: boxes draw, then their label, then the arrow to the next.
- `numbered {steps[] {text, in}, gap, color}`: hand-drawn numbered circles.

### Caption presets (`caption_style`)
`box` (default) · `highlight` (keywords on the highlighter) · `clean` (documentary: no box, shadowed) · `kinetic` (big, current
word highlighted) · `editorial` (black-and-white, square) · `energy` (highlighter box, current word on red) · `minimal` (small,
cinematic). Light presets switch to dark text when the caption sits on the page instead of the video.

## V2 — Editing director (`reel.py plan`)
Pacing presets: `low` (min scene 6 s, ≤4 graphic scenes/min, captions `clean`), `medium` (4 s, ≤8/min, `highlight`),
`high` (2.5 s, ≤14/min, `kinetic`, opens full-frame). Draft scenes keep a `_plan` note (role, confidence, reason) that
`--apply` strips. See AGENTS.md "V2 editing director" for the review steps.

## Colour grading (Style 09 default: RC Warm Cinematic)
Presets live in `grades/` and are never modified (variations go in `grades/custom/`). `RC_Warm_Cinematic_v1` keeps the
original CapCut sliders (`source`) and a `calibration` that maps them to visual equivalents; `engine/grade.py` builds a
33³ LUT (exposure, contrast, highlight roll-off, shadow lift, fade, saturation, warmth, six HSL bands, skin-tone
protection) + restrained sharpen + soft vignette. The grade is applied **to the footage only** while card frames are
extracted, so text, graphics and brand colours are never recoloured.

```bash
python3 reel.py grade <slug> --preset RC_Warm_Cinematic_v1 --intensity 85      # 0-100, writes grade.json
python3 reel.py grade <slug> --exposure 0.2 --temperature -2                    # whole-reel correction (EV / units)
python3 reel.py grade <slug> --clip 3 --exposure 0.15                           # one cut segment
python3 reel.py grade <slug> --off
python3 reel.py grade-preview <slug> [--times 2,12,24] [--intensity 60] [--mp4] # before/after sheet, checks, split MP4
python3 reel.py finalize-cut <slug> --full-frame                                # (re)extracts graded card frames
```
A project whose `scenes.json` has `"style": "cinematic"` gets RC Warm Cinematic at 100% unless `grade.json` says otherwise.
`grade-preview` reports highlight clipping, crushed shadows, skin hue/saturation shift, neutral-white cast and luma spread
across shots (flagged > 0.12 → add a per-clip exposure correction).
