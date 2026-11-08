# Reel Studio

Your own studio for Egyptian Arabic reels, driven by Claude (or Codex).

- **Mode A — Cut-out explainer.** Topic or workbook reel → script → ElevenLabs voiceover → animated paper cut-out scenes.
- **Mode B — Split-screen doodle edit.** Your raw talking-head footage → transcription → bad takes cut → your face in a sliding card with notebook doodles.

Both deliver 1080×1920 MP4 with synced Arabic captions.

## How a reel moves through it

```
brief → script ✔ → voiceover ✔ (A) / rough cut ✔ (B) → storyboard ✔ → render → notes → v2, v3… → final ✔
```

Each ✔ is your approval. Nothing expensive (voiceover credits, full renders) happens before the step in front of it is approved.

- **Storyboards first.** One frame per scene in a single image, so layout gets fixed before a full render.
- **Timestamped notes.** Pause the video, write "make the 15,000 bigger", save. Claude reads the notes, edits the scenes, renders the next version and marks them applied.
- **Every version kept.** `v001`, `v002`… with QA (size, fps, audio, bitrate) and a contact sheet.
- **Style library.** Reusable techniques (filling-squares stat, money-math reveal, highlighter headline…) and the reels you save as references.
- **Resumable anywhere.** Everything is plain files in `projects/<slug>/`, in git: start on one Claude account, finish on the other, or on your laptop.

## Quick start

- **In Claude:** attach this repo and say e.g. "make MB-007 as a cut-out explainer".
- **On your computer:** see [SETUP.md](SETUP.md), then `python3 reel.py studio`.

## Docs

- [AGENTS.md](AGENTS.md) — the workflow and rules the assistant follows
- [docs/SCENES.md](docs/SCENES.md) — scene and element reference
- [docs/STUDIO.md](docs/STUDIO.md) — the studio app: pipeline, editor, transcript fixes, compare
- [SETUP.md](SETUP.md) — cloud and local setup

Inspired by the structure of [mattp68/ai-video-studio](https://github.com/mattp68/ai-video-studio) (projects, storyboards, timestamped feedback, reference library); the engine is our own Arabic RTL renderer. Cairo font © The Cairo Project Authors, SIL Open Font License (`fonts/OFL.txt`).
