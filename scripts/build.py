#!/usr/bin/env python3
"""Build the static site from data/site.json and pages/*.html.

    python3 scripts/build.py          # writes index.html, 404.html and <slug>/index.html
    python3 scripts/build.py --check  # fails if a generated page is out of date

Every URL, the arXiv ID and the authors live in data/site.json. A project is one entry in its
"projects" list plus one page body, pages/<slug>.html. Page bodies may use these placeholders:

    {{root}}             relative path to the site root ("../" on a project page)
    {{logo:SLUG}}        the logo of a project, light or dark with the theme
    {{symbol:SLUG}}      the symbol of a project (decorative: its name stands beside it)
    {{link:KEY}}         a URL from "links"
    {{site:KEY}}         a value from "site"
    {{icon:NAME}}        an inline SVG icon (see ICONS)
    {{arxiv_button}}     the arXiv button: a link once paper.arxiv_id is set, "coming soon" before
    {{authors}}          the author block
    {{bibtex}}           the BibTeX block with a copy button
    {{paper:title}}      the paper title

The home page also uses {{cards}}, {{filters}}, {{rows}}, {{orgs}}, {{blog}}, {{contributors}} and
{{connect}}, from "projects", "research", "orgs", "blog", "paper.authors" and "contact"; {{blog}} is the
featured entries of "blog", and blog/index.html lists all of them by category. A blog post on other
people's work is one entry in "blog", one in "posts" and pages/blog/<slug>.html, written to
blog/<slug>/index.html.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
FONTS = ("https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400"
         "&family=Noto+Sans+Mono:wght@400;600&display=swap")

# Simple stroke icons (24x24) drawn for this site, and GitHub's mark (Octicons, MIT).
ICONS = {
    "github": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>',
    "paper": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/></svg>',
    "docs": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/><path d="M8 7h8M8 11h6"/></svg>',
    "map": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 4 3 6.5v13L9 17l6 2.5 6-2.5v-13L15 6.5z"/><path d="M9 4v13M15 6.5v13"/></svg>',
    "list": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "external": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
    "sun": '<svg class="sun" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/></svg>',
    "moon": '<svg class="moon" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11z"/></svg>',
    "copy": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a1 1 0 0 1 1-1h10"/></svg>',
    "hub": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="5" r="1.8"/><circle cx="4" cy="19" r="1.8"/><circle cx="20" cy="5" r="1.8"/><circle cx="20" cy="19" r="1.8"/><path d="M5.5 6.2 9.6 10M5.5 17.8 9.6 14M18.5 6.2 14.4 10M18.5 17.8 14.4 14"/></svg>',
    "scale": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18M7 21h10M4 7h16"/><path d="M4 7 1.5 13a3 3 0 0 0 5 0z"/><path d="M20 7l-2.5 6a3 3 0 0 0 5 0z"/></svg>',
    "terminal": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="4" width="19" height="16" rx="2.5"/><path d="m7 9 3 3-3 3M12.5 15H17"/></svg>',
    "box": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.8 20.5 7.5v9L12 21.2 3.5 16.5v-9z"/><path d="M3.5 7.5 12 12l8.5-4.5M12 12v9.2"/></svg>',
    "tool": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 6.5a4 4 0 0 0 5 5L21 13l-8 8-3-3 8-8M14.5 6.5 13 5a4 4 0 0 0-5.5 5.5L3 15l3 3 4.5-4.5"/></svg>',
    "route": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="18" r="2.2"/><circle cx="19" cy="6" r="2.2"/><path d="M7.2 18H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h7.8"/></svg>',
    "plus": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>',
    "pen": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19.5 8.5a2.83 2.83 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/></svg>',
    "chev-left": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m15 5-7 7 7 7"/></svg>',
    "chev-right": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/></svg>',
    "chat": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 4C5.4 4 2 6.7 2 10.1c0 1.9 1.1 3.6 2.8 4.7L4.2 17l2.7-1.4c.8.2 1.7.4 2.6.4"/><path d="M15 9c3.9 0 7 2.5 7 5.6 0 1.6-.9 3-2.2 4l.5 2-2.4-1.2c-.9.3-1.9.4-2.9.4-3.9 0-7-2.5-7-5.6S11.1 9 15 9z"/><path d="M7 8.6h.01M11.5 8.6h.01M12.6 14h.01M17.4 14h.01"/></svg>',
    "pause": '<svg class="i-pause" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>',
    "play": '<svg class="i-play" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="currentColor"><path d="M7 4.8v14.4a1 1 0 0 0 1.5.86l11.6-7.2a1 1 0 0 0 0-1.72L8.5 3.94A1 1 0 0 0 7 4.8z"/></svg>',
}

TYPE_ICON = {"Publication": "paper", "Code": "github", "Docs": "docs", "Research map": "map"}


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def icon(name: str) -> str:
    if name not in ICONS:
        raise SystemExit(f"error: unknown icon {name!r}; add it to ICONS in scripts/build.py")
    return ICONS[name]


def arxiv_url() -> str:
    a = DATA["paper"].get("arxiv_id", "").strip()
    return f"https://arxiv.org/abs/{a}" if a else ""


def link(key: str) -> str:
    if key == "arxiv":
        return arxiv_url()
    if key not in DATA["links"]:
        raise SystemExit(f"error: no link {key!r} in data/site.json; add it under \"links\"")
    return DATA["links"][key]


def arxiv_button() -> str:
    url = arxiv_url()
    if url:
        return f'<a class="btn" href="{esc(url)}">{icon("paper")}arXiv</a>'
    return (f'<span class="btn soon" role="link" aria-disabled="true" title="The arXiv preprint is coming soon">'
            f'{icon("paper")}arXiv <em>coming soon</em></span>')


def authors_block() -> str:
    p = DATA["paper"]
    marks = p["marks"]
    items = []
    for a in p["authors"]:
        sup = ",".join(str(i) for i in a["affiliations"]) + "".join(marks[m]["symbol"] for m in a["marks"])
        name = esc(a["name"])
        if a.get("homepage"):    # only a page the author or a source we trust gives; never a guessed one
            name = f'<a href="{esc(a["homepage"])}" target="_blank" rel="noopener">{name}</a>'
        items.append(f'<li>{name}<sup>{esc(sup)}</sup></li>')
    used = [m for m in marks if any(m in a["marks"] for a in p["authors"])]
    legend = "".join(f'<li><sup>{esc(marks[m]["symbol"])}</sup>{esc(marks[m]["label"])}</li>' for m in used)
    affils = "".join(f'<li><sup>{i}</sup>{esc(x)}</li>' for i, x in enumerate(p["affiliations"], 1))
    return (f'<section class="authors" aria-label="Authors">\n<div class="wrap">\n'
            f'<ul class="author-list">{"".join(items)}</ul>\n'
            f'<ul class="legend">{legend}</ul>\n<ul class="affils">{affils}</ul>\n</div>\n</section>')


def bibtex_text() -> str:
    p = DATA["paper"]

    def last_first(name: str) -> str:
        first, _, last = name.rpartition(" ")
        return f"{last}, {first}" if first else name

    names = " and ".join(last_first(a["name"]) for a in p["authors"])
    aid = p.get("arxiv_id", "").strip() or "XXXX.XXXXX"
    return (f"@article{{{p['bibtex_key']},\n"
            f"  title   = {{{p['title']}}},\n"
            f"  author  = {{{names}}},\n"
            f"  journal = {{arXiv preprint arXiv:{aid}}},\n"
            f"  year    = {{{p['year']}}}\n}}")


def code_block(cid: str, display: str, copy_text: str, label: str, cls: str = "") -> str:
    return (f'<div class="code has-copy"><pre id="{cid}" class="{cls}" data-text="{esc(copy_text)}" aria-label="{esc(label)}" tabindex="0">'
            f'{display}</pre><button class="copy" type="button" data-copy="{cid}" aria-label="Copy {esc(label)}">'
            f'{icon("copy")}<span>Copy</span></button></div>')


def bibtex_block() -> str:
    text = bibtex_text()
    return (f'<section class="section" id="bibtex" aria-labelledby="bibtex-h">\n<div class="wrap narrow">\n'
            f'<h2 id="bibtex-h">BibTeX</h2>\n'
            f'<p>If you use either project, please cite our paper:</p>\n'
            f'{code_block("bibtex-code", esc(text), text, "BibTeX", "wrap-lines")}\n</div>\n</section>')


def fill(text: str, root: str) -> str:
    def sub(m: re.Match[str]) -> str:
        key = m.group(1).strip()
        if key == "root":
            return root
        if key == "arxiv_button":
            return arxiv_button()
        if key == "authors":
            return authors_block()
        if key == "bibtex":
            return bibtex_block()
        if key == "paper:title":
            return esc(DATA["paper"]["title"])
        kind, _, arg = key.partition(":")
        if kind == "link":
            return esc(link(arg))
        if kind == "site":
            return esc(DATA["site"][arg])
        if kind == "logo":
            return logo(arg, root)
        if kind == "symbol":
            return symbol(arg, root)
        if kind == "icon":
            return icon(arg)
        raise SystemExit(f"error: unknown placeholder {{{{{key}}}}}; see the docstring of scripts/build.py")

    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", sub, text)


def head(tab: str, title: str, description: str, root: str, path: str, image: str, brand: str = "real2simhub") -> str:
    """The page head. `tab` is what the browser tab shows: only the page's own name, since a tab cuts off anything
    longer (owner, 2026-11-25; check_links.py enforces TAB_MAX). `title` is the full title that link previews show."""
    site = DATA["site"]
    url = site["url"].rstrip("/") + "/" + path
    img = site["url"].rstrip("/") + "/" + image
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(tab)}</title>
<meta name="description" content="{esc(description)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0b1020" media="(prefers-color-scheme: dark)">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(img)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="{root}assets/brand/svg/{brand}-favicon.svg">
<link rel="alternate icon" href="{root}assets/brand/{brand}.ico" sizes="16x16 32x32 48x48">
<link rel="apple-touch-icon" href="{root}assets/brand/png/{brand}-icon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{root}assets/css/site.css">
<script>try{{var t=localStorage.getItem("r2sh-theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
"""


