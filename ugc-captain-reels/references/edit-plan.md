# Edit plan format (`plan.json`)

`scripts/render.py plan.json` reads this file. All paths are relative to the folder containing `plan.json`. Times are in seconds.

```json
{
  "output": "out/brandname_tiktok_v1.mp4",
  "loudness_lufs": -14,
  "thumbnail_at": 0.8,
  "segments": [
    {"source": "clips/aroll_02.mp4", "in": 14.20, "out": 16.85, "zoom": 1.15},
    {"source": "clips/aroll_01.mp4", "in": 3.05,  "out": 7.40,
     "cover": {"source": "clips/broll_pour.mov", "in": 1.0}},
    {"source": "clips/broll_unbox.mp4", "in": 0.0, "out": 1.2, "audio": false, "captions": false},
    {"source": "clips/aroll_01.mp4", "in": 22.10, "out": 25.60, "zoom": 1.0}
  ],
  "captions": {
    "words_file": "work/words.json",
    "max_words": 3,
    "font": "Inter",
    "size": 84,
    "color": "#FFFFFF",
    "highlight": "#FFE600",
    "highlight_active": true,
    "uppercase": true,
    "y": 0.64
  },
  "text_overlays": [
    {"text": "I was wrong about this", "start": 0.0, "end": 2.2, "position": "top", "style": "hook"},
    {"text": "Link in bio 👆", "start": 30.5, "end": 34.0, "position": "bottom", "style": "label"}
  ],
  "music": {"source": "music/bed.mp3", "volume_db": -20, "duck": true}
}
```

## Segments

Played in order, back to back. Each one is cut from `source` between `in` and `out`, scaled to fill 1080×1920 (center crop — horizontal footage loses its sides, so check the framing), and conformed to 30 fps.

| field | default | meaning |
|---|---|---|
| `source`, `in`, `out` | required | clip and the part of it to use |
| `zoom` | 1.0 | punch-in. 1.12–1.2 on alternating jump cuts. Above ~1.3 phone footage gets soft |
| `cover` | — | `{"source", "in", "zoom"}`: show this B-roll for the segment's length while **keeping the segment's audio**. The way to put B-roll over talking. B-roll must be at least as long as the segment from its `in` |
| `audio` | true | false = silence (use for pure B-roll segments with no useful sound) |
| `volume` | 1.0 | linear gain for this segment's audio |
| `captions` | true | false = no captions for this segment |
| `fit` | `cover` (video) / `contain` (image) | `contain` shows the whole frame over a blurred fill. Use it for screenshots and reviews; also works inside `cover` |
| `mirror` | false | horizontal flip (only for selfie footage that came out mirrored; never on footage with readable text) |

**Still images** (.jpg/.png/.webp: review screenshots, comments, before/after photos) work as a segment `source` or a `cover` source. They're held for the segment's length (`in` 0, `out` = seconds to show), have no audio, and default to `fit: contain`. For a reaction-style callout, use the image as a `cover` over the A-roll line that talks about it.

## Captions

Built from `words_file` (from `transcribe.py`) and re-timed onto the edit automatically, so they follow your cuts. Words are grouped into chunks of up to `max_words`, breaking at punctuation and pauses; the word being spoken is colored `highlight`. `y` is the vertical center as a fraction of the height. Set `"enabled": false` to skip captions.

## Text overlays

`style: "hook"` = dark text on a white box (native TikTok text look), for the hook headline. `style: "label"` = white outlined text, for CTA/price/callouts. `position`: `top` (0.20), `upper` (0.30), `center` (0.45), `bottom` (0.74), or a number 0–1. Keep hook text to ≤ 7 words.

## Music

Optional. Loops to fill, fades out over the last second. `volume_db` −18 to −24 sits under the voice; `duck: true` lowers it further whenever the voice is speaking. For TikTok/Reels organic posts, trending sounds are better added in the app (licensing); only render music in when it's royalty-free or supplied by the brand.

## Other

- `loudness_lufs`: final loudness target (−14 is right for both platforms).
- `thumbnail_at`: if set, also writes `<output>_cover.jpg` from that time.
- `fonts_dir`: folder of extra .ttf/.otf files (e.g. a brand font) for captions/overlays.
- Intermediate files go to `work/` next to the plan; render with `--preview` for a quick low-quality check.
