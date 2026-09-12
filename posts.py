"""Fetch published posts from the Buttondown API and normalize them."""

import json
import re
import urllib.request

API_BASE = "https://api.buttondown.email/v1/emails"
SITE_URL = "https://verslografija.lt"


def _excerpt(e, max_chars=200):
    """Meta/og description text: the email's explicit description, else body text.

    Most emails have no description set, so derive one from the body: drop the
    editor comment, a leading h1 (it duplicates the title) and the leading cover
    image, then strip the remaining markup down to plain sentences.
    """
    desc = (e.get("description") or "").strip()
    if desc:
        return desc
    text = e.get("body") or ""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"\A\s*#[^\n]*\n+", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"[#*_`>\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."

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
                "excerpt": _excerpt(e),
                "image": e.get("image") or "",
                "body": e.get("body") or "",
                "url": f"{SITE_URL}/archive/{slug}/",
            }
        )
    return posts


def find_dropped_published(emails):
    """Published emails (sent/imported) that won't become a page (missing slug).

    Build-time guard: if non-empty, the site post count would silently undershoot
    Buttondown's published count. Returns a list of (id, status) for the offenders.
    """
    return [
        (e.get("id"), e.get("status"))
        for e in emails
        if e.get("status") in PUBLISHED_STATUSES and not (e.get("slug") or "").strip()
    ]
