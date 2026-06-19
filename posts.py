"""Fetch published posts from the Buttondown API and normalize them."""

import json
import urllib.request

API_BASE = "https://api.buttondown.email/v1/emails"
SITE_URL = "https://verslografija.lt"

# Statuses that are publicly published in the archive. "sent" = emailed posts,
# "imported" = posts migrated into Buttondown (the newsletter's early issues).
# Drafts/scheduled are excluded.
PUBLISHED_STATUSES = frozenset({"sent", "imported"})


def fetch_emails(api_key):
    """All emails, newest first (follows pagination). prepare_posts filters status."""
    emails = []
    page = 1
    while True:
        url = f"{API_BASE}?page={page}&ordering=-publish_date"
        req = urllib.request.Request(url, headers={"Authorization": f"Token {api_key}"})
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
        emails.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return emails


def prepare_posts(emails):
    """Normalize published email objects into post dicts. No cap; skips slugless and non-published."""
    posts = []
    for e in emails:
        if e.get("status") not in PUBLISHED_STATUSES:
            continue
        slug = (e.get("slug") or "").strip()
        if not slug:
            continue
        posts.append(
            {
                "slug": slug,
                "title": (e.get("subject") or "").strip(),
                "date": (e.get("publish_date") or "")[:10],
                "excerpt": (e.get("description") or "").strip(),
                "image": e.get("image") or "",
                "body": e.get("body") or "",
                "url": f"{SITE_URL}/archive/{slug}/",
            }
        )
    return posts
