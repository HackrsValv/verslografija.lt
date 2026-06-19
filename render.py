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
    """Strip the editor-mode directive, then render.

    Always run mistune: it renders markdown to HTML and passes raw HTML blocks
    through unchanged. The Buttondown "fancy" marker is unreliable — some
    fancy-marked posts contain plain markdown — so we no longer branch on it.
    """
    stripped = _EDITOR_MODE.sub("", body).strip()
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