LOGO_H = 32
LOGO_BOX = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', (ROOT / "assets/brand/svg/real2simhub-logo-small.svg").read_text(encoding="utf-8"))
LOGO_W = round(LOGO_H * float(LOGO_BOX[1]) / float(LOGO_BOX[2]))
SOCIAL = "assets/brand/png/real2simhub-social.png"


def logo(slug: str, root: str) -> str:
    """The project's logo, light or dark with the theme."""
    name = next((p["name"] for p in DATA["projects"] if p["slug"] == slug), DATA["site"]["name"])
    box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', (ROOT / f"assets/brand/svg/{slug}-logo.svg").read_text(encoding="utf-8"))
    return (f'<picture><source data-dark srcset="{root}assets/brand/svg/{slug}-logo-dark.svg" media="(prefers-color-scheme: dark)">'
            f'<img src="{root}assets/brand/svg/{slug}-logo.svg" alt="{esc(name)}" width="{float(box[1]):g}" height="{float(box[2]):g}"></picture>')


def symbol(slug: str, root: str, height: int = 22) -> str:
    """The project's symbol (decorative: its name stands beside it), light or dark with the theme."""
    box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', (ROOT / f"assets/brand/svg/{slug}-symbol.svg").read_text(encoding="utf-8"))
    return (f'<picture><source data-dark srcset="{root}assets/brand/svg/{slug}-symbol-dark.svg" media="(prefers-color-scheme: dark)">'
            f'<img src="{root}assets/brand/svg/{slug}-symbol.svg" alt="" width="{round(height * float(box[1]) / float(box[2]))}" height="{height}"></picture>')


