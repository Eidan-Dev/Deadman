"""Turn a recorded terminal session into an animated GIF.

Input: a JSON list of [seconds, text] pairs, where text may contain ANSI colors.
Record one with a pseudo-terminal (see README) so the output is real, not mocked.

    pip install Pillow
    python3 assets/render_terminal_gif.py session.json assets/demo.gif
"""

import json
import re
import sys

from PIL import Image, ImageDraw, ImageFont

COLS, ROWS = 120, 24
W, H, SS = 1000, 560, 2
BG, BAR, DEFAULT, DIM = (13, 17, 23), (30, 36, 46), (201, 209, 217), (110, 118, 129)
PALETTE = {"31": (255, 95, 86), "32": (63, 185, 80), "33": (229, 192, 123), "36": (86, 182, 194)}
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "C:/Windows/Fonts/consola.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size * SS)
        except OSError:
            continue
    return ImageFont.load_default()


class Terminal:
    def __init__(self):
        self.reset()

    def reset(self):
        self.lines = [[]]
        self.col = 0
        self.fg, self.bold, self.dim = DEFAULT, False, False

    def sgr(self, params):
        for p in (params.split(";") if params else ["0"]):
            if p in ("", "0"):
                self.fg, self.bold, self.dim = DEFAULT, False, False
            elif p == "1":
                self.bold = True
            elif p == "2":
                self.dim = True
            elif p in PALETTE:
                self.fg = PALETTE[p]
            elif p == "39":
                self.fg = DEFAULT

    def put(self, ch):
        if self.col >= COLS:
            self.lines.append([])
            self.col = 0
        line = self.lines[-1]
        while len(line) < self.col:
            line.append((" ", DEFAULT, False, False))
        cell = (ch, self.fg, self.bold, self.dim)
        if self.col < len(line):
            line[self.col] = cell
        else:
            line.append(cell)
        self.col += 1

    def feed(self, text):
        i = 0
        while i < len(text):
            c = text[i]
            if c == "\x1b":
                m = re.match(r"\x1b\[([0-9;?]*)([A-Za-z])", text[i:])
                if m:
                    params, cmd = m.group(1), m.group(2)
                    if cmd == "m":
                        self.sgr(params)
                    elif cmd == "J":
                        self.reset()
                    elif cmd == "K":
                        del self.lines[-1][self.col:]
                    i += m.end()
                    continue
                i += 1
                continue
            if c == "\r":
                self.col = 0
            elif c == "\n":
                self.lines.append([])
                self.col = 0
            elif c >= " ":
                self.put(c)
            i += 1


def draw(term, font, label_font):
    im = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W * SS, 40 * SS], fill=BAR)
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([(18 + i * 22) * SS, 14 * SS, (30 + i * 22) * SS, 26 * SS], fill=color)
    d.text((W * SS // 2 - 150 * SS, 12 * SS), "deadman · terminal", font=label_font, fill=DIM)
    rows = term.lines[-ROWS:]
    char_w, line_h = 8.6 * SS, 21 * SS
    for r, line in enumerate(rows):
        y = 56 * SS + r * line_h
        for c, (char, color, _bold, dim) in enumerate(line):
            if char != " ":
                d.text((28 * SS + c * char_w, y), char, font=font, fill=DIM if dim else color)
    return im.resize((W, H), Image.LANCZOS)


def main(session_path, output_path):
    events = json.load(open(session_path, encoding="utf-8"))
    font, label_font = load_font(14), load_font(13)
    term = Terminal()
    frames, durations = [], []
    for idx, (t, text) in enumerate(events):
        term.feed(text)
        frames.append(draw(term, font, label_font))
        nxt = events[idx + 1][0] if idx + 1 < len(events) else t + 2.0
        durations.append(int(min(max(nxt - t, 0.05), 1.2) * 1000))
    durations[-1] = 3500
    frames[0].save(output_path, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=2)
    print(f"wrote {output_path} ({len(frames)} frames)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
