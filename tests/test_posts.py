from posts import prepare_posts, SITE_URL


def test_prepare_posts_maps_fields_and_builds_url(sample_emails):
    posts = prepare_posts(sample_emails)
    assert len(posts) == 2
    p = posts[0]
    assert p["slug"] == "pasaku-taskai"
    assert p["title"] == "Pasakų taškai"
    assert p["date"] == "2026-06-05"
    assert p["url"] == f"{SITE_URL}/archive/pasaku-taskai/"
    assert p["image"].startswith("https://assets.buttondown.email/")
    assert p["body"]


def test_prepare_posts_skips_slugless(sample_emails):
    emails = sample_emails + [{"slug": "", "subject": "x", "body": "y", "status": "sent"}]
    posts = prepare_posts(emails)
    assert all(p["slug"] for p in posts)
    assert len(posts) == 2


def test_prepare_posts_keeps_sent_and_imported_drops_drafts():
    # Published archive = sent + imported. Drafts must not appear.
    emails = [
        {"slug": "a", "subject": "A", "publish_date": "2026-01-02T00:00:00Z", "status": "sent", "body": "x"},
        {"slug": "b", "subject": "B", "publish_date": "2024-01-01T00:00:00Z", "status": "imported", "body": "y"},
        {"slug": "c", "subject": "C", "publish_date": "2026-02-01T00:00:00Z", "status": "draft", "body": "z"},
    ]
    posts = prepare_posts(emails)
    assert [p["slug"] for p in posts] == ["a", "b"]  # draft dropped, order kept
