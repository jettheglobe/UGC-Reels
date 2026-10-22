#!/usr/bin/env python3
"""Inventory raw footage: duration, resolution, orientation, fps, audio, plus a
4-frame contact sheet per clip so you can SEE the B-roll before planning.

Usage:
    python inventory.py --base PROJECT_DIR clips/
Writes PROJECT_DIR/work/inventory.json and PROJECT_DIR/work/sheets/<clip>.jpg
"""
import argparse
import json
import os
import subprocess

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                          "-show_format", path], stdout=subprocess.PIPE, text=True).stdout
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    dur = float(d["format"].get("duration", 0))
    info = {"duration": round(dur, 2), "has_audio": a is not None}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []):
            rot = int(sd.get("rotation", rot) or rot)
        rot = int(v.get("tags", {}).get("rotate", rot))
        if abs(rot) in (90, 270):
            w, h = h, w
        num, den = v.get("avg_frame_rate", "0/1").split("/")
        info.update(width=w, height=h, fps=round(float(num) / float(den or 1), 2),
                    orientation="vertical" if h > w else "horizontal" if w > h else "square")
    return info


def sheet(path, dur, out):
    times = [dur * f for f in (0.1, 0.35, 0.6, 0.85)]
    inputs = []
    for t in times:
        inputs += ["-ss", f"{t:.2f}", "-i", path]
    fc = "".join(f"[{i}:v]scale=270:480:force_original_aspect_ratio=decrease,"
                 f"pad=270:480:(ow-iw)/2:(oh-ih)/2,setsar=1[f{i}];" for i in range(4))
    fc += "".join(f"[f{i}]" for i in range(4)) + "hstack=inputs=4[o]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
                    "-map", "[o]", "-frames:v", "1", out])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--base", default=".")
    args = ap.parse_args()
    base = os.path.abspath(args.base)
    sheets = os.path.join(base, "work", "sheets")
    os.makedirs(sheets, exist_ok=True)

    files = []
    for p in args.paths:
        full = os.path.join(base, p)
        if os.path.isdir(full):
            files += sorted(os.path.join(full, f) for f in os.listdir(full)
                            if os.path.splitext(f)[1].lower() in VIDEO_EXT)
        else:
            files.append(full)

    inv = {}
    for f in files:
        rel = os.path.relpath(f, base)
        info = probe(f)
        sp = os.path.join(sheets, rel.replace(os.sep, "__") + ".jpg")
        sheet(f, info["duration"], sp)
        info["contact_sheet"] = os.path.relpath(sp, base)
        inv[rel] = info
        print(f"{rel}: {info['duration']}s {info.get('width')}x{info.get('height')} "
              f"{info.get('orientation')} audio={info['has_audio']}")
    json.dump(inv, open(os.path.join(base, "work", "inventory.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
