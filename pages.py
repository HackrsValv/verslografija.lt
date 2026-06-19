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
    return """    <div class="mm-topbar">
        <div class="mm-meta"><span>Verslo Grafija · biuletenis</span><span>Vilnius · Est. MMXXIV</span></div>
        <header class="mm-plate mm-plate--slim">
            <a href="/" class="mm-mark mm-mark--sm" aria-label="Verslo Grafija">V</a>
            <a href="/" class="mm-wordmark mm-wordmark--sm">Verslo <span>Grafija</span></a>
            <nav class="mm-nav mm-nav--row">
                <a href="/">Pradžia</a>
                <a href="/archive/">Archyvas</a>
            </nav>
        </header>
    </div>"""


def _subscribe():
    return """    <section class="mm-coupon" id="prenumeruoti">
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
    </section>"""


def _prevnext(prev, nxt):
    def card(p, label, hue):
        if not p:
            return '<span class="mm-pn mm-pn--empty"></span>'
        return (
            f'<a class="mm-pn" style="--c:var(--{hue})" href="/archive/{p["slug"]}/">'
            f'<span class="mm-pn-label">{label}</span>'
            f'<span class="mm-pn-title">{escape(p["title"])}</span></a>'
        )
    left = card(prev, "&larr; Ankstesnis numeris", "teal")
    right = card(nxt, "Kitas numeris &rarr;", "oxblood")
    return f'    <nav class="mm-prevnext">\n        {left}\n        {right}\n    </nav>'


def post_page(post, prev, nxt):
    alt = f'{post["title"]} — iliustracija'
    cover = ""
    if post["image"]:
        cover = (
            f'<figure class="mm-cover">'
            f'<span class="mm-disc mm-disc--sm"></span>'
            f'<span class="mm-tone post-cover" style="view-transition-name:cover-{post["slug"]}">'
            f'<img src="{post["image"]}" alt="{escape(alt)}" loading="eager" decoding="async"></span>'
            f'</figure>'
        )
    body_html = render.article(post["body"], post["image"])
    head = _head(post["title"], post["excerpt"], post["url"], post["image"])
    return f"""<!DOCTYPE html>
<html lang="lt">
{head}
<body class="mm">
{_masthead()}
    <main>
        <article class="mm-post">
            <header class="mm-post-head">
                <p class="mm-kicker">Numeris · {post["date"]}</p>
                <h1 class="mm-post-title" style="view-transition-name:title-{post["slug"]}">{escape(post["title"])}</h1>
            </header>
            {cover}
            <div class="post-body mm-read">
{body_html}
            </div>
        </article>
{_prevnext(prev, nxt)}
{_subscribe()}
    </main>
    <footer class="mm-foot mm-foot--wide">
        <a class="mm-foot-ar" href="/archive/">Visas archyvas &rarr;</a>
        <span>&copy; 2024&ndash;2026 Verslo Grafija</span>
    </footer>
</body>
</html>"""




_ISSUE_HUES = ("oxblood", "teal", "orange", "sky")


def archive_index(posts):
    total = len(posts)
    rows = "\n".join(
        f"""            <a class="mm-issue" style="--c:var(--{_ISSUE_HUES[i % 4]})" href="/archive/{p['slug']}/">
                <span class="mm-issue-no">{total - i:02d}</span>
                <span class="mm-issue-date">{p['date']}</span>
                <h2 class="mm-issue-title">{escape(p['title'])}</h2>
                <span class="mm-issue-cta">&rarr;</span>
            </a>"""
        for i, p in enumerate(posts)
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
<body class="mm">
{_masthead()}
    <main>
        <div class="wrap">
            <header class="mm-arch-head">
                <h1>Archyvas</h1>
                <span>{total} numeriai · visi iš vidaus</span>
            </header>
            <div class="mm-issues">
{rows}
            </div>
        </div>
{_subscribe()}
    </main>
    <footer class="mm-foot mm-foot--wide">
        <a class="mm-foot-ar" href="/">&larr; Pradžia</a>
        <span>&copy; 2024&ndash;2026 Verslo Grafija</span>
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
