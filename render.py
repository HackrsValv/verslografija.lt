"""Convert a Buttondown email body into a clean, self-hosted article body."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import mistune

_EDITOR_MODE = re.compile(r"<!--\s*buttondown-editor-mode:[^>]*-->", re.IGNORECASE)
_VISA_LINK = re.compile(r"https://visa\.verslografija\.lt/archive/([^/\"')\s]+)/?")
_LEADING_FIGURE = re.compile(r"^\s*<figure\b[^>]*>.*?</figure>", re.IGNORECASE | re.DOTALL)
_LEADING_IMG = re.compile(r"^\s*(?:<p\b[^>]*>\s*)?<img\b[^>]*>(?:\s*</p>)?", re.IGNORECASE)
_IMG_OPEN = re.compile(r"<img\b", re.IGNORECASE)
# Signatures of markdown that failed to render (build-time guard).
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)
_MD_FOOTNOTE = re.compile(r"\[\^[^\]]+\]")
_MD_TABLE = re.compile(r"^\|.+\|\s*$", re.MULTILINE)

ALLOWED_TAGS = {
    "a", "p", "h2", "h3", "h4", "blockquote", "em", "strong",
    "ul", "ol", "li", "figure", "figcaption", "img", "sup", "hr", "code", "pre", "br",
    "section",
    "table", "thead", "tbody", "tr", "th", "td",
}
ALLOWED_ATTRS = {"href", "src", "alt", "id"}
TABLE_TAGS = {"table", "thead", "tbody", "tr", "th", "td"}
VOID_TAGS = {"img", "hr", "br"}

_md = mistune.create_markdown(escape=False, plugins=["footnotes", "table"])


_BR_LINE = re.compile(r"^\s*<br\s*/?>\s*$", re.IGNORECASE)
_BR_TAIL = re.compile(r"\s*<br\s*/?>\s*$", re.IGNORECASE)


def _unbr(body):
    """Rewrite <br>-joined lines into markdown hard breaks.

    mistune opens an HTML block at any line starting with a raw tag, so the
    email habit of joining ledger lines with <br> leaks every marker inside
    (bold, footnote refs). A lone <br> line is a visual separator: drop it.
    """
    return "\n".join(
        _BR_TAIL.sub("  ", line) for line in body.split("\n") if not _BR_LINE.match(line)
    )


def to_html(body):
    """Strip the editor-mode directive, then render.

    Always run mistune: it renders markdown to HTML and passes raw HTML blocks
    through unchanged. The Buttondown "fancy" marker is unreliable — some
    fancy-marked posts contain plain markdown — so we no longer branch on it.
    """
    stripped = _EDITOR_MODE.sub("", body).strip()
    return _md(_unbr(stripped))


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.table_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        if tag == "table":
            self.table_depth += 1
        elif tag in TABLE_TAGS and self.table_depth == 0:
            return  # stray email-layout wrapper: unwrap, keep children
        kept = "".join(
            f' {k}="{v}"' for k, v in attrs if k in ALLOWED_ATTRS and v is not None
        )
        slash = "" if tag not in VOID_TAGS else ""
        self.out.append(f"<{tag}{kept}{slash}>")

    def handle_startendtag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        if tag in TABLE_TAGS and self.table_depth == 0:
            return
        kept = "".join(
            f' {k}="{v}"' for k, v in attrs if k in ALLOWED_ATTRS and v is not None
        )
        self.out.append(f"<{tag}{kept}>")

    def handle_endtag(self, tag):
        if tag == "table":
            if self.table_depth:
                self.table_depth -= 1
            self.out.append("</table>")
            return
        if tag in TABLE_TAGS and self.table_depth == 0:
            return  # closes a wrapper we unwrapped
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


def _strip_cover(html, cover):
    """Remove the body's duplicate of the cover image.

    The template renders the cover separately, so the same image at the top of
    the body is a duplicate. Imported (email-HTML) posts wrap it in table markup,
    so it isn't always the leading node — match the cover URL anywhere and drop
    the first occurrence (plus any wrapper left empty).
    """
    if not cover:
        return _strip_leading_cover(html)
    name = re.escape(cover.rsplit("/", 1)[-1])
    img = re.compile(r"<img\b[^>]*" + name + r"[^>]*>", re.IGNORECASE)
    new = img.sub("", html, count=1)
    if new == html:
        return _strip_leading_cover(html)
    # tidy wrappers left empty by the removal
    new = re.sub(r"<p>\s*</p>", "", new, count=1)
    new = re.sub(r"<figure>\s*(?:<figcaption\b[^>]*>.*?</figcaption>\s*)?</figure>", "", new, count=1, flags=re.S)
    return new.strip()


def _load_alt_overrides():
    """Curated alt texts for body images whose source alt is empty (legacy
    beehiiv imports). Keyed by image file name; lives in memory/ so it is
    versioned with the repo, not with Buttondown's email archive."""
    path = Path(__file__).resolve().parent / "memory" / "inline-alts.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_alt_overrides(html, overrides):
    """Fill in alt="" on body images that have an override; never overwrite
    a real alt."""
    if not overrides:
        return html

    def fix(m):
        tag = m.group(0)
        if 'alt=""' not in tag:
            return tag
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            return tag
        name = src.group(1).rsplit("/", 1)[-1].split("?")[0]
        alt = overrides.get(name)
        if not alt:
            return tag
        return tag.replace('alt=""', f'alt="{alt}"', 1)

    return re.sub(r"<img\b[^>]*>", fix, html)


