# Acceptance — scaling-ui-test

Verdict: **PASS** · video: `exports/v002.mp4` · 49.6s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 0 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 1487 card frames for 49.6s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 60 captions, 159 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 57 moments checked; every visible text box inside the 1080×1920 frame |
| ✅ | Graphics clear of captions | no text graphic covers more than 20% of a caption |
| ✅ | Graphics clear of the face | face found at 56/57 moments; no front graphic covers more than 30% of it |
| ✅ | Text clear of platform UI (heuristic) | no text in the bottom 220 px or the lower right 100 px column |
| ✅ | Text readable on a phone (≥ 44 px) | every text ≥ 44 px (captions included) |
| ✅ | Art direction (focus, density, speaker, empty page) | 6 scenes: one dominant element each, ≤ 3 texts at once, ≤ 12 new words per 2 s, speaker ≥ 10% of the frame |
| ✅ | Correct Arabic shaping | 69 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 49.57s, 6566 kb/s, 40.7 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 193 kb/s; integrated -19.5 LUFS, LRA 4.4 LU, true peak -3.3 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | 1 designed transition(s) (conclusion-5:blur); no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Art direction per scene** (measured)

| scene | look first | focal px | max texts | max words | speaker share | empty moments |
|---|---|---|---|---|---|---|
| hook-1 | ممكن brand يقول لي: معايا budg | 131 | 1 | 9 | 44% | 0 |
| setup-2 | the speaker | — | 0 | 0 | 100% | 0 |
| example-3 | تخيل brand عنده stock أصلًا هو | 96 | 2 | 8 | 44% | 0 |
| process-4 | 1 المخزون يستحمل 2 الـ contrib | 68 | 1 | 12 | 37% | 1 |
| conclusion-5 | الـ scaling الحقيقي مش إنك تصر | 130 | 1 | 8 | 44% | 0 |
| cta-6 | ابعت لي SCALE | 120 | 1 | 3 | 44% | 0 |
