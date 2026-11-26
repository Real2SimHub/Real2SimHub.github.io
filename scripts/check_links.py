#!/usr/bin/env python3
"""Check the generated site offline: local links and assets, anchors, alt text and wording.

    python3 scripts/check_links.py

Every relative href/src/srcset/poster must exist on disk, every same-page or cross-page
#anchor must exist, every <img> needs an alt attribute, and no page may use words the project
avoids. Every page's <title>, which the browser tab shows, is only the page's name (at most TAB_MAX
characters, since a tab cuts off the rest); the full title goes to og:title for link previews. External links are listed (not fetched) so they can be compared with data/site.json.
Exits 1 on any problem.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

ROOT = Path(__file__).resolve().parent.parent
TAB_MAX = 24
PAGES = [
    "index.html",
    "404.html",
    "real2simlab/index.html",
    "awesome-real2sim/index.html",
    "blog/index.html",
    "blog/4dcodebench/index.html",
    "blog/video2world/index.html",
    "blog/physics-iq/index.html",
    "blog/iris/index.html",
    "blog/physcodegym/index.html",
    "blog/physimcode/index.html",
    "blog/agentic-real2sim/index.html",
    "blog/3dcodeverse/index.html",
]
# Words the site never uses (case-insensitive, whole words where it matters).
BANNED = [r"\bharness", r"video-to-simulation", r"leaderboard", r"state of the art", r"\bSOTA\b",
          r"revolutionary", r"\bconditions?\b", r"\bquer(y|ies)\b", r"queryable", r"\b289\b",
          r"\btrained model", r"\bour trainer"]


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str, int]] = []   # (attribute, value, line)
        self.ids: set[str] = set()
        self.imgs_without_alt: list[int] = []
        self.text: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        line = self.getpos()[0]
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "img" and "alt" not in a:
            self.imgs_without_alt.append(line)
        for key in ("href", "src", "poster"):
            if key in a and a[key]:
                self.refs.append((key, a[key], line))
        if "srcset" in a:
            for part in a["srcset"].split(","):
                if part.strip():
                    self.refs.append(("srcset", part.strip().split()[0], line))
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.text.append(data)


def main() -> int:
    problems: list[str] = []
    parsed: dict[Path, Page] = {}
    for rel in PAGES:
        f = ROOT / rel
        if not f.is_file():
            problems.append(f"{rel}: missing (run python3 scripts/build.py)")
            continue
        html = f.read_text(encoding="utf-8")
        p = Page()
        p.feed(html)
        parsed[f] = p
        tab = re.search(r"<title>([^<]*)</title>", html)
        if not tab or not tab.group(1).strip():
            problems.append(f"{rel}: no <title>")
        elif len(tab.group(1)) > TAB_MAX:
            problems.append(f"{rel}: tab title {tab.group(1)!r} is longer than {TAB_MAX} characters; "
                            "a browser tab cuts it off: show only the page's name, and put the full title in og:title")
        if not re.search(r'<meta property="og:title" content="[^"]+">', html):
            problems.append(f"{rel}: no og:title for link previews")

    external: set[str] = set()
    for f, p in parsed.items():
        rel = f.relative_to(ROOT)
        for line in p.imgs_without_alt:
            problems.append(f"{rel}:{line}: <img> without alt")
        text = " ".join(p.text)
        for pat in BANNED:
            for m in re.finditer(pat, text, flags=re.I):
                problems.append(f"{rel}: avoided wording {m.group(0)!r} in "
                                f"{text[max(0, m.start() - 40):m.end() + 40]!r}")
        for key, value, line in p.refs:
            url, frag = urldefrag(value)
            scheme = urlparse(url).scheme
            if scheme in ("http", "https"):
                external.add(url + (f"#{frag}" if frag else ""))
                continue
            if scheme in ("mailto", "data", "javascript"):
                continue
            if not url:
                target = f
            elif url.startswith("/"):   # root-relative (404.html is served at any depth)
                target = (ROOT / unquote(url).lstrip("/")).resolve()
            else:
                target = (f.parent / unquote(url)).resolve()
            if url.endswith("/") or (target.is_dir() and url):
                target = target / "index.html"
            if not target.exists():
                problems.append(f"{rel}:{line}: {key}={value!r} -> {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target} does not exist")
                continue
            if not target.resolve().is_relative_to(ROOT):
                problems.append(f"{rel}:{line}: {key}={value!r} leaves the site")
            if frag and target.suffix == ".html":
                tp = parsed.get(target.resolve())
                if tp is None:
                    tp = Page()
                    tp.feed(target.read_text(encoding="utf-8"))
                if frag not in tp.ids:
                    problems.append(f"{rel}:{line}: anchor #{frag} not found in {target.relative_to(ROOT)}")

    print("External links (not fetched):")
    for u in sorted(external):
        print(f"  {u}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"\nOK: {len(parsed)} pages, local links, anchors, alt text, wording and tab titles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
