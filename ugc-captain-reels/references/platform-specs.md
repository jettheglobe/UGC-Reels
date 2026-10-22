# TikTok and Instagram Reels specs

Both platforms take the same master file, so render once and post to both unless the brand wants different hooks or CTAs.

| | TikTok | Instagram Reels |
|---|---|---|
| Frame | 1080×1920, 9:16 | 1080×1920, 9:16 |
| Codec | H.264 + AAC, 30 fps | H.264 + AAC, 30 fps |
| Loudness | about −14 LUFS, peak ≤ −1 dBTP | same |
| Length for this business | 30–60s (ads usually 21–35s perform best) | 30–60s (keep under 90s to be eligible as a Reel everywhere) |
| Caption text | short, keyword-rich (TikTok search indexes it), 3–5 hashtags | 1–3 lines, 3–5 hashtags |
| Disclosure | toggle "Content disclosure → Paid partnership" for brand deals | "Add paid partnership label" |

## Safe zones (1080×1920)

App UI covers parts of the frame. Keep text and the product inside the middle area:

- **Top ~220 px**: status bar, "Following/For You", Reels header. The hook overlay at `top` (y=0.20, about 384 px) is below this.
- **Bottom ~420 px (TikTok) / ~480 px (Reels)**: username, caption, sound ticker. Keep captions at or above y≈0.70 (1344 px). The default caption `y` of 0.64 is safe on both.
- **Right ~140 px**: like/comment/share buttons. The caption styles use a 140 px right margin.

When the face sits low in frame, move captions up (`y` 0.30–0.40) so they don't cover the mouth. Don't put words on top of the product during a B-roll cover; move captions or turn them off for that segment.

## Retention cues that apply to both

- Something should move or change in the first second; the first spoken word should land within ~0.3 s.
- On-screen hook text doubles the hook for silent viewers (most people watch with sound off at first).
- Ending on a line that loops back to the start ("...and that's why I was wrong") boosts rewatches.
