# Acceptance — ceos-1

Verdict: **WARN** · video: `exports/v002.mp4` · 98.4s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 0 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 2951 card frames for 98.4s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 101 captions, 266 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 118 moments checked; every visible text box inside the 1080×1920 frame |
| ✅ | Graphics clear of captions | no text graphic covers more than 20% of a caption |
| ✅ | Graphics clear of the face | face found at 118/118 moments; no front graphic covers more than 30% of it |
| ✅ | Text clear of platform UI (heuristic) | no text in the bottom 220 px or the lower right 100 px column |
| ✅ | Text readable on a phone (≥ 44 px) | every text ≥ 44 px (captions included) |
| ⚠️ | Art direction (focus, density, speaker, empty page) | 15 note(s) to review |
| ✅ | Correct Arabic shaping | 121 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 98.37s, 6676 kb/s, 82.1 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 192 kb/s; integrated -13.5 LUFS, LRA 1.9 LU, true peak -1.4 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | 1 designed transition(s) (diversity:zoom); no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Art direction (focus, density, speaker, empty page)**
- seven: page mostly empty at 3 sampled moments
- ten: page mostly empty at 5 sampled moments
- motives: 6 text elements at once (competing)
- motives: no dominant element (largest text 51 px)
- motives: page mostly empty at 2 sampled moments
- same: no dominant element (largest text 50 px)
- same: page mostly empty at 2 sampled moments
- diversity: no dominant element (largest text 55 px)
- diversity: speaker frame only 5% of the screen
- explosion: 4 text elements at once (competing)
- explosion: no dominant element (largest text 48 px)
- explosion: speaker frame only 5% of the screen
- test: no dominant element (largest text 55 px)
- test: speaker frame only 5% of the screen
- how: 6 text elements at once (competing)

**Art direction per scene** (measured)

| scene | look first | focal px | max texts | max words | speaker share | empty moments |
|---|---|---|---|---|---|---|
| hook | the speaker | — | 0 | 0 | 100% | 0 |
| seven | بسبع إعلانات مختلفة | 171 | 1 | 3 | 44% | 3 |
| ten | ولا واحد بيشتريه لنفس السبب | 79 | 1 | 5 | 37% | 5 |
| motives | Statement | 51 | 6 | 2 | 37% | 2 |
| difference | شايف الفرق؟ | 82 | 1 | 6 | 91% | 0 |
| same | كله بيقول نفس الحاجة | 50 | 1 | 5 | 37% | 2 |
| diversity | jacket واحد | 55 | 2 | 4 | 5% | 1 |
| explosion | مريح طول اليوم | 48 | 4 | 10 | 5% | 1 |
| test | اختبر إيه اللي بيجيب عملا أكتر | 55 | 1 | 6 | 5% | 1 |
| ceos | Creative Engine OS | 108 | 2 | 5 | 44% | 1 |
| how | جاهزة تبدأ تختبرها | 85 | 6 | 9 | 37% | 1 |
| founder | the speaker | — | 0 | 0 | 100% | 0 |
| cta | اعمل follow واكتب ANGLES كام a | 110 | 1 | 9 | 44% | 1 |
