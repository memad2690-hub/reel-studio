# Studio app (`python3 reel.py studio`)

Local only (binds 127.0.0.1, rejects other hosts/origins). Everything it changes is a plain file in `projects/<slug>/`.

**Windows:** double-click `Start Reel Studio.bat` in the repo folder. It pulls the latest version, installs missing
packages, starts the studio and opens **http://127.0.0.1:8765** in your browser. Keep its window open while you work;
close it to stop. If 8765 is busy (a studio is already open) the window says so and uses the next free port.

## Making a reel, day to day
1. **+ New reel** (top of the project list): folder name, title, CTA keyword. New reels use look 2 and the RC Warm
   Cinematic grade.
2. **Upload** the talking-head video (.mp4/.mov/.m4v, up to 8 GB). It is copied into the project, checked for video
   and audio, and never replaced afterwards (make a new reel for a new take).
3. **Transcribe** (asks first: ElevenLabs credits). No key yet? Paste it once in the box that appears; it is saved
   on this computer only and never shown again.
4. **Rough cut**, then approve it in **Review**.
5. **Prepare footage** (graded full-frame card frames + caption timing; ~1 min per minute of video).
6. **Director → Generate edit**: *Auto Director* picks a style per scene from what is said; *Single Style* uses one
   style for the whole reel; *Hybrid Style* uses your style but keeps data scenes in 04 Data and comparisons in
   07 Battle. Calm / medium / energetic sets the pace. Your previous scenes are backed up, locked scenes are kept.
7. Click scenes in the **Timeline**, fix them in the inspector, **▶ Preview scene** for a quick look.
8. **Preview** (whole reel, half size, 15 fps, ~3× faster than an export; never counted as a version).
9. **Export** (1080×1920, 30 fps; becomes v001, v002…), then approve and **Download** in **Review**.

Grade: RC Warm Cinematic is applied to the footage and photos only, never to text, charts or graphics. Turn it off
or change its strength per project with `grade.json` (`{"preset": "RC_Warm_Cinematic_v1", "intensity": 0}`).
Approved look-1 projects keep their original look and grade.

## Tabs
- **Review** — rendered versions, timestamped notes, approve rough cut / final (unchanged).
- **Edit** — the pipeline and the editor:
  - **Pipeline (talking-head reels):** Upload → Transcribe → Rough cut → Prepare footage → Edit → Preview → Export →
    Approve, with the next step and what to do there shown under it.
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
render-draft, render, export, preview, direct (`plan --apply --director …`), segment, grade-preview, finalize-cut,
card-frames (`finalize-cut --frames-only`), roughcut, accept, stt); nothing else can be run. Uploads need the
studio's own header (`X-Reel-Upload`) plus the host/origin checks, are written to a `.part` file and only kept
if ffprobe finds video and audio.
