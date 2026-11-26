#!/usr/bin/env python3
"""Prepare the committed images from their sources on the authors' machine.

    python3 scripts/prepare_assets.py [--only figures,awesome,cards,blog,logos]

Sources (set these environment variables; nothing defaults to a local path):
  R2S_PAPER     the paper checkout (figures/*.pdf), read only
  R2S_AWESOME   the Awesome-Real2Sim checkout (assets/figures)
  R2S_RELEASE   the Real2SimLab checkout (docs/assets/teaser-*.svg, the README figure), read only
  R2S_ARXIV     the arXiv sources of the works the blog posts are about, one directory per
                version (the versions are listed in POST_FIGURES)

Needs pdftoppm, google-chrome and Pillow.
4DCodeBench declares no license: never take a frame of its data. The blog posts show figures from
the papers themselves, credited on the posts. Papers under arXiv's non-exclusive license (4DCodeBench,
Physics-IQ, PhySimCode) are reproduced with credit, as quotations; the others are CC BY 4.0 (IRIS,
PhysCodeGym, Agentic Real2Sim, 3DCodeVerse) or CC BY-SA 4.0 (Video2World). Physics-IQ's scenario grid
shows frames of its dataset, which is CC BY 4.0.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

SITE = Path(__file__).resolve().parent.parent
PAPER = Path(os.environ.get("R2S_PAPER", "<unset: R2S_PAPER>"))
AWESOME = Path(os.environ.get("R2S_AWESOME", "<unset: R2S_AWESOME>"))
RELEASE = Path(os.environ.get("R2S_RELEASE", "<unset: R2S_RELEASE>"))
ARXIV = Path(os.environ.get("R2S_ARXIV", "<unset: R2S_ARXIV>"))
CHROME = os.environ.get("CHROME", "google-chrome")

IMG = SITE / "assets" / "img"


def need(path: Path, what: str) -> Path:
    if not path.exists():
        sys.exit(f"error: {what} not found at {path}\n  fix: set the matching R2S_* variable (see the docstring)")
    return path


def run(cmd: list[str]) -> bytes:
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"error: {' '.join(cmd[:3])} ... failed:\n{r.stderr.decode(errors='replace')[-800:]}")
    return r.stdout


def figures() -> None:
    """Paper figures: PDF -> PNG at 200 dpi -> WebP."""
    out = IMG / "figures"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name in ["integrations", "teaser", "architecture", "benchmarks", "training"]:
            pdf = need(PAPER / "figures" / f"{name}.pdf", f"paper figure {name}.pdf")
            run(["pdftoppm", "-r", "200", "-png", "-singlefile", str(pdf), f"{tmp}/{name}"])
            im = Image.open(f"{tmp}/{name}.png").convert("RGB")
            im.save(out / f"{name}.webp", quality=88, method=6)
            print(f"figures/{name}.webp {im.size}")


def awesome() -> None:
    """Awesome-Real2Sim figures, copied unchanged: the overview and the taxonomy (light and dark) and the
    hand-drawn roadmap (one version, on white)."""
    out = IMG / "figures" / "awesome"
    out.mkdir(parents=True, exist_ok=True)
    names = [f"{name}-{theme}.svg" for name in ["overview", "taxonomy"] for theme in ["light", "dark"]] + ["roadmap.svg"]
    for name in names:
        src = need(AWESOME / "assets" / "figures" / name, f"Awesome figure {name}")
        shutil.copyfile(src, out / name)
        print(f"figures/awesome/{name}")


def fit(im: Image.Image, w: int, h: int, fx: float = 0.5, fy: float = 0.5) -> Image.Image:
    """Scale to cover w x h, then crop around the focus (fx, fy)."""
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = round((im.width - w) * fx)
    y = round((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))


def lab_hero(path: Path) -> None:
    """The right half of the paper's integrations figure: methods and benchmarks, each connected once to
    Real2SimLab, without the panel's title and its N + M line."""
    pdf = need(PAPER / "figures" / "integrations.pdf", "paper figure integrations.pdf")
    with tempfile.TemporaryDirectory() as tmp:
        run(["pdftoppm", "-r", "300", "-png", "-singlefile", str(pdf), f"{tmp}/i"])
        im = Image.open(f"{tmp}/i.png").convert("RGB")
    # Measured on the 300 dpi render (2625 x 771): from the METHODS heading to "give tasks, scorers".
    box = (1014, 168, 2607, 650)
    if im.size != (2625, 771):
        sys.exit(f"error: integrations.pdf renders at {im.size}, not 2625x771\n  fix: measure the crop box again in lab_hero()")
    crop = im.crop(box)
    pad = 36
    out = Image.new("RGB", (crop.width + 2 * pad, crop.height + 2 * pad), crop.getpixel((4, crop.height // 2)))
    out.paste(crop, (pad, pad))
    crop = out
    crop.save(path, quality=88, optimize=True, progressive=True)
    print(f"{path.relative_to(SITE)} {crop.size}")


def svg_crop(svg: Path, box: tuple[int, int, int, int], scale: int, out: Path, size: tuple[int, int], bg: str) -> None:
    """Render an SVG with Chrome at a device scale, crop box (in SVG px) and resize."""
    w, h = (int(float(v)) for v in _svg_size(svg))
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "p.html"
        page.write_text(f'<!doctype html><html><body style="margin:0;background:{bg}"><img src="file://{svg}" width="{w}" height="{h}"></body></html>')
        png = Path(tmp) / "s.png"
        run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
             f"--force-device-scale-factor={scale}", f"--window-size={w},{h}", "--virtual-time-budget=3000",
             f"--screenshot={png}", f"file://{page}"])
        im = Image.open(png).convert("RGB")
    x0, y0, x1, y1 = (v * scale for v in box)
    im.crop((x0, y0, x1, y1)).resize(size, Image.LANCZOS).save(out, quality=86, optimize=True, progressive=True)
    if out.is_relative_to(SITE):
        print(f"{out.relative_to(SITE)} {size}")


def _svg_size(svg: Path) -> tuple[str, str]:
    import re
    head = svg.read_text(encoding="utf-8")[:600]
    m = re.search(r'width="([\d.]+)" height="([\d.]+)"', head)
    if not m:
        sys.exit(f"error: no width/height in {svg}")
    return m.group(1), m.group(2)


SOFT = (249, 248, 255)  # the background of the paper's figures


def on_soft(fig: Image.Image, size: tuple[int, int], box: tuple[int, int, int, int], out: Path) -> None:
    """A figure fitted into box (x, y, w, h) of a soft violet canvas: the home cards and the posts of our own
    projects show our figures whole, never cut."""
    canvas = Image.new("RGB", size, SOFT)
    s = min(box[2] / fig.width, box[3] / fig.height)
    fig = fig.resize((round(fig.width * s), round(fig.height * s)), Image.LANCZOS)
    canvas.paste(fig, (box[0] + (box[2] - fig.width) // 2, box[1] + (box[3] - fig.height) // 2))
    canvas.save(out, quality=88, optimize=True, progressive=True)
    print(f"{out.relative_to(SITE)} {size}")


def awesome_box(scale: int = 4) -> Image.Image:
    """The middle box of the overview at the top of Awesome-Real2Sim's README: the list itself, with its
    sections, and the curves that lead into it."""
    svg = need(AWESOME / "assets" / "figures" / "overview-light.svg", "Awesome overview figure")
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "box.jpg"
        svg_crop(svg, (420, 18, 860, 340), scale, png, (440 * scale, 322 * scale), "#f9f8ff")
        im = Image.open(png).convert("RGB")
    # Let the curves fade out at both ends instead of stopping at the crop.
    fade = round(26 * scale)
    bg = Image.new("RGB", im.size, SOFT)
    mask = Image.new("L", im.size, 255)
    d = ImageDraw.Draw(mask)
    for x in range(fade):
        v = round(255 * x / fade)
        d.line([(x, 0), (x, im.height)], fill=v)
        d.line([(im.width - 1 - x, 0), (im.width - 1 - x, im.height)], fill=v)
    return Image.composite(im, bg, mask)


def svg_view(src: Path, view: tuple[float, float, float, float], out: Path) -> None:
    """A copy of an SVG figure that shows only the box (x, y, w, h) of it: a crop that stays a vector."""
    text = src.read_text(encoding="utf-8")
    m = re.search(r"<svg\b[^>]*>", text)
    if not m or "viewBox" not in m.group(0):
        sys.exit(f"error: {src} has no root <svg ... viewBox>\n  fix: check the figure, then the crops in cards()")
    x, y, w, h = view
    root = re.sub(r'\s(?:viewBox|width|height)="[^"]*"', "", m.group(0))
    root = root[:-1] + f' viewBox="{x} {y} {w} {h}" width="{w}" height="{h}">'
    out.write_text(text[: m.start()] + root + text[m.end():], encoding="utf-8")
    print(f"{out.relative_to(SITE)} {w}x{h}")


def awesome_panel(out: Path) -> None:
    """Panel 3 of the paper's Figure 1 (overview.pdf): the small Awesome-Real2Sim card, with its rounded
    corners made transparent so that it sits on either theme."""
    pdf = need(PAPER / "figures" / "overview.pdf", "paper figure overview.pdf")
    with tempfile.TemporaryDirectory() as tmp:
        run(["pdftoppm", "-r", "600", "-png", "-singlefile", str(pdf), f"{tmp}/o"])
        im = Image.open(f"{tmp}/o.png").convert("RGB")
    # Measured on the 600 dpi render (5250 x 1642): the third panel, border included (12 px radius = 75 px).
    if im.size != (5250, 1642):
        sys.exit(f"error: overview.pdf renders at {im.size}, not 5250x1642\n  fix: measure the crop box again in awesome_panel()")
    panel = im.crop((3850, 12, 5238, 1625))
    k = 4
    mask = Image.new("L", (panel.width * k, panel.height * k), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, mask.width - 1, mask.height - 1), radius=75 * k, fill=255)
    panel.putalpha(mask.resize(panel.size, Image.LANCZOS))
    panel = panel.resize((1000, round(panel.height * 1000 / panel.width)), Image.LANCZOS)
    panel.save(out, quality=92, method=6)
    print(f"{out.relative_to(SITE)} {panel.size}")


# The home cards show the README figure of each project whole, cropped to its panels (no margins, and no title
# line over the Lab's); phones get the middle box of each, which stays readable at that width. Boxes (x, y, w, h)
# in SVG px, measured on the figures.
OVERVIEWS = {
    # name: (source of the light figure, whole view, middle view)
    "real2simlab": ("RELEASE/docs/assets/teaser-light.svg", (14, 54, 1252, 452), (404, 100, 472, 360)),
    "awesome-real2sim": ("AWESOME/assets/figures/overview-light.svg", (14, 0, 1252, 362), (404, 8, 472, 342)),
}


def cards() -> None:
    """The home cards (the README figure of each project, light and dark, whole and its middle box), the
    small Awesome-Real2Sim card from the paper's Figure 1 for the header of its page, the Real2SimLab
    figure at the top of its page, and the thumbnails of our two posts."""
    out = IMG / "cards"
    out.mkdir(parents=True, exist_ok=True)
    lab_hero(out / "real2simlab-hero.jpg")
    for name, (src, whole, middle) in OVERVIEWS.items():
        base, rel = src.split("/", 1)
        for theme in ("light", "dark"):
            svg = need({"RELEASE": RELEASE, "AWESOME": AWESOME}[base] / rel.replace("-light.", f"-{theme}."),
                       f"{name} README figure ({theme})")
            svg_view(svg, whole, out / f"{name}-overview-{theme}.svg")
            svg_view(svg, middle, out / f"{name}-overview-middle-{theme}.svg")
    awesome_panel(out / "awesome-real2sim-panel.webp")
    hero = Image.open(out / "real2simlab-hero.jpg").convert("RGB")
    box = awesome_box()
    (IMG / "blog").mkdir(parents=True, exist_ok=True)
    on_soft(hero, (1200, 675), (40, 60, 1120, 555), IMG / "blog" / "real2simlab.jpg")
    on_soft(box, (1200, 675), (60, 40, 1080, 595), IMG / "blog" / "awesome-real2sim.jpg")


def pdf_image(pdf: Path, dpi: int) -> Image.Image:
    need(pdf, "figure of the paper")
    with tempfile.TemporaryDirectory() as tmp:
        run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", str(pdf), f"{tmp}/f"])
        return Image.open(f"{tmp}/f.png").convert("RGB")


def web(im: Image.Image, out: Path, width: int = 1800) -> None:
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(out, quality=90, method=6)
    print(f"{out.relative_to(SITE)} {im.size}")


# Posts on other people's work: figures from the papers' own arXiv sources, credited on the posts.
POST_FIGURES = {
    # name: (arXiv version, figure in the source, dpi for a PDF; None for a PNG or JPEG)
    "4dcodebench-teaser": ("2610.03715v1", "figures/main/teaser_cats_labels_light_1.pdf", 200),
    "4dcodebench-dataset": ("2610.03715v1", "figures/main/dataset_overview_1.pdf", 400),
    "video2world-teaser": ("2610.04432v3", "fig/shoutu4.pdf", 100),
    "video2world-overview": ("2610.04432v3", "fig/video2world.pdf", 100),
    # Physics-IQ: the switch frames of its dataset (CC BY 4.0) and its protocol figure.
    "physics-iq-scenarios": ("2501.09038v3", "figures/all_scenarios_overview.png", None),
    "physics-iq-protocol": ("2501.09038v3", "figures/method.pdf", 200),
    "iris-phenomena": ("2603.16432v3", "Benchmark_Preview.png", None),
    "physcodegym-teaser": ("2610.17288v1", "figures/physcodegym_teaser.pdf", 250),
    "physcodegym-pipeline": ("2610.17288v1", "resource/physcodegym_name_consistency_20261010/physcodegym_pipeline.pdf", 200),
    "physimcode-domains": ("2610.15722v1", "figures/pie_chart.pdf", 250),
    "physimcode-renders": ("2610.15722v1", "figures/failure_cases_closed.pdf", 300),
    "agentic-real2sim-architecture": ("2607.19190v5", "figures/compressed/Fig_teaser.jpg", None),
    "agentic-real2sim-droid": ("2607.19190v5", "figures/compressed/fig_2_new.jpg", None),
    "3dcodeverse-teaser": ("2610.22341v1", "figures_main/teaser.pdf", 250),
    "3dcodeverse-harness": ("2610.22341v1", "figures_main/harness_overview.pdf", 250),
}

# The home and blog-index card of each post (1200 x 675): (figure, crop box as fractions of it, or
# None for the whole figure; the horizontal and vertical focus of the cover crop).
POST_CARDS = {
    "physics-iq": ("physics-iq-scenarios", (0, 0, 1, 0.56), 0.5, 0.5),
    "iris": ("iris-phenomena", (0.028, 0, 0.47, 0.56), 0.5, 0.5),
    "physcodegym": ("physcodegym-teaser", None, 0.5, 0.5),
    "physimcode": ("physimcode-domains", None, 0.5, 0.5),
    "agentic-real2sim": ("agentic-real2sim-architecture", None, 0.5, 0.5),
    "3dcodeverse": ("3dcodeverse-teaser", None, 0.5, 0.5),
}


def raster_image(path: Path) -> Image.Image:
    """A PNG or JPEG figure on white (palette and transparent images included)."""
    im = Image.open(need(path, "figure of the paper"))
    im = im.convert("RGBA")
    flat = Image.new("RGB", im.size, (255, 255, 255))
    flat.paste(im, mask=im.getchannel("A"))
    return flat


def trim(im: Image.Image, pad: int = 12) -> Image.Image:
    """Cut the white margins that some figure PDFs carry, keeping a small border."""
    grey = im.convert("L").point(lambda v: 255 if v < 245 else 0)
    box = grey.getbbox()
    if box is None:
        return im
    l, t, r, b = box
    return im.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, im.width), min(b + pad, im.height)))


