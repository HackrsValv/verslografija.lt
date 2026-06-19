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


def test_fancy_marked_but_markdown_body_still_renders():
    # Regression: some Buttondown posts carry the "fancy" marker but contain
    # plain markdown. They must still be rendered to HTML, not passed through raw.
    body = ("<!-- buttondown-editor-mode: fancy -->\n"
            "![cover](https://assets.buttondown.email/images/x.png)\n\n"
            "## Skyrius\n\nTekstas su **bold**.")
    html = render.article(body)
    assert "## Skyrius" not in html          # heading rendered, not raw
    assert "<h2>" in html and "Skyrius" in html
    assert "![cover]" not in html            # cover image stripped, not raw
    assert "<strong>bold</strong>" in html


def test_md_leak_guard_flags_unrendered_markdown():
    # Build-time guard: catches any future render regression on real content.
    assert render.md_leaked("![x](y.png)") is True
    assert render.md_leaked("## Heading") is True
    assert render.md_leaked("<h2>Heading</h2><p>clean</p>") is False
