# Setup

The same repo works in two places. Projects live in git, so you can start a reel in one and finish it in the other.

## 1. In Claude (cloud, phone or desktop)

Attach the `memad2690-hub/reel-studio` repo to the chat (or ask Claude to add it). The cloud workspace already has Python, Node, Playwright and FFmpeg. Then just say what you want, e.g. "make CEOS-012 as a cut-out explainer". Claude reads `AGENTS.md`, works in `projects/<slug>/`, sends you the storyboard and videos in the chat, and commits the project files when you approve each step.

In the cloud you review in the chat: reply with notes like "v2 at 0:12, make the number bigger". Claude records them with `reel.py note` so the other account sees them too.

For Mode B transcription through the API, allow `api.elevenlabs.io` and `elevenlabsusercontent.com` in claude.ai Settings → Capabilities, and paste a restricted Speech-to-Text key when Claude asks. Without them, Claude uses the ElevenLabs connector or a transcript you supply.

## 2. On your own computer (Claude Code or Codex)

Needs: Python 3.10+, Node 20+, FFmpeg, Git.

**Mac**
```sh
brew install python node ffmpeg git        # skip what you already have
```
**Windows** (PowerShell)
```powershell
winget install Python.Python.3.12 OpenJS.NodeJS.LTS Gyan.FFmpeg Git.Git
```
Use `python` instead of `python3` on Windows if `python3` isn't found.

Then, in a folder of your choice:
```sh
git clone https://github.com/memad2690-hub/reel-studio
cd reel-studio
npm install
npx playwright install chromium
python3 -m pip install -r requirements.txt
python3 reel.py check
python3 scripts/make_demo.py      # renders two synthetic storyboards as a smoke test
python3 reel.py studio            # open the printed http://127.0.0.1:… address
```

The studio only listens on your own computer (127.0.0.1). Don't expose it to the internet.

For the STT API locally: `export ELEVENLABS_API_KEY=…` (Mac) / `setx ELEVENLABS_API_KEY …` (Windows), or save it to `~/.el_key`. Never commit it.

Open the folder in Claude Code (`claude` in the terminal) or Codex. Both read `AGENTS.md`.

## One-prompt setup (paste into Claude Code or Codex on your computer)

```text
Set up Reel Studio from https://github.com/memad2690-hub/reel-studio in a new local folder.
Read SETUP.md and AGENTS.md first. Check prerequisites (Python 3.10+, Node 20+, FFmpeg, Git)
and guide me through installing anything missing, with my approval.
Run npm install, npx playwright install chromium and pip install -r requirements.txt inside the folder.
Run python3 reel.py check, the unit tests and python3 scripts/make_demo.py,
show me the two demo storyboards, then start python3 reel.py studio and give me the address.
Ask before any paid service or system-wide change. Don't publish anything.
```

## Keeping both places in sync

- Before starting work: `git pull`.
- After an approval or a render: commit the project files (`git add projects/<slug> && git commit -m "…" && git push`). Claude does this when asked.
- Videos (MP4) and raw footage are not stored in git. Any version can be re-rendered: `versions/vNNN.scenes.json` holds the exact scenes used.
