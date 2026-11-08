# Acceptance — _acc-1-financial

Verdict: **WARN** · video: `exports/v005.mp4` · 48.6s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 6 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 1458 card frames for 48.6s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 57 captions, 147 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 60 moments checked; every visible text box inside the 1080×1920 frame |
| ✅ | Graphics clear of captions | no text graphic covers more than 20% of a caption |
| ✅ | Graphics clear of the face | face found at 60/60 moments; no front graphic covers more than 30% of it |
| ✅ | Text clear of platform UI (heuristic) | no text in the bottom 220 px or the lower right 100 px column |
| ✅ | Text readable on a phone (≥ 44 px) | every text ≥ 44 px (captions included) |
| ⚠️ | Art direction (focus, density, speaker, empty page) | 5 note(s) to review |
| ✅ | Correct Arabic shaping | 71 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 48.60s, 5934 kb/s, 36.1 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 193 kb/s; integrated -20.2 LUFS, LRA 5.9 LU, true peak -2.0 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | cuts only; no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Art direction (focus, density, speaker, empty page)**
- setup: two elements of equal weight compete for first look
- math: 5 text elements at once (competing)
- math: two elements of equal weight compete for first look
- margin: page mostly empty at 2 sampled moments
- breakeven: 5 text elements at once (competing)

**Art direction per scene** (measured)

| scene | look first | focal px | max texts | max words | speaker share | empty moments |
|---|---|---|---|---|---|---|
| hook | بيخسر أكتر | 112 | 2 | 3 | 100% | 0 |
| setup | Sales 56,000 ج | 103 | 3 | 4 | 37% | 0 |
| math | خسارة 5,000 ج | 74 | 5 | 7 | 37% | 0 |
| roas | ROAS 4 مبروك؟ | 92 | 2 | 4 | 63% | 0 |
| margin | ابدأ من Contribution Margin | 84 | 3 | 6 | 44% | 2 |
| breakeven | Break-even 5 | 155 | 5 | 9 | 37% | 0 |
| cta | اكتب في الكومنتات PROFIT فيديو | 120 | 1 | 9 | 44% | 0 |
