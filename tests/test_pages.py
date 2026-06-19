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


def test_archive_index_lists_all_posts_lt():
    posts = [_post(slug="a", title="Aaa"), _post(slug="b", title="Bbb")]
    html = pages.archive_index(posts)
    assert '<html lang="lt">' in html
    assert html.count("<h1") == 1  # page heading only
    assert 'href="/archive/a/"' in html and 'href="/archive/b/"' in html
    assert "Aaa" in html and "Bbb" in html
    assert "Aaa" in html and "Bbb" in html
