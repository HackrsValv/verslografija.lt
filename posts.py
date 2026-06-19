"""Fetch published posts from the Buttondown API and normalize them."""

import json
import urllib.request

API_BASE = "https://api.buttondown.email/v1/emails"
SITE_URL = "https://verslografija.lt"


def fetch_emails(api_key):
    """All sent emails, newest first (follows pagination)."""
    emails = []
    page = 1
    while True:
        url = f"{API_BASE}?page={page}&status=sent&ordering=-publish_date"
        req = urllib.request.Request(url, headers={"Authorization": f"Token {api_key}"})
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
        emails.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return emails


def prepare_posts(emails):
    """Normalize raw email objects into post dicts. No cap; skips slugless."""
    posts = []
    for e in emails:
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
