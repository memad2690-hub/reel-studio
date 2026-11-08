# Reel Studio V2 — architecture audit and implementation plan

Status: **decisions taken 2026-11-08; milestone 1 in progress.**

Decisions (Mohamed, 2026-11-08):
- D1 Renderer: **extend the current engine** (HTML/SVG + Playwright). No Remotion. Section 3 is superseded by "3b".
- D3 Director: **Claude in the session** (rule-based planner proposes, Claude refines; no per-reel API cost).
- D4 Collage images: **uploads + templates only** (no paid image generation).
- Media Buying brand preset: **current reel look** (cream grid, ink, yellow highlighter, green/red numbers, Cairo).
- Still open: reference screenshot, REEL_STUDIO_HANDOFF.md, CEOS font. (RC Warm Cinematic received 2026-11-08.)
Source brief: "Claude Code — AI Reel Studio V2" (9 styles, AI editing director, style mixing, editing UX).

## 1. What exists today (audited 2026-11-08, commit eda082c)

| Area | Today | Notes |
|---|---|---|
| Pipeline / CLI | `reel.py` (Python): new, build, storyboard, render (+ parts/join), notes, approve, stt, probe, roughcut, finalize-cut, align, library, studio | Approval gates, versioning, notes, QA, contact sheets all work and are tested. Keep. |
| Project data | `projects/<slug>/` plain JSON/MD in git: project, scenes, cuts, words, approvals, feedback, versions, STATUS | Resumable across accounts. Keep as the source of truth. |
| Rendering | `engine/build.py` turns `scenes.json` into one HTML/SVG page with `window.setTime(t)`; `engine/render.js` screenshots every frame in headless Chromium (Playwright) and pipes to x264 | Deterministic. Arabic shaping/RTL correct (browser text engine + bundled Cairo). |
| Components | `engine/kits.py`: Mode A cut-out kit (torn, label, person, chair, building, money, ballot, siren, calendar, card, stamp, seats) and Mode B doodle kit (headline, icon×16, wcard, pill, cta), shared text/number/arrow/xmark/check/steps/svg | String-built SVG. Fine for static shapes; awkward for layout morphing, springs, video-in-graphics. |
| Animation | `engine/runtime.js`: 6 entrance types (pop, stamp, shake, fade, slide, none), count-up numbers, Mode B card sliding top↔bottom (0.45s), captions | No exits beyond fade, no springs, no masks, no per-element layout morphing. |
| Talking head | Mode B: face card = PNG frames extracted from raw (≈3 GB / 50s reel), fixed 1000×920 card, two positions | The main limit for "frame resizing and repositioning". |
| Transcription | ElevenLabs Scribe v1 word timings (`reel.py stt`); `align` maps an approved clean script onto STT times | Works for Egyptian Arabic + English terms (6 reels done). |
| Cutting | `propose_cuts` (adjacent retakes) + hand-reviewed `cuts.json`; per-segment memory-safe cutting, frame-snapped | Auto retake detection misses multi-sentence retakes; human review stays. |
| Captions | One style per mode, 1–4 words, clause-balanced chunks | No presets, no keyword highlighting, no caption editor. |
| Studio UI | `studio/serve.py` + one HTML page: project list, version player, timestamped notes, storyboard notes, approvals, script view, library | No timeline, transcript editor, style selector, scene overrides. |
| Tests | 21 unit tests (timing, anchors, captions, cuts, slugs, versions, timing problems, QA, card slide, snap) + `make_demo.py` smoke test | Good base for regression tests. |

Measured here (2 vCPU / 7 GB cloud workspace): Mode B final render ≈ 14 s per second of output
(51 s reel → 710 s); card-frame extraction ≈ 100 s and ≈ 3 GB per 50 s reel; peak memory < 0.6 GB.

Not found anywhere: `REEL_STUDIO_HANDOFF.md`, the "RC Warm Cinematic" grade, the seven-frame reference screenshot.

Related asset: the installed **editorial-shortform-remotion** skill ships a Remotion 4 template with
Arabic-safe `NumberGraphic`/`KeywordGraphic`, `FrameworkCard`, `CameraRig` (punch-ins / framing),
`BlurTransition`, `AudioLayer`, plus `track_face.py` (OpenCV face tracking) and `validate_edl.py`.