def series(root: str, current: str) -> str:
    """The hub and its projects, one tab each, on every page."""
    items = [("real2simhub", DATA["site"], root or "./")] + [(p["slug"], p, f'{root}{p["slug"]}/') for p in DATA["projects"]]
    tabs = "".join(
        f'<a href="{href}" aria-label="{esc(x["name"])}"{" aria-current=" + chr(34) + "page" + chr(34) if key == current else ""}>'
        f'{symbol(key, root)}'
        f'<span class="long">{esc(x["name"])}</span><span class="short">{esc(x["short"])}</span></a>'
        for key, x, href in items)
    return f'<nav class="series" aria-label="The Real2SimHub series">{tabs}</nav>'


def header(root: str, current: str = "") -> str:
    site = DATA["site"]
    return f"""<header class="site-header">
<div class="wrap">
<a class="brand" href="{root or './'}" aria-label="{esc(site['name'])} home"><picture><source data-dark srcset="{root}assets/brand/svg/real2simhub-logo-small-dark.svg" media="(prefers-color-scheme: dark)"><img src="{root}assets/brand/svg/real2simhub-logo-small.svg" alt="{esc(site['name'])}" width="{LOGO_W}" height="{LOGO_H}"></picture></a>
{series(root, current)}
<div class="header-right">
<a class="org-link" href="{esc(site['github'])}">{icon("github")}<span class="org-name">{esc(site['github_name'])}</span></a>
<span class="divider" aria-hidden="true"></span>
<button class="theme-toggle" type="button" aria-label="Switch theme">{icon("sun")}{icon("moon")}</button>
</div>
</div>
</header>
"""


