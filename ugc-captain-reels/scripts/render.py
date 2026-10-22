#!/usr/bin/env python3
"""Render a vertical 9:16 short-form video from an edit plan (JSON).

Usage:
    python render.py plan.json [--workdir work] [--preview]

The plan format is documented in references/edit-plan.md. Pipeline:
  1. Cut every segment from its source, scale/crop to 1080x1920, apply
     punch-in zoom, and (optionally) cover the picture with B-roll while
     keeping the segment's own audio. Each segment becomes a uniform clip.
  2. Concatenate the clips.
  3. Build one .ass subtitle file (word-by-word captions + text overlays),
     burn it in, mix an optional music bed with ducking, and normalize
     loudness for TikTok/Reels.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from captions import build_ass, remap_words, load_words  # noqa: E402

W, H, FPS = 1080, 1920, 30
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXT


def input_args(path, start, dur):
    """Seek into a video, or loop a still image (screenshots, reviews) for `dur`."""
    if is_image(path):
        return ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", path]
    return ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", path]


def run(cmd):
    print("+ " + " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""), flush=True)
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-3000:])
        raise SystemExit(f"ffmpeg failed (exit {res.returncode})")
    return res


def has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "csv=p=0", path],
        stdout=subprocess.PIPE, text=True).stdout.strip()
    return bool(out)


def frame_filter(zoom=1.0, mirror=False, label_in="0:v", label_out="v", fit="cover"):
    """Scale to cover 1080x1920, punch in by `zoom`, center-crop, fix fps/sar."""
    zw, zh = int(round(W * zoom / 2) * 2), int(round(H * zoom / 2) * 2)
    if fit == "contain":  # whole image visible on a blurred fill (screenshots, reviews)
        return (f"[{label_in}]split=2[bg][fg];"
                f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3[bgb];"
                f"[fg]scale={int(W * 0.9)}:{int(H * 0.8)}:force_original_aspect_ratio=decrease[fgs];"
                f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS},format=yuv420p[{label_out}]")
    f = (f"[{label_in}]scale={zw}:{zh}:force_original_aspect_ratio=increase,"
         f"crop={W}:{H},setsar=1,fps={FPS}")
    if mirror:
        f += ",hflip"
    return f + f",format=yuv420p[{label_out}]"


def render_segment(seg, idx, base, workdir):
    src = os.path.join(base, seg["source"])
    t_in, t_out = float(seg["in"]), float(seg["out"])
    dur = t_out - t_in
    if dur <= 0:
        raise SystemExit(f"segment {idx}: out must be greater than in")
    out = os.path.join(workdir, f"seg_{idx:03d}.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error"] + input_args(src, t_in, dur)
    cover = seg.get("cover")
    use_audio = seg.get("audio", True) and not is_image(src) and has_audio(src)
    if cover:
        csrc = os.path.join(base, cover["source"])
        cmd += input_args(csrc, float(cover.get("in", 0)), dur)
    cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    silent_idx = 2 if cover else 1
    vin = "1:v" if cover else "0:v"
    vsrc = cover or seg
    zoom = float(vsrc.get("zoom", 1.0))
    fit = vsrc.get("fit", "contain" if is_image(os.path.join(base, vsrc["source"])) else "cover")
    filters = [frame_filter(zoom, seg.get("mirror", False), vin, "v", fit)]
    if use_audio:
        filters.append(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,"
                       f"volume={seg.get('volume', 1.0)},"
                       f"afade=t=in:d=0.015,afade=t=out:st={max(dur - 0.015, 0):.3f}:d=0.015[a]")
        alabel = "[a]"
    else:
        alabel = f"{silent_idx}:a"
    cmd += ["-filter_complex", ";".join(filters), "-map", "[v]", "-map", alabel,
            "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out]
    run(cmd)
    return out, dur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--preview", action="store_true", help="fast low-quality render")
    args = ap.parse_args()

    with open(args.plan) as f:
        plan = json.load(f)
    base = os.path.dirname(os.path.abspath(args.plan))
    workdir = args.workdir or os.path.join(base, "work")
    os.makedirs(workdir, exist_ok=True)
    output = os.path.join(base, plan.get("output", "final.mp4"))
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    # 1. segments
    clips, timeline, t = [], [], 0.0
    for i, seg in enumerate(plan["segments"]):
        path, dur = render_segment(seg, i, base, workdir)
        clips.append(path)
        timeline.append({"source": seg["source"], "in": float(seg["in"]),
                         "out": float(seg["out"]), "start": t,
                         "captions": seg.get("captions", True)})
        t += dur
    total = t

    # 2. concat
    listfile = os.path.join(workdir, "concat.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    joined = os.path.join(workdir, "joined.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listfile,
         "-c", "copy", joined])

    # 3. captions + overlays -> .ass
    cap = plan.get("captions", {})
    words = []
    if cap.get("enabled", True) and cap.get("words_file"):
        words = remap_words(load_words(os.path.join(base, cap["words_file"])), timeline)
    ass_path = os.path.join(workdir, "subs.ass")
    with open(ass_path, "w") as f:
        f.write(build_ass(words, plan.get("text_overlays", []), cap, W, H))

    # 4. final pass: burn subs, music bed, loudness
    fontsdir = plan.get("fonts_dir")
    sub_f = f"subtitles={ass_path}" + (f":fontsdir={os.path.join(base, fontsdir)}" if fontsdir else "")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", joined]
    music = plan.get("music")
    lufs = float(plan.get("loudness_lufs", -14))
    if music:
        cmd += ["-stream_loop", "-1", "-i", os.path.join(base, music["source"])]
        mvol = float(music.get("volume_db", -18))
        fc = (f"[0:v]{sub_f}[v];"
              f"[1:a]atrim=0:{total:.3f},volume={mvol}dB,"
              f"afade=t=out:st={max(total - 1.0, 0):.3f}:d=1[m];")
        if music.get("duck", True):
            fc += ("[0:a]asplit=2[voice][sc];"
                   "[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[mduck];")
        else:
            fc += "[0:a]anull[voice];[m]anull[mduck];"
        fc += f"[voice][mduck]amix=inputs=2:duration=first:normalize=0,loudnorm=I={lufs}:TP=-1.0:LRA=11[a]"
    else:
        fc = f"[0:v]{sub_f}[v];[0:a]loudnorm=I={lufs}:TP=-1.0:LRA=11[a]"
    crf = "28" if args.preview else "18"
    preset = "ultrafast" if args.preview else "medium"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-profile:v", "high", "-preset", preset, "-crf", crf,
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-movflags", "+faststart", output]
    run(cmd)

    if plan.get("thumbnail_at") is not None:
        thumb = os.path.splitext(output)[0] + "_cover.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(plan["thumbnail_at"]), "-i", output,
             "-frames:v", "1", "-q:v", "2", thumb])

    print(json.dumps({"output": output, "duration": round(total, 2),
                      "segments": len(clips), "caption_words": len(words)}, indent=2))
    if not plan.get("keep_workdir", True):
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
