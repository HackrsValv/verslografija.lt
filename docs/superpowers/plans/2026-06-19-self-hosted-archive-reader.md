# Self-Hosted Archive Reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render an archive index and one page per post on `verslografija.lt` from the Buttondown API, removing the dependency on Buttondown's hosted archive template.

**Architecture:** Split the existing single-file `build.py` into focused modules (`posts.py` fetch/prepare, `render.py` body→article HTML, `pages.py` templates) with `build.py` as orchestrator. Render each post's API `body` (markdown via mistune, or pass-through for Buttondown "fancy" HTML), wrap it in a pulp-press shell with `lang="lt"`, a single `<h1>`, lazy images, and a self-referential canonical. Output static files to the repo root for GitHub Pages.

**Tech Stack:** Python 3.12 (stdlib `urllib`/`html.parser`), `mistune` (markdown), `pytest` (tests). No JS, no build framework.

## Global Constraints

- Repo: `HackrsValv/verslografija.lt`, root-layout (files at repo root, NOT under `site/`). GitHub Pages serves from root; custom domain `verslografija.lt`.
- `build.py` runs in CI (`.github/workflows/build-landing.yml`) with `BUTTONDOWN_API_KEY` env secret; locally it falls back to `--key-file`.
- Post pages: `<html lang="lt">`, exactly one `<h1>` (the post title).
- URL scheme: `/archive/<slug>/` (mirrors Buttondown for phase-2 redirects). Output file: `archive/<slug>/index.html`.
- Cover images hot-linked from `assets.buttondown.email` (do not download).
- Cover image alt text: `"<post title> — iliustracija"` (em-rule is the literal character ` — `). Never the literal `cover`.
- Sanitizer tag allowlist: `a, p, h2, h3, h4, blockquote, em, strong, ul, ol, li, figure, figcaption, img, sup, hr, code, pre, br`. Attribute allowlist: `href, src, alt, id`.
- Markdown renderer: `mistune`. HTML sanitizer: hand-rolled on `html.parser` (no `bleach`).
- Build policy (andon): any post with an empty body or that raises during render fails the whole build, naming the slug. Never emit a broken page.
- Site base URL constant: `https://verslografija.lt` (no trailing slash).
- Reuse existing CSS tokens in `style.css` (`--body`, `--display`, `--mono`, `--accent`, `--text`, `--muted`, `--bg`, `--paper`, `--width`). Do not introduce new color literals.

---

## File Structure

| File | Responsibility |
|---|---|
| `posts.py` (create) | API fetch (paginated, all sent) + `prepare_posts` → post dicts |
| `render.py` (create) | `article(body)` → sanitized post-processed article HTML |
| `pages.py` (create) | `landing(posts)`, `archive_index(posts)`, `post_page(post, prev, nxt)` → HTML strings |
| `build.py` (rewrite) | Orchestrate: fetch → render → write files + `sitemap.xml` |
| `style.css` (modify) | Append `.post-*` and `.archive-*` rules |
| `.github/workflows/build-landing.yml` (modify) | Install deps; commit `index.html`, `archive/`, `sitemap.xml` |
| `requirements.txt` (create) | `mistune`, `pytest` |
| `tests/conftest.py` (create) | Shared fixtures (sample emails) |
| `tests/fixtures/emails_sample.json` (create) | 2 recorded emails: one plain-markdown, one fancy-HTML |
| `tests/test_posts.py` (create) | `prepare_posts` behavior |
| `tests/test_render.py` (create) | render pipeline behavior |
| `tests/test_pages.py` (create) | template invariants |
| `tests/test_build.py` (create) | end-to-end file generation against fixture |

---

## Task 1: Project scaffolding (deps, test dir, fixtures)

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py` (empty)
- Create: `tests/fixtures/emails_sample.json`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: pytest fixture `sample_emails` → `list[dict]` of raw Buttondown email objects (2 items: keys `slug, subject, publish_date, description, image, body, status`). Fixture `plain_email` and `fancy_email` → the individual dicts.

- [ ] **Step 1: Create `requirements.txt`**

```
mistune>=3.0,<4.0
pytest>=8.0
```

- [ ] **Step 2: Create the empty test package marker**

```bash
mkdir -p tests/fixtures
: > tests/__init__.py
```

- [ ] **Step 3: Create `tests/fixtures/emails_sample.json`**

```json
[
  {
    "slug": "pasaku-taskai",
    "subject": "Pasakų taškai",
    "publish_date": "2026-06-05T20:00:00.000000Z",
    "description": "Apie tai, kodėl istorijų taškai dekoreliuoja nuo laiko.",
    "image": "https://assets.buttondown.email/images/cover-pt.png",
    "status": "sent",
    "body": "![cover](https://assets.buttondown.email/images/cover-pt.png)\n\nProfesorius iškelia ranką.\n\n## Pirmas skyrius\n\nTekstas su [nuoroda į kitą įrašą](https://visa.verslografija.lt/archive/story-points/) viduje.\n\n> Citata čia.\n\nIšnaša.[^1]\n\n[^1]: Išnašos tekstas."
  },
  {
    "slug": "ziurek-ka-darau",
    "subject": "Žiūrėk ką darau, ne ką sakau",
    "publish_date": "2025-07-24T20:37:06.000000Z",
    "description": "Apie atotrūkį tarp deklaracijų ir veiksmų.",
    "image": "https://assets.buttondown.email/images/cover-zk.png",
    "status": "sent",
    "body": "<!-- buttondown-editor-mode: fancy --><figure><img src=\"https://assets.buttondown.email/images/cover-zk.png\" alt=\"cover\"></figure><p>Pirmas sakinys.</p><h2>Skyrius</h2><p>Antras <strong>sakinys</strong> su <a href=\"https://visa.verslografija.lt/archive/story-points/\">nuoroda</a>.</p><figure><img src=\"https://assets.buttondown.email/images/inline.png\" alt=\"diagrama\"><figcaption>Paaiškinimas</figcaption></figure>"
  }
]
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_emails():
    return json.loads((FIXTURES / "emails_sample.json").read_text())