## 2. Gap against the brief

| Brief item | Gap | Feasibility here |
|---|---|---|
| Style 01 Editorial Motion Explainer | Closest to Mode B. Missing: frame resize/reposition morphs, directional text, equation reveals, exits | High |
| 02 Kinetic typography | Missing word-by-word engine, masks, emphasis-driven intensity; text behind speaker needs segmentation | High (behind-speaker: medium) |
| 03 Paper cutout / collage | Mode A kit exists for illustrations; missing subject cutouts, photo stickers, paper-slide transitions | Medium (needs segmentation; AI images need a provider) |
| 04 Data storytelling | Have count-up + money-math reveal; missing bar/line/donut/waterfall/funnel/break-even components + a finance validator | High |
| 05 Floating UI / SaaS | Missing browser/window/cursor/scroll/zoom components; needs real CEOS screenshots/recordings | High once assets exist |
| 06 2.5D parallax | Needs subject masking per frame | Medium; MediaPipe selfie segmentation (pip, model bundled) is a candidate, must be tested on your car footage |
| 07 Split-screen battles | Missing split layouts, separators, scorecards | High |
| 08 Whiteboard | Have doodle icons/arrows; missing stroke-draw animation, circle/underline annotations | High (SVG stroke-dashoffset) |
| 09 Cinematic mini-doc | Skill template has punch-ins, blur, vignette; "RC Warm Cinematic" grade missing | High, grade needs its definition |
| AI editing director | Today the "director" is Claude writing scenes.json by hand per reel | See decision D3 |
| Captions: 6 presets, editor, keyword highlight | One preset per mode | High |
| Pacing / intensity presets | None | Medium–high (rules over transcript + roles) |
| Style mixing + brand presets | Palette per mode only | High; CEOS lime #D1FE17 + black/white is known, fonts are not |
| Editing UX (timeline, transcript, overrides, lock, regenerate one scene, compare variants) | Studio is review-only | Medium; large UI work |
| transitions.dev techniques | Not evaluated yet | To do in the transitions milestone (fetch + evaluate, re-implement, no copying) |

## 3. Proposed architecture

Keep the Python control plane (CLI, projects, gates, notes, versions, QA, STT, cutting, studio server).
Replace the rendering layer with **Remotion** (React), installed as a sub-package `engine2/`:

```
raw → probe/STT/cuts (existing) → plan.json  (scene planner output: roles, values, style, confidence)
                                        │
                     edit.json  (EDL v2: shots, layouts, components, captions, transitions, brand, intensity)
                                        │      validate (layout safe zones, face overlap, finance checks, density)
                         Remotion composition  → stills sheet → render (parts) → existing QA/versions/notes
```

Why Remotion over extending the current SVG engine:
- Talking-head layouts become a component (`TalkingHeadFrame`) that plays the raw video directly
  (OffthreadVideo), resizes/repositions with springs, and needs no 3 GB PNG extraction per reel.
- Springs, masks, staggered reveals, shared-element morphs and charts are ordinary React code; the
  current string-built SVG would need a hand-written animation system for each.
- Your installed skill already has Arabic-safe Remotion components and a validator to start from.

What stays: all project files and CLI verbs; old `scenes.json` projects keep rendering with the
current engine (Modes A/B untouched), so nothing approved is touched or re-rendered.

Risks to measure before committing (not yet benchmarked): Remotion render speed on 2 vCPU vs the
current 14 s/s; OffthreadVideo decode of 1440×2560 HEVC (may need a one-time CFR H.264 proxy);
segmentation quality in a car interior.

## 3b. Architecture as decided (extend the current engine)

- Talking head: card frames extracted full-frame (1080×1920) once per reel; the runtime crops/zooms
  them into any layout (full, hero, top, bottom, picture-in-picture) using a face focus point, and
  morphs the card between layouts with deterministic easing/springs.
- Scenes gain `layout`; elements gain directional entrances, springs, wipes and exits.
- New components are added to `engine/kits.py` + `runtime.js`; a finance validator checks every
  equation/stat in `build`, and `render` refuses to run on a failed check (like missing anchors).
- Old Mode A/B projects render exactly as before (new keys are optional).

## 4. Milestones (each ends with a real render you approve)

