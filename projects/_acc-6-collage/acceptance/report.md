# Acceptance — _acc-6-collage

Verdict: **WARN** · video: `exports/v003.mp4` · 71.8s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 0 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 2153 card frames for 71.8s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 75 captions, 185 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 80 moments checked; every visible text box inside the 1080×1920 frame |
| ✅ | Graphics clear of captions | no text graphic covers more than 20% of a caption |
| ✅ | Graphics clear of the face | face found at 80/80 moments; no front graphic covers more than 30% of it (full-frame dim behind: 01 نفس النوع ولا مختلف؟, 02 Creative Diversity metric جوه Ads Man) |
| ✅ | Text clear of platform UI (heuristic) | no text in the bottom 220 px or the lower right 100 px column |
| ✅ | Text readable on a phone (≥ 44 px) | every text ≥ 44 px (captions included) |
| ⚠️ | Art direction (focus, density, speaker, empty page) | 7 note(s) to review |
| ✅ | Correct Arabic shaping | 87 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 71.77s, 8243 kb/s, 74.0 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 191 kb/s; integrated -17.1 LUFS, LRA 4.6 LU, true peak -1.5 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | 6 designed transition(s) (same:zoom, why:zoom, metric:blur, path:blur, angles:zoom, cta:blur); no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Art direction (focus, density, speaker, empty page)**
- same: no dominant element (largest text 58 px)
- why: 4 text elements at once (competing)
- levels: 4 text elements at once (competing)
- levels: no dominant element (largest text 62 px)
- levels: page mostly empty at 2 sampled moments
- angles: 5 text elements at once (competing)
- cta: page mostly empty at 3 sampled moments

**Art direction per scene** (measured)

| scene | look first | focal px | max texts | max words | speaker share | empty moments |
|---|---|---|---|---|---|---|
| hook | 01 نفس النوع ولا مختلف؟ | 84 | 1 | 5 | 100% | 0 |
| same | عشر إعلانات على Meta | 58 | 2 | 5 | 58% | 0 |
| why | ≠ three creative angles | 67 | 4 | 4 | 58% | 0 |
| metric | 02 Creative Diversity metric ج | 88 | 1 | 7 | 100% | 0 |
| path | Ads Manager Columns Customize  | 58 | 2 | 7 | 14% | 1 |
| levels | Low | 62 | 4 | 7 | 44% | 2 |
| angles | التنوع = تغير الـ angle | 72 | 5 | 8 | 37% | 0 |
| cta | اكتب في الكومنتات ANGLES أمثلة | 120 | 2 | 8 | 43% | 3 |