def footer(root: str) -> str:
    site = DATA["site"]
    projects = "".join(f'<a href="{root}{p["slug"]}/">{esc(p["name"])}</a>' for p in DATA["projects"])
    return f"""<footer class="site-footer">
<div class="wrap">
<div class="foot-top"><span>© {esc(site['year'])} {esc(site['org_name'])} · {esc(site['name'])}</span><nav aria-label="Projects">{projects}<a href="{esc(site['github'])}">GitHub</a><a href="{esc(link('credits'))}">Credits</a></nav></div>
</div>
</footer>
<script src="{root}assets/js/site.js"></script>
</body>
</html>
"""


def card(p: dict, root: str) -> str:
    """A project card: its README figure whole on a wide screen and its middle box on a phone, each in the
    page's theme (sources marked data-dark follow the theme toggle; data-media narrows them to phones)."""
    phone = "(max-width: 760px)"
    sources = []
    if p.get("card_middle_dark"):
        sources.append(f'<source data-dark data-media="{phone}" srcset="{root}{p["card_middle_dark"]}" '
                       f'media="{phone} and (prefers-color-scheme: dark)">')
    if p.get("card_dark"):
        sources.append(f'<source data-dark srcset="{root}{p["card_dark"]}" media="(prefers-color-scheme: dark)">')
    if p.get("card_middle"):
        sources.append(f'<source srcset="{root}{p["card_middle"]}" media="{phone}">')
    return (f'<a class="card" href="{root}{p["slug"]}/">'
            f'<span class="card-fig"><picture>{"".join(sources)}<img src="{root}{p["card"]}" alt="{esc(p["card_alt"])}" '
            f'loading="lazy" decoding="async"></picture></span>'
            f'<span class="card-foot"><span class="card-text"><span class="card-name">{esc(p["name"])}</span>'
            f'<span class="card-tag">{esc(p["tagline"])}</span></span>'
            f'<span class="card-go" aria-hidden="true">{icon("arrow")}</span></span></a>')