@pytest.fixture
def plain_email(sample_emails):
    return next(e for e in sample_emails if e["slug"] == "pasaku-taskai")


@pytest.fixture
def fancy_email(sample_emails):
    return next(e for e in sample_emails if e["slug"] == "ziurek-ka-darau")
```

- [ ] **Step 5: Install deps and verify pytest collects nothing yet**

Run: `python -m pip install -r requirements.txt && python -m pytest -q`
Expected: `no tests ran` (exit code 5) — confirms pytest is installed and the package imports.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt tests/__init__.py tests/fixtures/emails_sample.json tests/conftest.py
git commit -m "chore: add test scaffolding and deps for archive reader"
```

---

## Task 2: `posts.py` — fetch and prepare

**Files:**
- Create: `posts.py`
- Create: `tests/test_posts.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `SITE_URL = "https://verslografija.lt"` (str constant).
  - `fetch_emails(api_key: str) -> list[dict]` — all sent emails, newest first (paginated).
  - `prepare_posts(emails: list[dict]) -> list[dict]` — each: `{"slug": str, "title": str, "date": str (YYYY-MM-DD), "excerpt": str, "image": str, "body": str, "url": str}`. No cap. Skips emails with no slug. Order preserved (newest first).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_posts.py
from posts import prepare_posts, SITE_URL


def test_prepare_posts_maps_fields_and_builds_url(sample_emails):
    posts = prepare_posts(sample_emails)
    assert len(posts) == 2
    p = posts[0]
    assert p["slug"] == "pasaku-taskai"
    assert p["title"] == "Pasakų taškai"
    assert p["date"] == "2026-06-05"
    assert p["url"] == f"{SITE_URL}/archive/pasaku-taskai/"
    assert p["image"].startswith("https://assets.buttondown.email/")
    assert p["body"]


def test_prepare_posts_skips_slugless(sample_emails):
    emails = sample_emails + [{"slug": "", "subject": "x", "body": "y", "status": "sent"}]
    posts = prepare_posts(emails)
    assert all(p["slug"] for p in posts)
    assert len(posts) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_posts.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'posts'`.

- [ ] **Step 3: Write minimal implementation**

```python
# posts.py
"""Fetch published posts from the Buttondown API and normalize them."""

import json
import urllib.request

API_BASE = "https://api.buttondown.email/v1/emails"
SITE_URL = "https://verslografija.lt"


def fetch_emails(api_key):
    """All sent emails, newest first (follows pagination)."""
    emails = []
    page = 1
    while True:
        url = f"{API_BASE}?page={page}&status=sent&ordering=-publish_date"
        req = urllib.request.Request(url, headers={"Authorization": f"Token {api_key}"})
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
        emails.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return emails


def prepare_posts(emails):
    """Normalize raw email objects into post dicts. No cap; skips slugless."""
    posts = []
    for e in emails:
        slug = (e.get("slug") or "").strip()
        if not slug:
            continue
        posts.append(
            {
                "slug": slug,
                "title": (e.get("subject") or "").strip(),
                "date": (e.get("publish_date") or "")[:10],
                "excerpt": (e.get("description") or "").strip(),
                "image": e.get("image") or "",
                "body": e.get("body") or "",
                "url": f"{SITE_URL}/archive/{slug}/",
            }
        )
    return posts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_posts.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add posts.py tests/test_posts.py
git commit -m "feat: posts module — fetch all sent emails and normalize"
```

---

## Task 3: `render.py` — markdown/HTML to clean article body

