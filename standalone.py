#!/usr/bin/env python3
"""Build a self-contained single-file deck from a slaydy deck folder,
or take one apart again.

UPSTREAM-OWNED. Every update replaces this file whole, and an edit here is
skipped by take-update.sh from then on (UPDATING.md §1). If the export can't
see an asset of yours, make the asset visible instead of patching this: put
what your script fetches behind a real <script src> and it is inlined like
any other script (CUSTOMIZING.md, Layer 3). For what can't be a file, a
fork-owned standalone_hook.py beside this script adds to the bundle (see
run_hook below); the in-browser export has the slaydy:serialize event for
the same job.

Usage:  python3 standalone.py path/to/deck.html [out.html]
        python3 standalone.py --lint path/to/deck.html
        python3 standalone.py --no-lint path/to/deck.html [out.html]
        python3 standalone.py --explode path/to/standalone.html [out.html]

Build writes one file next to the deck, named after the deck's <title> (or
to out.html): slide markup stays at the top of the file, hand-editable; the
compacted stylesheet and runtime are appended at the end of <body>; images
and the footer logo become data: URIs; data-themes is stripped (the theme
is baked in) and <html> is marked data-standalone. Mirrors the runtime's
own "Single file" export — keep the two in sync (see inlineAssets in
runtime.js).

Build lints the deck first (density budgets, deck structure, what the tier
asks for, markup the skill forbids) and prints what it finds; the file is
written either way. --lint does only that, and exits 1 when anything needs
fixing. --no-lint builds without it. A fork tells the lint about its own
markup in a lint.json beside this script (see lint_config below).

Explode is the inverse, for revising a deck when only the standalone file
exists: inlined images come out as files in images/ (byte-identical files
already there are reused, so a round trip restores original names), the
bundled stylesheet and runtime come out as bundle.css / bundle.js, and the
result (deck-work.html by default) is a small, grep-able markup file that
build accepts straight back. Base64 never passes through a revision.
"""
import base64, hashlib, importlib.util, json, math, mimetypes, re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote_to_bytes

mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("image/avif", ".avif")  # only in the stdlib map from 3.9


