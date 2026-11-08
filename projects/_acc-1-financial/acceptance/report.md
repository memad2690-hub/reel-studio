# Acceptance — _acc-1-financial

Verdict: **WARN** · video: `exports/v003.mp4` · 48.6s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 6 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 1458 card frames for 48.6s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 57 captions, 147 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 60 moments checked; every visible text box inside the 1080×1920 frame |
| ⚠️ | Graphics clear of captions | 1 overlap(s) to review |
| ✅ | Graphics clear of the face | face found at 60/60 moments; no front graphic covers more than 30% of it |
| ⚠️ | Text clear of platform UI (heuristic) | 1 text box(es) where app buttons/captions may cover them |
| ✅ | Correct Arabic shaping | 74 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 48.60s, 4689 kb/s, 28.5 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 193 kb/s; integrated -20.2 LUFS, LRA 5.9 LU, true peak -2.0 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | cuts only; no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Graphics clear of captions**
- {"t": 5, "text": "بيخسر أكتر", "caption": "أكتر"}

**Text clear of platform UI (heuristic)**
- {"t": 30.98, "text": "وبرضو خسران 5,000 ج"}

Flagged moments: `acceptance/flagged.png`