def research_row(r: dict, root: str) -> str:
    t = r["type"]
    href = ""
    if r.get("href_when_arxiv") and arxiv_url():
        href = arxiv_url()
    elif r.get("link"):
        href = link(r["link"])
    elif r.get("href"):
        href = root + r["href"]
    owner = f'{esc(r["owner"])}<b>{esc(r["title"])}</b>' if r.get("owner") else esc(r["title"])
    inner = (f'<span class="meta"><span class="type t-{slug(t)}">{icon(TYPE_ICON[t])}{esc(t)}</span>'
             f'<span class="date">{esc(r["date"])}</span></span>'
             f'<span><span class="title">{owner}</span><span class="desc">{esc(r["description"])}</span></span>'
             f'<span class="arrow" aria-hidden="true">{icon("arrow")}</span>')
    return f'<li class="row" data-type="{slug(t)}"><a href="{esc(href)}">{inner}</a></li>'


def orgs_block(root: str) -> str:
    """The contributors' institutions: two rows of logos that move in opposite directions (paused on
    hover, with a pause button, and still for reduced motion). The second copy of each row only
    closes the loop and is hidden from screen readers. The logos load eagerly: lazy images in a
    moving row load only as each slides into view, so phones showed empty tiles."""
    rows = [[o for o in DATA["orgs"] if o.get("row", 1) == r] for r in (1, 2)]

    def logos(row: list[dict], hidden: bool) -> str:
        items = "".join(
            f'<li class="org"><span class="org-logo{" wide" if o.get("wide") else ""}"><img src="{root}{esc(o["logo"])}" alt="" '
            f'width="{96 if o.get("wide") else 40}" height="40" decoding="async"></span>'
            f'<span class="org-name">{esc(o["name"])}</span></li>' for o in row)
        aria = ' aria-hidden="true"' if hidden else ""
        return f'<ul class="logo-set"{aria}>{items}</ul>'

    windows = "".join(
        f'<div class="logo-window"><div class="logo-track{" reverse" if i else ""}" style="--logo-time:{8 * len(row)}s">'
        f'{logos(row, False)}{logos(row, True)}</div></div>' for i, row in enumerate(rows) if row)
    return (f'<div class="orgs" role="group" aria-labelledby="orgs-h">\n<p class="orgs-h" id="orgs-h">Contributors come from:</p>\n'
            f'<div class="marquee" data-marquee>{windows}'
            f'<button class="marquee-toggle" type="button" aria-pressed="false" aria-label="Pause the moving logos">'
            f'{icon("pause")}{icon("play")}</button></div>\n</div>')


BLOG_CATEGORIES = ["Our work", "Benchmarks", "Methods"]


def post_card(b: dict, root: str) -> str:
    return (f'<li class="post"><a href="{root}{esc(b["href"])}"><span class="post-img"><img src="{root}{esc(b["image"])}" '
            f'alt="{esc(b["alt"])}" width="1200" height="675" loading="lazy" decoding="async"><span class="post-org">{esc(b["org"])}</span></span>'
            f'<span class="post-body"><span class="post-label">{esc(b["label"])}</span><span class="post-title">{esc(b["title"])}</span>'
            f'<span class="post-text">{esc(b["text"])}</span></span></a></li>')


def blog_block(root: str) -> str:
    """The home page's blog: the featured posts in a grid (CSS shows fewer on narrow screens), then a
    button to the blog page with every post."""
    bad = [b["title"] for b in DATA["blog"] if b.get("category") not in BLOG_CATEGORIES]
    if bad:
        raise SystemExit(f"error: blog entries {bad} have no known category; fix: set \"category\" to one of {BLOG_CATEGORIES}")
    cards = "".join(post_card(b, root) for b in DATA["blog"] if b.get("featured"))
    return (f'<ul class="post-grid featured" aria-label="Featured blog posts">{cards}</ul>\n'
            f'<p class="more-posts"><a class="btn" href="{root}blog/">All {len(DATA["blog"])} posts{icon("arrow")}</a></p>')