def min_css(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return "\n".join(l.strip() for l in t.splitlines() if l.strip())


def min_js(t: str) -> str:
    t = re.sub(r"^[ \t]*/\*.*?\*/", "", t, flags=re.S | re.M)
    lines = (l.strip() for l in t.splitlines())
    return "\n".join(l for l in lines if l and not l.startswith("//"))


def is_rel(u: str) -> bool:
    return bool(u) and not re.match(r"^(data:|blob:|https?:|//)", u)


def read_asset(p: Path, minifier) -> str:
    """Prefer a pre-minified sibling (runtime.min.js, built by build.sh) when
    it was built from this source; otherwise compact the source. build.sh
    stamps each .min with its source's hash, which survives the copies and
    clones that reset file times. A .min from before the stamp falls back to
    being at least as new as the source."""
    m = p.with_name(re.sub(r"\.(css|js)$", r".min.\1", p.name))
    if m.is_file():
        text = m.read_text(encoding="utf-8")
        stamp = re.match(r"/\*! slaydy-min (\w+) \*/", text)
        if stamp:
            current = hashlib.sha1(p.read_bytes()).hexdigest()[:12] == stamp.group(1)
        else:
            current = m.stat().st_mtime >= p.stat().st_mtime
        if current:
            return text
    return minifier(p.read_text(encoding="utf-8"))


def data_uri(p: Path) -> str:
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


CSS_URL = re.compile(r"""url\(\s*(['"]?)([^)'"]+)\1\s*\)""")


def inline_css_urls(css: str, base: Path) -> str:
    """Rewrite a stylesheet's relative url() references (fonts, ornaments,
    icons) to data: URIs, resolving against the stylesheet's own folder —
    themes/x.css referring to ../assets/y.woff2 must resolve correctly.
    Anything with a #fragment passes through untouched (a data: URI can't
    address a fragment, so inlining url(file.svg#filter) would kill the
    filter), as do root-absolute /paths (they resolve against a server root
    this builder doesn't have — and `base / "/x"` would escape the deck
    folder entirely), anything is_rel rejects, and targets missing on disk.
    Mirrors the runtime's inlineCSSUrls — keep the two in sync."""
    def swap(m):
        u = m.group(2).strip()
        if "#" in u or u.startswith("/") or not is_rel(u):
            return m.group(0)
        target = base / re.sub(r"\?.*$", "", u)
        if not target.is_file():
            return m.group(0)
        return f"url({data_uri(target)})"
    return CSS_URL.sub(swap, css)


DECK_BLOCK = re.compile(r"<(style|script)([^>]*\bdata-deck\b[^>]*)>([\s\S]*?)</\1>")


def check_deck_blocks(html: str) -> None:
    """A deck may carry its own <style data-deck> / <script data-deck> for
    content under [data-custom]. Two placement rules make that safe, and both
    are cheap to get wrong silently, so they fail loudly here instead.

    1. Both live in <head>. The bundle this script appends sits at the end of
       <body>, and --explode reclaims it by position (see the regex below) —
       a deck block sitting next to it would be swallowed as runtime.
    2. No relative url() in deck CSS. Nothing inlines it, and inlining it
       would drag base64 back through the next revision, which the explode
       side exists to prevent."""
    head = html.split("</head>", 1)[0]
    for m in DECK_BLOCK.finditer(html):
        tag = m.group(1)
        if m.start() > len(head):
            sys.exit(f"error: <{tag} data-deck> must live in <head> — found one in <body>.\n"
                     f"       The runtime bundle is appended at the end of <body>; a deck block\n"
                     f"       there is indistinguishable from it on the way back out.")
        if tag == "style":
            rel = [u for _q, u in CSS_URL.findall(m.group(3)) if is_rel(u.strip())]
            if rel:
                sys.exit(f"error: <style data-deck> references a relative url({rel[0]}).\n"
                         f"       Custom CSS can't carry assets — use an <img> or inline SVG\n"
                         f"       in the slide instead, so images keep travelling as files.")


# ---- lint -------------------------------------------------------------------
# The numbers are LAYOUTS.md "Density budgets" and the deck rules of SKILL.md
# §3 and §10 — keep the three in sync. "fix" lines break a rule that can be
# counted; "check" lines are matters of judgment: pacing (dividers, agenda)
# and what a tier asks for by default, which a slide may have a reason to skip. Content the runtime leaves alone ([data-custom]), the user's own
# stickers, speaker notes and icons are never counted.

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids = tag, dict(attrs), parent, []

    @property
    def cls(self):
        return (self.attrs.get("class") or "").split()

    def walk(self, skip=lambda n: False):
        for k in self.kids:
            if isinstance(k, Node) and not skip(k):
                yield k
                yield from k.walk(skip)

    def text(self, skip=lambda n: False):
        return "".join(k if isinstance(k, str) else ("" if skip(k) else k.text(skip)) for k in self.kids)


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("#root", [], None)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n.parent and n.tag != tag:
            n = n.parent
        if n.parent:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def _ignored(n):
    return ("data-custom" in n.attrs or "sticker" in n.cls or n.tag == "svg"
            or (n.tag == "aside" and "notes" in n.cls))


HEADLINE = {"title": 8, "section": 4, "statement": 12, "bullets": 8, "split": 8, "full": 8,
            "gallery": 8, "end": 8, "callout": 6, "callout-full": 5}
REVEALS = {"bullets": ("ul", "ol"), "cards": ("cards",), "stats": ("stats",), "bento": ("bento",),
           "compare": ("compare",), "timeline": ("timeline",), "table": ("tbody",)}
SEPARATOR = re.compile(r"[·•|]|\s[—–/]\s")
# the repeated unit each grid layout counts: class, fewest, most
UNITS = {"cards": ("card", 3, 3), "bento": ("cell", 5, 5), "stats": ("stat", 3, 3),
         "compare": ("col", 2, 2), "timeline": ("step", 3, 5)}
THEME_TOKENS = {"--app-bg", "--bg", "--fg", "--muted", "--faint", "--surface", "--accent", "--accent-2",
                "--accent-fg", "--wash-opacity", "--font-display", "--font-body", "--font-mono", "--pad"}
LINT_KEYS = {"enabled", "inline_properties", "units", "skip"}


def lint_config() -> dict:
    """What an install declares about its own markup, read from a fork-owned
    lint.json beside this script. Every key is optional:

        {
          "enabled": true,
          "inline_properties": ["--x", "--y", "--v"],
          "units": { "bento": "bento-tile",
                     "timeline": { "class": "tl-node", "min": 3, "max": 6 } },
          "skip": ["callout"]
        }

    inline_properties — custom properties the install's layouts read from an
    inline style (a position, a size, a count). They are values, not styling,
    and are accepted where named here; a real CSS property never is.
    units — the class an install gives a layout's repeated unit (cells, steps,
    cards, columns, figures) when it is not the stock one, optionally with how
    many the layout takes.
    skip — layouts whose budgets and counts the lint leaves alone entirely.
    enabled — false turns the lint off for this install."""
    f = Path(__file__).resolve().parent / "lint.json"
    if not f.is_file():
        return {}
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"lint.json is not valid JSON ({e})") from None
    unknown = set(cfg) - LINT_KEYS if isinstance(cfg, dict) else {"(not an object)"}
    if unknown:
        raise ValueError(f"lint.json: unknown key {', '.join(sorted(unknown))} — the keys are {', '.join(sorted(LINT_KEYS))}")
    return cfg


