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
