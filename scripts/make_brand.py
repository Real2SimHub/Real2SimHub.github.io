#!/usr/bin/env python3
"""Draw the Real2SimHub logo family and write every file of assets/brand/.

    python3 scripts/make_brand.py --fonts DIR          # all files
    python3 scripts/make_brand.py --fonts DIR --svg    # the SVG files only

DIR holds three fonts from github.com/google/fonts (all SIL Open Font License 1.1): the variable
Outfit.ttf (ofl/outfit) and Fraunces-Italic.ttf (ofl/fraunces), and ChakraPetch-Bold.ttf (ofl/chakrapetch).

The mark is one ribbon that runs from Real (R) to Sim (S) and back: an infinity sign whose left loop
holds an R and whose right loop holds an S. The loops are circles joined by 45-degree lines; the leg
of the R and the ends of the S are cut at the same 45 degrees.

Every project shares the mark and the word "Real2Sim", always in one font and one colour. Its own
word tells it apart: Hub, the root, changes only the colour; Lab is set in an engineered font whose
corners are cut at the same 45 degrees as the mark, and Awesome in a serif italic (literature), each
with its own gradient. Where its name is small (the tabs of the site and of the browser, the row of
projects in a README), a symbol of its own stands for it: the loop for Hub, a flask for Lab, a map for
Awesome. To add a project, add an entry to PROJECTS.

Needs fonttools and skia-pathops; pillow and google-chrome for the PNG, PDF and ICO files. Text is
stored as outlines, so no file needs a font.
"""
from __future__ import annotations

import argparse
import math
import subprocess
import tempfile
from pathlib import Path

import pathops
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUT = Path(__file__).resolve().parent.parent / "assets" / "brand"

# Colours -----------------------------------------------------------------------------------------
INK, VIOLET, NIGHT, PAPER, LILAC = "#2e1065", "#7c3aed", "#140a2e", "#f5f3ff", "#a78bfa"
THEMES = {
    "": dict(core=INK, mark=("#2a0f6b", "#6d28d9", "#a66bff"), word="light"),
    "-dark": dict(core=PAPER, mark=("#f5f3ff", "#c4b5fd", "#9469fa"), word="dark"),
    "-black": dict(core="#000", mark=("#000",), word=("#000",)),
    "-white": dict(core="#fff", mark=("#fff",), word=("#fff",)),
}
TILE = dict(mark=("#fff",))

# Projects: the own word, where it stands, its font, its colours on light and dark, and the icon tile.
# `symbol` is an entry of SYMBOLS (none: the loop). The font is (file, axes, scale, tracking, extra stroke weight), chosen so that the word has the
# height and weight of Outfit's capitals. "Hub" is the root: one plain colour.
PROJECTS = {
    "real2simhub": dict(
        name="Real2SimHub", own="Hub", place="after", font=("Outfit", {"wght": 700}, 1.0, -0.014, 0),
        light=(VIOLET,), dark=(LILAC,), tile=("#7c3aed", "#3b0f86"),
        line="Building the infrastructure of real-to-simulation together."),
    "real2simlab": dict(
        name="Real2SimLab", own="Lab", place="after", font=("ChakraPetch-Bold", {}, 0.985, 0.022, 2.6),
        light=("#6d28d9", "#2563eb", "#0ea5c9"), dark=("#a78bfa", "#60a5fa", "#22d3ee"), tile=("#4338ca", "#0284c7"), symbol="flask",
        line="A unified platform for real-to-simulation."),
    "awesome-real2sim": dict(
        name="Awesome-Real2Sim", own="Awesome", place="before", font=("Fraunces-Italic", {"wght": 700, "opsz": 36, "SOFT": 0, "WONK": 0}, 1.0, -0.015, 0),
        light=("#c026d3", "#f43f5e", "#f97316"), dark=("#e879f9", "#fb7185", "#fdba74"), tile=("#a21caf", "#f0562f"), symbol="map",
        line="A research map of real-to-simulation."),
}
DIAG = math.sqrt(0.5)

