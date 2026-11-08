# Acceptance — _acc-5-comparison

Verdict: **WARN** · video: `exports/v002.mp4` · 47.3s

| | Check | Result |
|---|---|---|
| ✅ | No incorrect financial calculations | 0 financial component(s) checked by the build (totals, results, tones, chart sums) |
| ✅ | No missing assets | audio present; 1419 card frames for 47.3s; fonts bundled |
| ✅ | Graphics timed to speech | every anchor found; nothing timed after its scene ends |
| ✅ | Caption timing | 52 captions, 130 words; each caption starts on its first spoken word (±1 frame) |
| ✅ | No clipped text | 55 moments checked; every visible text box inside the 1080×1920 frame |
| ✅ | Graphics clear of captions | no text graphic covers more than 20% of a caption |
| ✅ | Graphics clear of the face | face found at 55/55 moments; no front graphic covers more than 30% of it |
| ✅ | Text clear of platform UI (heuristic) | no text in the bottom 220 px or the lower right 100 px column |
| ✅ | Text readable on a phone (≥ 44 px) | every text ≥ 44 px (captions included) |
| ⚠️ | Art direction (focus, density, speaker, empty page) | 2 note(s) to review |
| ✅ | Correct Arabic shaping | 66 distinct texts; Cairo loaded; letters join (each word drawn shaped differs from its letters drawn apart) |
| ✅ | No broken RTL | every line with Arabic runs right→left (also when it starts with a Latin word); numbers read left→right |
| ✅ | Page runs without errors | no page or console errors |
| ✅ | Export format (1080×1920 · 9:16 · 30 fps · H.264 · MP4) | 1080×1920, 30/1, h264 High yuv420p, faststart yes, 47.30s, 4617 kb/s, 27.3 MB |
| ✅ | Consistent audio | aac 48000 Hz 2ch 193 kb/s; integrated -21.3 LUFS, LRA 4.0 LU, true peak -4.4 dBTP; audio length = video length ±0.1 s |
| ✅ | Stable rendering (decodes cleanly, no black frames) | whole file decodes without errors; no black frames ≥ 0.1 s |
| ✅ | Smooth transitions | 4 designed transition(s) (ads:whip, mistake:blur, test:whip, recap:zoom); no frozen picture ≥ 1.5 s |
| ✅ | Deterministic rerenders | 4 frames rendered twice: byte-identical PNGs |

**Art direction (focus, density, speaker, empty page)**
- mistake: page mostly empty at 2 sampled moments
- three: 18 new words within 2 s (more than a 2-second read)

**Art direction per scene** (measured)

| scene | look first | focal px | max texts | max words | speaker share | empty moments |
|---|---|---|---|---|---|---|
| hook | أغلى؟ | 230 | 1 | 1 | 90% | 0 |
| ads | الإعلان الأول design ممتاز الأ | 58 | 1 | 12 | 50% | 0 |
| mistake | الأجمل مش دايمًا بيكسب | 84 | 2 | 5 | 44% | 2 |
| three | 3 حاجات | 112 | 3 | 18 | 14% | 0 |
| test | تخمين تختار إعلان اختبار فعلي  | 58 | 1 | 10 | 50% | 0 |
| recap | Attention Relevance وReason to | 149 | 1 | 5 | 44% | 0 |