**Files:**
- Create: `render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `mistune`.
- Produces:
  - `to_html(body: str) -> str` — strip editor-mode comment; markdown→HTML for plain, pass-through for fancy.
  - `sanitize(html: str) -> str` — allowlist tags/attrs, unwrap unknown tags, drop unknown attrs.
  - `article(body: str) -> str` — full pipeline: `to_html` → strip leading cover → `sanitize` → lazy-load inline images → rewrite `visa.` links. Returns article HTML with no `<h1>` and no leading cover image.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_render.py
import render


def test_plain_markdown_renders_and_keeps_no_cover(plain_email):
    html = render.article(plain_email["body"])
    assert "<h2>" in html and "Pirmas skyrius" in html
    # leading cover image removed
    assert "cover-pt.png" not in html
    # no h1 in article body
    assert "<h1" not in html


def test_fancy_html_passes_through_without_directive(fancy_email):
    html = render.article(fancy_email["body"])
    assert "buttondown-editor-mode" not in html
    assert "<h2>" in html
    # leading cover figure removed, inline figure kept
    assert "cover-zk.png" not in html
    assert "inline.png" in html


def test_inline_images_get_lazy_loading(fancy_email):
    html = render.article(fancy_email["body"])
    assert 'loading="lazy"' in html
    assert 'decoding="async"' in html


def test_visa_links_rewritten_local(plain_email):
    html = render.article(plain_email["body"])
    assert "https://visa.verslografija.lt/archive/story-points/" not in html
    assert "/archive/story-points/" in html


def test_sanitize_unwraps_unknown_tags_and_drops_attrs():
    dirty = '<div onclick="x"><script>bad()</script><p style="x" id="ok">hi</p></div>'
    clean = render.sanitize(dirty)
    assert "<div" not in clean and "<script" not in clean
    assert "onclick" not in clean and "style=" not in clean
    assert 'id="ok"' in clean and ">hi<" in clean
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_render.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'render'`.

- [ ] **Step 3: Write the implementation**

```python
# render.py
"""Convert a Buttondown email body into a clean, self-hosted article body."""

import re
from html.parser import HTMLParser

import mistune

_EDITOR_MODE = re.compile(r"<!--\s*buttondown-editor-mode:[^>]*-->", re.IGNORECASE)
_VISA_LINK = re.compile(r"https://visa\.verslografija\.lt/archive/([^/\"')\s]+)/?")
_LEADING_FIGURE = re.compile(r"^\s*<figure\b[^>]*>.*?</figure>", re.IGNORECASE | re.DOTALL)
_LEADING_IMG = re.compile(r"^\s*(?:<p\b[^>]*>\s*)?<img\b[^>]*>(?:\s*</p>)?", re.IGNORECASE)
_IMG_OPEN = re.compile(r"<img\b", re.IGNORECASE)

ALLOWED_TAGS = {
    "a", "p", "h2", "h3", "h4", "blockquote", "em", "strong",
    "ul", "ol", "li", "figure", "figcaption", "img", "sup", "hr", "code", "pre", "br",
}
ALLOWED_ATTRS = {"href", "src", "alt", "id"}
VOID_TAGS = {"img", "hr", "br"}

_md = mistune.create_markdown(escape=False)


def to_html(body):
    """Strip the editor-mode directive; markdown->HTML for plain, pass-through for fancy."""
    stripped = _EDITOR_MODE.sub("", body).strip()
    if "buttondown-editor-mode: fancy" in body:
        return stripped
    return _md(stripped)


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        kept = "".join(
            f' {k}="{v}"' for k, v in attrs if k in ALLOWED_ATTRS and v is not None
        )
        slash = "" if tag not in VOID_TAGS else ""
        self.out.append(f"<{tag}{kept}{slash}>")

    def handle_startendtag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        kept = "".join(
            f' {k}="{v}"' for k, v in attrs if k in ALLOWED_ATTRS and v is not None
        )
        self.out.append(f"<{tag}{kept}>")

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.out.append(data)


def sanitize(html):
    """Keep only allowlisted tags/attrs; unwrap unknown tags (keep their text)."""
    p = _Sanitizer()
    p.feed(html)
    p.close()
    return "".join(p.out)


def _strip_leading_cover(html):
    html = html.lstrip()
    new = _LEADING_FIGURE.sub("", html, count=1)
    if new != html:
        return new.lstrip()
    return _LEADING_IMG.sub("", html, count=1).lstrip()


def _lazy_images(html):
    return _IMG_OPEN.sub('<img loading="lazy" decoding="async"', html)


def article(body):
    """Full pipeline -> clean article HTML (no leading cover, no h1)."""
    html = to_html(body)
    html = _strip_leading_cover(html)
    html = sanitize(html)
    html = _lazy_images(html)
    html = _VISA_LINK.sub(r"/archive/\1/", html)
    return html.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_render.py -q`
Expected: PASS (5 passed). If `test_sanitize_unwraps_unknown_tags_and_drops_attrs` fails on the `<script>` body text leaking, note: `html.parser` surfaces script text as data; assert only that the `<script>` tag is gone — the test already checks `"<script" not in clean`, which holds because tags are dropped.

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: render module — body to clean article HTML"
```

---

## Task 4: `pages.py` — post page template

**Files:**
- Create: `pages.py`
- Create: `tests/test_pages.py`

**Interfaces:**
- Consumes: `render.article`.
- Produces: `post_page(post: dict, prev: dict | None, nxt: dict | None) -> str` — full HTML document. `prev`/`nxt` are post dicts (older/newer) or `None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pages.py
import pages


def _post(slug="pasaku-taskai", title="Pasakų taškai"):
    return {
        "slug": slug,
        "title": title,
        "date": "2026-06-05",
        "excerpt": "Santrauka.",
        "image": "https://assets.buttondown.email/images/cover-pt.png",
        "body": "![cover](https://assets.buttondown.email/images/cover-pt.png)\n\n## Skyrius\n\nTekstas.",
        "url": "https://verslografija.lt/archive/pasaku-taskai/",
    }


