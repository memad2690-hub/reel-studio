# Studio app (`python3 reel.py studio`)

Local only (binds 127.0.0.1, rejects other hosts/origins). Everything it changes is a plain file in `projects/<slug>/`.

## Tabs
- **Review** — rendered versions, timestamped notes, approve rough cut / final (unchanged).
- **Edit** — the pipeline and the editor:
  - **Pipeline:** Import → Transcribe → Rough cut → Script + timing → Analyze → Style → Storyboard → Review → Export.
    Green = done (file or approval exists). **run** starts the matching `reel.py` command as a job with a live log
    (one job at a time, cancel button). Transcribe asks first because it uses ElevenLabs credits; a full-quality
    render asks first because it takes long. Approvals stay manual (Review / Storyboards tabs).
  - **Preview:** the built page, scrubbable and playable with the reel's audio, fed card frames and cut-outs
    exactly like the renderer (draft quality: renders remain the reference).
  - **Timeline:** scenes (colour = style, 🔒 locked, ⟿ transition) over the director's reading of the speech
    (role, darker = more confident). Click a scene to open it.
  - **Scene inspector:** start word, style, layout, transition, caption preset, zoom, parallax, elements (JSON),
    lock. **Save** sends only what changed, validates it, rebuilds and lists anything that would block render.
    **Regenerate this scene** replaces only that scene's graphics with the director's draft for the same speech
    (heard numbers only; elements that would come in too late to read are dropped; if the director proposes no
    graphics the scene is left unchanged). Locked scenes refuse edits and regeneration and are kept by
    `reel.py plan --apply`.
  - **Variants:** save the current scenes.json as a named snapshot (never overwritten); "use" swaps it in.
- **Transcript** — words grouped by scene. Click a word to fix its spelling (one word; count and timings kept, so
  the speaker's words are never added, removed or re-timed); scene/element anchors that used the old spelling are
  updated, and a fix that would still break timing is refused. Shift-click toggles a caption highlight keyword.
  Every fix is logged in `transcript_edits.json`.
- **Compare** — two rendered versions side by side, played and scrubbed together, with what changed between their
  scene snapshots (`versions/<vid>.scenes.json`).

## Safety
Every write first copies the previous file (`scenes.prev-<time>.json`, `words.prev-<time>.json`) and appends to
`edits.json`. If an edit makes the project unbuildable it is rolled back. Source media, exports, approvals and
brand/grade presets are never written by the editor. Jobs are a fixed allowlist (build, storyboard, plan,
render-draft, render, segment, grade-preview, finalize-cut, roughcut, stt); nothing else can be run.