def blog_page() -> str:
    """blog/: every post, under its category, and an invitation to write one."""
    root = "../"
    counts = {c: sum(1 for b in DATA["blog"] if b.get("category") == c) for c in BLOG_CATEGORIES}
    chips = "".join(f'<a href="#{slug(c)}">{esc(c)}<span>{counts[c]}</span></a>' for c in BLOG_CATEGORIES if counts[c])
    sections = "".join(
        f'<section class="blog-cat" id="{slug(c)}" aria-labelledby="{slug(c)}-h">\n<h2 id="{slug(c)}-h">{esc(c)}</h2>\n'
        f'<ul class="post-grid">{"".join(post_card(b, root) for b in DATA["blog"] if b.get("category") == c)}</ul>\n</section>\n'
        for c in BLOG_CATEGORIES if counts[c])
    yours = (f'<section class="blog-cat" id="yours" aria-labelledby="yours-h">\n<h2 id="yours-h">Yours</h2>\n'
             f'<ul class="post-grid"><li class="post more"><a href="{root}#connect"><span class="post-img">{icon("pen")}</span>'
             f'<span class="post-body"><span class="post-label">Yours</span><span class="post-title">Write a post</span>'
             f'<span class="post-text">Share your method, benchmark or dataset on Real2SimHub: get in touch.</span></span></a></li></ul>\n</section>')
    body = (f'<section class="research blog-page" aria-labelledby="blog-h">\n<div class="wrap">\n'
            f'<p class="crumb"><a href="{root}">Real2SimHub</a></p>\n<h1 id="blog-h">Blog</h1>\n'
            f'<p class="lead">Our projects, and the benchmarks and methods of real-to-simulation, each in a short post.</p>\n'
            f'<nav class="blog-chips" aria-label="Categories">{chips}</nav>\n{sections}{yours}\n</div>\n</section>')
    return (head("Blog · Real2SimHub", "Blog · Real2SimHub", "Posts on Real2SimHub: our projects, and the benchmarks and methods of real-to-simulation.",
                 root, "blog/", SOCIAL)
            + header(root) + '<main id="main">\n' + fill(body, root) + "\n</main>\n" + footer(root))


def contributors_block() -> str:
    """Everyone who contributed, in one box, sorted by surname (the last word) and then given name."""
    names = sorted(DATA["contributors"], key=lambda n: (n.split()[-1].casefold(), n.casefold()))
    items = "".join(f"<li>{esc(n)}</li>" for n in names)
    return (f'<div class="names-box"><ul class="names">{items}</ul></div>\n'
            f'<p class="names-note">Listed alphabetically by surname.</p>')


def connect_block(root: str) -> str:
    """Email, and the two WeChat codes (the group and a person), each shown in a dialog; without
    JavaScript the link opens the image."""
    c = DATA["contact"]

    def qr(key: str, title: str, hint: str) -> str:
        return (f'<a class="contact" href="{root}{esc(c[key])}" data-qr data-qr-title="{esc(title)}">'
                f'<span class="contact-ico wechat">{icon("chat")}</span><span class="contact-text"><b>{esc(title)}</b>'
                f'<span>{esc(hint)}</span></span></a>')

    # The address is plain text, so it can be selected; the icon and the title open the mail app.
    return (f'<div class="contacts">\n'
            f'<div class="contact"><a class="contact-ico" href="mailto:{esc(c["email"])}" aria-label="Write an email">{icon("mail")}</a>'
            f'<span class="contact-text"><b><a href="mailto:{esc(c["email"])}">Email</a></b>'
            f'<span class="addr" id="email-addr">{esc(c["email"])}</span></span>'
            f'<button class="mail-copy" type="button" data-copy="email-addr" aria-label="Copy the email address">'
            f'{icon("copy")}<span>Copy</span></button></div>\n'
            f'{qr("wechat_group", "WeChat group", "Scan the code to join")}\n'
            f'{qr("wechat_personal", "WeChat", "Scan the code to add")}\n</div>\n'
            f'<dialog class="qr-dialog" aria-labelledby="qr-title"><form method="dialog">'
            f'<p class="qr-title" id="qr-title"></p><span class="qr-img"></span>'
            f'<button class="btn" type="submit">Close</button></form></dialog>')


