# Reel Studio — instructions for the assistant (Claude Code, Codex, cloud sessions)

You produce vertical Egyptian Arabic reels for Mohamed Emad in two modes, using the files and commands in this repo. Every decision lives in `projects/<slug>/`, so any session or account can resume. Read `PROJECT_CONTEXT.md` once, `docs/SCENES.md` before writing scenes, and the project's `STATUS.md`, `approvals.json` and open notes before touching an existing project.

## Modes

- **A — Cut-out explainer** (fully generated): script → ElevenLabs voiceover → paper cut-out scenes. 24fps.
- **B — Split-screen doodle edit** (his own footage): raw A-roll → STT → cut bad takes → rough cut → face card sliding top/bottom + notebook doodles. 30fps, his voice.

Pick from the request: a topic, reel ID or "voiceover" → A; an uploaded video of him talking → B. Reel IDs (CEOS-0xx, MB-0xx) come from his "Reel Production OS" workbook.

## The pipeline and its approval gates

Never skip a gate. A gate is passed only by `approvals.json` (set by him in the studio, or by you with `reel.py approve` after he says OK in chat).

| Mode A | Mode B |
|---|---|
| 1. `reel.py new <slug> --mode A` · fill `brief.md` | 1. `reel.py new <slug> --mode B` · footage → `raw/raw.mp4` |
| 2. Write `script.md` → **gate: script** (before any credits) | 2. `probe` → STT (`stt`) → `roughcut` → **gate: roughcut** |
| 3. Voiceover → `audio/vo.mp3` + `words.json` → **gate: voiceover** | 3. Clean transcript in 6 sections (`script_clean.txt`) → **gate: script** |
| 4. Write `scenes.json` → `storyboard` → **gate: storyboard** | 4. `finalize-cut` (+ `--crop`) → `scenes.json` → `storyboard` → **gate: storyboard** |
| 5. `render` → notes loop → **gate: final** | 5. `render` → notes loop → **gate: final** |

## Commands (all from the repo root)

```
python3 reel.py check                      # prerequisites
python3 reel.py status [slug]              # where every project stands
python3 reel.py new <slug> --mode A|B --title "…" --reel-id CEOS-012 --cta AUDIT   # slug: lowercase a-z 0-9 - _ (mb-007)
python3 reel.py build <slug>               # page + anchor check (fast)
python3 reel.py storyboard <slug>          # storyboard/sbNNN.png, one frame per scene
python3 reel.py render <slug> [--draft]    # exports/vNNN.mp4 + QA + contact sheet
python3 reel.py render <slug> --from 0 --to 90 --version v004   # long videos in silent parts (pick an unused version), then:
python3 reel.py join <slug> v004           # checks the parts cover the reel, adds the audio once
python3 reel.py notes <slug> | note | resolve <slug> <ids> --version vNNN
python3 reel.py approve <slug> script|voiceover|roughcut|storyboard|final [--version]
python3 reel.py stt <slug> <audio-or-video> [--out words_raw.json]
python3 reel.py import-words <slug> <transcript.json>
python3 reel.py probe|roughcut|crop-preview|finalize-cut|align <slug> …   # Mode B
python3 reel.py library list|show --id X|add-ref --url …
python3 reel.py studio                     # local review site (127.0.0.1)
python3 scripts/make_demo.py               # synthetic smoke test of both modes
python3 -m unittest discover -s tests
```

Rendering speed: ~70s per 27s of Mode A, ~70s per 17s of Mode B here. Keep each command under 10 minutes; split anything longer than ~2 minutes of video with `--from/--to` + `join`.

## Feedback loop (the point of the studio)

1. He leaves notes in the studio (timestamped on a version, on a storyboard frame, or on the script) or in chat. Chat notes → `reel.py note <slug> "…" --t 12.4 --version v003` so they are recorded.
2. `reel.py notes <slug>` → change `scenes.json` (or the script/cuts) → `storyboard` for layout changes, `render` for timing/animation changes.
3. `reel.py resolve <slug> <ids> --version v004`, and say which notes were applied and which weren't (and why).
4. Older-version notes are context, not permission to overwrite an approved version. Every render is a new version; never overwrite an export.

## Style library

`library/techniques.json` holds reusable techniques with a working element example each. When he names one ("use money-math-reveal"), copy its pattern. When he saves a reference reel (`library/references.json`), analyse it only from what you can actually see (the file he uploads, or screenshots): note hook timing, pacing, how numbers appear, caption style, then add or extend a technique. Never invent analysis of a link you could not open. Inspiration is not permission to copy someone's footage, audio, logos or branding.