# Symbols in a 24-unit box: (lines, filled areas). They differ in shape, not only in colour, and stay
# legible at 20 px.
FLASK = "L3.9 18.5A1.9 1.9 0 0 0 5.53 21.4H18.47A1.9 1.9 0 0 0 20.1 18.5L"
SYMBOLS = {
    "flask": (f"M8.1 2.6H15.9M9.7 2.6V8.8{FLASK}14.3 8.8V2.6", f"M6.45 14.2{FLASK}17.55 14.2Z"),
    "map": ("M2.4 6.6L8.9 3.3L15.1 6.6L21.6 3.3V17.4L15.1 20.7L8.9 17.4L2.4 20.7ZM8.9 3.3V17.4M15.1 6.6V20.7",
            "M8.9 3.3L15.1 6.6V20.7L8.9 17.4Z"),
}


# The mark ------------------------------------------------------------------------------------------
# Units: the centre line of each loop is a circle of radius 100. `band` is the width of the ribbon,
# `gap` the space around the strand on top, `height`/`stem` the letters, `s_weight` the weight of the S.
REGULAR = dict(band=22, gap=9, height=118, stem=21, bowl=(72.5, 78), s_weight=640)
SMALL = dict(band=24, gap=12, height=118, stem=24, bowl=(74, 79), s_weight=740)   # under about 90 px wide
TINY = dict(band=44, gap=20, height=0)                                          # icons under 64 px: no letters
BOLD = dict(band=58, gap=26, height=0)                                          # the loop in a browser tab, 16 px
R0 = 100.0
D = R0 / DIAG  # the loops touch 45-degree lines through the centre


def xy(x, y):
    return f"{x:.2f} {y:.2f}"


def ribbon_path(band, gap):
    h, o = band / 2, (band / 2 + gap) * DIAG
    ro, ri, t, e = R0 + h, R0 - h, R0 * DIAG, h * DIAG
    return ("M" + xy(o - e, o + e) + "L" + xy(t - e, t + e) + f"A{ro:g} {ro:g} 0 1 0 " + xy(t - e, -t - e)
            + "L" + xy(-t - e, t - e) + f"A{ri:g} {ri:g} 0 1 1 " + xy(-t - e, -t + e)
            + "L" + xy(-o - e, -o + e) + "L" + xy(-o + e, -o - e) + "L" + xy(-t + e, -t - e)
            + f"A{ro:g} {ro:g} 0 1 0 " + xy(-t + e, t + e) + "L" + xy(t + e, -t + e)
            + f"A{ri:g} {ri:g} 0 1 1 " + xy(t + e, t - e) + "L" + xy(o + e, o - e) + "Z")


def centre_line(band, gap):
    """the ribbon's centre line from the Real end to the Sim end (for drawing it on in a video)"""
    o, t = (band / 2 + gap) * DIAG, R0 * DIAG
    return (f"M{xy(-o, -o)}L{xy(-t, -t)}A{R0:g} {R0:g} 0 1 0 {xy(-t, t)}L{xy(t, -t)}A{R0:g} {R0:g} 0 1 1 {xy(t, t)}L{xy(o, o)}")


def letter_r(cx, height, stem, bowl):
    """a stem, a half-round bowl and a 45-degree leg that leaves the corner of stem and bowl"""
    hb, bw = bowl
    leg, top, base = 0.95 * stem / DIAG, -height / 2, height / 2
    ro, yb = hb / 2, top + hb
    ri, xb, right = ro - stem, bw - ro, stem + leg + (base - yb)
    x0 = cx - right / 2
    p = lambda x, y: xy(x0 + x, y)  # noqa: E731
    k, cy = right - base, top + ro  # the leg's upper edge is x = y + k; find where it meets the bowl
    b, c = 2 * (k - xb - cy), (k - xb) ** 2 + cy**2 - ro**2
    y = (-b + math.sqrt(b * b - 8 * c)) / 4
    return (f"M{p(0, base)}L{p(0, top)}L{p(xb, top)}A{ro:g} {ro:g} 0 0 1 {p(y + k, y)}L{p(right, base)}L{p(right - leg, base)}"
            f"L{p(stem, yb)}L{p(stem, base)}ZM{p(stem, top + stem)}L{p(stem, yb - stem)}L{p(xb, yb - stem)}"
            f"A{ri:g} {ri:g} 0 0 0 {p(xb, top + stem)}Z")


