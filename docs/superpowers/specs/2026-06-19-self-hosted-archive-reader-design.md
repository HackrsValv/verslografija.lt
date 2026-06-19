# Self-Hosted Archive Reader — Design

**Date:** 2026-06-19
**Status:** Approved, ready for implementation plan
**Repo:** `HackrsValv/verslografija.lt` (GitHub Pages, custom domain `verslografija.lt`)

## Problem

Posts are read on Buttondown's hosted archive (`visa.verslografija.lt/archive/<slug>/`). That template imposes accessibility defects we cannot fix from outside it:

- `<html lang="en">` on Lithuanian content (Buttondown's `locale` enum has no `lt`; WCAG 3.1.1).
- Two `<h1>` per page (site name + post subject).
- No image lazy-loading.

`build.py` already fetches every published post via the Buttondown API and renders the landing page. Extending it to render the full reading experience on our own domain removes the dependency on Buttondown's template and closes these gaps. An audit of the Buttondown archive scored 18/20 with a hard ceiling around 18 because those three gaps are template-locked; a self-hosted reader can reach the same 19+ the landing page now holds.

## Scope

This spec covers **Spec 1: the self-hosted reader** only — an archive index plus a page per post on `verslografija.lt`, built from the API. It links alongside the existing Buttondown archive and is independently verifiable.

A later **Spec 2 (hard cutover)** disables Buttondown's public archive and redirects `visa./archive/*` → `verslografija.lt`. That is DNS/hosting work (the `visa.` subdomain CNAMEs to Buttondown; GitHub Pages only does client-side redirects) and must not gate building the reader. Cut over once the reader is proven live. URL scheme below mirrors Buttondown's `/archive/<slug>/` so the phase-2 redirects map 1:1 and old email links translate cleanly.

## Approach

Extend `build.py`, rendering each post from the API `body` field. Chosen over scraping Buttondown's rendered archive (which would keep a runtime dependency on the template we intend to retire) and over hand-porting posts to markdown files (which loses API automation).

## Architecture

`build.py` is currently one file (fetch + `prepare_posts` + landing render). Split into focused modules per the codebase's many-small-files norm:

- `posts.py` — API fetch (paginated, `status=sent`, newest first) and `prepare_posts` → list of post dicts: `slug`, `title` (email `subject`), `date` (`publish_date`), `excerpt` (email `description`), `image`, `body`, `canonical` (our URL).
- `render.py` — body string → clean article HTML. The core module.
- `pages.py` — page templates as pure functions: `landing(posts)`, `archive_index(posts)`, `post_page(post, prev, next)`.
- `build.py` — orchestration: fetch → render each → write files → write sitemap.

Each module has one purpose and is unit-testable in isolation. `pages.py` functions take data and return HTML strings; they touch no I/O.

## Data flow

1. `posts.fetch()` → all sent emails, newest first.
2. `posts.prepare()` → list of post dicts.
3. For each post: `render.article(body)` → article HTML; `pages.post_page(post, prev, next)` → full page; write `site/archive/<slug>/index.html`.
4. `pages.archive_index(posts)` → `site/archive/index.html`.
5. `pages.landing(posts[:4])` → `site/index.html` (existing behavior; internal links rewritten to local `/archive/<slug>/`).
6. `build.sitemap(posts)` → `site/sitemap.xml`.

Prev/next derive from the date-sorted list: prev = older, next = newer.

## Render module (`render.py`)

Input: the email `body`. Steps:

1. Strip the `<!-- buttondown-editor-mode: ... -->` comment (present in both modes).
2. Detect mode:
   - **plain** (11 of 14 current posts): markdown → HTML via **mistune** (pure-Python, no C deps, CI-friendly).
   - **fancy** (3 of 14): already clean semantic HTML; pass through.
3. **Sanitize** with a hand-rolled allowlist built on `html.parser` (no `bleach` dependency; the content is our own, so the pass is for normalization and defense-in-depth, not untrusted input):
   - Tags: `a, p, h2, h3, h4, blockquote, em, strong, ul, ol, li, figure, figcaption, img, sup, hr, code, pre, br`.
   - Attributes: `href`, `src`, `alt`, `id`.
   - Unknown tags are unwrapped (contents kept); unknown attributes dropped.
4. **Post-process** the HTML:
   - Remove the leading cover image (first `<figure>`/`<img>` or `![cover]`); the template renders the cover in its own slot from the email `image` field, controlling alt, lazy-loading, and reserved aspect-ratio.
   - Add `loading="lazy"` and `decoding="async"` to remaining inline `<img>`.
   - Rewrite `https://visa.verslografija.lt/archive/<slug>/` links → `/archive/<slug>/`.
   - Preserve `<sup>` footnotes.

Body content tops out at `<h2>` (verified across all 14 posts); the post title is the page's only `<h1>`.

Observed body inventory (14 sent posts): tags `a, blockquote, em, figcaption, figure, h2, img, li, ol, p, strong, sup`; only special token is the `buttondown-editor-mode` comment. No subscribe widgets, paywalls, or template variables.

## Post page (`pages.py: post_page`)

Pulp-press shell consistent with `style.css`. `<html lang="lt">`. Exactly one `<h1>` (the post title).

- **Head**: `<title>`, meta description (email `description`), Open Graph + Twitter (image, title, description, `og:url` = our canonical), `<link rel="canonical">` → our URL, favicon, `style.css`.
- **Body**: compact masthead (logo links home); `<article>` with mono date, `<h1>` title, cover image (`loading="eager"`, `alt="<title> — iliustracija"`, reserved aspect-ratio to prevent CLS), rendered article HTML at a 65–75ch measure; prev/next nav (`← senesnis` / `naujesnis →`); reused subscribe block from the landing; footer.

New `.post-*` article styles appended to `style.css`: `p`, `h2`/`h3`, `blockquote`, `ul`/`ol`, `figure`/`figcaption`, footnote `sup`. Reuses existing tokens (`--body`, `--display`, `--accent`, etc.).

## Archive index (`pages.py: archive_index`)

`site/archive/index.html`, `lang="lt"`, all posts reverse-chronological. Double-rule list: date (mono) + title (display), each linking to `/archive/<slug>/`. The landing's "Archyvas" nav link repoints from `visa.verslografija.lt/archive/` to local `/archive/`.

## Output structure

```
site/index.html                    landing (internal links rewritten local)
site/archive/index.html            archive list
site/archive/<slug>/index.html     one page per post
site/style.css                     extended with .post-* and .archive-* rules
site/sitemap.xml                   all post URLs
site/assets/                       favicon, logo (existing)
```

Slugs come from the email `slug` field (already URL-safe, matches Buttondown's paths for 1:1 phase-2 redirects). Cover images stay hot-linked from `assets.buttondown.email`, matching the current landing page.

## SEO

- Each post sets `rel=canonical` and `og:url` to its `verslografija.lt` URL (our site is the source of truth under the planned cutover).
- `sitemap.xml` lists every post URL.

## Error handling (andon / stop-the-line)

- Image-less post → existing `.featured-image--placeholder` treatment.
- Empty/malformed body, or a render/sanitize error → **fail the build and name the offending slug.** A broken post is a defect to fix, not to ship. The whole build fails rather than emitting a broken page.
- Slug collisions are not possible (Buttondown enforces unique slugs).

## Testing

- **Unit (`render.py`)**: plain-markdown and fancy-HTML fixtures → assert the editor-mode comment is stripped, the leading cover removed, `loading="lazy"` added to inline images, only allowlisted tags survive, and no `<h1>` appears in body output.
- **Golden**: render all current sent posts → each is well-formed HTML with exactly one `<h1>`, `lang="lt"`, and a self-referential canonical.
- **Integration**: run the build against a recorded API response fixture (no live API in tests) → assert the expected files are written.
- **Browser/a11y**: screenshot and probe a rendered post with `agent-browser` → confirm `lang="lt"`, single `<h1>`, descriptive cover alt, lazy inline images, AAA body contrast, and a visible keyboard focus ring. These are the dimensions the Buttondown archive could not satisfy.

## Locked decisions

- Markdown renderer: **mistune**.
- Sanitizer: **hand-rolled allowlist** on `html.parser` (no `bleach`).
- Cover images: **hot-linked** from Buttondown's CDN.
- **Sitemap** generated.
- Build policy: **fail on any bad post.**
- URL scheme: **`/archive/<slug>/`** (mirrors Buttondown for phase-2 redirects).

## Out of scope (Spec 2)

Disabling Buttondown's public archive, `visa.` subdomain redirects, DNS changes, and setting Buttondown's per-email `canonical_url` to our URLs. Built after the reader is proven live.