1. **Foundation + Style 01** — `engine2/` Remotion package, EDL v2 schema + validator, TalkingHeadFrame /
   DynamicVideoLayout / AnimatedHeadline / KeywordHighlight / FinancialStatCard / AnimatedCounter /
   AnimatedArrow / CaptionLayer / CTAOverlay / TransitionManager; Media Buying brand preset; 3 caption
   presets. Validate by re-editing **mb-roas-loss** from its approved cut as V2 and comparing to v001.
   Benchmark render time against v001.
2. **Data storytelling (04) + finance validator** — ProfitWaterfall, bar/line/donut, break-even and CM
   diagrams; every number traced to the transcript or labelled مثال; arithmetic checked in tests.
3. **Kinetic typography (02) + split-screen (07) + whiteboard (08)** — word-level engine, emphasis
   intensity, comparison layouts, stroke drawing; remaining caption presets.
4. **Scene planner (director)** — transcript → roles (hook/setup/example/contrast/reveal/CTA),
   values, comparisons, processes → style + confidence; low confidence = clean talking head.
   Pacing rules + Low/Medium/High intensity + density budgets enforced by the validator.
5. **Cinematic (09) + parallax (06) + collage (03)** — punch-ins, chapter titles, film texture, grade
   preset; segmentation spike first, with fallbacks when the mask is poor.
6. **Floating UI / CEOS (05)** — from real CEOS screenshots/recordings only.
7. **Style mixing + brand presets + transitions** — CEOS / Media Buying presets, transitions.dev study.
8. **Editing UX in the existing studio** — Import → Transcribe → Analyze → Style → Generate → Review →
   Export; transcript + caption editor, timeline, scene overrides/lock/regenerate-one-scene, variants.
9. **Acceptance suite** — the six test reels from the brief, rerender determinism, export checks.

## 5. Decisions needed (blocking)

- **D1 Rendering stack** — Remotion (recommended) vs extend current engine. Remotion is free for
  individuals and companies of up to 3 people; larger companies need a paid company license.