def paint(colours, x0, x1):
    """(defs, fill) for one colour or a gradient from x0 to x1; ids are unique per gradient, so that
    several logos may be inlined in one page"""
    if len(colours) == 1:
        return "", colours[0]
    name = "r2s-" + "-".join(c[1:].lower() for c in colours) + f"-{round(x1 - x0)}"
    stops = "".join(f'<stop offset="{i / (len(colours) - 1):g}" stop-color="{c}"/>' for i, c in enumerate(colours))
    return (f'<defs><linearGradient id="{name}" gradientUnits="userSpaceOnUse" x1="{x0:.1f}" y1="0" x2="{x1:.1f}" y2="0">{stops}</linearGradient></defs>',
            f"url(#{name})")


class Mark:
    def __init__(self, p, word):
        self.half_w, self.half_h = D + R0 + p["band"] / 2, R0 + p["band"] / 2
        self.ribbon, self.line = ribbon_path(p["band"], p["gap"]), centre_line(p["band"], p["gap"])
        self.r = letter_r(-D, p["height"], p["stem"], p["bowl"]) if p["height"] else ""
        self.s = word.letter("S", p["s_weight"], p["height"], D) if p["height"] else ""
        self.aspect = self.half_w / self.half_h

    def svg(self, theme, height, cx, cy):
        """the mark, `height` tall, centred on (cx, cy)"""
        defs, fill = paint(theme["mark"], -self.half_w, self.half_w)
        s = height / (2 * self.half_h)
        letters = f'<path class="r" d="{self.r}"/><path class="s" d="{self.s}"/>' if self.r else ""
        return f'{defs}<g fill="{fill}" transform="translate({cx:.2f} {cy:.2f}) scale({s:.5f})"><path class="ribbon" d="{self.ribbon}"/>{letters}</g>'



