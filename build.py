#!/usr/bin/env python3
"""
Build verslografija.lt landing page from Buttondown API.

Fetches latest published posts, extracts cover images and excerpts,
generates a static index.html. Designed to run in GitHub Actions
or locally.

Usage:
    BUTTONDOWN_API_KEY=xxx python build.py
    # or
    python build.py --key-file ../memory/buttondown-key.txt
"""

import json
import os
import re
import sys
import urllib.request
from html import escape
from pathlib import Path
from textwrap import dedent

API_BASE = "https://api.buttondown.email/v1/emails"
ARCHIVE_BASE = "https://visa.verslografija.lt/archive"
SITE_DIR = Path(__file__).parent
MAX_POSTS = 4  # 1 featured + 3 grid


def get_api_key():
    """Get Buttondown API key from env or file."""
    key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if key:
        return key

    # Try local key file
    for path in [
        SITE_DIR.parent / "memory" / "buttondown-key.txt",
        Path.home() / ".buttondown-key",
    ]:
        if path.exists():
            key = path.read_text().strip()
            if key and "PASTE" not in key:
                return key

    print("Error: No API key found.", file=sys.stderr)
    print("Set BUTTONDOWN_API_KEY env var or create memory/buttondown-key.txt", file=sys.stderr)
    sys.exit(1)


def fetch_emails(api_key):
    """Fetch all published emails from Buttondown, newest first."""
    emails = []
    page = 1

    while True:
        url = f"{API_BASE}?page={page}&status=sent&ordering=-publish_date"
        req = urllib.request.Request(url, headers={"Authorization": f"Token {api_key}"})

        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        results = data.get("results", [])
        if not results:
            break

        emails.extend(results)
        if not data.get("next"):
            break
        page += 1

    return emails


def extract_first_image(body):
    """Extract the first image URL from markdown/HTML body."""
    # Try markdown image syntax first
    md_match = re.search(r'!\[.*?\]\((https://assets\.buttondown\.email/images/[^)]+)\)', body)
    if md_match:
        return md_match.group(1)

    # Try HTML img tag
    html_match = re.search(r'<img[^>]+src="(https://assets\.buttondown\.email/images/[^"]+)"', body)
    if html_match:
        return html_match.group(1)

    # Try any image URL (unsplash etc.)
    any_match = re.search(r'(?:src="|!\[.*?\]\()(https://[^")\s]+\.(?:png|jpg|jpeg|webp)[^")\s]*)', body)
    if any_match:
        return any_match.group(1)

    return None


def extract_excerpt(body, max_chars=200):
    """Extract a clean text excerpt from post body."""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', body)
    # Strip markdown images
    text = re.sub(r'!\[.*?\]\([^)]+\)', '', text)
    # Strip markdown formatting
    text = re.sub(r'[#*_`~\[\]]', '', text)
    # Strip HTML comments
    text = re.sub(r'<!--.*?-->', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Skip very short fragments (headers, etc.)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 30]

    excerpt = ""
    for sentence in sentences:
        if len(excerpt) + len(sentence) > max_chars:
            break
        excerpt += sentence + " "

    excerpt = excerpt.strip()
    if not excerpt and text:
        excerpt = text[:max_chars].rsplit(' ', 1)[0] + "..."

    return excerpt


def prepare_posts(emails):
    """Prepare post data for rendering."""
    posts = []
    for email in emails:
        if len(posts) >= MAX_POSTS:
            break

        subject = email.get("subject", "")
        slug = email.get("slug", email.get("id", ""))
        body = email.get("body", "")
        publish_date = email.get("publish_date", "")[:10]
        image_url = extract_first_image(body)
        excerpt = extract_excerpt(body)

        posts.append({
            "title": subject,
            "slug": slug,
            "date": publish_date,
            "url": f"{ARCHIVE_BASE}/{slug}/",
            "image": image_url,
            "excerpt": excerpt,
        })

    return posts


def render_card(post, index):
    """Render a single post card."""
    title_escaped = escape(post["title"])
    date = post["date"]
    url = post["url"]

    if post["image"]:
        image_html = f'''<div class="card-image">
                        <img src="{post["image"]}"
                             alt="{title_escaped} — iliustracija"
                             loading="lazy">
                    </div>'''
    else:
        image_html = '''<div class="card-image card-image--placeholder">
                        <span class="card-image-v">V</span>
                    </div>'''

    return f'''
                <a href="{url}" class="card">
                    {image_html}
                    <div class="card-content">
                        <span class="card-date">{date}</span>
                        <h3 class="card-title">{title_escaped}</h3>
                    </div>
                </a>
'''


