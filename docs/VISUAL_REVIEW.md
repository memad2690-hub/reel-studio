# Visual review — V1 approved vs V2 acceptance reels (2026-11-08)

Method: contact sheets of the four comparison videos (a frame every 3–4.5 s, all panels side by side), plus measured
rendered font sizes of every visible text (`engine/inspect.js`, 50–80 moments per reel). Judged as a viewer on a phone:
1080 px ≈ 68 mm on a 6.1" screen, so 40 px text is under 3 mm tall.

## Measured text sizes before the pass (smallest per component)

| Reel | Smallest texts |
|---|---|
| ROAS editorial (case 1) | pill 25 px · statcard label 34 · CTA line 38 · equation rows 49 |
| ROAS data (case 4) | waterfall labels 30 · bar labels 34 · CTA 38 · break-even labels 40 |
| Pretty vs selling (case 5) | versus items 38 · numbered 46 · pills 46 |
| Testing plan (case 3) | CTA 38 · statcard label 40 · flow nodes 44 |
| Creative diversity (case 6) | chapter subtitle 31 · CTA 38 · minimal captions 42 · flow nodes 44 |

## Findings per reel

**ROAS — V1 vs V2 editorial vs V2 data**
1. V2 improves understanding: full-frame hook with the speaker large (0–5 s); waterfall shows where the 100,000 goes (16–22 s).
2. V2 weaker: the calculation (13–22 s) — speaker shrunk to a 350 px PiP, equation rows small; V1's big "فاضل 20,000 بس" reads faster.
3. Text too small: equation rows, waterfall/bar labels (30–34 px), "كل 1 ج إعلان ← 4 ج مبيعات" pill, break-even labels.
4. Distracting motion: none severe; the counting-up statcard (7 s) shows odd intermediate values ("99,103").
5. Empty space: 10–12 s (speaker small, page empty until the costs arrive), 34–36 s ("20% هامش المساهمة" alone), 43–47 s CTA (half the screen empty for 3 s).
6. Competing elements: none; the opposite problem — too little dominant content.

**Pretty vs selling — V1 vs V2 comparison**
1. Better: "أغلى؟" behind the speaker in the hook; final kinetic recap is big and clear.
2. Weaker: the versus cards (4–12 s, 40–45 s) appear as large empty white boxes before their items; items are small.
3. Too small: versus items (38 px), the three-step list (22–31 s), the "الصح" badge.
4. Motion: card whips between pip/half layouts at 34 s pass through a tiny frame.
5. Empty space: 13–15 s and 19–21 s (speaker in top card, page empty), 22–31 s (tiny PiP + short list in a tall empty area).
6. Competing: none.

**Testing plan — V1 vs V2 kinetic + whiteboard**
1. Better: circled "creative واحد" (10 s); "three angles" kinetic; flow of audience/offer/angle shows the three suspects.
2. Weaker: 13–20 s and 26–36 s — tiny PiP, small diagram, lots of empty page. V1's bigger cards under a big speaker read faster.
3. Too small: flow nodes (44 px in narrow boxes), numbered rules, "ads budget" label, CTA line.
4. Motion: the flash into "plan" (23 s) is fine; the kinetic arrives late so the flash lands on an empty page.
5. Empty space: 4–8 s (graphics arrive 4 s into the scene), 23–26 s, 39–42 s (flow at the top, speaker at the bottom, gap between).
6. Competing: none.

**Creative diversity — V1 vs V2 collage + cinematic**
1. Better: warm cinematic look; chapter cards; taped paper notes give the collage a real art direction.
2. Weaker: hook (0–5 s) — minimal caption is small and thin over busy footage; V1's big headline is clearer.
3. Too small: minimal captions (42 px), chapter subtitle (31 px), flow nodes, CTA line.
4. Motion: fine.
5. Empty space: sticker scenes (10–19 s, 55–64 s): the sticker sits small bottom-right, the notes are small at the top, the middle is empty.
6. Competing: none. Cut-out edge quality: a grey car-seat shape stays attached beside the speaker (14 s, 55 s).
7. Grade: RC Warm Cinematic is consistent across all scenes (verified by eye on the sheets).