def test_post_page_is_lithuanian_single_h1_canonical():
    html = pages.post_page(_post(), prev=None, nxt=None)
    assert '<html lang="lt">' in html
    assert html.count("<h1") == 1
    assert 'rel="canonical" href="https://verslografija.lt/archive/pasaku-taskai/"' in html
    assert '<title>Pasakų taškai' in html


def test_post_page_cover_has_descriptive_alt():
    html = pages.post_page(_post(), prev=None, nxt=None)
    assert 'alt="Pasakų taškai — iliustracija"' in html
    assert 'alt="cover"' not in html


def test_post_page_prevnext_links():
    older = _post(slug="senas", title="Senas")
    newer = _post(slug="naujas", title="Naujas")
    html = pages.post_page(_post(), prev=older, nxt=newer)
    assert 'href="/archive/senas/"' in html
    assert 'href="/archive/naujas/"' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pages.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pages'`.

- [ ] **Step 3: Write the implementation**

```python
# pages.py
"""HTML page templates for the self-hosted site. Pure functions, no I/O."""

from html import escape

import render

SITE_URL = "https://verslografija.lt"


def _head(title, description, canonical, image):
    img_meta = ""
    if image:
        img_meta = (
            f'<meta property="og:image" content="{image}">\n'
            f'    <meta name="twitter:image" content="{image}">'
        )
    return f"""<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{escape(title)}">
    <meta property="og:description" content="{escape(description)}">
    <meta property="og:type" content="article">
    <meta property="og:locale" content="lt_LT">
    <meta property="og:url" content="{canonical}">
    {img_meta}
    <meta name="twitter:card" content="summary_large_image">
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <link rel="stylesheet" href="/style.css">
</head>"""


def _masthead():
    return """    <header class="post-masthead">
        <a href="/" class="post-masthead-logo" aria-label="Verslo Grafija">
            <img src="/assets/logo-verslografija.svg" alt="" width="40" height="40">
            <span>Verslo Grafija</span>
        </a>
    </header>"""


def _subscribe():
    return """    <section class="subscribe" id="prenumeruoti">
        <div class="subscribe-inner">
            <p class="subscribe-tagline">Visi kažką žiūrim, o kartais ir parašom</p>
            <form action="https://buttondown.com/api/emails/embed-subscribe/verslografija"
                  method="post" target="popupwindow" class="subscribe-form">
                <label for="bd-email" class="sr-only">El. paštas</label>
                <input type="email" name="email" id="bd-email" placeholder="El. paštas"
                       autocomplete="email" inputmode="email" autocapitalize="off"
                       autocorrect="off" spellcheck="false" maxlength="254"
                       aria-describedby="bd-note" required>
                <button type="submit">Prenumeruoti</button>
            </form>
            <p class="subscribe-note" id="bd-note">Šlamštas iš vidaus</p>
        </div>
    </section>"""


def _prevnext(prev, nxt):
    left = (
        f'<a class="post-nav-prev" href="/archive/{prev["slug"]}/">&larr; {escape(prev["title"])}</a>'
        if prev else "<span></span>"
    )
    right = (
        f'<a class="post-nav-next" href="/archive/{nxt["slug"]}/">{escape(nxt["title"])} &rarr;</a>'
        if nxt else "<span></span>"
    )
    return f'    <nav class="post-nav">\n        {left}\n        {right}\n    </nav>'


def post_page(post, prev, nxt):
    alt = f'{post["title"]} — iliustracija'
    cover = ""
    if post["image"]:
        cover = (
            f'<div class="post-cover"><img src="{post["image"]}" '
            f'alt="{escape(alt)}" loading="eager" decoding="async"></div>'
        )
    body_html = render.article(post["body"])
    head = _head(post["title"], post["excerpt"], post["url"], post["image"])
    return f"""<!DOCTYPE html>
<html lang="lt">
{head}
<body>
{_masthead()}
    <main>
        <article class="post">
            <span class="post-date">{post["date"]}</span>
            <h1 class="post-title">{escape(post["title"])}</h1>
            {cover}
            <div class="post-body">
{body_html}
            </div>
        </article>
{_prevnext(prev, nxt)}
{_subscribe()}
    </main>
    <footer class="footer">
        <div class="footer-inner">
            <a href="/archive/" class="footer-archive">Visas archyvas &rarr;</a>
            <p class="footer-copy">&copy; 2024&ndash;2026 Verslo Grafija</p>
        </div>
    </footer>
</body>
</html>"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pages.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add pages.py tests/test_pages.py
git commit -m "feat: pages module — post page template"
```

---

## Task 5: `pages.py` — archive index template

**Files:**
- Modify: `pages.py` (add `archive_index`)
- Modify: `tests/test_pages.py` (add tests)

