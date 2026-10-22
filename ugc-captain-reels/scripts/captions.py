#!/usr/bin/env python3
"""Caption helpers: map word timings onto the edited timeline and write an
.ass subtitle file with bold, word-by-word "pop" captions plus text overlays.

Word timings come from words.json (written by transcribe.py):
    {"files": {"clips/aroll_01.mp4": [{"w": "Okay", "s": 0.12, "e": 0.40}, ...]}}
"""
import json
import re

PUNCT_BREAK = re.compile(r"[.,!?;:]$")


def load_words(path):
    with open(path) as f:
        return json.load(f)["files"]


def remap_words(files, timeline):
    """Return words on the output timeline for every segment that keeps captions."""
    out = []
    for seg in timeline:
        if not seg.get("captions", True):
            continue
        for w in files.get(seg["source"], []):
            mid = (w["s"] + w["e"]) / 2
            if seg["in"] <= mid <= seg["out"]:
                s = seg["start"] + max(w["s"], seg["in"]) - seg["in"]
                e = seg["start"] + min(w["e"], seg["out"]) - seg["in"]
                out.append({"w": w["w"], "s": s, "e": max(e, s + 0.05)})
    out.sort(key=lambda x: x["s"])
    return out


def ts(t):
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def esc(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def chunk_words(words, max_words=3, max_gap=0.4):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["s"] - cur[-1]["e"] > max_gap
                    or PUNCT_BREAK.search(cur[-1]["w"])):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def hex_to_ass(color, alpha="00"):
    """'#RRGGBB' -> '&HAABBGGRR'"""
    c = color.lstrip("#")
    return f"&H{alpha}{c[4:6]}{c[2:4]}{c[0:2]}".upper()


def build_ass(words, overlays, cap, W=1080, H=1920):
    font = cap.get("font", "Inter")
    size = int(cap.get("size", 84))
    color = hex_to_ass(cap.get("color", "#FFFFFF"))
    hi = hex_to_ass(cap.get("highlight", "#FFE600"))
    outline = int(cap.get("outline", 7))
    y = int(H * float(cap.get("y", 0.64)))
    upper = cap.get("uppercase", True)
    highlight = cap.get("highlight_active", True)
    max_words = int(cap.get("max_words", 3))

    hook_font = cap.get("overlay_font", font)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{font},{size},{color},{color},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,"
        f"1,{outline},3,5,100,140,0,1",
        # Hook / label overlays: dark text on a white box, like native TikTok text
        f"Style: Hook,{hook_font},64,&H00111111,&H00111111,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,"
        f"100,100,0,0,3,14,0,5,100,140,0,1",
        f"Style: Label,{hook_font},54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,"
        f"100,100,0,0,1,5,2,5,100,140,0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    chunks = chunk_words(words, max_words)
    for ci, ch in enumerate(chunks):
        nxt = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else None
        chunk_end = ch[-1]["e"] + 0.15
        if nxt is not None:
            # hold the caption through short pauses so it doesn't flicker
            chunk_end = nxt if nxt - ch[-1]["e"] < 0.5 else min(chunk_end, nxt)
        texts = [(w["w"].upper() if upper else w["w"]) for w in ch]
        texts = [esc(t) for t in texts]
        pop = r"{\fscx88\fscy88\t(0,90,\fscx100\fscy100)}"
        pos = rf"{{\pos({W // 2},{y})}}"
        if not highlight:
            lines.append(f"Dialogue: 1,{ts(ch[0]['s'])},{ts(chunk_end)},Cap,,0,0,0,,"
                         f"{pos}{pop}{' '.join(texts)}")
            continue
        for wi, w in enumerate(ch):
            start = ch[0]["s"] if wi == 0 else w["s"]
            end = ch[wi + 1]["s"] if wi + 1 < len(ch) else chunk_end
            if end <= start:
                continue
            parts = [(rf"{{\c{hi}}}{t}{{\c{color}}}" if j == wi else t) for j, t in enumerate(texts)]
            lead = pop if wi == 0 else ""
            lines.append(f"Dialogue: 1,{ts(start)},{ts(end)},Cap,,0,0,0,,{pos}{lead}{' '.join(parts)}")

    ypos = {"top": 0.20, "upper": 0.30, "center": 0.45, "bottom": 0.74}
    for ov in overlays:
        p = ov.get("position", "top")
        oy = int(H * (float(p) if isinstance(p, (int, float)) else ypos.get(p, 0.20)))
        style = "Hook" if ov.get("style", "hook") == "hook" else "Label"
        lines.append(f"Dialogue: 2,{ts(float(ov['start']))},{ts(float(ov['end']))},{style},,0,0,0,,"
                     rf"{{\pos({W // 2},{oy})}}{esc(ov['text'])}")
    return "\n".join(lines) + "\n"
