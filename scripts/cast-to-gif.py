#!/usr/bin/env python3
"""Convert asciinema v2 .cast to animated GIF using Pillow.

Usage: python3 scripts/cast-to-gif.py [--speed 1.5] [--width 800]
Reads docs/demo.cast, writes docs/demo.gif.
"""
import json, re, sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CAST = ROOT / "docs" / "demo.cast"
OUT = ROOT / "docs" / "demo.gif"

# Terminal colors (Catppuccin Mocha)
BG = (30, 30, 46)
FG = (205, 214, 244)
GREEN = (166, 227, 161)
CYAN = (137, 180, 250)
YELLOW = (249, 226, 175)
WHITE = (255, 255, 255)
DIM = (147, 153, 178)

FONT_PATHS = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFMono-Regular.otf",
    "/System/Library/Fonts/Monaco.dfont",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def find_font(size=14):
    for p in FONT_PATHS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', s)


def colorize_line(line):
    """Return list of (text, color) tuples from a raw line with ANSI."""
    segments = []
    color = FG
    for part in re.split(r'(\x1b\[[0-9;]*m)', line):
        m = re.match(r'\x1b\[([0-9;]*)m', part)
        if m:
            for c in m.group(1).split(';'):
                if c in ('0', ''):
                    color = FG
                elif c == '1':
                    color = WHITE
                elif c == '32':
                    color = GREEN
                elif c == '33':
                    color = YELLOW
                elif c == '36':
                    color = CYAN
                elif c == '4':
                    pass
        elif part:
            # Strip any remaining non-SGR escapes
            clean = re.sub(r'\x1b\[[0-9;]*[A-HJ-Z]', '', part)
            if clean:
                segments.append((clean, color))
    return segments


def render_frame(raw_lines, width, height, font, char_w, char_h, padding=12):
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Title bar
    bar_h = 26
    draw.rectangle([0, 0, width, bar_h], fill=(49, 50, 68))
    for i, c in enumerate([(243, 139, 168), (249, 226, 175), (166, 227, 161)]):
        draw.ellipse([10 + i * 18, 7, 20 + i * 18, 17], fill=c)
    draw.text((width // 2 - 50, 5), "llm-wiki demo", fill=(166, 173, 200), font=font)

    y = bar_h + padding
    for line in raw_lines:
        x = padding
        for text, color in colorize_line(line):
            draw.text((x, y), text, fill=color, font=font)
            x += len(text) * char_w
        y += char_h
        if y > height - padding:
            break
    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--speed", type=float, default=1.5)
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--max-frames", type=int, default=45)
    args = parser.parse_args()

    with open(CAST) as f:
        raw = f.read().strip().split("\n")

    header = json.loads(raw[0])
    events = [json.loads(l) for l in raw[1:]]

    # Replay: accumulate output, snapshot at pauses
    full_output = ""
    frames = []  # (lines_with_ansi, duration_ms)
    prev_ts = 0.0

    for i, (ts, typ, data) in enumerate(events):
        if typ != "o":
            continue
        full_output += data
        delay = ts - prev_ts

        # Emit frame at significant pauses or end
        is_last = (i == len(events) - 1)
        if delay > 0.12 or is_last:
            # Process: split on \r\n, handle \x1b[2J (clear screen)
            text = full_output
            # Handle clear screen: only keep content after last clear
            if '\x1b[2J' in text:
                text = text.rsplit('\x1b[2J', 1)[-1]
            # Remove cursor positioning
            text = re.sub(r'\x1b\[H', '', text)
            # Split into lines
            lines = text.replace('\r\n', '\n').replace('\r', '').split('\n')

            dur = max(int(delay * 1000 / args.speed), 80)
            frames.append((lines, dur))

        prev_ts = ts

    # Thin if too many frames
    if len(frames) > args.max_frames:
        step = len(frames) / args.max_frames
        thinned = []
        idx = 0.0
        while idx < len(frames):
            thinned.append(frames[int(idx)])
            idx += step
        if thinned[-1] != frames[-1]:
            thinned.append(frames[-1])
        frames = thinned

    # Render
    font_size = max(11, args.width // 62)
    font = find_font(font_size)
    bbox = font.getbbox("M")
    char_w = bbox[2] - bbox[0]
    char_h = int((bbox[3] - bbox[1]) * 1.35)
    visible_rows = 32
    img_h = 26 + 24 + visible_rows * char_h

    print(f"Rendering {len(frames)} frames at {args.width}x{img_h}, font {font_size}px...")

    images = []
    durations = []
    for lines, dur in frames:
        # Take last N visible rows
        display = lines[-visible_rows:] if len(lines) > visible_rows else lines
        img = render_frame(display, args.width, img_h, font, char_w, char_h)
        images.append(img)
        durations.append(dur)

    durations[-1] = max(durations[-1], 4000)  # hold last frame

    images[0].save(
        OUT, save_all=True, append_images=images[1:],
        duration=durations, loop=0, optimize=True,
    )
    kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT} ({len(images)} frames, {kb:.0f} KB)")


if __name__ == "__main__":
    main()