- **D2 Missing inputs** — the seven-frame reference screenshot; `REEL_STUDIO_HANDOFF.md` and the
  "RC Warm Cinematic" grade (from another repo/account?); Media Buying brand fonts/colors (use the
  current cream/ink/red/blue/yellow/green palette?); CEOS fonts (lime #D1FE17 + black/white known).
- **D3 "AI" director** — Claude in the session plans each reel (no extra cost; how the six reels were
  made) vs an in-app planner calling an LLM API (needs a key and per-reel cost).
- **D4 Paid/optional providers** — AI image generation for collage (e.g. the connected Magnific account,
  uses its credits) or user-uploaded/template assets only.

## 6. Known limits of this environment

2 vCPU / 7 GB, no GPU; Hugging Face downloads blocked (local Whisper models unavailable here —
ElevenLabs STT works); Google Drive only via your PC folder; renders must be split into ≤10-minute commands.

## 7. Progress log

### Milestone 1 — Style 01 Editorial Motion Explainer (2026-11-08) — APPROVED ("New style is perfect", reference: mb-roas-loss-v2 v002)
Built (extends the current engine; old projects unchanged — demo B storyboard identical, approved reels untouched):
- Talking-head layouts `top`, `bottom`, `hero`, `full`, `pip-right`, `pip-left` with face-focus cropping from
  full-frame card frames (`finalize-cut --full-frame`) and a 0.45 s morph between layouts; graphics wait
  for the morph; captions follow the scene's target layout.
- Motion: `spring`, `wipe`, `slide-left/right/up/down` entrances; `fade`/`shrink`/`slide-*` exits.
- Components: `statcard` (tone-colored, count-up, never a leading minus) and `equation` (rows + computed
  result; build checks the arithmetic and the sign/tone; a failed check blocks render).
- Caption presets `box` / `highlight` (keywords on the brand highlighter) / `clean`; brand presets
  `media-buying` and `ceos` (lime #D1FE17).
- Bug fixed on the way: `finalize-cut` failed on a project with no `build/` folder yet.
- Tests: 29 passing (8 new for V2).

Validation on real footage: project `mb-roas-loss-v2` (same approved cut + script as `mb-roas-loss`).
Measured here: full-frame card extraction 140 s / 4.0 GB / 207 MB peak for 48.6 s; render 597 s for
48.6 s (≈12.3 s per output second) vs ≈13.9 s/s for the original reel 1 render — full-frame layouts
did not slow rendering.

Determinism: the same 5 frames rendered twice are byte-identical (md5).

Not done yet in M1 terms: arrows/diagram components beyond the existing arrow, keyword highlight
inside headlines beyond the existing highlighter, low-res preview renders, transitions.dev study.

### Milestone 2 — Style 04 Data Storytelling (2026-11-08)
Built: `engine/charts.py` with `bars` (+ dashed reference line), `waterfall`, `donut`, `line`, `funnel`,
`breakeven`; per-item timing on spoken words; runtime animations (bars grow, lines draw, donut segments sweep,
labels fade in). Finance checks block render: waterfall result, donut total, funnel order and rates, break-even
math and verdict. Percentages isolated for RTL. Gallery project `scripts/make_gallery.py` (`_demo-data`).
Tests: 35 passing (6 new chart checks).
Measured: gallery (no talking-head frames) renders 40 s in 66 s (≈1.7 s per output second) vs ≈12 s/s for
reels with full-frame card PNGs — card-frame loading dominates render time; a faster card-frame format is the
main performance lever (to benchmark: JPEG q≈95 card frames, or lower PNG compression).

### Milestone 3 — Styles 02 / 07 / 08 + caption presets (2026-11-08)
Built `engine/fx.py`: `kinetic` (exact spoken words, per-word timing, RTL wrap, emphasis, 3 intensities), `versus`
(winner reveal, loser dims, drawn divider + VS), `scorecard` (computed totals/winner, checked), `beforeafter` (computed
% change, direction-aware colour, checked), whiteboard `circle_mark` / `underline` / `hand_arrow` / `flow` / `numbered`
(deterministic hand-drawn strokes). Layouts `half-top` / `half-bottom`; brand `whiteboard`; caption presets now 7
(box, highlight, clean, kinetic, editorial, energy, minimal) with an active-word highlight driven by word times.
Gallery `_demo-styles` (draft render 1368 frames in 79 s). Tests: 40 passing.
Deferred to milestone 5 (needs segmentation): text behind the speaker.

### Milestone 4 — AI editing director, first pass (2026-11-08)
`engine/planner.py` + `reel.py plan`: sentences → roles (hook, data, process, comparison, contrast, emphasis, example,
conclusion, cta, setup) with confidence and reason; Egyptian-Arabic + digit number parser (money / percent / ratio / count,
e.g. "خمسة وعشرين ألف" = 25,000, "عشرين في المية" = 20%, "بـ5 آلاف" = 5,000); pacing presets low/medium/high
(min scene length, graphic-scene budget per minute, layout rotation, caption preset); merging rules (same-role
neighbours, ordinal lists across explanation sentences, short scenes fold into plain neighbours without stretching
visuals); draft scenes with statcards (heard numbers only), numbered lists, versus (either/or), kinetic lines, CTA.
Output `plan.md` / `plan.json` / `scenes.draft.json`; `--apply` backs up `scenes.json` first.
Evaluated on the six real reels (plans in each project). Known limits: step names from Arabic-only sentences are rough
(Claude rewrites them); comparisons need "ولا" or "الأولاني/التاني"; calculations are drafted as stat cards, not equations.
Tests: 46 passing (6 new).

### Style 09 grade — RC_Warm_Cinematic_v1 (2026-11-08)
Locked preset `grades/RC_Warm_Cinematic_v1.json` (original CapCut sliders + calibration v1), LUT pipeline in
`engine/grade.py`, intensity 0–100, whole-reel and per-clip exposure/white-balance corrections, footage-only application
(overlay pixels identical to the ungraded render within codec noise: 0.49/255 vs 2.83/255 on the face), before/after
sheet + split-screen test MP4 + checks (`reel.py grade-preview`). Measured on mb-roas-loss raw at 100%: highlight
clipping 0.34% → 0%, crushed shadows < 0.6% (dark seats), skin hue +1.0–1.1°, skin saturation −5.7%, cyan shirt
saturation −19%, neutral cast 0.021, luma spread across shots 0.001. Calibration is by measurement on this footage,
not a side-by-side with CapCut: a CapCut-exported frame of the same shot would let calibration v2 match it exactly.
Tests: 45 passing (an earlier note said 52 — recounted).

### Milestone 5 — Styles 09 Cinematic · 06 Parallax · 03 Collage + segmentation (2026-11-08)
Built: `engine/segment.py` (U²-Net human seg via onnxruntime from the rembg GitHub release — MediaPipe's bundled models
are gone and Google storage is blocked here), mask cleanup + temporal smoothing + per-frame quality score, `reel.py
segment`; runtime cut-out layer, `behind` elements, parallax, `sticker` layout with quality fallback; scene `zoom` /
`punch`; film grain/letterbox; `chapter` and `photo` (uploads only, plain/polaroid/archival/tape, Ken Burns);
cinematic style defaults (RC Warm Cinematic grade + grain).
Measured on mb-roas-loss raw (copy `_style09-test`): segmentation 370 frames in 249 s (≈0.67 s/frame, every 2nd frame
inferred), quality mean 0.787, min 0.675, 0 frames below 0.62; render with cut layer + parallax 12 s (360 frames) in
266 s ≈ 22 s per output second (vs ≈12–14 s/s without the cut layer).
Known limit: car-seat backs adjacent to the shoulders partly stay in the cut-out (exclusion zones reduce it).
Tests: 55 passing (10 new: cinematic defaults, chapter, missing photo, behind fallback / behind with cut-outs, sticker,
mask refine, exclude zone, quality score, mask threshold).

### Milestone 7 — Style mixing, scene transitions, brand presets (2026-11-08)
transitions.dev study (fetched 2026-11-08): a library of ~44 web UI micro-interactions; no licence stated, so no code
was copied — only general motion ideas, re-implemented for a frame-exact renderer. Adopted: text swap with blur →
`blur-in`; toast rise (fade + blur + scale) → `rise`; blur exit; cross-blur → scene `blur` transition. Already covered:
stroke-drawn checks (whiteboard draw), staggered line reveals (kinetic), shake, spring pop. Not adopted: hover / pointer /
physics / drag interactions (no viewer input in a video); digit drum counters (future: needs per-digit clipping in SVG).
Built: per-scene `style` with style defaults and mixing checks; scene transitions cut/blur/whip/flash/zoom on a `#main`
layer (only added when a reel uses one); per-scene caption presets; brand presets with default caption + transition,
`brand_overrides`, unknown-brand / style / transition / caption-preset checks; `reel.py brands`.
Measured: 24 s mixed sample (720 frames, full-frame card PNGs) rendered in 233 s ≈ 9.7 s per output second;
finalize-cut --full-frame for the 48.6 s reel 1458 frames in 116 s.
Regression: 11 projects render pixel-identical storyboard stills vs milestone 5 (card frames present only in `_demo-b`;
the approved reels' card frames had been deleted, so their footage layer was checked through `_demo-b`).
Known limit: `zoom` scales the whole layer, so a small PiP layout can touch the frame edge during a layout change.
Tests: 61 in tests/test_pipeline.py (6 new).

### Milestone 8 — Editing UX in the existing studio (2026-11-08)
Built `engine/editor.py` (validated scene patches, backups + edits.json, rollback on build failure, locks,
regenerate-one-scene, plan --apply keeps locked scenes, transcript spelling fixes with anchor follow-up, caption
keyword toggle, variants, version scene diff) and studio tabs Edit / Transcript / Compare with an allowlisted job
runner (live log, cancel, one at a time, cost confirmation for STT). Docs: `docs/STUDIO.md`.
Verified in a headless browser on a copy of `_demo-b`: pipeline + plan job, scene save, lock, regenerate, variant,
transcript fix (anchor updated), two draft renders through the job runner (514 frames in 55 s and 56 s), compare view;
no page errors. Guards checked over HTTP: locked scene, second job, STT without confirmation, foreign Origin, unknown job.
Bugs found by the tests and fixed: regenerate could keep draft graphics timed after the scene ends; a spelling fix on an
anchor word broke timing; regenerate with no proposal wiped the scene.
Not built (future): drag-to-retime on the timeline, caption line-break editing, a frame-accurate preview of grade
changes inside the editor (grade-preview job covers it), undo button (backups exist; restore is manual for now).
Tests: 72 in tests/test_pipeline.py (11 new).
