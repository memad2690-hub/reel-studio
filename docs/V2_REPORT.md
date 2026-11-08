# Reel Studio V2 — delivery report (2026-11-08)

The V2 brief was implemented as an extension of the existing engine (decision D1): Python builds a deterministic
HTML/SVG page per reel, Playwright/Chromium draws each frame, FFmpeg encodes. Claude in the session is the editing
director (D3). All numbers below were measured in this project's 2 vCPU / 7 GB cloud workspace unless marked
otherwise; nothing here is estimated or taken from vendor claims.

## Deliverables

| Brief deliverable | Where | Status |
|---|---|---|
| Updated source | `engine/`, `reel.py`, `studio/` | done |
| Reusable motion-graphics library | `engine/kits.py`, `charts.py`, `fx.py` (+ `docs/SCENES.md`) | done |
| Nine editing styles | 01 editorial · 02 kinetic · 03 collage · 04 data · 06 parallax · 07 battle · 08 whiteboard · 09 cinematic | **8 of 9**; 05 floating UI (CEOS) blocked: needs real CEOS screens/recordings |
| AI scene planning | `engine/planner.py`, `reel.py plan` (roles, confidence, pacing presets, heard-numbers only) | done (first pass; Claude edits the draft) |
| Arabic transcription + captions | ElevenLabs Scribe word timings (`reel.py stt`), `align`, 7 caption presets, per-scene presets | done |
| Style mixing | per-scene `style`, transitions, brand presets, mixing checks | done |
| Updated editing interface | studio Edit / Transcript / Compare tabs, job runner | done |
| Colour grade | `RC_Warm_Cinematic_v1` (locked), intensity, per-clip corrections, checks | done |
| Sample exports | `projects/_acc-*/exports/` + comparison exports | done (see below) |
| Tests and validation | `tests/test_pipeline.py`, `reel.py accept`, `docs/ACCEPTANCE.md` | done |
| Technical documentation | `docs/SCENES.md`, `docs/STUDIO.md`, `docs/ACCEPTANCE.md`, `docs/V2_PLAN.md`, `AGENTS.md` | done |

## Acceptance results

| # | Case | Project / export | Styles | Length · render time | Verdict | Notes |
|---|---|---|---|---|---|---|
| 1 | Egyptian Arabic financial explainer | `_acc-1-financial` v003 | 01 + 04 | 48.6 s · 488 s | ⚠️ warn | caption meets the hook headline as it fades (27 px); hero graphics reach the app-button band |
| 2 | CEOS SaaS feature demo | — | 05 | — | ⛔ blocked | needs real CEOS screens/recordings |
| 3 | Mixed Arabic-English marketing | `_acc-3-mixed` v001 | 02 + 08 | 50.8 s · 456 s | ✅ pass |  |
| 4 | Data-heavy profitability | `_acc-4-data` v001 | 04 | 48.6 s · 551 s | ✅ pass | break-even ROAS 5 computed from the spoken 100,000 / 80,000 |
| 5 | Comparison | `_acc-5-comparison` v001 | 07 + 06 | 47.3 s · 512 s | ✅ pass | text behind the speaker in the hook (segmented frames 1–110) |
| 6 | Collage creative strategy | `_acc-6-collage` v002 | 03 + 09 | 71.8 s · 961 s | ✅ pass | first render v001 failed: 1 paper note ran off the frame, kinetic text met a caption, audio peak −0.1 dBTP → fixed |

All five rendered cases pass: caption timing, Arabic shaping, RTL (including Latin-first mixed lines), clipped text, finance, assets, page errors, export format (1080×1920, 30 fps, H.264 High yuv420p, faststart, AAC 48 kHz), audio (true peak ≤ −1.5 dBTP with the new limiter; −0.5 dBTP on case 3, rendered before it), clean decode, no black or frozen frames, and byte-identical rerenders. Reports: `projects/_acc-*/acceptance/report.md`.

**Bugs found by acceptance and fixed:** captions on full-height layouts ran 9 px off the bottom and sat in the app-button band (new `captions.B.max_bottom` = 1680); waterfall labels collided with the value under a negative bar; a hand-drawn arrow with an out-of-range `bend`; scattered weak mask frames made the cut-out flicker (now decided per scene); `finalize-cut` silently replaced an aligned `words.json` (now `--frames-only` + backup); rare one-pixel-column differences between two renders under heavy load (single raster thread: 9/9 parallel renders identical, no slowdown); source audio peaking at −0.1 dBTP (−1.5 dBTP limiter, loudness unchanged at −17.1 LUFS).

**Checker bugs found and fixed while validating it:** punctuation in transcript vs captions, non-joining test words, width-equal joined forms in Cairo (now a pixel comparison), RTL tie at glyph edges (now glyph centres), and full-frame backdrops counted as text boxes.

**Regression:** 11 existing projects re-rendered against the previous commit: every difference is the intended caption move on `full`/`bottom` scenes (y ≥ 1560), plus 5 anti-aliased pixels on one card corner; everything else is pixel-identical. Existing exports are untouched.