## Output quality (non-negotiable)

- Deliver 1080×1920. Never 720×1280. Mode A is authored at 720×1280 and rendered with deviceScaleFactor 1.5.
- Intermediates: Mode B frames are lossless PNG. Mode A frames are JPEG q95 (visually lossless for flat cut-out graphics; PNG is about 7x slower), or PNG with `render --lossless` for short reels. Encode with x264 once at the end (crf 16 A / 15 B, preset slow, yuv420p, AAC 192k, +faststart).
- Mode B card frames are extracted **from raw.mp4** with the cut list (never from the rough cut).
- `render` runs QA (size, fps, audio, bitrate) and saves a contact sheet. Look at the sheet before sending. Tell him the in-app preview may look softer than the downloaded file.
- Wants sharper footage? Shoot 4K, it gets downscaled to 1080 with lanczos. Don't render 2K.

## Script rules

- Natural Egyptian Arabic, short sentences, his English business terms in Latin script (ROAS, Break-even, Contribution Margin, Ads Manager).
- From a reel ID: use the workbook row (sheet 'CEOS • 30 Reels' or 'Media Buying • 30', header row 4, data rows 5–34; A ID, H title, J hook type, K format, N CTA keyword, O–T the six sections, W shot list, AD evidence/caveats). Keep his wording; adjust only for speech (numbers as spoken words in Mode A).
- From a topic: search the web first, use only verified numbers, attribute claims ("X بيقول إن…"), include the main counter-view in one line. Political/news: neutral wording.
- Illustrative numbers get a "مثال" tag. Never invent results.
- Structure: HOOK 0–3s, CONTEXT 3–10s, TENSION 10–20s, VALUE 20–35s, PAYOFF 35–45s, CTA 45–60s. Workbook reels 45–60s; explainers 60–180s.
- CTA keyword from the workbook column N (e.g. "اكتب AUDIT"). Brand badge default "محمد عماد".

## ElevenLabs