# The wordmark --------------------------------------------------------------------------------------
class Word:
    SIZE, TRACK = 120, -0.014
    JOIN, HYPHEN = 0.092, 0.062  # ink gaps, in em: before "Hub"/"Lab", and on each side of the hyphen

    def __init__(self, folder):
        self.folder, self.cache = Path(folder), {}

    def font(self, name, axes):
        key = (name, *sorted(axes.items()))
        if key not in self.cache:
            f = TTFont(self.folder / f"{name}.ttf")
            self.cache[key] = instantiateVariableFont(f, axes) if "fvar" in f else f
        return self.cache[key]

    @staticmethod
    def kern(f, left, right):
        if "GPOS" not in f:
            return 0
        table = f["GPOS"].table
        wanted = {i for r in table.FeatureList.FeatureRecord if r.FeatureTag == "kern" for i in r.Feature.LookupListIndex}
        for i in sorted(wanted):
            for st in table.LookupList.Lookup[i].SubTable:
                st = st.ExtSubTable if st.LookupType == 9 else st
                if st.LookupType != 2 or left not in st.Coverage.glyphs:
                    continue
                if st.Format == 1:
                    for pair in st.PairSet[st.Coverage.glyphs.index(left)].PairValueRecord:
                        if pair.SecondGlyph == right:
                            return getattr(pair.Value1, "XAdvance", 0) or 0
                else:
                    value = st.Class1Record[st.ClassDef1.classDefs.get(left, 0)].Class2Record[st.ClassDef2.classDefs.get(right, 0)].Value1
                    if value and getattr(value, "XAdvance", 0):
                        return value.XAdvance
        return 0

    def run(self, text, font, left, scale=1.0, track=None, bold=0.0):
        """outline of `text` with its ink starting at x = `left`, baseline y = 0: (path data, ink start,
        ink end); `bold` adds that much to every stroke"""
        f, size = self.font(*font), self.SIZE * scale
        glyphs, cmap, k = f.getGlyphSet(), f.getBestCmap(), size / f["head"].unitsPerEm
        track = self.TRACK if track is None else track

        def draw(x):
            path, last = pathops.Path(), None
            for ch in text:
                g = cmap[ord(ch)]
                if last:
                    x += self.kern(f, last, g) * k
                glyph = pathops.Path()
                glyphs[g].draw(TransformPen(glyph.getPen(glyphSet=glyphs), (k, 0, 0, -k, x, -bold / 2)))
                glyph.simplify(fix_winding=True)
                if bold:
                    edge = pathops.Path(glyph)
                    edge.stroke(bold, pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, 4)
                    glyph = pathops.op(glyph, edge, pathops.PathOp.UNION)
                glyph.draw(path.getPen(glyphSet=glyphs))
                x += f["hmtx"][g][0] * k + track * size
                last = g
            path.simplify(fix_winding=True)
            return path

        path = draw(left - draw(0).bounds[0])
        return path_data(path), path.bounds[0], path.bounds[2]

    def letter(self, ch, weight, height, cx):
        """one capital, `height` from baseline to cap line, centred on (cx, 0)"""
        f = self.font("Outfit", {"wght": weight})
        k = height / f["OS/2"].sCapHeight
        path, glyphs = pathops.Path(), f.getGlyphSet()
        glyphs[f.getBestCmap()[ord(ch)]].draw(TransformPen(path.getPen(glyphSet=glyphs), (k, 0, 0, -k, 0, 0)))
        path.simplify(fix_winding=True)
        x0, y0, x1, y1 = path.bounds
        return path_data(path.transform(1, 0, 0, 1, cx - (x0 + x1) / 2, -(y0 + y1) / 2))

    @property
    def cap(self):
        f = self.font("Outfit", {"wght": 700})
        return f["OS/2"].sCapHeight * self.SIZE / f["head"].unitsPerEm

    def svg(self, project, theme):
        """the project's name, ink from x = 0, baseline at y = 0: (svg, ink end)"""
        colours = project[theme["word"]] if isinstance(theme["word"], str) else theme["word"]
        name, axes, scale, track, bold = project["font"]
        core, em = ("Outfit", {"wght": 700}), self.SIZE

        def own(x):
            d, x0, x1 = self.run(project["own"], (name, axes), x, scale, track, bold)
            defs, fill = paint(colours, x0, x1)
            return f'{defs}<path class="own" fill="{fill}" d="{d}"/>', x1

        if project["place"] == "before":
            out, x = own(0.0)
            d, _, x = self.run("-", core, x + self.HYPHEN * em)
            out += f'<path class="own" fill="{colours[-1]}" d="{d}"/>'
            d, _, x = self.run("Real2Sim", core, x + self.HYPHEN * em)
            return out + f'<path class="core" fill="{theme["core"]}" d="{d}"/>', x
        d, _, x = self.run("Real2Sim", core, 0.0)
        tail, x = own(x + self.JOIN * em)
        return f'<path class="core" fill="{theme["core"]}" d="{d}"/>' + tail, x


def path_data(p):
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    p.draw(pen)
    return pen.getCommands()