def lint(html: str, folder: Path) -> list[tuple[str, str]]:
    """Return (level, message) pairs for a folder deck's markup."""
    cfg = lint_config()
    allowed_props = set(cfg.get("inline_properties", []))
    skip = set(cfg.get("skip", []))
    units = dict(UNITS)
    for layout, u in cfg.get("units", {}).items():
        u = u if isinstance(u, dict) else {"class": u}
        _, lo, hi = UNITS.get(layout, ("", 1, 99))
        units[layout] = (u["class"].lstrip("."), u.get("min", lo), u.get("max", hi))
    tree = Tree()
    tree.feed(html)
    every = list(tree.root.walk())
    out: list[tuple[str, str]] = []
    fix = lambda m: out.append(("fix", m))
    check = lambda m: out.append(("check", m))
    words = lambda n: len(n.text(_ignored).split())
    plural = lambda k, w: f"{k} {w}{'' if k == 1 else 's'}"

    # the shell: a deck without it renders black
    deck = next((n for n in every if n.tag == "div" and "deck" in n.cls
                 and n.parent and "stage" in n.parent.cls), None)
    if not deck:
        return [("fix", 'no <div class="stage"><div class="deck"> wrapper — copy the deck skeleton exactly (LAYOUTS.md)')]
    sheets = [n.attrs.get("href", "") for n in every if n.tag == "link" and n.attrs.get("rel") == "stylesheet"]
    local = [h for h in sheets if is_rel(h)]
    # an install's own skeleton.html is the authority on its wiring: with one beside this
    # script the stock shell is not assumed, and whatever blocks it carries are its own
    skeleton = Path(__file__).resolve().parent / "skeleton.html"
    skel = " ".join(skeleton.read_text(encoding="utf-8", errors="ignore").split()) if skeleton.is_file() else ""
    if not skel:
        theme = next((n.attrs.get("href") for n in every if n.tag == "link" and n.attrs.get("id") == "theme"), None)
        if not theme:
            fix('no <link rel="stylesheet" … id="theme"> — copy the deck skeleton exactly (LAYOUTS.md)')
        elif local and local[0] != theme and local.index(theme) < next((i for i, h in enumerate(local) if "runtime" in h or "bundle" in h), 0):
            fix("the theme stylesheet is linked before runtime.css — runtime.css comes first")
        if not any(n.tag == "script" and re.search(r"(runtime|bundle)[\w.]*\.js$", n.attrs.get("src", "")) for n in every):
            fix('no <script src="runtime.js"> at the end of <body> — copy the deck skeleton exactly (LAYOUTS.md)')
    for n in every:
        if n.tag not in ("style", "script") or "data-deck" in n.attrs:
            continue
        if skel and " ".join(n.text().split()) in skel:
            continue
        if n.tag == "style" and not {"id", "data-theme"} & set(n.attrs):
            fix("a <style> block without data-deck — decks carry no CSS of their own (SKILL.md §10)")
        if n.tag == "script" and "src" not in n.attrs:
            fix("an inline <script> without data-deck — decks carry no JavaScript of their own (SKILL.md §10)")
    css = ""
    for h in local:
        f = folder / re.sub(r"\?.*$", "", h)
        if f.is_file():
            css += f.read_text(encoding="utf-8", errors="ignore")

    slides = [n for n in deck.kids if isinstance(n, Node) and n.tag == "section" and "slide" in n.cls]
    kind = lambda s: next((c[7:] for c in s.cls if c.startswith("slide--")), "?")
    kinds = [kind(s) for s in slides]
    brief = next((n.attrs.get("content", "") for n in every
                  if n.tag == "meta" and n.attrs.get("name") == "slaydy-brief"), "")
    tier = (re.search(r"tier=(\w+)", brief) or [None, None])[1]
    staged = tier in ("polished", "bespoke")
    if not brief:
        check('no <meta name="slaydy-brief"> in <head> — the tier and tone are lost for the next revision')

    for i, (s, k) in enumerate(zip(slides, kinds), 1):
        at = f"slide {i} ({k})"
        if k in ("placeholder", "blank"):
            continue
        if css and f".slide--{k}" not in css:
            fix(f"{at}: no such layout in this deck's stylesheets — use one from LAYOUTS.md")
            continue
        inside = list(s.walk(_ignored))
        by_cls = lambda c: [n for n in inside if c in n.cls]
        by_tag = lambda *t: [n for n in inside if n.tag in t]

        def cap(nodes, limit, what, unit="word"):
            for n in nodes:
                size = len(n.text(_ignored).strip()) if unit == "character" else words(n)
                if size > limit:
                    quote = " ".join(n.text(_ignored).split())
                    quote = quote if len(quote) <= 44 else quote[:42] + "…"
                    fix(f'{at}: {what} "{quote}" is {plural(size, unit)}, limit {limit}')

        def count(nodes, lo, hi, what):
            if not lo <= len(nodes) <= hi:
                want = str(lo) if lo == hi else f"{lo}–{hi}"
                fix(f"{at}: {plural(len(nodes), what)}, the layout takes {want}")

        def unit(what):
            """The layout's repeated unit, counted. None of the stock class at all
            usually means the install marks this layout up its own way, which is
            its right: say how to declare it instead of asking for a rebuild."""
            c, lo, hi = units[k]
            nodes = by_cls(c)
            if not nodes and k not in cfg.get("units", {}):
                check(f"{at}: no .{c} inside it, so nothing was counted — if this install marks up "
                      f"{k} its own way, name the class under \"units\" in lint.json (CUSTOMIZING.md)")
            else:
                count(nodes, lo, hi, what)
            return nodes

        if k not in skip:
            heads = [n for n in inside if n.tag in ("h1", "h2") or (k == "callout-full" and n.tag == "h3")]
            if k in HEADLINE:
                cap(heads[:1], HEADLINE[k], "headline")
            cap(by_cls("lead"), 20, "lead")
            items = by_tag("li")
            nums = by_cls("stat__num")
            if k == "bullets":
                count(items, 1, 5, "item"); cap(items, 14, "item")
            elif k == "agenda":
                count(items, 1, 10, "item"); cap(by_cls("t") or items, 6, "item")
            elif k == "cards":
                unit("card"); cap(by_cls("h3"), 4, "card title"); cap(by_cls("body"), 25, "card body")
            elif k == "bento":
                unit("cell"); cap(by_cls("h3"), 3, "cell title"); cap(by_cls("body"), 14, "cell body")
                cap(nums, 6, "number", "character")
            elif k == "stats":
                unit("figure"); cap(nums, 6, "number", "character"); cap(by_cls("body"), 12, "stat body")
            elif k == "number":
                cap(nums, 7, "number", "character")
            elif k == "compare":
                cols = unit("column")
                cap(by_cls("h3"), 3, "column title"); cap(items, 10, "item")
                for c in cols:
                    n_items = [n for n in c.walk(_ignored) if n.tag == "li"]
                    if len(n_items) > 4:
                        fix(f"{at}: a column has {len(n_items)} items, limit 4")
            elif k == "table":
                rows = by_tag("tr")
                body_rows = [r for r in rows if r.parent and r.parent.tag == "tbody"]
                widest = max((len([c for c in r.kids if isinstance(c, Node)]) for r in rows), default=0)
                if widest > 5:
                    fix(f"{at}: {widest} columns, limit 5")
                if len(body_rows) > 6:
                    fix(f"{at}: {len(body_rows)} body rows, limit 6")
                cap(by_tag("td"), 6, "cell"); cap(by_tag("th"), 3, "header")
            elif k == "timeline":
                unit("step"); cap(by_cls("caption"), 3, "step caption")
                cap(by_cls("h3"), 3, "step title"); cap(by_cls("body"), 8, "step body")
            elif k in ("callout", "callout-full"):
                pins = by_cls("pin")
                if len(pins) > (6 if k == "callout" else 5):
                    fix(f"{at}: {len(pins)} pins, limit {6 if k == 'callout' else 5}")
                if len(pins) != len(items):
                    fix(f"{at}: {plural(len(pins), 'pin')} but {plural(len(items), 'note')} — they pair by order")
                cap(items, 12 if k == "callout" else 10, "note")
            elif k == "split":
                body = by_cls("split__body")
                total = sum(words(p) for b in body for p in b.walk(_ignored) if p.tag == "p")
                if total > 60:
                    fix(f"{at}: body is {total} words, limit 60")
            elif k == "quote":
                cap(by_tag("blockquote"), 30, "quotation"); cap(by_tag("figcaption"), 12, "attribution")
            elif k == "image":
                cap(by_cls("credit"), 12, "credit")
            elif k == "gallery":
                count([n for g in by_cls("gallery") for n in g.kids if isinstance(n, Node) and n.tag == "figure"], 2, 4, "image")
            elif k == "code":
                for pre in by_tag("pre"):
                    lines = pre.text().strip("\n").split("\n")
                    if len(lines) > 14:
                        fix(f"{at}: {len(lines)} lines of code, limit 14")
                    if max(map(len, lines), default=0) > 60:
                        fix(f"{at}: a code line is {max(map(len, lines))} characters, limit 60")

        for n in inside:
            if "style" in n.attrs and "pin" not in n.cls:
                # a custom property is a value handed to a layout, not styling; a CSS property
                # or a theme token set inline is the deck restyling itself
                props = [d.split(":", 1)[0].strip() for d in n.attrs["style"].split(";") if d.strip()]
                css_props = [p for p in props if not p.startswith("--")]
                tokens = [p for p in props if p in THEME_TOKENS]
                undeclared = [p for p in props if p.startswith("--") and p not in THEME_TOKENS and p not in allowed_props]
                if css_props:
                    fix(f"{at}: inline style ({css_props[0]}) on <{n.tag}> — only a callout .pin may carry one (SKILL.md §10)")
                elif tokens:
                    fix(f"{at}: the theme token {tokens[0]} set inline on <{n.tag}> — a deck never restyles the theme (SKILL.md §10)")
                elif undeclared:
                    check(f"{at}: {', '.join(undeclared)} set inline on <{n.tag}> — leave it if this install's layout reads it "
                          f"(and name it under \"inline_properties\" in lint.json); remove it if you made it up")
            if {"meta", "eyebrow", "chip", "caption"} & set(n.cls) and SEPARATOR.search(n.text(_ignored).strip()):
                fix(f'{at}: a typed separator in "{" ".join(n.text(_ignored).split())[:40]}" — '
                    f"use bare <span>s in .meta, or reword (SKILL.md §10)")
            if n.tag == "img":
                src = n.attrs.get("src", "")
                if src.startswith("data:"):
                    fix(f"{at}: a base64 image in the folder deck — images are files with relative paths")
                elif is_rel(src) and not (folder / src).is_file():
                    fix(f"{at}: image {src} does not exist — use a real file or leave the slot empty")

        if staged:
            notes = [n for n in s.walk() if n.tag == "aside" and "notes" in n.cls and n.text().strip()]
            if not notes and (tier == "bespoke" or k not in ("title", "section", "end", "image")):
                fix(f"{at}: no speaker notes — the {tier} tier has them on every "
                    f"{'slide' if tier == 'bespoke' else 'content slide'}")
            if k == "agenda" and any("data-reveal" in n.attrs for n in inside):
                fix(f"{at}: data-reveal on an agenda — never")
            want = REVEALS.get(k)
            if want and not any("data-reveal" in n.attrs for n in inside if n.tag in want or set(want) & set(n.cls)):
                check(f"{at}: no data-reveal on its list or grid — the {tier} tier reveals them, "
                      f"unless the slide must be read at a glance")
            if k != "bento" and any("data-animate" not in n.attrs and re.search(r"\d", n.text()) for n in nums):
                check(f'{at}: a number without data-animate="count" — the {tier} tier counts stats up')
            if k == "section" and tier == "polished" and s.attrs.get("data-transition") != "wipe":
                check(f'{at}: no data-transition="wipe" — the polished tier wipes into section dividers')

    # the deck as a whole
    n = len(slides)
    real = [k for k in kinds if k not in ("placeholder", "blank")]
    if real and real[0] != "title":
        fix(f"the deck opens with a {real[0]} slide — open with slide--title")
    if real and real[-1] != "end":
        fix(f"the deck closes with a {real[-1]} slide — close with slide--end")
    if n > 40:
        fix(f"{n} slides — cap is 40")
    for i, (a, b) in enumerate(zip(kinds, kinds[1:]), 1):
        if a == b == "bullets":
            fix(f"slides {i} and {i + 1} are both bullets — vary the layout (bento, compare, timeline)")
    content = [k for k in kinds if k not in ("title", "agenda", "section", "end")]
    if "agenda" in kinds and len(content) <= 8:
        check(f"an agenda for {plural(len(content), 'content slide')} — add one only above 8")
    dividers = [i for i, k in enumerate(kinds) if k == "section"]
    for d, nxt in zip(dividers, dividers[1:] + [n]):
        group = [k for k in kinds[d + 1:nxt] if k != "end"]
        if len(group) < 4:
            check(f"slide {d + 1} (section) opens a group of {plural(len(group), 'slide')} — "
                  f"a divider opens 4–7 content slides; merge the group or drop the divider")
    for k in ("stats", "number", "quote"):
        if kinds.count(k) > max(1, math.ceil(n / 10)):
            fix(f"{kinds.count(k)} {k} slides in {n} — at most one per 10 slides")
    return out


