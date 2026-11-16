# Acceptance — mb-32

Verdict: **WARN** · video: `exports/v001.mp4` · 63.3s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 1 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 1899 card frames for 63.3s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 74 captions, 188 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 84 moments checked; every visible text box inside the 1080×1920 frame |
| ✅ | Graphics clear of captions | no text graphic covers more than 20% of a caption |
| ✅ | Graphics clear of the face | face found at 84/84 moments; no front graphic covers more than 30% of it |
| ✅ | Text clear of platform UI (heuristic) | no text in the bottom 220 px or the lower right 100 px column |
| ✅ | Text readable on a phone (≥ 44 px) | every text ≥ 44 px (captions included) |
| ⚠️ | Art direction (focus, density, speaker, empty page) | 3 note(s) to review |
| ✅ | Correct Arabic shaping | 108 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 63.30s, 6350 kb/s, 50.2 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 192 kb/s; integrated -21.2 LUFS, LRA 4.2 LU, true peak -2.1 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | 7 designed transition(s) (question:blur, cpm-means:blur, battle:whip, stage:blur, when:blur, apples:blur, funnel:blur); no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Art direction (focus, density, speaker, empty page)**
- battle: 16 new words within 2 s (more than a 2-second read)
- same: two elements of equal weight compete for first look
- cta: page mostly empty at 2 sampled moments

**Art direction per scene** (measured)

| scene | look first | focal px | max texts | max words | speaker share | empty moments |
|---|---|---|---|---|---|---|
| hook | الـ CPM | 80 | 3 | 7 | 37% | 0 |
| question | إيه أحسن أكيد ما نعرفش | 140 | 1 | 5 | 44% | 0 |
| cpm-means | الـ CPM بيقولك الظهور بكام مش  | 138 | 1 | 9 | 44% | 0 |
| battle | campaign رخيصة مش هتشتري 10 طل | 58 | 2 | 16 | 50% | 0 |
| order | CTR Landing page views Convers | 60 | 1 | 8 | 44% | 0 |
| stage | تشوف ساعتها كل حملة بتقع في أن | 141 | 1 | 8 | 44% | 0 |
| when | امتى بقى الـ CPM يبقى | 98 | 1 | 5 | 44% | 0 |
| same | لو عِلي فجأة السوق أو الموسم | 70 | 3 | 6 | 37% | 1 |
| apples | كأنك بتقارن apples to oranges | 247 | 1 | 7 | 39% | 1 |
| funnel | لازم تتابع الـ funnel كلها | 126 | 1 | 8 | 44% | 0 |
| cta | اعمل follow واكتب FUNNEL dashb | 120 | 1 | 10 | 44% | 2 |
