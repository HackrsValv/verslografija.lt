#!/usr/bin/env python3
"""Build verslografija.lt: landing, archive index, and one page per post.

Fetches published posts from the Buttondown API and renders static HTML to the
repo root for GitHub Pages.

Usage:
    BUTTONDOWN_API_KEY=xxx python build.py
    python build.py --key-file memory/buttondown-key.txt
    python build.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

import pages
import posts

SITE_DIR = Path(__file__).parent
SITE_URL = posts.SITE_URL


def get_api_key():
    key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if key:
        return key
    for path in [SITE_DIR / "memory" / "buttondown-key.txt", Path.home() / ".buttondown-key"]:
        if path.exists():
            key = path.read_text().strip()
            if key and "PASTE" not in key:
                return key
    print("Error: No API key found. Set BUTTONDOWN_API_KEY or use --key-file.", file=sys.stderr)
    sys.exit(1)


def _sitemap(prepared):
    urls = [f"{SITE_URL}/", f"{SITE_URL}/archive/"] + [p["url"] for p in prepared]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


def write_site(prepared, out_dir):
    """Render and write all pages. Raises ValueError(slug) on an empty body."""
    if not prepared:
        raise ValueError("no posts to build")
    written = []

    landing_html = pages.landing(prepared[:4])
    (out_dir / "index.html").write_text(landing_html)
    written.append(out_dir / "index.html")

    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(pages.archive_index(prepared))
    written.append(archive_dir / "index.html")

    # newest-first: prev = older (next index), nxt = newer (previous index)
    for i, post in enumerate(prepared):
        if not post["body"].strip():
            raise ValueError(f"empty body for post: {post['slug']}")
        prev = prepared[i + 1] if i + 1 < len(prepared) else None
        nxt = prepared[i - 1] if i > 0 else None
        page_dir = archive_dir / post["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(pages.post_page(post, prev, nxt))
        written.append(page_dir / "index.html")

    (out_dir / "sitemap.xml").write_text(_sitemap(prepared))
    written.append(out_dir / "sitemap.xml")
    return written


def main():
    parser = argparse.ArgumentParser(description="Build verslografija.lt")
    parser.add_argument("--key-file", help="Path to Buttondown API key file")
    parser.add_argument("--dry-run", action="store_true", help="Build to a temp dir and report")
    args = parser.parse_args()

    if args.key_file:
        os.environ["BUTTONDOWN_API_KEY"] = Path(args.key_file).read_text().strip()

    api_key = get_api_key()
    print("Fetching posts from Buttondown API...")
    emails = posts.fetch_emails(api_key)
    prepared = posts.prepare_posts(emails)
    print(f"  {len(prepared)} posts")

    out = SITE_DIR
    if args.dry_run:
        import tempfile
        out = Path(tempfile.mkdtemp(prefix="vg-build-"))

    written = write_site(prepared, out)
    print(f"Wrote {len(written)} files to {out}")


if __name__ == "__main__":
    main()