_CDN_SRC = re.compile(r'(src=")(https://assets\.buttondown\.email/[^"]+)(")')


def _cdn_inline_images(html):
    """Bound inline image weight: Buttondown's CDN can resize on request, so
    inline originals (often 1-2 MB) fetch a fixed 800px width. The cover never
    reaches here because _strip_cover removes it from the body.
    """
    return _CDN_SRC.sub(r"\g<1>\g<2>?w=800\g<3>", html)


def _wrap_tables(html):
    """Wrap each table in a horizontal-scroll container (wide tables on phones)."""
    return (html.replace("<table>", '<div class="mm-tablewrap"><table>')
                .replace("</table>", "</table></div>"))


def _lazy_images(html):
    return _IMG_OPEN.sub('<img loading="lazy" decoding="async"', html)


def md_leaked(html):
    """True if rendered output still contains unrendered markdown (image, heading, footnote, table)."""
    return bool(
        _MD_IMAGE.search(html) or _MD_HEADING.search(html)
        or _MD_FOOTNOTE.search(html) or _MD_TABLE.search(html)
    )


def article(body, cover=""):
    """Full pipeline -> clean article HTML (no duplicate cover, no h1).

    `cover` is the post's cover image URL; its duplicate at the top of the body
    is removed. Sanitize first so email-table wrappers are unwrapped before the
    cover strip. Raises ValueError if markdown leaked (a render regression);
    run at build time this fails CI before a broken post can deploy.
    """
    html = to_html(body)
    # The email body opens with "# Title", which mistune renders as <h1>.
    # The template already shows the title, so drop the heading (tags AND text)
    # — sanitize() alone would strip the tags but leave the bare text behind.
    html = re.sub(r"<h1>.*?</h1>", "", html, count=1, flags=re.S)
    html = sanitize(html)
    html = _strip_cover(html, cover)
    html = _lazy_images(html)
    html = _cdn_inline_images(html)
    html = _apply_alt_overrides(html, _load_alt_overrides())
    html = _wrap_tables(html)
    html = _VISA_LINK.sub(r"/archive/\1/", html)
    html = html.strip()
    if md_leaked(html):
        raise ValueError("unrendered markdown leaked into article output")
    return html