## Performance and cost (measured)

| What | Measured | Notes |
|---|---|---|
| Final render, talking-head reels with full-frame card PNGs | 9.1–11.4 s per output second (acceptance renders: 50.8 s in 461 s, 47.3 s in 517 s, 48.6 s in 488–556 s) | Chromium screenshot + PNG decode dominate; 2 vCPU |
| Final render with a speaker cut-out layer through the reel | 71.8 s in 961 s ≈ 13.4 s/s (case 6, cut-outs in 3 scenes) | cut-out PNG loaded per frame |
| Graphics-only render (no footage) | 1.7 s per output second (40 s in 66 s) | milestone 2 gallery |
| Draft render (veryfast/crf 22, cropped legacy cards) | 514 frames in 55 s | studio job runner, demo project |
| Card-frame extraction (`finalize-cut --full-frame`) | 1458 frames in 116–140 s (48.6 s reel), ≈ 4 GB of PNG | grade adds time (not separately timed) |
| Speaker segmentation (U²-Net, CPU) | ≈ 0.67 s per frame (370 frames in 249 s) | every 2nd frame inferred; only scenes that use cut-outs need it |
| Acceptance checks for one reel | ≈ 33 s for 48.6 s incl. two determinism renders | |
| Single raster thread (determinism fix) | 150 frames: 25.0 s vs 28.5 s with multi-thread raster | no slowdown |
| Peak memory of a render | < 0.6 GB (milestone 0) | |

**Cost per exported video:** rendering, grading, segmentation, planning and checks run locally at no API cost.
The only paid call in the pipeline is ElevenLabs speech-to-text for the word timings (one call per reel; the studio
asks before running it). Its price depends on your ElevenLabs plan and was not measured here.

**Implementation choices compared** (what was measured vs not):
- *Current engine (HTML/SVG + Chromium + FFmpeg)* — measured above. Arabic shaping and RTL come from Chromium's text
  stack and are verified by `accept` (shaping, RTL, digit order). Runs on the user's Windows PC with Python, Node and FFmpeg.
- *Remotion* — not built (decision D1), so **not benchmarked**; no speed or quality claim is made.
- *Generative video models* — not used: ordinary motion graphics are template-driven and deterministic.
- *Lever not yet benchmarked:* JPEG q≈95 card frames instead of PNG (expected to cut decode time; must be measured).

## Comparison exports

Side-by-side videos of the approved V1 reels and their V2 acceptance versions (360×640 per panel, audio from the right panel), made with `scripts/compare_exports.sh` in 76 s for all four:
- `exports/comparisons/roas_v1_vs_v2-editorial_vs_v2-data.mp4` — V1 · V2 Style 01 · V2 Style 04
- `exports/comparisons/pretty-vs-selling_v1_vs_v2-comparison.mp4` — V1 · V2 Styles 07 + 06
- `exports/comparisons/testing-plan_v1_vs_v2-mixed.mp4` — V1 · V2 Styles 02 + 08
- `exports/comparisons/creative-diversity_v1_vs_v2-collage.mp4` — V1 · V2 Styles 03 + 09

## Known limitations

- Style 05 (floating UI / CEOS) is blocked until real CEOS screens or recordings are provided; no invented UI is shown.
- Segmentation leaves objects that touch the speaker in a similar colour (car-seat backs at the shoulders) partly in the
  cut-out; quality on the creative-diversity footage is lower (mean 0.69–0.70) than on the ROAS footage (0.79).
  Weak scenes fall back as a whole (no flicker); exclusion zones help.
- The platform-UI check uses fixed bands (bottom 220 px, lower-right 100 px), not each app's live layout.
- Overlap checks are geometric; whether a graphic over the face is intended is a human call (they are warnings).
- The colour grade is per reel or per cut clip, not per scene; calibration is by measurement on this footage, not a
  side-by-side with a CapCut export.
- Planner step names from Arabic-only sentences are rough; Claude rewrites them. Comparisons need "ولا" or ordinal cues.
- `zoom` transition scales the whole layer: a small PiP can touch the frame edge during a layout change.
- No drag-to-retime timeline, caption line-break editor or undo button yet (every write is backed up; restore is manual).
- Renders here must be split into ≤ 10-minute commands; on the user's PC they can run in one go.

## Future enhancements

1. Benchmark JPEG card frames (and smaller card frames for PiP layouts) to cut render time.
2. Style 05 with real CEOS captures: recorded UI clips, cursor/zoom callouts, lime brand preset.
3. Better segmentation for car interiors (a larger matting model, or per-reel exclusion masks drawn in the studio).
4. Studio: drag scene edges on the timeline, caption line-break editing, one-click restore of any backup.
5. Digit-drum counters and per-digit animations (from the transitions study).
6. Loudness targeting per platform (currently only a −1.5 dBTP peak limiter is applied).
7. A low-resolution preview render (half size) for faster iteration, after measuring the gain.