**Interfaces:**
- Produces: `archive_index(posts: list[dict]) -> str` — full HTML document listing all posts newest-first, each linking to `/archive/<slug>/`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_pages.py
def test_archive_index_lists_all_posts_lt():
    posts = [_post(slug="a", title="Aaa"), _post(slug="b", title="Bbb")]
    html = pages.archive_index(posts)
    assert '<html lang="lt">' in html
    assert html.count("<h1") == 1  # page heading only
    assert 'href="/archive/a/"' in html and 'href="/archive/b/"' in html
    assert "Aaa" in html and "Bbb" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pages.py::test_archive_index_lists_all_posts_lt -q`
Expected: FAIL with `AttributeError: module 'pages' has no attribute 'archive_index'`.

- [ ] **Step 3: Write the implementation (append to `pages.py`)**

```python
def archive_index(posts):
    rows = "\n".join(
        f"""        <a class="archive-row" href="/archive/{p['slug']}/">
            <span class="archive-date">{p['date']}</span>
            <span class="archive-title">{escape(p['title'])}</span>
        </a>"""
        for p in posts
    )
    head = _head(
        "Archyvas — Verslo Grafija",
        "Visi Verslo Grafijos įrašai.",
        f"{SITE_URL}/archive/",
        "",
    )
    return f"""<!DOCTYPE html>
<html lang="lt">
{head}
<body>
{_masthead()}
    <main>
        <section class="archive">
            <h1 class="archive-heading">Archyvas</h1>
{rows}
        </section>
{_subscribe()}
    </main>
    <footer class="footer">
        <div class="footer-inner">
            <a href="/" class="footer-archive">&larr; Pradžia</a>
            <p class="footer-copy">&copy; 2024&ndash;2026 Verslo Grafija</p>
        </div>
    </footer>
</body>
</html>"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pages.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add pages.py tests/test_pages.py
git commit -m "feat: pages module — archive index template"
```

---

## Task 6: `pages.py` — landing template (port, links rewritten local)

**Files:**
- Modify: `pages.py` (add `landing`)
- Modify: `tests/test_pages.py` (add test)

**Interfaces:**
- Produces: `landing(posts: list[dict]) -> str` — the existing landing markup (featured + 3-card grid + subscribe), but featured/card links point to local `/archive/<slug>/` and the "Archyvas" nav link points to `/archive/`.

Reference: the current landing markup lives in `build.py:render_page`/`render_card` (the version on `main`). Port it verbatim into `landing()`, changing only:
1. Featured `<a href>` and card `<a href>` from the Buttondown `absolute_url` to `/archive/{slug}/`.
2. The masthead nav "Archyvas" link from `https://visa.verslografija.lt/archive/` to `/archive/`.
3. The footer "Visas archyvas" link likewise to `/archive/`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_pages.py
def test_landing_links_are_local():
    posts = [_post(slug=f"p{i}", title=f"T{i}") for i in range(4)]
    html = pages.landing(posts)
    assert "visa.verslografija.lt" not in html
    assert 'href="/archive/p0/"' in html      # featured
    assert 'href="/archive/"' in html          # nav + footer archive
    assert html.count("<h1") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pages.py::test_landing_links_are_local -q`
Expected: FAIL with `AttributeError: module 'pages' has no attribute 'landing'`.

- [ ] **Step 3: Write the implementation (append to `pages.py`)**

```python
def _land_card(post):
    cover = (
        f'<div class="card-image"><img src="{post["image"]}" '
        f'alt="{escape(post["title"])} — iliustracija" loading="lazy" decoding="async"></div>'
        if post["image"]
        else '<div class="card-image card-image--placeholder"><span class="card-image-v">V</span></div>'
    )
    return f"""                <a href="/archive/{post['slug']}/" class="card">
                    {cover}
                    <div class="card-content">
                        <span class="card-date">{post['date']}</span>
                        <h3 class="card-title">{escape(post['title'])}</h3>
                    </div>
                </a>"""


def landing(posts):
    featured = posts[0]
    grid = posts[1:4]
    f_alt = f'{featured["title"]} — iliustracija'
    if featured["image"]:
        f_img = (
            f'<div class="featured-image"><img src="{featured["image"]}" '
            f'alt="{escape(f_alt)}" loading="eager" decoding="async"></div>'
        )
    else:
        f_img = '<div class="featured-image featured-image--placeholder"><span class="card-image-v">V</span></div>'
    cards = "\n".join(_land_card(p) for p in grid)
    img_meta = ""
    if featured["image"]:
        img_meta = (
            f'<meta property="og:image" content="{featured["image"]}">\n'
            f'    <meta name="twitter:image" content="{featured["image"]}">'
        )
    return f"""<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verslo Grafija</title>
    <meta name="description" content="Stato tvorą atviroje pievoje. Optimizuoja procesą, kuris neturėjo egzistuoti. Cituoja eksperimentą, kurio nebuvo.">
    <meta property="og:title" content="Verslo Grafija">
    <meta property="og:description" content="Stato tvorą atviroje pievoje. Optimizuoja procesą, kuris neturėjo egzistuoti. Cituoja eksperimentą, kurio nebuvo.">
    {img_meta}
    <meta property="og:type" content="website">
    <meta property="og:locale" content="lt_LT">
    <meta property="og:url" content="https://verslografija.lt">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <header class="masthead">
        <div class="masthead-inner">
            <a href="/" class="masthead-logo" aria-label="Verslo Grafija">
                <img src="/assets/logo-verslografija.svg" alt="" width="64" height="64">
            </a>
            <h1 class="masthead-title">Verslo Grafija</h1>
            <p class="masthead-tagline">Visi kažką žiūrim, o kartais ir parašom</p>
            <nav class="masthead-nav">
                <a href="#naujausios">Naujausios</a>
                <a href="#prenumeruoti">Prenumeruoti</a>
                <a href="/archive/">Archyvas</a>
            </nav>
        </div>
    </header>
    <main>
        <section class="featured" id="naujausios">
            <a href="/archive/{featured['slug']}/" class="featured-link">
                {f_img}
                <div class="featured-content">
                    <span class="featured-date">{featured['date']}</span>
                    <h2 class="featured-title">{escape(featured['title'])}</h2>
                    <p class="featured-excerpt">{escape(featured['excerpt'])}</p>
                    <span class="featured-cta">Skaityti &rarr;</span>
                </div>
            </a>
        </section>
        <section class="post-grid">
            <h2 class="section-header">Šviežiausi įrašai</h2>
            <div class="grid">
{cards}
            </div>
        </section>
{_subscribe()}
    </main>
    <footer class="footer">
        <div class="footer-inner">
            <a href="/archive/" class="footer-archive">Visas archyvas &rarr;</a>
            <p class="footer-copy">&copy; 2024&ndash;2026 Verslo Grafija</p>
        </div>
    </footer>