def render_page(posts):
    """Render the full index.html page."""
    if not posts:
        print("Warning: No posts found!", file=sys.stderr)
        return None

    featured = posts[0]
    grid_posts = posts[1:4]

    # Featured image
    if featured["image"]:
        featured_image = f'''<div class="featured-image">
                    <img src="{featured["image"]}"
                         alt="{escape(featured["title"])} — iliustracija"
                         loading="eager">
                </div>'''
        og_image = featured["image"]
    else:
        featured_image = '''<div class="featured-image featured-image--placeholder">
                    <span class="card-image-v">V</span>
                </div>'''
        og_image = ""

    # Grid cards
    cards_html = "".join(render_card(p, i) for i, p in enumerate(grid_posts))

    # OG image meta
    og_image_meta = ""
    if og_image:
        og_image_meta = f'''<meta property="og:image" content="{og_image}">
    <meta name="twitter:image" content="{og_image}">'''

    return dedent(f'''\
<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verslo Grafija</title>
    <meta name="description" content="Stato tvorą atviroje pievoje. Optimizuoja procesą, kuris neturėjo egzistuoti. Cituoja eksperimentą, kurio nebuvo.">

    <!-- Open Graph -->
    <meta property="og:title" content="Verslo Grafija">
    <meta property="og:description" content="Stato tvorą atviroje pievoje. Optimizuoja procesą, kuris neturėjo egzistuoti. Cituoja eksperimentą, kurio nebuvo.">
    {og_image_meta}
    <meta property="og:type" content="website">
    <meta property="og:locale" content="lt_LT">
    <meta property="og:url" content="https://verslografija.lt">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Verslo Grafija">
    <meta name="twitter:description" content="Stato tvorą atviroje pievoje. Optimizuoja procesą, kuris neturėjo egzistuoti. Cituoja eksperimentą, kurio nebuvo.">

    <link rel="icon" type="image/x-icon" href="assets/favicon.ico">
    <link rel="icon" type="image/png" sizes="64x64" href="assets/favicon-verslografija.png">
    <link rel="stylesheet" href="style.css">
</head>
<body>

    <!-- === MASTHEAD === -->
    <header class="masthead">
        <div class="masthead-inner">
            <a href="/" class="masthead-logo" aria-label="Verslo Grafija">
                <img src="assets/logo-verslografija.svg" alt="V" width="64" height="64">
            </a>
            <h1 class="masthead-title">Verslo Grafija</h1>
            <p class="masthead-tagline">Visi kažką žiūrim, o kartais ir parašom</p>
            <nav class="masthead-nav">
                <a href="#naujausios">Naujausios</a>
                <a href="#prenumeruoti">Prenumeruoti</a>
                <a href="https://visa.verslografija.lt/archive/">Archyvas</a>
            </nav>
        </div>
    </header>

    <main>

        <!-- === FEATURED POST === -->
        <section class="featured" id="naujausios">
            <a href="{featured["url"]}" class="featured-link">
                {featured_image}
                <div class="featured-content">
                    <span class="featured-date">{featured["date"]}</span>
                    <h2 class="featured-title">{escape(featured["title"])}</h2>
                    <p class="featured-excerpt">
                        {escape(featured["excerpt"])}
                    </p>
                    <span class="featured-cta">Skaityti &rarr;</span>
                </div>
            </a>
        </section>

        <!-- === POST GRID === -->
        <section class="post-grid">
            <h2 class="section-header">Šviežiausi įrašai</h2>
            <div class="grid">
{cards_html}
            </div>
        </section>

        <!-- === SUBSCRIBE === -->
        <section class="subscribe" id="prenumeruoti">
            <div class="subscribe-inner">
                <img src="assets/logo-verslografija.svg" alt="V" class="subscribe-logo" width="80" height="80">
                <p class="subscribe-tagline">Visi kažką žiūrim, o kartais ir parašom</p>
                <form action="https://buttondown.com/api/emails/embed-subscribe/verslografija"
                      method="post"
                      target="popupwindow"
                      class="subscribe-form">
                    <label for="bd-email" class="sr-only">El. paštas</label>
                    <input type="email"
                           name="email"
                           id="bd-email"
                           placeholder="El. paštas"
                           required>
                    <button type="submit">Prenumeruoti</button>
                </form>
                <p class="subscribe-note">Šlamštas iš vidaus</p>
            </div>
        </section>


    </main>

    <!-- === FOOTER === -->
    <footer class="footer">
        <div class="footer-inner">
            <a href="https://visa.verslografija.lt/archive/" class="footer-archive">Visas archyvas &rarr;</a>
            <p class="footer-copy">&copy; 2024&ndash;2026 Verslo Grafija</p>
        </div>
    </footer>

</body>
</html>
''')


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build verslografija.lt landing page")
    parser.add_argument("--key-file", help="Path to Buttondown API key file")
    parser.add_argument("--dry-run", action="store_true", help="Print output instead of writing")
    args = parser.parse_args()

    if args.key_file:
        os.environ["BUTTONDOWN_API_KEY"] = Path(args.key_file).read_text().strip()

    api_key = get_api_key()
    print("Fetching posts from Buttondown API...")
    emails = fetch_emails(api_key)
    print(f"  Found {len(emails)} published emails")

    posts = prepare_posts(emails)
    print(f"  Using {len(posts)} posts for landing page:")
    for i, p in enumerate(posts):
        img_status = "has image" if p["image"] else "no image"
        label = "FEATURED" if i == 0 else f"CARD {i}"
        print(f"    [{label}] {p['date']} — {p['title']} ({img_status})")

    html = render_page(posts)
    if html is None:
        sys.exit(1)

    if args.dry_run:
        print(html)
    else:
        output = SITE_DIR / "index.html"
        output.write_text(html)
        print(f"\nWritten to {output}")
        print(f"  Size: {len(html):,} bytes")


if __name__ == "__main__":
    main()
