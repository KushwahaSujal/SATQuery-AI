"""Cuts horizontal screen recordings into one vertical (1080x1920) demo video, hard cut to hard cut.

Each segment of the plan becomes a vertical shot: a blurred, darkened fill of the recording behind,
one or more horizontal crops of it ("panels") stacked in the middle, a header naming the deliverable
on top and a caption underneath. Sped-up segments get an automatic "N× speed" badge, so no one
watching can mistake a 2-minute video job for a 15-second one. Segments are rendered separately with
identical encoder settings and joined with the concat demuxer, so every join is a clean hard cut.

Plan format (JSON) — see demo_resources/recording/edit_plan.example.json:
    {"output": "demo_vertical.mp4",
     "brand": "SatQuery AI · SIH 2026",
     "segments": [
        {"card": "SatQuery AI", "subtitle": "…", "duration": 2.5},
        {"src": "raw/03_masking.mkv", "in": "0:04", "out": "0:31", "speed": 1,
         "panels": [[0, 90, 1920, 990]],            # x, y, w, h in source pixels; omit = full frame
         "step": "1 / 4", "title": "Text-prompted masking",
         "caption": "\\"mask airplanes\\" → Grounding DINO + SAM 2", "mute": false}]}

Paths in the plan are relative to the plan file. Needs ffmpeg: PATH, $FFMPEG, or `pip install
imageio-ffmpeg`.

Usage:
    python scripts/demo/make_vertical.py demo_resources/recording/edit_plan.json
    python scripts/demo/make_vertical.py plan.json --only 3      # re-render one segment, then join
    python scripts/demo/make_vertical.py plan.json --preview     # 540x960, fast, for checking cuts
    python scripts/demo/make_vertical.py --grab raw/03_masking.mkv 0:21   # frame PNG, to measure panels
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
MARGIN = 40
HEADER_BOTTOM, CAPTION_TOP = 360, 1560          # panels live between these two lines
ACCENT = (56, 189, 248)                         # sky-400, reads on the dark blurred fill
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/noto", "C:/Windows/Fonts"]


def ffmpeg_exe() -> str:
    exe = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found: install it (sudo apt install ffmpeg) or `pip install imageio-ffmpeg`")


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    names = ["DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf", "arialbd.ttf"] if bold else \
            ["DejaVuSans.ttf", "NotoSans-Regular.ttf", "arial.ttf"]
    for d in FONT_DIRS:
        for n in names:
            if Path(d, n).exists():
                return ImageFont.truetype(str(Path(d, n)), size)
    return ImageFont.load_default(size)


def seconds(t) -> float:
    if isinstance(t, (int, float)):
        return float(t)
    s = 0.0
    for part in str(t).split(":"):
        s = s * 60 + float(part)
    return s


def probe(ff: str, src: Path) -> tuple:
    """(width, height, has_audio) from ffmpeg's banner; the imageio build ships no ffprobe."""
    err = subprocess.run([ff, "-hide_banner", "-i", str(src)], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    if not m:
        sys.exit(f"cannot read video stream of {src}:\n{err[-800:]}")
    return int(m.group(1)), int(m.group(2)), "Audio:" in err


def layout(panels: list) -> list:
    """Stack panels at full content width, then shrink uniformly until they fit the content band."""
    gap, box_w, box_h = 24, W - 2 * MARGIN, CAPTION_TOP - HEADER_BOTTOM - 40
    sizes = [(box_w, box_w * h / w) for _, _, w, h in panels]
    total = sum(h for _, h in sizes) + gap * (len(sizes) - 1)
    k = min(1.0, (box_h - gap * (len(sizes) - 1)) / (total - gap * (len(sizes) - 1)))
    sizes = [(int(w * k) // 2 * 2, int(h * k) // 2 * 2) for w, h in sizes]
    y = HEADER_BOTTOM + 20 + (box_h - (sum(h for _, h in sizes) + gap * (len(sizes) - 1))) // 2
    out = []
    for pw, ph in sizes:
        out.append(((W - pw) // 2, y, pw, ph))
        y += ph + gap
    return out


def draw_wrapped(d: ImageDraw.ImageDraw, text: str, y: int, f, fill, width_chars: int, spacing=10) -> int:
    for line in textwrap.wrap(text, width_chars):
        tw = d.textlength(line, font=f)
        d.text(((W - tw) / 2, y), line, font=f, fill=fill)
        y += f.size + spacing
    return y


def overlay_png(seg: dict, brand: str, boxes: list, path: Path) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, HEADER_BOTTOM], fill=(8, 12, 20, 200))
    d.rectangle([0, CAPTION_TOP, W, H], fill=(8, 12, 20, 200))
    d.text((MARGIN, 70), brand, font=font(True, 34), fill=ACCENT)
    if seg.get("step"):
        f = font(True, 34)
        d.text((W - MARGIN - d.textlength(seg["step"], font=f), 70), seg["step"], font=f, fill=(200, 210, 225))
    if seg.get("title"):
        draw_wrapped(d, seg["title"], 150, font(True, 64), (255, 255, 255), 24)
    if seg.get("caption"):
        draw_wrapped(d, seg["caption"], CAPTION_TOP + 60, font(False, 42), (230, 236, 245), 40)
    for x, y, w, h in boxes:                                  # thin frame so panels read as screens
        d.rounded_rectangle([x - 3, y - 3, x + w + 2, y + h + 2], radius=10, outline=(255, 255, 255, 90), width=3)
    speed = float(seg.get("speed", 1))
    if speed > 1.01:
        label = f"{speed:g}× speed"
        f = font(True, 34)
        tw = d.textlength(label, font=f)
        x0, y0 = W - MARGIN - tw - 36, CAPTION_TOP - 90
        d.rounded_rectangle([x0, y0, x0 + tw + 36, y0 + 60], radius=30, fill=(245, 158, 11, 235))
        d.text((x0 + 18, y0 + 11), label, font=f, fill=(20, 20, 20))
    img.save(path)


def card_png(seg: dict, brand: str, path: Path) -> None:
    img = Image.new("RGB", (W, H), (8, 12, 20))
    d = ImageDraw.Draw(img)
    for i in range(H):                                        # faint vertical gradient
        c = int(8 + 22 * i / H)
        d.line([(0, i), (W, i)], fill=(c // 2, c, c + 14))
    y = 760
    y = draw_wrapped(d, seg["card"], y, font(True, 96), (255, 255, 255), 16, 18)
    d.line([(W / 2 - 80, y + 20), (W / 2 + 80, y + 20)], fill=ACCENT, width=6)
    if seg.get("subtitle"):
        draw_wrapped(d, seg["subtitle"], y + 70, font(False, 44), (205, 215, 230), 34)
    if brand:
        f = font(True, 32)
        d.text(((W - d.textlength(brand, font=f)) / 2, H - 160), brand, font=f, fill=ACCENT)
    img.save(path)


ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
SILENCE = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]


def render(ff: str, seg: dict, i: int, base: Path, brand: str, work: Path, scale: float) -> Path:
    out = work / f"seg_{i:02d}.mp4"
    ow, oh = int(W * scale) // 2 * 2, int(H * scale) // 2 * 2
    final = f"scale={ow}:{oh},format=yuv420p" if scale != 1 else "format=yuv420p"
    if "card" in seg:
        png = work / f"card_{i:02d}.png"
        card_png(seg, brand, png)
        dur = str(seg.get("duration", 2.5))
        cmd = [ff, "-y", "-loop", "1", "-t", dur, "-i", str(png), *SILENCE,
               "-filter_complex", f"[0:v]{final}[v]", "-map", "[v]", "-map", "1:a", "-t", dur, *ENC, str(out)]
    else:
        src = (base / seg["src"]).resolve()
        sw, sh, has_audio = probe(ff, src)
        panels = seg.get("panels") or [[0, 0, sw, sh]]
        boxes = layout(panels)
        png = work / f"ovl_{i:02d}.png"
        overlay_png(seg, brand, boxes, png)
        speed = float(seg.get("speed", 1))
        t_in, t_out = seconds(seg.get("in", 0)), seg.get("out")
        trim = ["-ss", f"{t_in}"] + (["-to", f"{seconds(t_out)}"] if t_out is not None else [])
        n = len(panels)
        g = [f"[0:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS},split={n + 1}[bgsrc]" + "".join(f"[p{k}]" for k in range(n)),
             f"[bgsrc]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:3,eq=brightness=-0.22[bg]"]
        last = "bg"
        for k, ((x, y, w, h), (bx, by, bw, bh)) in enumerate(zip(panels, boxes)):
            g.append(f"[p{k}]crop={w}:{h}:{x}:{y},scale={bw}:{bh}:flags=lanczos[f{k}]")
            g.append(f"[{last}][f{k}]overlay={bx}:{by}[t{k}]")
            last = f"t{k}"
        g.append(f"[{last}][1:v]overlay=0:0,{final}[v]")
        keep_audio = has_audio and speed == 1 and not seg.get("mute", False)
        audio_in = [] if keep_audio else SILENCE
        a_map = "0:a:0" if keep_audio else "2:a"
        cmd = [ff, "-y", *trim, "-i", str(src), "-i", str(png), *audio_in,
               "-filter_complex", ";".join(g), "-map", "[v]", "-map", a_map, "-shortest", *ENC, str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"segment {i} failed:\n{' '.join(cmd)}\n{r.stderr[-1500:]}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", type=Path, nargs="?")
    ap.add_argument("--only", type=int, action="append", help="re-render just these segment numbers (1-based)")
    ap.add_argument("--preview", action="store_true", help="half resolution, for checking cuts quickly")
    ap.add_argument("--grab", nargs=2, metavar=("SRC", "TIME"), help="save one full-size frame as PNG and exit")
    a = ap.parse_args()

    if a.grab:
        src, t = Path(a.grab[0]), seconds(a.grab[1])
        out = src.with_name(f"{src.stem}_at_{t:g}s.png")
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", f"{t}", "-i", str(src), "-frames:v", "1",
                        str(out)], check=True)
        print(f"-> {out}  (open it in any image viewer; panel boxes are x, y, w, h in these pixels)")
        return
    if not a.plan:
        ap.error("a plan file is required unless --grab is used")

    plan = json.loads(a.plan.read_text())
    base, ff = a.plan.resolve().parent, ffmpeg_exe()
    scale = 0.5 if a.preview else 1.0
    work = base / (".vertical_work_preview" if a.preview else ".vertical_work")
    work.mkdir(exist_ok=True)
    brand = plan.get("brand", "")
    parts = []
    for i, seg in enumerate(plan["segments"], 1):
        seg_file = work / f"seg_{i:02d}.mp4"
        if a.only and i not in a.only and seg_file.exists():
            parts.append(seg_file)
            continue
        print(f"[{i}/{len(plan['segments'])}] {seg.get('title') or seg.get('card')}", flush=True)
        parts.append(render(ff, seg, i, base, brand, work, scale))

    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    out = base / (plan.get("output", "demo_vertical.mp4") if not a.preview else "preview_vertical.mp4")
    r = subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
                        "-movflags", "+faststart", str(out)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"join failed:\n{r.stderr[-1500:]}")
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", subprocess.run([ff, "-hide_banner", "-i", str(out)],
                                                                      capture_output=True, text=True).stderr)
    secs = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0
    print(f"-> {out}  ({secs:.1f} s{'  — over 3:00, YouTube will not treat it as a Short' if secs > 180 else ''})")


if __name__ == "__main__":
    main()