</body>
</html>"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pages.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add pages.py tests/test_pages.py
git commit -m "feat: pages module — landing template with local links"
```

---

## Task 7: `style.css` — article and archive styles

**Files:**
- Modify: `style.css` (append a `=== POST + ARCHIVE ===` block before the `=== PRINT ===` section)

**Interfaces:** none (CSS). Verified visually in Task 10.

- [ ] **Step 1: Append the rules**

Insert immediately before the `/* === PRINT === */` comment in `style.css`:

```css
/* === POST + ARCHIVE === */

.post-masthead {
    max-width: var(--width);
    margin: 0 auto;
    padding: 1.5rem;
    border-bottom: 2px solid var(--rule);
}

.post-masthead-logo {
    display: inline-flex;
    align-items: center;
    gap: 0.625rem;
    font-family: var(--display);
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.9rem;
}

.post {
    max-width: var(--width);
    margin: 2.5rem auto 0;
    padding: 0 1.5rem;
}

.post-date {
    font-family: var(--mono);
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--muted);
}

.post-title {
    font-family: var(--display);
    font-size: 2.5rem;
    font-weight: 800;
    text-transform: uppercase;
    line-height: 1.05;
    letter-spacing: 0.01em;
    margin: 0.5rem 0 1.5rem;
    overflow-wrap: break-word;
    hyphens: auto;
}

.post-cover {
    aspect-ratio: 2 / 1;
    overflow: hidden;
    background: var(--paper);
    border: 3px solid var(--rule);
    margin-bottom: 2rem;
}

.post-cover img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: contrast(1.1) grayscale(0.05);
}

.post-body {
    max-width: 68ch;
    font-size: 1.0625rem;
    line-height: 1.75;
}

.post-body p { margin: 0 0 1.4rem; }

.post-body h2 {
    font-family: var(--display);
    font-size: 1.5rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    margin: 2.5rem 0 1rem;
}

.post-body h3 {
    font-family: var(--display);
    font-size: 1.15rem;
    font-weight: 700;
    text-transform: uppercase;
    margin: 2rem 0 0.75rem;
}

.post-body a {
    color: var(--accent);
    border-bottom: 1px solid var(--accent);
}

.post-body blockquote {
    margin: 1.75rem 0;
    padding: 0.5rem 0 0.5rem 1.5rem;
    border-left: 3px solid var(--rule);
    font-style: italic;
    color: var(--muted);
}

.post-body ul, .post-body ol { margin: 0 0 1.4rem; padding-left: 1.5rem; }
.post-body li { margin: 0 0 0.5rem; }

.post-body figure { margin: 2rem 0; }
.post-body figure img { width: 100%; border: 2px solid var(--rule); }
.post-body figcaption {
    font-family: var(--mono);
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-top: 0.5rem;
}

.post-body sup a { border-bottom: none; }

