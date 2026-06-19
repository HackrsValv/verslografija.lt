"""HTML page templates for the self-hosted site. Pure functions, no I/O."""

from html import escape

import render

SITE_URL = "https://verslografija.lt"


def _kinetic(text):
    """Wrap each letter in an indexed span for the ink-stamp masthead reveal."""
    spans = []
    i = 0
    for ch in text:
        if ch == " ":
            spans.append('<span class="ksp"> </span>')
        else:
            spans.append(f'<span style="--k:{i}">{escape(ch)}</span>')
            i += 1
    return "".join(spans)


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
            f'<div class="post-cover" style="view-transition-name:cover-{post["slug"]}"><img src="{post["image"]}" '
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
            <h1 class="post-title" style="view-transition-name:title-{post["slug"]}">{escape(post["title"])}</h1>
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


_COL_HUES = ("oxblood", "teal", "orange")


def _mm_col(post, n, hue):
    cover = (
        f'<div class="mm-tone" style="view-transition-name:cover-{post["slug"]}"><img src="{post["image"]}" '
        f'alt="{escape(post["title"])} — iliustracija" loading="lazy" decoding="async"></div>'
        if post["image"]
        else '<div class="mm-tone mm-tone--ph">V</div>'
    )
    return f"""            <a class="mm-col" style="--c:var(--{hue})" href="/archive/{post['slug']}/">
                <span class="mm-no">{n:02d}</span>
                {cover}
                <span class="mm-col-date">{post['date']}</span>
                <h3 class="mm-col-title" style="view-transition-name:title-{post['slug']}">{escape(post['title'])}</h3>
            </a>"""


def landing(posts):
    featured = posts[0]
    grid = posts[1:4]
    f_alt = f'{featured["title"]} — iliustracija'
    if featured["image"]:
        hero_fig = (
            f'<a class="mm-hero-fig" href="/archive/{featured["slug"]}/" aria-label="{escape(featured["title"])}">'
            f'<span class="mm-disc"></span>'
            f'<span class="mm-tone" style="view-transition-name:cover-{featured["slug"]}">'
            f'<img src="{featured["image"]}" alt="{escape(f_alt)}" loading="eager" decoding="async"></span></a>'
        )
        img_meta = (
            f'<meta property="og:image" content="{featured["image"]}">\n'
            f'    <meta name="twitter:image" content="{featured["image"]}">'
        )
    else:
        hero_fig = '<div class="mm-hero-fig"><span class="mm-tone mm-tone--ph">V</span></div>'
        img_meta = ""
    cols = "\n".join(_mm_col(p, i + 1, _COL_HUES[i % 3]) for i, p in enumerate(grid))
    return f"""<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="google-site-verification" content="XuC0uXgnDy6USPp0RSUBgz-R0EzUSiqGz8wp0O0v4fY">
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
<body class="mm">
    <div class="wrap">
        <div class="mm-meta"><span>№ 01 — Verslo Grafija</span><span>Vilnius · Est. MMXXIV</span></div>
        <header class="mm-plate">
            <a href="/" class="mm-mark" aria-label="Verslo Grafija">V</a>
            <h1 class="mm-wordmark">Verslo <span>Grafija</span></h1>
            <nav class="mm-nav">
                <a href="#naujausios">Naujausios</a>
                <a href="#prenumeruoti">Prenumeruoti</a>
                <a href="/archive/">Archyvas</a>
            </nav>
        </header>

        <section class="mm-hero" id="naujausios">
            <div class="mm-hero-idea">
                <p class="mm-kicker">Biuletenis apie darbą</p>
                <h2 class="mm-hero-line">Visi kažką <em>žiūrim</em>.<br>O kartais ir <span class="knock">parašom</span>.</h2>
                <p class="mm-hero-sub">Stato tvorą atviroje pievoje. Optimizuoja procesą, kuris neturėjo egzistuoti. Cituoja eksperimentą, kurio nebuvo.</p>
            </div>
            {hero_fig}
        </section>
    </div>

    <section class="mm-band">
        <a class="mm-band-inner" href="/archive/{featured['slug']}/">
            <span class="mm-band-date">Naujausias · {featured['date']}</span>
            <h3 class="mm-band-title" style="view-transition-name:title-{featured['slug']}">{escape(featured['title'])}</h3>
            <span class="mm-band-cta">Skaityti &rarr;</span>
        </a>
    </section>

    <div class="wrap">
        <div class="mm-sechead"><h2>Šviežiausi įrašai</h2><span>Iš archyvo</span></div>
        <div class="mm-three">
{cols}
        </div>
    </div>

    <section class="mm-coupon" id="prenumeruoti">
        <h2>Šlamštas, kurį verta atidaryti</h2>
        <p>Visi kažką žiūrim, o kartais ir parašom.</p>
        <form action="https://buttondown.com/api/emails/embed-subscribe/verslografija"
              method="post" target="popupwindow">
            <label for="bd-email" class="sr-only">El. paštas</label>
            <input type="email" name="email" id="bd-email" placeholder="El. paštas"
                   autocomplete="email" inputmode="email" autocapitalize="off"
                   autocorrect="off" spellcheck="false" maxlength="254"
                   aria-describedby="bd-note" required>
            <button type="submit">Prenumeruoti</button>
        </form>
        <p class="mm-fine" id="bd-note">Šlamštas iš vidaus · be jokių blokerių</p>
    </section>

    <div class="wrap">
        <footer class="mm-foot">
            <a class="mm-foot-ar" href="/archive/">Visas archyvas &rarr;</a>
            <span>&copy; 2024&ndash;2026 Verslo Grafija</span>
        </footer>
    </div>
</body>
</html>"""