def run_lint(html: str, src: Path) -> int:
    """Lint and print; returns how many findings are 'fix'."""
    if lint_config().get("enabled") is False:
        print("lint: off for this install (lint.json)")
        return 0
    return report(lint(html, src.parent), src)


def report(findings, src: Path) -> int:
    """Print the findings; returns how many are 'fix'."""
    fixes = sum(1 for lvl, _ in findings if lvl == "fix")
    if not findings:
        print(f"lint: clean — {src.name}")
        return 0
    print(f"lint: {fixes} to fix, {len(findings) - fixes} to check — {src.name}")
    for lvl, msg in sorted(findings, key=lambda f: f[0] != "fix"):
        print(f"  {lvl:<5}  {msg}")
    if fixes:
        print('Fix every "fix" line in the deck (cut words or split the slide, never restyle) and run\n'
              "this again until none remain. In a revision, slides the user wrote are theirs: leave those.")
    return fixes



def deck_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", m.group(1)).strip() if m else ""
    return name or "deck"


# what a hook adds is fenced, so --explode can take it back out and a rebuild
# does not carry it twice
HOOK_OPEN, HOOK_CLOSE = "/* slaydy-hook */", "/* /slaydy-hook */"
HOOKED = re.compile(re.escape(HOOK_OPEN) + r"[\s\S]*?" + re.escape(HOOK_CLOSE) + r"\n?")


