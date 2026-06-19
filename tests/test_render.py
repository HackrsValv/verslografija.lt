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
