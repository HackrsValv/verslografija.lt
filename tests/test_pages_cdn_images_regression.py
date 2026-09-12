import re

import pages


def _post(slug="pasaku-taskai", title="Pasakų taškai"):
    return {
        "slug": slug,
        "title": title,
        "date": "2026-06-05",
        "excerpt": "Santrauka.",
        "image": "https://assets.buttondown.email/images/cover-pt.png",
        "body": "![cover](https://assets.buttondown.email/images/cover-pt.png)  ## Skyrius  Tekstas.",
        "url": f"https://verslografija.lt/archive/{slug}/",
    }


def _cover_html(html):
    return html.split('<figure class="mm-cover">')[1].split("</figure>")[0]


def test_post_page_hero_requests_smaller_cdn_variant():
    # Regression: ISSUE-005 — the post hero shipped the full-size PNG (1.8 MB)
    # to every visitor. Buttondown assets resize on demand with ?w=.
    cover = _cover_html(pages.post_page(_post(), prev=None, nxt=None))
    assert 'src="https://assets.buttondown.email/images/cover-pt.png?w=1200"' in cover
    assert "cover-pt.png?w=800 800w" in cover
    assert "cover-pt.png?w=1200 1200w" in cover
    assert "sizes=" in cover
    assert 'loading="eager"' in cover


def test_post_page_og_image_stays_full_size_for_crawlers():
    html = pages.post_page(_post(), prev=None, nxt=None)
    assert '<meta property="og:image" content="https://assets.buttondown.email/images/cover-pt.png">' in html


def test_landing_emits_resized_variants_for_hero_and_tiles():
    html = pages.landing([_post(slug=f"p{i}") for i in range(4)])
    assert "cover-pt.png?w=1200" in html  # featured hero
    assert "cover-pt.png?w=400" in html   # grid tiles


def test_no_img_tag_ships_a_full_size_buttondown_cover():
    pages_html = [
        pages.post_page(_post(), prev=None, nxt=None),
        pages.landing([_post(slug=f"p{i}") for i in range(4)]),
    ]
    for html in pages_html:
        for img in re.findall(r"<img[^>]*>", html):
            src = re.search(r'src="([^"]+)"', img).group(1)
            assert "?w=" in src, f"full-size cover shipped: {src}"


def test_non_cdn_urls_are_left_alone():
    assert pages._img_url("https://example.com/a.png", 800) == "https://example.com/a.png"
    assert pages._img_url("https://assets.buttondown.email/images/a.png", 800) == (
        "https://assets.buttondown.email/images/a.png?w=800"
    )
    assert pages._img_url("https://assets.buttondown.email/images/a.png?x=1", 800) == (
        "https://assets.buttondown.email/images/a.png?x=1&w=800"
    )