def run_hook(folder: Path, html: str) -> tuple[str, str]:
    """The export's one extension point, the Python twin of slaydy:serialize.

    A fork may ship standalone_hook.py beside this script (or one folder down,
    brand/standalone_hook.py) defining

        def hook(folder: Path, html: str) -> str | dict

    It is called once per build with the deck folder and the deck's markup and
    returns JavaScript to run before the runtime — typically the assets a
    brand script would otherwise fetch at display time, assigned to a global
    it reads — or {"js": ..., "css": ...} to add a stylesheet as well. The
    hook is looked for next to this script only, never in the deck folder: a
    deck is content, and content must not get to run code. A hook that raises
    stops the build; a deck silently missing its brand assets is worse."""
    here = Path(__file__).resolve().parent
    found = sorted(f for f in [here / "standalone_hook.py", *here.glob("*/standalone_hook.py")] if f.is_file())
    if not found:
        return "", ""
    spec = importlib.util.spec_from_file_location("standalone_hook", found[0])
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        got = mod.hook(folder, html)
    except Exception as e:
        sys.exit(f"error: {found[0]} failed — {type(e).__name__}: {e}")
    got = got if isinstance(got, dict) else {"js": got or ""}
    fence = lambda t: f"{HOOK_OPEN}\n{t.strip()}\n{HOOK_CLOSE}" if t and t.strip() else ""
    return fence(got.get("css", "")), fence(got.get("js", ""))


