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