def blog() -> None:
    """Figures of the posts on other people's work, from the papers' arXiv sources, and the cards of
    those posts: 4DCodeBench's task panel (the top of its Figure 1), Video2World's Figure 1, and a
    crop of one figure for each of the others (POST_CARDS)."""
    out = IMG / "blog"
    out.mkdir(parents=True, exist_ok=True)
    figs = {}
    for name, (v, path, dpi) in POST_FIGURES.items():
        src = ARXIV / v / path
        im = pdf_image(src, dpi) if dpi else raster_image(src)
        figs[name] = im if name.startswith(("4dcodebench", "video2world")) else trim(im)  # those two: as before
    for name, im in figs.items():
        web(im, out / f"{name}.webp")
    teaser = figs["4dcodebench-teaser"]
    if teaser.size != (3017, 2984):
        sys.exit(f"error: the 4DCodeBench teaser renders at {teaser.size}, not 3017x2984\n  fix: measure the box again in blog()")
    task = teaser.crop((22, 129, 1972, 1207))  # the input video, the reconstructed video and its 4D geometry
    cards = {"4dcodebench": task, "video2world": figs["video2world-teaser"]}
    for post, (name, box, fx, fy) in POST_CARDS.items():
        im = figs[name]
        if box:
            im = im.crop((round(box[0] * im.width), round(box[1] * im.height),
                          round(box[2] * im.width), round(box[3] * im.height)))
        cards[post] = fit(im, 1200, 675, fx, fy)
    for post, im in cards.items():
        fit(im, 1200, 675).save(out / f"{post}.jpg", quality=88, optimize=True, progressive=True)
    print(f"blog cards: {', '.join(cards)} (1200, 675)")


def logos() -> None:
    """The institutions' logos for the home page: each PNG (also drawn in the video) as a 120 px WebP,
    three times the 40 px it is shown at, so it stays sharp on phones and loads fast."""
    for src in sorted((IMG / "orgs").glob("*.png")):
        im = Image.open(src).convert("RGBA").resize((120, 120), Image.LANCZOS)
        out = src.with_suffix(".webp")
        im.save(out, "WEBP", quality=92, method=6)
        print(f"orgs/{out.name} {out.stat().st_size / 1000:.1f} kB (from {src.stat().st_size / 1000:.1f} kB)")


def main() -> None:
    steps = {"figures": figures, "awesome": awesome, "cards": cards, "blog": blog, "logos": logos}
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")
        bad = [s for s in only if s not in steps]
        if bad:
            sys.exit(f"error: unknown step {bad}; choose from {', '.join(steps)}")
    for name, fn in steps.items():
        if only is None or name in only:
            fn()


if __name__ == "__main__":
    main()
