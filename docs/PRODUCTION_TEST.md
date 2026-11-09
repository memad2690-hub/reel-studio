# First real production test (V2 usability)

**Reel:** `projects/scaling-ui-test`, from one Egyptian Arabic talking-head video (the scaling-readiness raw, 143 MB,
filmed in a car). It is a new project, so the approved `mb-scaling-readiness` is not touched.
**How:** the studio UI, driven click by click in a headless browser (the same buttons a person uses).

| Step | What happened | Time |
|---|---|---|
| + New reel | project created with look 2 + RC Warm Cinematic grade | instant |
| Upload | 143 MB copied in with a progress bar, checked by ffprobe | ~5 s locally |
| Transcribe | 166 words (ElevenLabs, asked first) | 4 s |
| Rough cut | dropped a false start and a retake | 95 s |
| Approve rough cut | Review tab | — |
| Prepare footage | 1,487 graded full-frame card frames | 230 s |
| Director (Auto) | 6 scenes, 3 styles (kinetic, editorial, whiteboard) | <1 s |
| ▶ Preview scene | 16 s scene previewed | 15–20 s |
| Preview (whole reel) | 49.6 s at half size, 15 fps | 83 s |
| Export | v001, then v002: 1080×1920, 30 fps, 49.6 s, audio, ~7 Mbps, QA clean | ~12 min (cloud) |

## Found by watching the preview (not by the tests) and fixed
- **A checklist was read as a comparison.** "هل المخزون يستحمل؟ هل الـ contribution positive؟ …" became an empty
  A-vs-B card labelled with the wrong words ("لأ؟ هل"). Fixes: a run of "هل …؟" questions is a checklist (a
  whiteboard list, one step per question, in his words, retakes and "يعني هل …" restatements skipped), and
  "… ولا لأ؟" is a yes/no question, not A vs B.
- **Repeated words all came in at the first one.** Anchors now carry `nth`, so each list step appears as he asks
  that question.
- **Kinetic text ran off the bottom of the frame** (hook and conclusion). Long phrases get the `top` layout, the
  build tells the runtime the region's room, and the runtime shrinks a phrase that would not fit (look 2 only,
  never below 46 px). Phrases now stop at the end of his sentence, even when a quote mark follows the full stop.
- **The CTA card said "اكتب في الكومنتات" when he said "ابعت لي".** The card now uses his own verb, and the
  reel's CTA keyword is recognised even when spoken in lowercase ("scale").
- **Auto Director used 4 styles** while the art check says more than 3 reads as noise. Auto is now capped at 3.
- Studio: a failed Prepare (disk full) left a half-written frame folder that showed as done; scene preview did not
  start after switching scenes; approved projects showed Upload/Prepare as not done; unfinished reels now open on
  Edit.

## Still weak (honest list)
- The checklist scene is correct but plain: small text in a large empty paper area. It needs a stronger whiteboard
  treatment (bigger steps, ticks or hand-drawn boxes).
- Setup scenes with no strong cue stay as clean talking head. That is fine, but a human editor might add one
  B-roll or keyword there.
- The Director has no access to B-roll or photos of its own, so Style 09's photo moments only appear when you add
  images.