# Files ---------------------------------------------------------------------------------------------
def doc(w, h, body, title="Real2SimHub"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" width="{w:g}" height="{h:g}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')


def alone(mark, theme, height=256, pad=12):
    w, h = round(height * mark.aspect) + 2 * pad, height + 2 * pad
    return w, h, mark.svg(theme, height, w / 2, h / 2)


def logo(mark, word, project, theme, height=124, gap=36, pad=4):
    text, end = word.svg(project, theme)
    w = height * mark.aspect
    total, h = round(w + gap + end + 2 * pad), height + 2 * pad
    return total, h, f'{mark.svg(theme, height, pad + w / 2, h / 2)}<g class="word" transform="translate({pad + w + gap:.2f} {h / 2 + word.cap / 2:.2f})">{text}</g>'


def stacked(mark, word, project, theme, height=230, gap=46, pad=8):
    text, end = word.svg(project, theme)
    total = round(end + 2 * pad)
    return total, round(height + gap + word.cap + 2 * pad + 4), (
        f'{mark.svg(theme, height, total / 2, pad + height / 2)}<g class="word" transform="translate({pad} {pad + height + gap + word.cap:.2f})">{text}</g>')


def icon(mark, project, width, radius):
    a, b = project["tile"]
    name = f"r2s-tile-{a[1:]}-{b[1:]}"
    defs = f'<defs><linearGradient id="{name}" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'
    return doc(240, 240, f'{defs}<rect width="240" height="240" rx="{radius}" fill="url(#{name})"/>{mark.svg(TILE, width / mark.aspect, 120, 120)}', project["name"])


def drawn(project, fill, weight):
    """a project's symbol from SYMBOLS"""
    lines, areas = SYMBOLS[project["symbol"]]
    return (f'<path fill="{fill}" d="{areas}"/><path fill="none" stroke="{fill}" stroke-width="{weight}" '
            f'stroke-linecap="round" stroke-linejoin="round" d="{lines}"/>')


def symbol(mark, project, tone):
    """the project's symbol alone, in the colours of its own word"""
    if "symbol" not in project:
        return doc(28, 24, mark.svg(dict(mark=project[tone]), 27 / mark.aspect, 14, 12), project["name"])
    defs, fill = paint(project[tone], 2, 22)
    return doc(24, 24, defs + drawn(project, fill, 2), project["name"])


def favicon(mark, project):
    """the symbol in a square, a little bolder; one file whose colours follow the browser's theme"""
    last = max(len(project["light"]) - 1, 1)
    stops = "".join(f'<stop class="c{i}" offset="{i / last:g}" stop-color="{c}"/>' for i, c in enumerate(project["light"]))
    dark = "".join(f".c{i}{{stop-color:{c}}}" for i, c in enumerate(project["dark"]))
    defs = (f'<style>@media (prefers-color-scheme:dark){{{dark}}}</style>'
            f'<defs><linearGradient id="r2s-tab" gradientUnits="userSpaceOnUse" x1="2" y1="0" x2="22" y2="0">{stops}</linearGradient></defs>')
    body = drawn(project, "url(#r2s-tab)", 2.2) if "symbol" in project else mark.svg(dict(mark=("url(#r2s-tab)",)), 24 / mark.aspect, 12, 12)
    return doc(24, 24, defs + body, project["name"])


def write_svgs(word):
    regular, small, tiny, bold = Mark(REGULAR, word), Mark(SMALL, word), Mark(TINY, word), Mark(BOLD, word)
    svg = OUT / "svg"
    svg.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, theme in THEMES.items():
        files[f"real2sim-mark{name}"] = doc(*alone(regular, theme), "Real2Sim")
        files[f"real2sim-mark-small{name}"] = doc(*alone(small, theme), "Real2Sim")
        files[f"real2sim-loop{name}"] = doc(*alone(tiny, theme), "Real2Sim")
        for key, project in PROJECTS.items():
            files[f"{key}-logo{name}"] = doc(*logo(regular, word, project, theme), project["name"])
            files[f"{key}-logo-stacked{name}"] = doc(*stacked(regular, word, project, theme), project["name"])
            if name in ("", "-dark"):
                files[f"{key}-logo-small{name}"] = doc(*logo(small, word, project, theme, gap=30), project["name"])
    # The organisation's GitHub avatar: the mark in its own colours on white, as in the READMEs and the paper.
    files["real2sim-avatar"] = doc(240, 240, '<rect width="240" height="240" fill="#fff"/>'
                                   + small.svg(THEMES[""], 196 / small.aspect, 120, 120), "Real2SimHub")
    for key, project in PROJECTS.items():
        files[f"{key}-icon"] = icon(regular, project, 196, 54)
        files[f"{key}-icon-small"] = icon(tiny, project, 214, 50)
        files[f"{key}-avatar"] = icon(small, project, 178, 0)
        files[f"{key}-symbol"] = symbol(tiny, project, "light")
        files[f"{key}-symbol-dark"] = symbol(tiny, project, "dark")
        files[f"{key}-favicon"] = favicon(bold, project)
    for name, text in files.items():
        (svg / f"{name}.svg").write_text(text, encoding="utf-8")
    return files


def chrome(page, size, *flags):
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "page.html"
        html.write_text(page, encoding="utf-8")
        cmd = ["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={size[0]},{size[1]}", *flags, html.as_uri()]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)