## The problems that matter most (ranked)
1. Text below phone-readable size in charts, lists, diagrams, pills and CTA lines.
2. Talking head too small (350 px PiP) in exactly the scenes that carry the argument.
3. Empty page while the speaker waits small for graphics that arrive seconds later.
4. Versus boxes drawn empty before their content; weak comparison hierarchy.
5. Sticker composition (small, bottom corner) and seat remnants on the cut-out.
6. Minimal captions too small/thin on full-frame footage.

What V2 already does better than V1 is kept: full-frame hooks, text behind the speaker, waterfall, chapter cards,
paper notes, kinetic recaps, the grade.

## Changes (engine "look 2", opt-in per project; approved look-1 reels render exactly as before)
1. Readable text: every text below 58 px ×1.2 (max 58), floor 46 px; equation labels fit their row; flow boxes and
   versus columns fit their text; minimal captions 56 px with a stronger shadow.
2. No tiny talking heads: PiP 480×600 (was 350×430), new `split` layout (speaker 1000×760 + 760 px of graphics),
   bigger collage sticker; data/whiteboard styles default to `split`.
3. Speaker first: when graphics arrive ≥ 2 s into a scene, the speaker stays big until they do.
4. Versus boxes fit their content; bigger items and winner badge. Counters count in round steps.
5. Captions step aside while kinetic typography shows the same words; on a PiP the caption stays on the card.
6. Segmentation: motion-adaptive smoothing — no translucent hand trails on the cut-out.
7. Art direction in the planner (`plan.md` table: look first, speaker, elements, reading time; ≥ 3 amounts → one chart;
   ≤ 3 elements) and measured in `reel.py accept` (`readable` + `art` checks).
8. Scene revisions in the acceptance reels: duplicate pills removed, break-even "5" made the focal element,
   calculation scenes moved from tiny PiP to `split`, hook headlines lifted clear of the caption, the collage scene with
   a seat/pillar remnant moved to `split`.

## Results (measured, before → after, with the same checks)

| Reel | Smallest text | Texts < 44 px (sampled) | Smallest speaker share | Empty-page moments | Art notes |
|---|---|---|---|---|---|
| ROAS editorial (case 1) | 25 → 27 px* | 37 → 1* | 7% → 37% | 7 → 2 | 10 → 5 |
| Testing plan (case 3) | 38 → 46 px | 9 → 0 | 7% → 14% | 14 → 6 | 8 → 3 |
| ROAS data (case 4) | 30 → 46 px | 42 → 0 | 7% → 37% | 7 → 2 | 6 → 3 |
| Pretty vs selling (case 5) | 38 → 46 px | 21 → 0 | 7% → 14% | 2 → 2 | 3 → 2 |
| Creative diversity (case 6) | 31 → 45 px | 12 → 0 | 7% → 14% | 13 → 6 | 13 → 7 |

\* the remaining 27 px is a pill caught in its spring entrance (it settles at 54 px); `accept` skips elements still
animating in. Finance and timing problems: 0 before and after in every reel.
Before/after stills: `exports/comparisons/before_after/*.png`; comparison videos re-rendered in `exports/comparisons/`.

## Judged by eye (not by the tests)
- Clearly better: every calculation and list scene (speaker big, text legible), versus cards, break-even, CTA waits,
  cinematic captions, the testing-plan "fail"/"plan" scenes (no caption collisions, no duplicated words).
- Same: pretty-vs-selling "mistake" (was already fine), hooks that were already full-frame.
- Trade-off: creative-diversity "why" lost its cut-out sticker (15% of its frames have a weak mask, so the whole scene
  falls back to a tilted framed card — clean, but less "collage"); the "angles" scene uses `split` instead of the
  sticker because the car-door pillar stays attached to the cut-out on that footage.
- Still to judge on a phone: whether the 46–58 px body text feels right in the hand, and whether the speaker-first move
  (big → layout) reads as intentional rather than busy. These are taste calls the measurements can't make.
