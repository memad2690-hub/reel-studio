# Acceptance suite (V2 milestone 9)

`python3 reel.py accept <slug> [--video exports/vNNN.mp4] [--no-determinism]`
→ `projects/<slug>/acceptance/report.md` + `report.json` (+ `flagged.png`: stills of every flagged moment).
The studio's job runner can start it too (`accept`). Each check is ✅ pass · ⚠️ warn (review) · ❌ fail · ⛔ blocked.

## What is checked, and how

| Check | Method | Fails / warns when |
|---|---|---|
| Financial calculations | the build's finance checks (equation, waterfall, donut, funnel, break-even, scorecard, before/after) | any total, result, tone or chart sum is wrong (❌; render is blocked too) |
| Missing assets | build problems + card-frame count vs duration + audio file | a photo, card frames or audio is missing (❌) |
| Graphics timed to speech | build anchor problems | an anchor word is not found, or an element comes in after its scene ends (❌) |
| Caption timing | captions vs `words.json` | caption words ≠ spoken words (punctuation ignored), a caption starts > 1 frame from its first word, ends before its last word, lasts < 0.2 s, overlaps the next one, or an active-word highlight is off by > 1 frame (❌) |
| Clipped text | Chromium layout boxes at ~1 sample per 1.5 s + 4 per scene; suspects re-checked 0.6 s later so entrances still sliding in don't count | a text box (or the caption box) runs off the 1080×1920 frame (❌); a non-text graphic runs > 40 px off (⚠️) |
| Graphics clear of captions | box intersection | a text graphic covers > 20% of the caption (⚠️) |
| Graphics clear of the face | OpenCV face detection on the real card frames, mapped through the layout | a front graphic covers > 30% of the detected face (⚠️; text *behind* the speaker is exempt) |
| Platform UI (heuristic) | fixed bands, not an official spec: bottom 220 px and the lower-right 100 px column | text sits mostly inside them (⚠️) |
| Arabic shaping | each Arabic word that has a joining letter pair is drawn twice in Cairo: as is, and with its letters forced apart (ZWNJ); identical pixels = unshaped | any line whose words all render unshaped, or Cairo not loaded (❌) |
| Broken RTL | glyph centres in Chromium, using each element's own direction | a line containing Arabic does not run right→left (also when it starts with a Latin word), or a digit run does not read left→right (❌) |
| Page errors | Chromium console | any page/console error (❌) |
| Export format | ffprobe + MP4 atom order | not 1080×1920, 30 fps, H.264 High/Main yuv420p, square pixels, MP4 with faststart, or frame count ≠ duration × fps (❌) |
| Consistent audio | ffprobe + ffmpeg `ebur128` + `silencedetect` | not AAC ≥ 44.1 kHz ≥ 128 kb/s, or audio ≠ video length ±0.1 s (❌); true peak > −0.5 dBTP or silent gaps > 1.2 s inside the reel (⚠️). Integrated loudness is reported, not judged. |
| Stable rendering | full decode + `blackdetect` | decode errors or black frames ≥ 0.1 s (❌) |
| Smooth transitions | lists the designed transitions + `freezedetect` | a frozen picture ≥ 1.5 s (⚠️) |
| Text readable on a phone | rendered font size (font-size × on-screen scale) of every visible text and the caption | text below 44 px (⚠️), below 34 px (❌) |
| Art direction (heuristic) | per scene, from the sampled moments: texts visible at once, words that appeared within the last 2 s, the largest text (or a chart covering ≥ 12% of the frame) as the focal element, speaker frame share, empty-page moments | > 3 texts at once, > 12 new words per 2 s, no element ≥ 64 px and no large chart, two equally big texts, speaker < 10% of the frame, page mostly empty at ≥ 2 moments (⚠️) — a per-scene table is added to report.md |
| Deterministic rerenders | the storyboard frames rendered twice, SHA-256 of the PNGs | any byte differs (❌) |

Platform compatibility is checked as format conformance (the row "Export format"): 1080×1920 9:16, 30 fps, H.264
High yuv420p, AAC 48 kHz, MP4 with the index at the front. Upload limits (length, size) differ by app and change over
time and are not checked.

## The six cases (from the brief)

| # | Brief case | Project | Footage | Styles |
|---|---|---|---|---|
| 1 | Egyptian Arabic financial explainer | `_acc-1-financial` | approved ROAS reel (V2 scenes as approved) | 01 editorial + 04 equation |
| 2 | CEOS SaaS feature demonstration | — | **blocked**: no real CEOS screens or recordings yet | 05 |
| 3 | Mixed Arabic-English marketing reel | `_acc-3-mixed` | testing-plan reel | 02 kinetic + 08 whiteboard |
| 4 | Data-heavy profitability explanation | `_acc-4-data` | ROAS speech (its numbers are spoken) | 04 data (bars, waterfall, break-even) |
| 5 | Comparison reel | `_acc-5-comparison` | pretty-vs-selling reel | 07 battle + 06 parallax (text behind the speaker) |
| 6 | Collage creative-strategy reel | `_acc-6-collage` | creative-diversity reel | 03 collage (sticker + paper notes) + 09 cinematic (RC Warm Cinematic 85%) |

Every number on screen in these cases is spoken in the reel or computed from spoken numbers (break-even ROAS =
100,000 ÷ 20,000). The `_acc-*` projects are working copies: raw footage is hard-linked, the approved projects are not
modified.

Results: see docs/V2_REPORT.md.