- Voice (Mode A): `creative_list_voices` (languages ["ar"], search "Egyptian"). Default storytelling voice "Mahmoud Soliman – Egyptian Story" (`oOge1k8044i7H9hCreX6`; check it's still listed); energetic Egyptian male for marketing reels. Model `eleven_v4`. About 2,240 credits per 2.5-minute take.
- **Never repeat a credit-spending generation call to retry.** Script must be approved first.
- Save `flow_id`, `voice_id`, `generation_id` of the chosen take in `project.json` → `elevenlabs`, and download the MP3 to `audio/vo.mp3` straight away (signed URLs expire within about a day; the MP3 is committed so it survives).
- Word timings: `reel.py stt <slug> audio/vo.mp3 --out words.json` (API), or without the API: pin the take with `creative_add_flow_asset_node`, run `creative_transcribe_audio` (eleven_scribe_v1) on it, make ONE `creative_get_flow_run_status` call, save the JSON, then `reel.py import-words <slug> that.json`.
- STT API key: `$ELEVENLABS_API_KEY` or `~/.el_key` (create with `umask 077`). Ask him to paste a restricted Speech-to-Text key with a credit cap if missing. Never echo it or write it into files, commits, memory or handoffs.
- Cloud sessions need `api.elevenlabs.io` and `elevenlabsusercontent.com` in his allowed domains (claude.ai Settings → Capabilities). Test: `curl -sS -o /dev/null -w '%{http_code}' https://api.elevenlabs.io/v1/models` (a CONNECT 403 means blocked). Fallbacks: connector transcription (sentence-level only) or a word-level SRT/JSON from him; for audio, deliver the silent render and ask for the MP3.

## Mode B specifics

- `probe` first: codec, size, bitrate, and the contact sheet (lens covered? framing?).
- `roughcut` proposes cuts: keeps the last complete take of repeated sentences, drops false starts, cuts inside pauses > 0.6s, 35ms audio fades per piece. Review `cuts.json` (raw timestamps + reasons), edit if needed, `roughcut --reuse`. Send the rough cut with the list of cuts and doubtful spots; wait for approval.
- Fix STT spellings in `script_clean.txt` ("ROAS five" → "ROAS 5", English in Latin script).
- `finalize-cut` maps word times onto the edited timeline through the cut list (no second STT run needed), cuts the final audio from raw, and extracts card frames. Check the crop first with `crop-preview <slug> W:H:X:Y` (e.g. `1080:994:0:700` to hide a car sunshade).
- If he wants the on-screen words to follow the clean script exactly, `align` times `script_clean.txt` against `words.json`.

## Files and git

- Commit project text (json/md), `audio/` (voiceovers), storyboards and `versions/*.scenes.json` snapshots. MP4s, raw footage and `build/` are ignored: any version can be re-rendered from its snapshot.
- Work on `main` unless he asks for a branch. Never push anything that contains the API key. Never publish or post videos anywhere.

## Rules

- No copyrighted characters, other creators' logos or branding, or real photos of public figures (silhouettes only in Mode A).
- Product demos: stylized UI cards, never fake real dashboards or results.
- If he attaches the workbook and asks: set Format (K) to "Cut-out explainer (AI)" (A) or keep "Talking head" + a note in W (B); status "Editing" or later; leave analytics blank until real numbers exist; never overwrite formula cells.

## Handoff (end of every substantial session)

He switches between two Claude accounts. End with:

```
Objective · Project slug(s) + stage · Repo/branch + last commit SHA · Files changed
ElevenLabs flow / generation IDs · Versions made (sb/v/rc) + QA · Notes applied / still open
Tests run + results · Blockers & risks · Exact next action · Approvals still needed
```
Never include the API key.

## V2 editing director (Styles 01–09, milestone 4+)
After `finalize-cut` (use `--full-frame` for V2 layouts) and `align`:
1. `python3 reel.py plan <slug> --intensity low|medium|high [--brand media-buying|ceos|whiteboard]` writes
   `plan.md` (segment, role, confidence, numbers heard, proposed treatment and why), `plan.json`, `scenes.draft.json`.
   It never touches `scenes.json` unless `--apply` (which first saves `scenes.prev-<time>.json`).
2. Read `plan.md` like an editor: keep what fits, fix roles, write real step names/labels, upgrade money scenes to an
   `equation`/`waterfall` when the narration walks through a calculation. Low-confidence segments stay plain talking head.
3. Every number on screen must be one the speaker said (the planner only drafts heard numbers); illustrative values get a
   `مثال` pill; the build's finance checks must pass.
4. Storyboard → approval gate as before. Reference docs: `docs/SCENES.md` (all components), `docs/V2_PLAN.md` (status).
5. Cut-out effects (text behind the speaker, parallax, sticker collage) need `python3 reel.py segment <slug>` after
   `finalize-cut --full-frame`; check `build/mask/quality.json` and the storyboard stills: frames below
   `mask_min_quality` fall back automatically. Budget ≈0.7 s per frame for segmentation and ≈22 s per output second to
   render with the cut layer (measured, 2 vCPU). Photos/collage images come only from the user's uploads in `assets/`.
6. Mixing (milestone 7): give scenes a `style` (01–09) only where the content changes register; prefer cuts and use
   `blur`/`whip`/`flash`/`zoom` for real section changes (≈1 per 5 s at most). Read the build `notes` for mixing warnings.
   Brand look comes from `studio.config.json` presets; per-reel tweaks only via `brand_overrides`.
7. The user may edit in the studio (docs/STUDIO.md). Before changing a project, read `edits.json` and respect
   `locked` scenes; never overwrite a locked scene, a variant, or a `*.prev-*` backup.
8. Before delivering a final render, run `python3 reel.py accept <slug>` and review every ⚠️/❌ (stills in
   `acceptance/flagged.png`). To remake card frames of an aligned project use `finalize-cut --full-frame --frames-only`
   (a plain `finalize-cut` re-maps raw words; it backs up `words.json` first).
9. Art direction (look 2, docs/VISUAL_REVIEW.md): decide per scene what the viewer looks at first and make it the
   biggest thing on screen; ≤ 3 elements at once; on-screen text a 2-second read (≈ 10 words); keep the speaker big
   (`split`, `hero`, 480 px PiP — never a tiny frame) when the moment is personal or the graphic doesn't need the room;
   don't repeat the caption in a pill or kinetic line (captions step aside for kinetic text automatically); prefer one
   chart over several stat cards. Use the cut-out only where it is clean in the stills (attached seat/pillar shapes →
   use `split` instead). Check `acceptance/report.md` → "Art direction per scene" and `readable`.