def home() -> str:
    root = ""
    types = []
    for r in DATA["research"]:
        if r["type"] not in types:
            types.append(r["type"])
    filters = '<button type="button" data-filter="all" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" data-filter="{slug(t)}" aria-pressed="false">{esc(t)}</button>' for t in types)
    body = (ROOT / "pages" / "home.html").read_text(encoding="utf-8")
    body = body.replace("{{cards}}", "\n".join(card(p, root) for p in DATA["projects"]))
    body = body.replace("{{filters}}", filters)
    body = body.replace("{{rows}}", "\n".join(research_row(r, root) for r in DATA["research"]))
    body = body.replace("{{orgs}}", orgs_block(root))
    body = body.replace("{{blog}}", blog_block(root))
    body = body.replace("{{contributors}}", contributors_block())
    body = body.replace("{{connect}}", connect_block(root))
    site = DATA["site"]
    return (head(site["name"], f"{site['name']}: a community to build the infrastructure of real-to-simulation together",
                 site["description"], root, "",
                 SOCIAL)
            + header(root, "real2simhub") + '<main id="main">\n' + fill(body, root) + "\n</main>\n" + footer(root))


def project(p: dict) -> str:
    root = "../"
    src = ROOT / "pages" / f"{p['slug']}.html"
    if not src.exists():
        raise SystemExit(f"error: project {p['slug']!r} has no page body; create pages/{p['slug']}.html")
    body = src.read_text(encoding="utf-8")
    social = f'assets/brand/png/{p["slug"]}-social.png'
    return (head(p["name"], p["page_title"], p["page_description"], root, p["slug"] + "/", social, p["slug"])
            + header(root, p["slug"]) + '<main id="main">\n' + fill(body, root) + "\n</main>\n" + footer(root))


def post(p: dict) -> str:
    root = "../../"
    src = ROOT / "pages" / "blog" / f"{p['slug']}.html"
    if not src.exists():
        raise SystemExit(f"error: blog post {p['slug']!r} has no page body; create pages/blog/{p['slug']}.html")
    body = (f'<article class="article" aria-labelledby="post-h">\n<div class="wrap narrow">\n'
            f'<p class="crumb"><a href="{root}blog/">Blog</a></p>\n<h1 id="post-h">{esc(p["title"])}</h1>\n'
            + src.read_text(encoding="utf-8") + '\n</div>\n</article>')
    if ":" not in p["title"]:
        raise SystemExit(f"error: blog post {p['slug']!r}: its title needs the form 'Name: subtitle'; the tab shows the name")
    return (head(p["title"].split(":")[0].strip(), p["title"], p["description"], root, f"blog/{p['slug']}/", SOCIAL)
            + header(root) + '<main id="main">\n' + fill(body, root) + "\n</main>\n" + footer(root))


def not_found() -> str:
    root = "/"
    body = ('<section class="mission"><div class="wrap"><h1>Page not found</h1>'
            '<p class="lead">This page does not exist. Go back to <a href="/">Real2SimHub</a>.</p></div></section>')
    return (head("Page not found", "Page not found · Real2SimHub", DATA["site"]["description"], root, "404.html", SOCIAL)
            + header(root) + '<main id="main">\n' + body + "\n</main>\n" + footer(root))


def outputs() -> dict[Path, str]:
    out = {ROOT / "index.html": home(), ROOT / "404.html": not_found(), ROOT / "blog" / "index.html": blog_page()}
    for p in DATA["projects"]:
        out[ROOT / p["slug"] / "index.html"] = project(p)
    for p in DATA.get("posts", []):
        out[ROOT / "blog" / p["slug"] / "index.html"] = post(p)
    return out


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for path, text in outputs().items():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.relative_to(ROOT))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("error: out of date: " + ", ".join(map(str, stale)) + "; fix: python3 scripts/build.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
