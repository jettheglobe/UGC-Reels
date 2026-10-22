#!/usr/bin/env python3
"""Transcribe talking-head clips with word-level timestamps.

Usage:
    python transcribe.py --base PROJECT_DIR clips/aroll_01.mp4 clips/aroll_02.mp4
    python transcribe.py --base PROJECT_DIR --srt capcut.srt --source clips/aroll_01.mp4

Writes (merging with anything already there):
    PROJECT_DIR/work/words.json      word timings keyed by clip path (relative to base)
    PROJECT_DIR/work/transcript.md   readable phrases with in/out times, for picking takes

Uses faster-whisper if installed (pip install faster-whisper), else openai-whisper.
With --srt (e.g. a CapCut auto-caption export) no speech model is needed; word
timings are spread across each cue by character length, which is close enough
for captions but less precise for tight cuts.
"""
import argparse
import json
import os
import re
import sys

GAP = 0.35  # silence that splits phrases


def whisper_words(path, model_name):
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_name, device="auto", compute_type="int8")
        segs, _ = model.transcribe(path, word_timestamps=True, vad_filter=True, language="en")
        return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
                for s in segs for w in (s.words or []) if w.word.strip()]
    except ImportError:
        pass
    try:
        import whisper
    except ImportError:
        sys.exit("No speech model found. Run: pip install faster-whisper  "
                 "(or export an SRT from CapCut and use --srt)")
    model = whisper.load_model(model_name)
    res = model.transcribe(path, word_timestamps=True, language="en")
    return [{"w": w["word"].strip(), "s": round(w["start"], 3), "e": round(w["end"], 3)}
            for s in res["segments"] for w in s.get("words", []) if w["word"].strip()]


def srt_time(t):
    h, m, rest = t.strip().replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def srt_words(path):
    words = []
    blocks = re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().strip())
    for b in blocks:
        lines = [l for l in b.strip().splitlines() if l.strip()]
        tl = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if tl is None:
            continue
        a, z = [srt_time(x) for x in lines[tl].split("-->")]
        toks = " ".join(lines[tl + 1:]).split()
        total = sum(len(t) + 1 for t in toks) or 1
        t = a
        for tok in toks:
            d = (z - a) * (len(tok) + 1) / total
            words.append({"w": tok, "s": round(t, 3), "e": round(t + d * 0.9, 3)})
            t += d
    return words


def phrases(words):
    out, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > GAP or re.search(r"[.!?]$", cur[-1]["w"])):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def fmt(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--base", default=".")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--srt")
    ap.add_argument("--source", help="clip the --srt belongs to")
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    work = os.path.join(base, "work")
    os.makedirs(work, exist_ok=True)
    wpath = os.path.join(work, "words.json")
    data = json.load(open(wpath)) if os.path.exists(wpath) else {"files": {}}

    jobs = []
    if args.srt:
        if not args.source:
            sys.exit("--srt needs --source <clip it belongs to>")
        jobs.append((args.source, srt_words(args.srt)))
    for c in args.clips:
        print(f"transcribing {c} ...", flush=True)
        jobs.append((c, whisper_words(os.path.join(base, c) if not os.path.isabs(c) else c, args.model)))

    for clip, words in jobs:
        rel = os.path.relpath(os.path.join(base, clip), base) if not os.path.isabs(clip) \
            else os.path.relpath(clip, base)
        data["files"][rel] = words
    json.dump(data, open(wpath, "w"), indent=1)

    md = ["# Transcript (phrases split on pauses > %.2fs)\n" % GAP,
          "Use these in/out times in the edit plan. Pad ~0.05s before and ~0.10s after a phrase.\n"]
    for clip, words in data["files"].items():
        md.append(f"\n## {clip}\n")
        prev_end = None
        for p in phrases(words):
            if prev_end is not None and p[0]["s"] - prev_end > 1.0:
                md.append(f"  ... {p[0]['s'] - prev_end:.1f}s pause ...")
            text = " ".join(w["w"] for w in p)
            md.append(f"- `{fmt(p[0]['s'])} - {fmt(p[-1]['e'])}` "
                      f"(in={p[0]['s']:.2f} out={p[-1]['e']:.2f}) {text}")
            prev_end = p[-1]["e"]
    open(os.path.join(work, "transcript.md"), "w").write("\n".join(md) + "\n")
    print(f"wrote {wpath} and work/transcript.md")


if __name__ == "__main__":
    main()