def to_png(svg_file, target, width, background="00000000"):
    text = svg_file.read_text(encoding="utf-8")
    w, h = (float(v) for v in text.split('viewBox="', 1)[1].split('"', 1)[0].split()[2:])
    height = round(width * h / w)
    page = f'<!doctype html><style>html,body{{margin:0;background:transparent}}svg{{display:block;width:{width}px;height:{height}px}}</style>{text}'
    # A window is never narrower than about 500 px, so small images are cut out of a larger one.
    chrome(page, (max(width, 600), max(height, 600)), f"--default-background-color={background}", f"--screenshot={target}")
    from PIL import Image

    Image.open(target).crop((0, 0, width, height)).save(target, optimize=True)


def to_pdf(svg_file, target, width_pt):
    text = svg_file.read_text(encoding="utf-8")
    w, h = (float(v) for v in text.split('viewBox="', 1)[1].split('"', 1)[0].split()[2:])
    height = width_pt * h / w
    page = (f'<!doctype html><style>@page{{size:{width_pt}pt {height:.3f}pt;margin:0}}html,body{{margin:0}}'
            f'svg{{display:block;width:{width_pt}pt;height:{height - 0.05:.3f}pt}}</style>{text}')
    chrome(page, (800, 600), "--no-pdf-header-footer", f"--print-to-pdf={target}")


def social(word, project):
    theme = THEMES["-dark"]
    w, h, body = logo(Mark(REGULAR, word), word, project, theme)
    line, _, end = word.run(project["line"], ("Outfit", {"wght": 400}), 0)
    k, s = 1000 / w, 0.33
    glow = project["tile"][len(project["light"]) > 1]
    return (f'<!doctype html><style>html,body{{margin:0}}</style><svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640">'
            f'<defs><radialGradient id="a" cx=".1" cy="0" r=".9"><stop stop-color="#5b21b6" stop-opacity=".75"/><stop offset="1" stop-color="#5b21b6" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="b" cx="1" cy="1" r=".8"><stop stop-color="{glow}" stop-opacity=".34"/><stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect width="1280" height="640" fill="{NIGHT}"/><rect width="1280" height="640" fill="url(#a)"/><rect width="1280" height="640" fill="url(#b)"/>'
            f'<g transform="translate({(1280 - w * k) / 2:.1f} {286 - h * k / 2:.1f}) scale({k:.4f})">{body}</g>'
            f'<g transform="translate({(1280 - end * s) / 2:.1f} {286 + h * k / 2 + 100:.1f}) scale({s})"><path fill="#d6c9ff" d="{line}"/></g></svg>')


