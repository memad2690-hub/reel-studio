# Acceptance — mb-testing-plan-v2

Verdict: **WARN** · video: `exports/v001.mp4` · 50.8s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 1 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 1523 card frames for 50.8s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 55 captions, 145 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 65 moments checked; every visible text box inside the 1080×1920 frame |
| ✅ | Graphics clear of captions | no text graphic covers more than 20% of a caption |
| ✅ | Graphics clear of the face | face found at 65/65 moments; no front graphic covers more than 30% of it |
| ✅ | Text clear of platform UI (heuristic) | no text in the bottom 220 px or the lower right 100 px column |
| ✅ | Text readable on a phone (≥ 44 px) | every text ≥ 44 px (captions included) |
| ⚠️ | Art direction (focus, density, speaker, empty page) | 3 note(s) to review |
| ✅ | Correct Arabic shaping | 77 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 50.77s, 6525 kb/s, 41.4 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 192 kb/s; integrated -17.5 LUFS, LRA 4.2 LU, true peak -1.5 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | 1 designed transition(s) (plan:blur); no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Art direction (focus, density, speaker, empty page)**
- hook: page mostly empty at 2 sampled moments
- suspects: two elements of equal weight compete for first look
- rules: two elements of equal weight compete for first look

**Art direction per scene** (measured)

| scene | look first | focal px | max texts | max words | speaker share | empty moments |
|---|---|---|---|---|---|---|
| hook | ads budget 50,000 ج | 130 | 2 | 5 | 44% | 2 |
| mistake | أكتر خطأ بشوفه | 98 | 3 | 7 | 14% | 0 |
| suspects | مفيش اختبار بيفصل بينهم | 105 | 3 | 4 | 44% | 0 |
| decide | هتحدد بناءً على إيه؟ | 84 | 1 | 4 | 63% | 0 |
| plan | اعمل testing plan | 92 | 2 | 7 | 44% | 1 |
| rules | ثبت المتغيرات | 74 | 3 | 6 | 14% | 0 |
| payoff | بتشتريلك معلومات | 101 | 3 | 4 | 44% | 0 |
| cta | اكتبلي BUDGET مثال testing pla | 120 | 1 | 7 | 44% | 0 |