def build(deck_path: Path, out_path: Path) -> None:
    folder = deck_path.parent
    html = deck_path.read_text(encoding="utf-8")
    check_deck_blocks(html)
    hook_css, hook_js = run_hook(folder, html)
    css_parts, js_parts = [], []
    theme_blocks: list[tuple[str, str]] = []
    active_name = {"v": None}
    themes_m = re.search(r'data-themes="([^"]*)"', html)
    theme_names = themes_m.group(1).split() if themes_m else []

    def take_link(m):
        tag = m.group(0)
        if 'rel="stylesheet"' not in tag:
            return tag
        href = re.search(r'href="([^"]+)"', tag)
        if not href or not is_rel(href.group(1)):
            return tag
        sheet = folder / href.group(1)
        if 'id="theme"' in tag:
            # themes travel with the file (mirrors the runtime's inlineAssets):
            # every declared theme becomes its own <style data-theme> block,
            # only the active one enabled — cycleTheme flips `media`
            active = re.search(r"([^/]+)\.css$", href.group(1))
            active_name["v"] = active.group(1) if active else None
            names = list(dict.fromkeys(theme_names or [active_name["v"]]))
            for name in filter(None, names):
                f = folder / "themes" / f"{name}.css"
                if f.is_file():
                    theme_blocks.append((name, inline_css_urls(read_asset(f, min_css), f.parent)))
            if active_name["v"] and active_name["v"] not in [n for n, _ in theme_blocks] and sheet.is_file():
                theme_blocks.append((active_name["v"], inline_css_urls(read_asset(sheet, min_css), sheet.parent)))
            return ""
        css_parts.append(inline_css_urls(read_asset(sheet, min_css), sheet.parent))
        return ""

    # three sequences can derail the HTML parser's script-data states
    # (</script ends it, <!-- followed by <script swallows the real
    # close tag); each escape is the same text inside a string, regex
    # or comment, and \u0073 is a valid identifier escape.
    safe_js = lambda js: (js.replace("</script", "<\\/script")
                            .replace("<!--", "<\\u0021--")
                            .replace("<script", "<\\u0073cript"))

    def take_script(m):
        src = m.group(1)
        if not is_rel(src):
            return m.group(0)
        js_parts.append(safe_js(read_asset(folder / src, min_js)))
        return ""

    def inline_img(m):
        src = m.group(1)
        if not is_rel(src):
            return m.group(0)
        return m.group(0).replace(f'src="{src}"', f'src="{data_uri(folder / src)}"', 1)

    html = re.sub(r"<link[^>]*>\n?", take_link, html)
    html = re.sub(r'<script src="([^"]+)"></script>\n?', take_script, html)
    html = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', inline_img, html)
    if hook_js:
        js_parts.insert(0, safe_js(hook_js))      # before the runtime and the brand's own scripts
    if hook_css:
        css_parts.append(hook_css)

    logo = re.search(r'data-logo="([^"]+)"', html)
    if logo and is_rel(logo.group(1)):
        html = html.replace(logo.group(0), f'data-logo="{data_uri(folder / logo.group(1))}"')

    if len(theme_blocks) < 2:                                   # one theme baked in — nothing to cycle
        html = re.sub(r'\s*data-themes="[^"]*"', "", html)      # before the JS bundle lands
    html = html.replace("<html", "<html data-standalone", 1)
    html = html.replace(
        "</head>", '<style id="standalone-guard">body{visibility:hidden}</style>\n</head>', 1
    )
    disabled = ' media="not all"'
    theme_css = "".join(
        f'<style data-theme="{n}"{"" if n == active_name["v"] else disabled}>\n{c}\n</style>\n'
        for n, c in theme_blocks
    )
    bundle = (
        "<style>\n" + "\n".join(css_parts) + "\nbody{visibility:visible}\n</style>\n"
        + theme_css
        + "<script>\n" + "\n".join(js_parts) + "\n</script>\n"
    )
    html = html.replace("</body>", bundle + "</body>", 1)

    out_path.write_text(html, encoding="utf-8")
    print(f"{out_path}  ({out_path.stat().st_size // 1024} KB)")


