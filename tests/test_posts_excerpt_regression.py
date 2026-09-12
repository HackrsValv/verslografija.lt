from posts import prepare_posts


def test_prepare_posts_excerpt_falls_back_to_body_text():
    # Regression: ISSUE-001 (found by /qa 2026-09-11) — emails without a
    # description produced content="" meta description on post pages.
    emails = [
        {"slug": "a", "subject": "Antraštė", "publish_date": "2026-01-02T00:00:00Z",
         "status": "sent",
         "body": "<!-- buttondown-editor-mode: fancy -->\n# Antraštė\n\n"
                 "![cover](https://assets.buttondown.email/images/c.png)\n\n"
                 "Pirmas sakinys apie verslą. Antras sakinys apie procesą.\n\n"
                 "<h2>Skyrius</h2>\n"},
    ]
    p = prepare_posts(emails)[0]
    assert p["excerpt"].startswith("Pirmas sakinys")
    assert "Antraštė" not in p["excerpt"].split("Pirmas")[0]  # no duplicated title prefix
    assert "<" not in p["excerpt"] and "!" not in p["excerpt"]


def test_prepare_posts_excerpt_prefers_explicit_description():
    emails = [
        {"slug": "a", "subject": "A", "publish_date": "2026-01-02T00:00:00Z",
         "status": "sent", "description": "Autoriaus aprašymas.", "body": "Kūno tekstas."},
    ]
    assert prepare_posts(emails)[0]["excerpt"] == "Autoriaus aprašymas."
