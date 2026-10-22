---
name: ugc-captain-reels
description: Assembles finished vertical 9:16 short-form UGC videos (TikTok and Instagram Reels, 30-60s) for the UGC Captain from raw footage — picks the best takes from transcripts, cuts dead air, layers product B-roll over talking-head audio, burns in bold word-by-word captions and hook text, adds a ducked music bed, normalizes loudness, and renders an upload-ready MP4 with ffmpeg, styled after reference creators such as Nate Flake. Use this skill whenever the user shares or points to raw clips, A-roll/B-roll, a folder of footage, or a CapCut SRT and wants a reel, TikTok, UGC ad, or short made, edited, assembled, cut down, re-cut to a different length, or restyled "like Nate Flake" (or another reference creator), even if they just say "here's my footage, make the video." Also use it to add or update a reference creator's style profile from example videos. Not for written-only copy or long-form/horizontal YouTube edits.
---

# UGC Captain Reels

Turn raw footage into a finished, upload-ready vertical video in a reference creator's style. The user is the on-camera creator ("UGC Captain"); the video is usually a UGC ad or organic post for a brand's product.

The bar: a brand should be able to post the output as-is. That means a hook that lands in the first 1–2 seconds, no dead air, a visual change every few seconds, captions people can read with the sound off, and a clear call to action.

## Files in this skill

- `references/ugc-playbook.md`: what high-performing UGC does, a library of 8 proven formats with beat timings, a hook bank and CTA patterns. Read it every time, because choosing the right format for the footage matters more than anything else.
- `references/creators/nate-flake.md`: the default style profile (look, pacing, voice). Read it every time unless the user names another creator.
- `references/creators/_template.md` — template for adding a new creator.
- `references/ugc-captain.md` — the user's own on-camera persona and brand voice. Read it every time; the reference creator shapes *structure and pacing*, the persona shapes *voice*.
- `references/edit-plan.md` — the edit plan JSON format the renderer reads. Read before writing a plan.
- `references/platform-specs.md` — TikTok/Reels specs, safe zones, lengths. Read when choosing caption/text placement or delivering.
- `scripts/inventory.py`, `scripts/transcribe.py`, `scripts/render.py`, `scripts/analyze_reference.py` — the pipeline (see below).

Requirements: `ffmpeg`/`ffprobe` and Python 3. For transcription, `pip install faster-whisper` (first run downloads a model). If that's not possible, ask the user to export auto-captions from CapCut as SRT and use `transcribe.py --srt`.

## Workflow

### 1. Get the brief

You need: the product and its one main benefit, the offer/CTA (link in bio, TikTok Shop, code), platform (TikTok, Reels, or both), target length (30–60s; default ~30s for paid ads (21–35s is the most-cited conversion sweet spot), 35–60s for organic story or podcast-style posts), the reference creator (default Nate Flake), and where the footage is. Pull what you can from the conversation and the clips themselves; only ask for what's truly missing. If the brand sent a brief with must-say lines or banned claims, those override style choices.

