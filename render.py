"""Convert a Buttondown email body into a clean, self-hosted article body."""

import re
from html.parser import HTMLParser

import mistune

_EDITOR_MODE = re.compile(r"<!--\s*buttondown-editor-mode:[^>]*-->", re.IGNORECASE)
_VISA_LINK = re.compile(r"https://visa\.verslografija\.lt/archive/([^/\"')\s]+)/?")
_LEADING_FIGURE = re.compile(r"^\s*<figure\b[^>]*>.*?</figure>", re.IGNORECASE | re.DOTALL)
_LEADING_IMG = re.compile(r"^\s*(?:<p\b[^>]*>\s*)?<img\b[^>]*>(?:\s*</p>)?", re.IGNORECASE)
_IMG_OPEN = re.compile(r"<img\b", re.IGNORECASE)
# Signatures of markdown that failed to render (build-time guard).
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)

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


def _lazy_images(html):
    return _IMG_OPEN.sub('<img loading="lazy" decoding="async"', html)


def md_leaked(html):
    """True if rendered output still contains unrendered markdown (image or heading)."""
    return bool(_MD_IMAGE.search(html) or _MD_HEADING.search(html))


def article(body, cover=""):
    """Full pipeline -> clean article HTML (no duplicate cover, no h1).

    `cover` is the post's cover image URL; its duplicate at the top of the body
    is removed. Sanitize first so email-table wrappers are unwrapped before the
    cover strip. Raises ValueError if markdown leaked (a render regression);
    run at build time this fails CI before a broken post can deploy.
    """
    html = to_html(body)
    html = sanitize(html)
    html = _strip_cover(html, cover)
    html = _lazy_images(html)
    html = _VISA_LINK.sub(r"/archive/\1/", html)
    html = html.strip()
    if md_leaked(html):
        raise ValueError("unrendered markdown leaked into article output")
    return html
