import json
from pathlib import Path

import build
import posts


def test_write_site_generates_all_pages(tmp_path, sample_emails):
    prepared = posts.prepare_posts(sample_emails)
    written = build.write_site(prepared, tmp_path)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "archive" / "index.html").exists()
    assert (tmp_path / "archive" / "pasaku-taskai" / "index.html").exists()
    assert (tmp_path / "archive" / "ziurek-ka-darau" / "index.html").exists()
    assert (tmp_path / "sitemap.xml").exists()
    post_html = (tmp_path / "archive" / "pasaku-taskai" / "index.html").read_text()
    assert '<html lang="lt">' in post_html
    assert post_html.count("<h1") == 1
    sm = (tmp_path / "sitemap.xml").read_text()
    assert "https://verslografija.lt/archive/pasaku-taskai/" in sm


def test_write_site_fails_loud_on_empty_body(tmp_path, sample_emails):
    bad = posts.prepare_posts(sample_emails)
    bad[0]["body"] = "   "
    import pytest
    with pytest.raises(ValueError) as exc:
        build.write_site(bad, tmp_path)
    assert "pasaku-taskai" in str(exc.value)