.post-nav {
    max-width: var(--width);
    margin: 3rem auto 0;
    padding: 1.5rem;
    border-top: 2px solid var(--rule);
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-family: var(--display);
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.post-nav a { color: var(--accent); }

.archive {
    max-width: var(--width);
    margin: 2.5rem auto 0;
    padding: 0 1.5rem;
}

.archive-heading {
    font-family: var(--display);
    font-size: 2rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 1.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 3px solid var(--rule);
}

.archive-row {
    display: flex;
    align-items: baseline;
    gap: 1.5rem;
    padding: 1.1rem 0;
    border-bottom: 1px solid var(--rule);
}

.archive-row:hover { background: var(--accent-light); }

.archive-date {
    font-family: var(--mono);
    font-size: 0.625rem;
    letter-spacing: 0.2em;
    color: var(--muted);
    flex: 0 0 5.5rem;
}

.archive-title {
    font-family: var(--display);
    font-size: 1.15rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.01em;
    line-height: 1.2;
}

.archive-row:hover .archive-title { color: var(--accent); }

@media (max-width: 480px) {
    .post-title { font-size: 1.75rem; }
    .post { padding: 0 1rem; }
    .post-body { font-size: 1rem; }
    .archive { padding: 0 1rem; }
    .archive-row { flex-direction: column; gap: 0.25rem; }
}
```

- [ ] **Step 2: Verify CSS brace balance**

Run: `awk '{o+=gsub(/{/,"{"); c+=gsub(/}/,"}")} END{print o==c ? "OK" : "MISMATCH"}' style.css`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add style.css
git commit -m "feat: article and archive index styles"
```

---

## Task 8: `build.py` — orchestrate, write files, sitemap

**Files:**
- Rewrite: `build.py`
- Create: `tests/test_build.py`

**Interfaces:**
- Consumes: `posts.fetch_emails`, `posts.prepare_posts`, `pages.landing`, `pages.archive_index`, `pages.post_page`.
- Produces:
  - `get_api_key() -> str` (unchanged behavior: env `BUTTONDOWN_API_KEY`, else key files).
  - `write_site(posts: list[dict], out_dir: Path) -> list[Path]` — writes `index.html`, `archive/index.html`, `archive/<slug>/index.html` per post, `sitemap.xml`; returns written paths. Raises `ValueError(slug)` on any empty body.
  - `main()` — CLI entry (`--key-file`, `--dry-run`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build.py
import json
from pathlib import Path

import build
import posts


def test_write_site_generates_all_pages(tmp_path, sample_emails):
    prepared = posts.prepare_posts(sample_emails)
    written = build.write_site(prepared, tmp_path)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "archive" / "index.html").exists()
    assert (tmp_path / "archive" / "pasaku-taskai" / "index.html").exists()
    assert (tmp_path / "archive" / "ziurek-ka-darau" / "index.html").exists()
    assert (tmp_path / "sitemap.xml").exists()
    post_html = (tmp_path / "archive" / "pasaku-taskai" / "index.html").read_text()
    assert '<html lang="lt">' in post_html
    assert post_html.count("<h1") == 1
    sm = (tmp_path / "sitemap.xml").read_text()
    assert "https://verslografija.lt/archive/pasaku-taskai/" in sm


def test_write_site_fails_loud_on_empty_body(tmp_path, sample_emails):
    bad = posts.prepare_posts(sample_emails)
    bad[0]["body"] = "   "
    import pytest
    with pytest.raises(ValueError) as exc:
        build.write_site(bad, tmp_path)
    assert "pasaku-taskai" in str(exc.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_build.py -q`
Expected: FAIL — `build.write_site` does not exist yet (current `build.py` only renders the landing page).

- [ ] **Step 3: Rewrite `build.py`**

```python
#!/usr/bin/env python3
"""Build verslografija.lt: landing, archive index, and one page per post.

Fetches published posts from the Buttondown API and renders static HTML to the
repo root for GitHub Pages.

Usage:
    BUTTONDOWN_API_KEY=xxx python build.py
    python build.py --key-file memory/buttondown-key.txt
    python build.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

import pages
import posts

SITE_DIR = Path(__file__).parent
SITE_URL = posts.SITE_URL


def get_api_key():
    key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if key:
        return key
    for path in [SITE_DIR / "memory" / "buttondown-key.txt", Path.home() / ".buttondown-key"]:
        if path.exists():
            key = path.read_text().strip()
            if key and "PASTE" not in key:
                return key
    print("Error: No API key found. Set BUTTONDOWN_API_KEY or use --key-file.", file=sys.stderr)
    sys.exit(1)


def _sitemap(prepared):
    urls = [f"{SITE_URL}/", f"{SITE_URL}/archive/"] + [p["url"] for p in prepared]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


def write_site(prepared, out_dir):
    """Render and write all pages. Raises ValueError(slug) on an empty body."""
    if not prepared:
        raise ValueError("no posts to build")
    written = []

    landing_html = pages.landing(prepared[:4])
    (out_dir / "index.html").write_text(landing_html)
    written.append(out_dir / "index.html")

    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(pages.archive_index(prepared))
    written.append(archive_dir / "index.html")

    # newest-first: prev = older (next index), nxt = newer (previous index)
    for i, post in enumerate(prepared):
        if not post["body"].strip():
            raise ValueError(f"empty body for post: {post['slug']}")
        prev = prepared[i + 1] if i + 1 < len(prepared) else None
        nxt = prepared[i - 1] if i > 0 else None
        page_dir = archive_dir / post["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(pages.post_page(post, prev, nxt))
        written.append(page_dir / "index.html")

    (out_dir / "sitemap.xml").write_text(_sitemap(prepared))
    written.append(out_dir / "sitemap.xml")
    return written


def main():
    parser = argparse.ArgumentParser(description="Build verslografija.lt")
    parser.add_argument("--key-file", help="Path to Buttondown API key file")
    parser.add_argument("--dry-run", action="store_true", help="Build to a temp dir and report")
    args = parser.parse_args()

    if args.key_file:
        os.environ["BUTTONDOWN_API_KEY"] = Path(args.key_file).read_text().strip()

    api_key = get_api_key()
    print("Fetching posts from Buttondown API...")
    emails = posts.fetch_emails(api_key)
    prepared = posts.prepare_posts(emails)
    print(f"  {len(prepared)} posts")

    out = SITE_DIR
    if args.dry_run:
        import tempfile
        out = Path(tempfile.mkdtemp(prefix="vg-build-"))

    written = write_site(prepared, out)
    print(f"Wrote {len(written)} files to {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest -q`
Expected: PASS (all tests across the four test files green).

- [ ] **Step 5: Commit**

```bash
git add build.py tests/test_build.py
git commit -m "feat: build orchestration — landing, archive, posts, sitemap"
```

---

## Task 9: CI workflow — install deps, commit generated tree

**Files:**
- Modify: `.github/workflows/build-landing.yml`

**Interfaces:** none.

- [ ] **Step 1: Replace the workflow body**

```yaml
name: Build Landing Page

on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: python -m pip install -r requirements.txt

      - name: Run tests
        run: python -m pytest -q

      - name: Build site
        env:
          BUTTONDOWN_API_KEY: ${{ secrets.BUTTONDOWN_API_KEY }}
        run: python build.py

      - name: Check for changes
        id: changes
        run: |
          git add -A
          git diff --cached --quiet && echo "changed=false" >> "$GITHUB_OUTPUT" || echo "changed=true" >> "$GITHUB_OUTPUT"

      - name: Commit and push
        if: steps.changes.outputs.changed == 'true'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git commit -m "chore: rebuild site with latest posts"
          git push
```

- [ ] **Step 2: Lint the YAML locally**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/build-landing.yml')); print('YAML OK')"`
Expected: `YAML OK` (if `yaml` is unavailable, skip; CI will validate).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build-landing.yml
git commit -m "ci: install deps, run tests, commit full generated tree"
```

---

## Task 10: Live build + browser/a11y verification

**Files:** none (verification + generated output commit).

**Interfaces:** none.

- [ ] **Step 1: Build the real site locally**

Run: `python build.py --key-file <path-to-buttondown-key>`
Expected: `Wrote N files ...`, and `archive/<slug>/index.html` exists for every post.

- [ ] **Step 2: Serve and screenshot a rendered post**

```bash
python3 -m http.server 8732 &
agent-browser set viewport 1440 900
agent-browser open "http://localhost:8732/archive/pasaku-taskai/"
agent-browser screenshot /tmp/post-desktop.png --full
```
Expected: pulp-press article renders — masthead, date, single h1 title, 2:1 cover, serif body at comfortable measure, prev/next, subscribe, footer.

- [ ] **Step 3: Probe the a11y invariants**

```bash
agent-browser eval "JSON.stringify({lang:document.documentElement.lang, h1:document.querySelectorAll('h1').length, coverAlt:document.querySelector('.post-cover img')?.alt, lazy:[...document.querySelectorAll('.post-body img')].every(i=>i.loading==='lazy')})"
```
Expected: `{"lang":"lt","h1":1,"coverAlt":"... — iliustracija","lazy":true}`

- [ ] **Step 4: Probe contrast + keyboard focus**

```bash
agent-browser press Tab
agent-browser eval "(()=>{const e=document.activeElement;const s=getComputedStyle(e);return JSON.stringify({fv:e.matches(':focus-visible'),outline:s.outlineColor});})()"
```
Expected: `fv:true`, outline `rgb(139, 26, 26)`.

- [ ] **Step 5: Stop the server and commit the generated tree**

```bash
pkill -f "http.server 8732"
git add -A
git commit -m "build: generate self-hosted archive and post pages"
```

---

## Self-Review (completed during planning)

- **Spec coverage:** architecture split → Tasks 2,3,4,8; render pipeline (mistune/passthrough/sanitize/cover-strip/lazy/link-rewrite) → Task 3; post template (lang=lt, single h1, canonical, cover alt, prev/next, subscribe) → Task 4; archive index → Task 5; landing link rewrite → Task 6; output structure + sitemap → Task 8; CSS → Task 7; SEO canonical + sitemap → Tasks 4,8; andon fail-on-bad-body → Task 8; tests (unit/golden/integration/browser) → Tasks 2,3,4,5,6,8,10; locked decisions (mistune, hand-rolled sanitizer, hot-link, sitemap, fail-build, `/archive/<slug>/`) → honored throughout. No gaps.
- **Placeholder scan:** no TBD/TODO; every code step contains complete code; `<path-to-buttondown-key>` in Task 10 is an operator-supplied runtime value, not a code placeholder.
- **Type consistency:** `prepare_posts` dict keys (`slug,title,date,excerpt,image,body,url`) are consumed unchanged by `pages.*` and `build.write_site`; `post_page(post, prev, nxt)`, `archive_index(posts)`, `landing(posts)`, `render.article(body)`, `write_site(prepared, out_dir)` signatures are consistent across all references.

## Notes for the implementer

- The landing port in Task 6 must match the current `main` markup. If unsure of a class name, read `index.html` on `main` and mirror it; the CSS in `style.css` already styles those classes.
- The `mistune` footnote syntax (`[^1]`) renders to `<sup>`/`<section class="footnotes">`. The sanitizer drops `section` (not allowlisted) but keeps its inner `<ol>/<li>` — acceptable. If you want the footnotes wrapped, add `section` and `class` to the allowlists in a follow-up; out of scope here.
- Asset paths switch to absolute (`/assets/...`, `/style.css`) because post pages live at `/archive/<slug>/`; the landing already works with absolute paths.