If there is no footage yet, don't stop — write a shoot plan in the reference creator's style (hook options, script with the persona's voice, A-roll setups and a B-roll shot list) so the user can film, then come back to assemble.

### 2. Set up the project and look at the footage

Work in a project folder (the user's footage folder, or a new one). Paths in the plan are relative to it.

```bash
python <skill>/scripts/inventory.py --base PROJECT clips/
```

This prints duration/resolution/orientation/audio per clip and writes a 4-frame contact sheet per clip into `work/sheets/`. **Look at the contact sheets** (read the images). You need to know what each B-roll clip actually shows to place it on the right line of the script, and to spot problems — horizontal footage that will crop badly, a clip that's out of focus, the product label facing away.

Classify each clip as A-roll (talking to camera, has speech) or B-roll (product, hands, lifestyle, screen recording).

### 3. Transcribe the A-roll

```bash
python <skill>/scripts/transcribe.py --base PROJECT clips/aroll_01.mp4 clips/aroll_02.mp4
```

Writes `work/words.json` (word timings, used for captions) and `work/transcript.md` (phrases with in/out times). Read `transcript.md` — this is how you "watch" the talking head.

### 4. Write the paper edit

Before writing any JSON, pick the format from `ugc-playbook.md` that fits the footage and the brief. Testimonial is the default for product ads. Use listicle when the footage has distinct points, unboxing when there's packaging footage, reaction when there's a screenshot to respond to, and podcast-style when the setup has a mic. Then lay out the story beat by beat in that format's timings, dressed in the reference creator's look and pacing. For each beat, pick the best take:

- **Choose takes on delivery, not just words.** Prefer the take with the fewest restarts and filler, with the line said in one breath. When the same line appears several times, the last complete take is usually the keeper (creators restart until they nail it).
- **Hook first.** The strongest, most specific line goes at 0:00 even if it was filmed later. No "hey guys", no intro, no logo.
- **Cut every pause.** Each phrase in the transcript is a candidate segment; drop stumbles, "um/so/like" openers, and repeated lines. Pad cuts by ~0.05s before and ~0.10s after the words so nothing sounds clipped.
- **B-roll on the claims.** Whenever the script names something visual (the product, texture, result, app screen), cover that line with matching B-roll using `cover` — the voice keeps playing. Aim for a visual change every 2–4 seconds via a cut, a cover, or a punch-in.
- **Punch-ins on jump cuts.** When two A-roll segments butt together from the same camera, alternate `zoom` (1.0 ↔ 1.12–1.2) so the jump cut reads as intentional.
- **CTA last**, said plainly, with an on-screen text overlay.
- **Hit the length.** Sum the segments; trim the weakest middle beat before touching the hook or CTA.

Show the user the paper edit as a compact table (time, line, picture) when the request is open-ended or the footage gives real choices; for a straightforward "cut this", just proceed.

### 5. Write the edit plan and render

Write `PROJECT/plan.json` following `references/edit-plan.md` (segments, covers, captions, hook text overlay, optional music bed). Then:

```bash
python <skill>/scripts/render.py PROJECT/plan.json --preview   # fast check
python <skill>/scripts/render.py PROJECT/plan.json             # final
```

### 6. Check your own work before handing it over

Grab frames and look at them — a render that "succeeded" can still be wrong.

```bash
for t in 0.5 2 5 10 20; do ffmpeg -y -v error -ss $t -i OUT.mp4 -frames:v 1 -vf scale=360:640 work/qa_$t.png; done
```

Check: the hook text and captions are inside the safe zone and not covering the face or product; B-roll lands on the right line; nothing is letterboxed or stretched; total duration matches the target; loudness is about −14 LUFS (`ffmpeg -i OUT.mp4 -af ebur128 -f null - 2>&1 | grep "I:" | tail -1`). Fix the plan and re-render if anything is off.

### 7. Deliver

Give the user:
1. The final MP4 path (and the `_cover.jpg` if `thumbnail_at` was set).
2. A short edit summary: length, hook used, takes chosen, anything you dropped and why.
3. Post copy per platform: TikTok caption (short, 3–5 hashtags, keyword-rich because TikTok search reads it) and Reels caption (a line or two more, 3–5 hashtags). Remind them to add "Paid partnership"/#ad disclosure when it's a paid brand deal.
4. **Hook variants.** For paid ads, render 3 versions that differ only in the opening segment(s) and hook text, e.g. `out/<brand>_hookA.mp4`, `hookB`, `hookC`. Copy `plan.json` to `plan_hookB.json` and swap only the first segments and the hook overlay. Brands test hooks at equal spend and scale the winner, so variants are often worth more than polish. For organic posts, list the alternate hooks with their in/out times instead of rendering them.

Keep `plan.json` — revisions ("make it 30s", "use the other hook", "less music") are just plan edits and a re-render.

## Adding or refreshing a reference creator

Best input is 3–5 downloaded videos of the creator's top-performing posts. Run:

```bash
python <skill>/scripts/analyze_reference.py refs/*.mp4 --out PROJECT/work/refs [--transcribe]
```

It reports duration, cut count, average shot length, cuts in the first 3s and loudness, and saves contact sheets of every shot and of the first 3 seconds. Look at the sheets, read transcripts, and fill in `references/creators/_template.md` as `references/creators/<name>.md`. Capture patterns (hook types, beat structure, pacing numbers, caption look, B-roll habits), not their actual lines — the goal is to borrow what makes the format work while the UGC Captain stays recognizably themselves, and copying another creator's scripts would get the user's content flagged as unoriginal.
