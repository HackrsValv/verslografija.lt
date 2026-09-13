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


def test_cover_duplicate_removed_from_body_including_email_html():
    cover = "https://assets.buttondown.email/images/abc123.jpg"
    # email-table HTML (imported style): cover wrapped, not the leading node
    body = ('<!-- buttondown-editor-mode: fancy --><tr id="content-blocks">'
            f'<img alt="t" border="0" src="{cover}" width="660"/><p>Tekstas.</p>')
    out = render.article(body, cover)
    assert "abc123.jpg" not in out      # cover not duplicated in body
    assert "Tekstas." in out


def test_footnotes_rendered_not_raw():
    body = ("Tekstas su išnaša.[^1]\n\n"
            "## Skyrius\n\nDar tekstas.[^2]\n\n"
            "[^1]: Pirmas šaltinis.\n[^2]: Antras šaltinis.")
    out = render.article(body)
    assert "[^1]" not in out and "[^1]:" not in out   # not raw
    assert "<sup" in out                                # inline ref rendered
    assert "Pirmas šaltinis." in out                    # definition present
    assert 'href="#fn' in out or 'id="fn' in out        # anchor wiring


def test_article_strips_leading_h1_text_not_just_tags():
    """Regression: the body's leading "# Title" h1 must lose its TEXT too,
    not only its tags — otherwise the bare title duplicates the page heading."""
    html = render.article("# Pavadinimas\n\nTekstas prasideda.", cover="")
    assert "<h1" not in html
    assert "Pavadinimas" not in html.split("<p>")[0]


def test_br_joined_lines_render_markdown_inside():
    # Email bodies join ledger-style lines with <br>. mistune starts an HTML
    # block at any line beginning with a raw tag, so markdown inside (bold,
    # footnote refs) leaks - exactly what broke the 2026-09-13 build.
    body = ("<br>\n"
            "**Pajamos** - 7 mlrd.<br>\n"
            "**F1 komanda** - maziau nei desimtadalis pajamu[^1]<br>\n"
            "\n"
            "## Skyrius\n\n"
            "[^1]: Saltinis.")
    out = render.article(body)
    assert "<strong>Pajamos</strong>" in out
    assert "**Pajamos**" not in out
    assert "[^1]" not in out
    assert "<sup" in out
    assert "<br" in out  # the line-per-line shape survives


def test_lone_br_line_starts_a_new_block():
    # A <br> alone on a line was only a visual separator in the email; it must
    # not leave a stray empty paragraph or swallow the next line's markdown.
    body = "<br>\n**Pajamos** - 7 mlrd.<br>\n**Antra** - 2 mlrd.<br>\n\nPabaiga."
    out = render.article(body)
    assert "<p></p>" not in out
    assert "<strong>Pajamos</strong>" in out
    assert "<strong>Antra</strong>" in out


def test_markdown_table_renders_as_wrapped_table():
    # GFM tables in the email body must become a real <table> (wrapped for
    # mobile scroll), not a paragraph of raw pipes.
    body = ("| utopija | piecemeal |\n|---|---|\n"
            "| Visa sistema | Po truputi |\n\nTekstas toliau.")
    out = render.article(body)
    assert "<table>" in out and "<th" in out and "<td" in out
    assert "|---|" not in out and "| utopija" not in out
    assert "mm-tablewrap" in out


def test_md_leak_guard_flags_raw_table_pipes():
    assert render.md_leaked("| a | b |\n|---|---|") is True
    assert render.md_leaked("<table><tr><td>a</td></tr></table>") is False


def test_email_table_wrapper_tr_is_unwrapped():
    # Imported Buttondown bodies open with <tr id="content-blocks"> layout
    # wrappers. Table tags are allowlisted for real markdown tables, but a
    # stray <tr> outside any <table> must still be unwrapped, not printed.
    body = ('<!-- buttondown-editor-mode: fancy --><tr id="content-blocks">'
            '<p>Tekstas apie suvestines.</p></tr>')
    out = render.article(body)
    assert "<tr" not in out and "</tr>" not in out
    assert "Tekstas apie suvestines." in out


def test_inline_buttondown_images_get_cdn_width():
    # Inline body images are 1-2 MB originals on Buttondown's CDN; the CDN can
    # resize on demand, so every inline image requests a bounded width.
    # text first: a leading body image is treated as the cover duplicate and
    # stripped, so test the genuinely inline case as real posts have it
    body = ("Tekstas pries paveiksleli.\n\n"
            "![Tron (1982) - scena](https://assets.buttondown.email/images/x1.jpg)\n\n"
            "![kita](https://example.com/plain.png)")
    out = render.article(body, "https://assets.buttondown.email/images/other.png")
    assert "x1.jpg?w=800" in out
    assert "plain.png?w=800" not in out   # non-Buttondown hosts stay untouched
    assert "plain.png" in out


def test_cover_image_not_double_resized():
    # The cover is stripped from the body, so only genuinely inline images
    # carry the CDN width; nothing gets a second ?w= appended.
    cover = "https://assets.buttondown.email/images/cover99.png"
    body = (f"![]( {cover} )\n\n"
            "Tekstas.\n\n"
            "![inline](https://assets.buttondown.email/images/in1.png)")
    out = render.article(body, cover)
    assert out.count("?w=800") == 1       # only the inline one
    assert "cover99.png?w=800" not in out


def test_inline_alt_override_applied(monkeypatch):
    # Legacy beehiiv imports carry alt="" in the source body. The curated
    # overrides in memory/inline-alts.json restore the descriptive alt text,
    # so rebuilds do not lose it again.
    monkeypatch.setattr(render, "_load_alt_overrides",
                        lambda: {"maltz.png": "Citatos kortele: Maxwell Maltz"})
    body = ('Tekstas. </p><img alt="" border="0" height="auto" '
            'src="https://media.beehiiv.com/uploads/asset/file/1d46/maltz.png?t=1">'
            "<p>Toliau.")
    out = render.article(body, "https://assets.buttondown.email/images/other.png")
    assert 'alt="Citatos kortele: Maxwell Maltz"' in out


def test_inline_alt_override_ignores_unknown_images(monkeypatch):
    monkeypatch.setattr(render, "_load_alt_overrides", lambda: {"maltz.png": "x"})
    body = ('Tekstas. </p><img alt="" src="https://media.beehiiv.com/kita.png">'
            '<img alt="jau yra" src="https://media.beehiiv.com/maltz.png">')
    out = render.article(body, "https://assets.buttondown.email/images/other.png")
    assert 'src="https://media.beehiiv.com/kita.png"' in out
    assert 'alt="jau yra"' in out          # never overwrites a real alt
    assert 'alt="x"' not in out