def write_rasters(word):
    from PIL import Image

    svg, png, pdf = OUT / "svg", OUT / "png", OUT / "pdf"
    png.mkdir(exist_ok=True)
    pdf.mkdir(exist_ok=True)
    for name in THEMES:
        to_png(svg / f"real2sim-mark{name}.svg", png / f"real2sim-mark{name}.png", 1200)
        to_pdf(svg / f"real2sim-mark{name}.svg", pdf / f"real2sim-mark{name}.pdf", 180)
        for key in PROJECTS:
            to_png(svg / f"{key}-logo{name}.svg", png / f"{key}-logo{name}.png", 2400)
            to_png(svg / f"{key}-logo-stacked{name}.svg", png / f"{key}-logo-stacked{name}.png", 1600)
            to_pdf(svg / f"{key}-logo{name}.svg", pdf / f"{key}-logo{name}.pdf", 360)
    to_png(svg / "real2sim-avatar.svg", png / "real2sim-avatar-1024.png", 1024)
    sizes = (16, 32, 48)
    for key, project in PROJECTS.items():
        to_png(svg / f"{key}-avatar.svg", png / f"{key}-avatar-1024.png", 1024)
        for px in (180, 192, 512, 1024):
            to_png(svg / f"{key}-icon.svg", png / f"{key}-icon-{px}.png", px)
        for px in sizes:
            to_png(svg / f"{key}-favicon.svg", png / f"{key}-favicon-{px}.png", px)
        frames = [Image.open(png / f"{key}-favicon-{px}.png").convert("RGBA") for px in sizes]
        frames[-1].save(OUT / f"{key}.ico", sizes=[(px, px) for px in sizes], append_images=frames[:-1])
        chrome(social(word, project), (1280, 640), f"--screenshot={png / f'{key}-social.png'}")
    chrome(preview(), (1600, 920), "--allow-file-access-from-files", f"--screenshot={OUT / 'preview.png'}")


def preview():
    svg = lambda name: (OUT / "svg" / f"{name}.svg").as_uri()  # noqa: E731
    img = lambda name, h, style="": f'<img src="{svg(name)}" style="height:{h}px;{style}">'  # noqa: E731
    cell = lambda cls, body, style="": f'<div class="{cls}" style="{style}">{body}</div>'  # noqa: E731
    dark = f"background:{NIGHT}"
    rows = "".join(cell("half", img(f"{k}-logo", 64)) + cell("half", img(f"{k}-logo-dark", 64), dark) for k in PROJECTS)
    stacks = "".join(cell("third", img(f"{k}-logo-stacked", 146)) for k in PROJECTS)
    icons = "".join(cell("third", img(f"{k}-icon", 110) + img(f"{k}-avatar", 110, "border-radius:50%") + img(f"{k}-icon-small", 48) + img(f"{k}-icon-small", 32) + img(f"{k}-symbol", 36) + img(f"{k}-favicon", 16)) for k in PROJECTS)
    mono = "".join(cell("third", img(f"{k}-logo-black", 38)) for k in PROJECTS)
    return f"""<!doctype html><style>
body{{margin:0;background:#f4f2fb;padding:28px;width:1600px;display:grid;grid-template-columns:repeat(6,1fr);gap:18px;box-sizing:border-box}}
div{{background:#fff;border-radius:20px;display:flex;align-items:center;justify-content:center;gap:20px;padding:24px 14px;box-sizing:border-box;min-width:0}}
.half{{grid-column:span 3}}.third{{grid-column:span 2}}</style>{rows}{stacks}{icons}{mono}"""


def main():
    ap = argparse.ArgumentParser(description="Draw the logo files of the Real2SimHub family.")
    ap.add_argument("--fonts", required=True, help="folder with Outfit.ttf, ChakraPetch-Bold.ttf and Fraunces-Italic.ttf (OFL, from google/fonts)")
    ap.add_argument("--svg", action="store_true", help="write the SVG files only")
    args = ap.parse_args()
    for name in sorted({"Outfit"} | {p["font"][0] for p in PROJECTS.values()}):
        if not (Path(args.fonts) / f"{name}.ttf").is_file():
            ap.error(f"no {name}.ttf in {args.fonts}; download it from github.com/google/fonts")
    word = Word(args.fonts)
    names = write_svgs(word)
    if not args.svg:
        write_rasters(word)
    print(f"{len(names)} SVG files" + ("" if args.svg else ", PNG, PDF and ICO files") + f" in {OUT}")


if __name__ == "__main__":
    main()
