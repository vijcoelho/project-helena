"""Draws the site's ASCII Helena from site/assets/img/helena.jpg.

    python extras/ascii.py                 # prints the art (paste it into <script id="arte"> in site/index.html)
    python extras/ascii.py preview.png     # also renders it white on black, to look at before pasting

How: the drawing is black ink on white paper. The paper outside the figure is found by flood fill and dropped, so only
what is white INSIDE her (skin, highlights, seams) lights up, plus a thin rim where the figure meets the paper (black hair
on a black page has no edge without it). Each cell then gets the character whose SHAPE is closest to what is under it, not
just its density: a seam becomes / | \\ _, a filled area becomes @ % #, and a soft falloff near the edges gives volume.
"""
import pathlib, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

ROOT = pathlib.Path(__file__).resolve().parent.parent
COLS, ROWS, CW, CH = 160, 96, 10, 17          # cells, and the pixels each one is matched at (0.6 wide: the site's font)
BOX = (140, 62, 940, 862)                      # the part of the 1024 px drawing that is shown
GLYPHS = " .:-=+*#%@/\\|_'`,;~^\"!()<>"
FONT = 'C:/Windows/Fonts/consolab.ttf'


def target():
    """The picture to match, 0..1: white inside the figure, shaded, plus the rim."""
    src = Image.open(ROOT / 'site' / 'assets' / 'img' / 'helena.jpg').convert('L')
    ink = src.point(lambda v: 255 if v < 140 else 0)
    # paper = white reachable from the border; the ink is thickened first so a hairline gap in a contour does not leak
    closed = ink.filter(ImageFilter.MaxFilter(5)).point(lambda v: 0 if v else 255)
    seed = closed.copy()
    for xy in [(2, 2), (1020, 2), (2, 500), (1020, 500), (500, 2), (60, 1000), (1000, 900)]:
        if seed.getpixel(xy) == 255:
            ImageDraw.floodfill(seed, xy, 128)
    paper = seed.point(lambda v: 255 if v == 128 else 0).filter(ImageFilter.MaxFilter(5))
    inside = ImageChops.subtract(src.point(lambda v: 255 if v >= 140 else 0), paper)
    rim = ImageChops.subtract(paper.filter(ImageFilter.MaxFilter(7)), paper)       # 3 px of paper next to the figure
    # volume: full strength away from the ink, softer next to it, and a light from the upper left
    soft = inside.filter(ImageFilter.GaussianBlur(9))
    a = np.asarray(inside, float) / 255 * (0.62 + 0.38 * np.asarray(soft, float) / 255)
    yy, xx = np.mgrid[0:1024, 0:1024]
    a *= 1.0 - 0.22 * np.clip((xx * 0.6 + yy * 0.4 - 380) / 520, 0, 1)
    a = np.maximum(a, np.asarray(rim, float) / 255 * 0.42)
    img = Image.fromarray((a * 255).astype('uint8')).crop(BOX).resize((COLS * CW, ROWS * CH), Image.LANCZOS)
    return np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), float) / 255


def glyphs():
    font = ImageFont.truetype(FONT, CH)
    out = []
    for g in GLYPHS:
        im = Image.new('L', (CW, CH), 0)
        ImageDraw.Draw(im).text((CW / 2, CH / 2 + 1), g, fill=255, font=font, anchor='mm')
        out.append(np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), float) / 255)
    return np.stack(out)


def draw():
    t, g = target(), glyphs()
    cells = t.reshape(ROWS, CH, COLS, CW).transpose(0, 2, 1, 3)                    # rows, cols, CH, CW
    err = ((cells[:, :, None] - g[None, None]) ** 2).sum(axis=(3, 4))             # rows, cols, glyphs
    err += (g.sum(axis=(1, 2)) * 0.012)[None, None]                               # ties go to the lighter character
    tone, low = cells.mean(axis=(2, 3)), cells.min(axis=(2, 3))
    # a thin line is drawn with line characters only: a seam made of @ and % reads as noise
    heavy = np.array([c in '*#%@' for c in GLYPHS])
    err[(tone < 0.30)[:, :, None] & heavy[None, None]] = 1e9
    pick = err.argmin(axis=2)
    # a cell that is filled edge to edge has no shape to match: its tone picks from the ramp, which is where volume comes from
    ramp = '+*#%@'
    full = low > 0.42
    steps = np.clip(((tone - 0.52) / (0.90 - 0.52) * len(ramp)).astype(int), 0, len(ramp) - 1)
    pick[full] = np.array([GLYPHS.index(c) for c in ramp])[steps[full]]
    lines = [''.join(GLYPHS[i] for i in row).rstrip() for row in pick]
    while lines and not lines[-1]:
        lines.pop()
    return lines


if __name__ == '__main__':
    art = draw()
    print('\n'.join(art))
    if sys.argv[1:]:
        w = max(len(l) for l in art)
        im = Image.new('L', (w * CW, len(art) * CH), 0)
        d, font = ImageDraw.Draw(im), ImageFont.truetype(FONT, CH)
        for y, line in enumerate(art):
            for x, c in enumerate(line):
                if c != ' ':
                    d.text((x * CW + CW / 2, y * CH + CH / 2 + 1), c, fill=191, font=font, anchor='mm')
        im.save(sys.argv[1])