# guess_extension says ".jpe" for jpeg and similar oddities — pin the common ones
EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/svg+xml": ".svg",
       "image/webp": ".webp", "image/gif": ".gif", "image/avif": ".avif"}


def store_asset(imgdir: Path, uri: str) -> str:
    """Write one data: URI out as a file in images/, returning its relative
    path. A byte-identical file already there is reused, so exploding a deck
    whose images came from this folder restores the original names."""
    header, _, payload = uri.partition(",")
    mime = header[5:].split(";")[0]
    data = base64.b64decode(payload) if header.endswith(";base64") else unquote_to_bytes(payload)
    imgdir.mkdir(exist_ok=True)
    for f in sorted(imgdir.iterdir()):
        if f.is_file() and f.stat().st_size == len(data) and f.read_bytes() == data:
            return f"images/{f.name}"
    name = f"asset-{hashlib.sha1(data).hexdigest()[:8]}{EXT.get(mime) or mimetypes.guess_extension(mime) or '.bin'}"
    (imgdir / name).write_bytes(data)
    return f"images/{name}"


def explode(src: Path, html: str, out: Path) -> None:
    folder = src.parent
    # the appended bundle: one <style> ending in the visibility marker, then
    # any embedded theme blocks (<style data-theme>, added when the deck
    # declares several themes), then one <script> holding the runtime (its
    # own </script instances are escaped as <\/script, so the first real
    # close tag ends it; <!-- and <script are escaped too, left as is in
    # bundle.js since they mean the same text)
    m = re.search(
        r"<style>([\s\S]*?body\{visibility:visible\}[\s\S]*?)</style>\s*"
        r"((?:<style data-theme=[\s\S]*?</style>\s*)*)"
        r"<script>([\s\S]*?)</script>\s*(?=</body>)", html)
    if not m:
        sys.exit("no inlined bundle found — is this a standalone (data-standalone) deck?")
    # what a hook added is rebuilt by the hook, not carried in the bundle
    css = HOOKED.sub("", m.group(1)).replace("body{visibility:visible}", "").strip() + "\n"
    js = HOOKED.sub("", m.group(3)).replace("<\\/script", "</script").strip() + "\n"
    (folder / "bundle.css").write_text(css, encoding="utf-8")
    (folder / "bundle.js").write_text(js, encoding="utf-8")
    active = None
    for tm in re.finditer(r'<style data-theme="([^"]+)"( media="not all")?>\n?([\s\S]*?)\n?</style>', m.group(2)):
        name, disabled, theme_css = tm.group(1), tm.group(2), tm.group(3)
        (folder / "themes").mkdir(exist_ok=True)
        (folder / "themes" / f"{name}.css").write_text(theme_css.strip() + "\n", encoding="utf-8")
        if not disabled:
            active = name
    html = html[:m.start()] + '<script src="bundle.js"></script>\n' + html[m.end():]
    html = re.sub(r'\s*<style id="standalone-guard">[^<]*</style>', "", html)
    theme_link = f'<link rel="stylesheet" href="themes/{active}.css" id="theme">\n' if active else ""
    html = html.replace("</head>", '<link rel="stylesheet" href="bundle.css">\n' + theme_link + "</head>", 1)
    html = re.sub(r'<html([^>]*?) data-standalone(="")?', r"<html\1", html, count=1)
    imgdir = folder / "images"
    count = [0]

    def swap(mm):
        count[0] += 1
        return mm.group(0).replace(mm.group(1), store_asset(imgdir, mm.group(1)), 1)

    html = re.sub(r'src="(data:[^"]+)"', swap, html)
    html = re.sub(r'data-logo="(data:[^"]+)"', swap, html)
    out.write_text(html, encoding="utf-8")
    print(f"{out}  ({out.stat().st_size // 1024} KB) + bundle.css + bundle.js, {count[0]} image ref(s) → images/")


if __name__ == "__main__":
    args = sys.argv[1:]
    no_lint = "--no-lint" in args
    args = [a for a in args if a != "--no-lint"]
    mode = args[0][2:] if args and args[0] in ("--explode", "--lint") else "build"
    if mode != "build":
        args = args[1:]
    if not args or len(args) > 2 or any(a.startswith("-") for a in args):
        sys.exit(__doc__.strip())
    src = Path(args[0])
    if not src.is_file():
        sys.exit(f"not found: {src}")
    html = src.read_text(encoding="utf-8")
    if mode == "lint":
        try:
            sys.exit(1 if run_lint(html, src) else 0)
        except ValueError as e:
            sys.exit(f"error: {e}")
    if mode == "explode":
        explode(src, html, Path(args[1]) if len(args) > 1 else src.with_name("deck-work.html"))
    else:
        out = Path(args[1]) if len(args) > 1 else src.with_name(deck_title(html) + ".html")
        if out.resolve() == src.resolve():
            sys.exit("output would overwrite the input — pass a different out.html")
        build(src, out)
        try:                                   # advice only: a lint bug must never fail a build
            no_lint or run_lint(html, src)
        except Exception as e:
            print(f"lint: skipped ({type(e).__name__}: {e})")
