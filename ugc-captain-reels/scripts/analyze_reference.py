#!/usr/bin/env python3
"""Measure a reference creator video so its style can be written into a
creator profile (references/creators/<name>.md).

Usage:
    python analyze_reference.py ref_videos/nate_01.mp4 [--out work/refs] [--transcribe]

Reports: duration, number of cuts, average shot length, cuts in the first 3s,
loudness, and saves a contact sheet of the first frame after every cut plus the
first 3 seconds (the hook) so you can look at framing, text and captions.
"""
import argparse
import json
import os
import re
import subprocess
import sys


def scene_cuts(path, thresh):
    res = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-vf",
                          f"select='gt(scene,{thresh})',showinfo", "-an", "-f", "null", "-"],
                         stderr=subprocess.PIPE, text=True)
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", res.stderr)]


def loudness(path):
    res = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                         stderr=subprocess.PIPE, text=True)
    m = re.findall(r"I:\s+(-?[0-9.]+) LUFS", res.stderr)
    return float(m[-1]) if m else None


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", path], stdout=subprocess.PIPE,
                                text=True).stdout.strip())


def tile(path, times, out, cols=6):
    times = times[:24] or [0]
    rows = (len(times) + cols - 1) // cols
    inputs = []
    for t in times:
        inputs += ["-ss", f"{t + 0.05:.2f}", "-i", path]
    n = len(times)
    fc = "".join(f"[{i}:v]scale=180:320:force_original_aspect_ratio=decrease,"
                 f"pad=180:320:(ow-iw)/2:(oh-ih)/2,setsar=1[f{i}];" for i in range(n))
    pads = cols * rows - n
    for j in range(pads):
        fc += f"color=black:s=180x320:d=1[p{j}];"
    labels = "".join(f"[f{i}]" for i in range(n)) + "".join(f"[p{j}]" for j in range(pads))
    layout = "|".join(f"{(k % cols) * 180}_{(k // cols) * 320}" for k in range(cols * rows))
    fc += f"{labels}xstack=inputs={cols * rows}:layout={layout}[o]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
                    "-map", "[o]", "-frames:v", "1", out])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", default="work/refs")
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--transcribe", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    report = []
    for v in args.videos:
        name = os.path.splitext(os.path.basename(v))[0]
        dur = duration(v)
        cuts = scene_cuts(v, args.threshold)
        shots = [0.0] + cuts
        lengths = [b - a for a, b in zip(shots, shots[1:] + [dur])]
        r = {"video": v, "duration": round(dur, 1), "cuts": len(cuts),
             "avg_shot_s": round(sum(lengths) / len(lengths), 2),
             "cuts_first_3s": sum(1 for c in cuts if c < 3),
             "cuts_per_10s": round(len(cuts) / dur * 10, 1) if dur else 0,
             "loudness_lufs": loudness(v)}
        tile(v, shots, os.path.join(args.out, f"{name}_shots.jpg"))
        tile(v, [0, 0.5, 1.0, 1.5, 2.0, 2.5], os.path.join(args.out, f"{name}_hook.jpg"))
        r["shots_sheet"] = os.path.join(args.out, f"{name}_shots.jpg")
        r["hook_sheet"] = os.path.join(args.out, f"{name}_hook.jpg")
        if args.transcribe:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from transcribe import whisper_words
            words = whisper_words(v, "small.en")
            r["transcript"] = " ".join(w["w"] for w in words)
            r["words_per_min"] = round(len(words) / dur * 60) if dur else None
        report.append(r)
        print(json.dumps(r, indent=1))
    json.dump(report, open(os.path.join(args.out, "reference_report.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
