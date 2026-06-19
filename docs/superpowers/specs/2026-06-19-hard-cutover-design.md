# Hard Cutover: Retire the Buttondown Archive — Design

**Date:** 2026-06-19
**Status:** Approved, ready for implementation plan
**Depends on:** Spec 1 (self-hosted archive reader) — shipped and live at `verslografija.lt/archive/`.

## Problem

`visa.verslografija.lt/archive/<slug>/` is Buttondown's hosted archive. Spec 1 replaced its reading experience with self-hosted pages on `verslografija.lt`, but `visa.` still serves Buttondown's copy, and every already-sent email links to `visa.` URLs. The goal is to retire `visa.` as a live destination and send all its traffic to the self-hosted pages, without breaking the links in sent emails.

## Constraints (verified)

- `visa.verslografija.lt` currently resolves via `CNAME custom-domains.buttondown.com`. Buttondown serves the archive there.
- `verslografija.lt` apex points to GitHub Pages; `www` → `hackrsvalv.github.io`. The owner controls DNS.
- DNS is hosted at the `.lt` registrar (`domreg.lt` / nameservers `u1`–`u4.domains.lt`). It is not behind Cloudflare, so no server-side redirect rules are available without a provider migration.
- The Buttondown email-sending domain is `siuncia.verslografija.lt` and must not be touched.
- Buttondown exposes no API to disable the public archive. Repointing the `visa.` DNS record away from `custom-domains.buttondown.com` is sufficient: Buttondown stops serving `visa.` once DNS no longer points at it.
- The self-hosted post pages already set `rel="canonical"` to their `verslografija.lt` URL and are listed in `sitemap.xml`, so search-engine authority already favors the new URLs.

## Approach

Stand up a tiny GitHub Pages "redirector" site bound to `visa.verslografija.lt` that forwards every path to the same path on `verslografija.lt`. Repoint the `visa.` DNS record to GitHub Pages. The path map is a pure 1:1 (`visa./archive/<slug>/` → `verslografija.lt/archive/<slug>/`), so a single wildcard rule covers all posts with no per-slug enumeration.

Rejected: migrating DNS to Cloudflare for true 301s (touches the email domain's records and all DNS, high blast radius for marginal SEO gain given canonical + sitemap already exist). Rejected: per-slug `<meta http-equiv="refresh">` stubs (needs its own sync build; gains nothing over a wildcard since the mapping is uniform).

## Mechanism: wildcard `404.html`

GitHub Pages serves a repository's `404.html` for any path it cannot match. A redirector repo containing only a `404.html` therefore intercepts every incoming path. The page reads `location.pathname` (plus query and hash) and redirects to the same path on `verslografija.lt`. This is client-side (the HTTP status is 404 before the JS runs), which is acceptable here because these are retired URLs whose canonical authority already lives on `verslografija.lt`.

## Components

### New repo: `HackrsValv/visa-redirect`

Public, GitHub Pages enabled (source: `main` branch, root). Three files:

- `CNAME` — single line: `visa.verslografija.lt`.
- `404.html` — wildcard redirector:
  ```html
  <!DOCTYPE html>
  <html lang="lt">
  <head>
    <meta charset="UTF-8">
    <meta name="robots" content="noindex">
    <link rel="canonical" href="https://verslografija.lt/">
    <script>
      location.replace("https://verslografija.lt" + location.pathname + location.search + location.hash);
    </script>
  </head>
  <body>
    <p>Persikėlėme. <a id="go" href="https://verslografija.lt/">Tęsti &rarr;</a></p>
    <script>
      document.getElementById("go").href =
        "https://verslografija.lt" + location.pathname + location.search + location.hash;
    </script>
  </body>
  </html>
  ```
- `index.html` — the root (`visa.verslografija.lt/`) is a real match (not a 404), so it needs its own redirect to `https://verslografija.lt/archive/`:
  ```html
  <!DOCTYPE html>
  <html lang="lt">
  <head>
    <meta charset="UTF-8">
    <meta name="robots" content="noindex">
    <link rel="canonical" href="https://verslografija.lt/archive/">
    <meta http-equiv="refresh" content="0; url=https://verslografija.lt/archive/">
    <script>location.replace("https://verslografija.lt/archive/");</script>
  </head>
  <body><p>Persikėlėme. <a href="https://verslografija.lt/archive/">Archyvas &rarr;</a></p></body>
  </html>
  ```

The `<noscript>` path is covered for the root by `meta refresh`; for deep paths the visible link is JS-filled, and a no-JS visitor sees the "Persikėlėme" link to the home page. No-JS deep-link fidelity is a deliberate non-goal (negligible audience; canonical + sitemap carry SEO).

### DNS change (owner-performed, at `domreg.lt`)

Repoint the `visa` record:

- From: `CNAME visa → custom-domains.buttondown.com`
- To: `CNAME visa → hackrsvalv.github.io`

This is the single manual step the owner performs; the implementer cannot change DNS.

### Buttondown cleanup (optional, after cutover verified)

Once `visa.` serves the redirector, optionally remove the custom domain from the Buttondown newsletter settings to avoid Buttondown re-claiming it. Not required for correctness.

## Sequencing and safety

1. Create and publish the `visa-redirect` repo; enable Pages; confirm it builds (it will not serve on `visa.` until DNS moves, but the build must be green).
2. Owner repoints the `visa.` DNS record.
3. During DNS propagation there is no downtime: resolvers still pointing at Buttondown get the old archive; resolvers seeing the new record get the redirector. Both destinations are valid.
4. After propagation, verify (below), then optionally do the Buttondown cleanup.

## Rollback

Repoint the `visa.` CNAME back to `custom-domains.buttondown.com`. Buttondown resumes serving within propagation time. No data is lost; the redirector repo can stay in place, dormant.

## Verification

- GitHub Pages for `visa-redirect` shows the custom domain `visa.verslografija.lt` as configured with a valid certificate.
- After propagation: `curl -sI https://visa.verslografija.lt/archive/story-points/` returns HTTP 404 with the redirector HTML body (the JS redirect is not visible to `curl`); fetching the body confirms it contains the `location.replace` to `https://verslografija.lt/archive/story-points/`.
- In a browser, `visa.verslografija.lt/archive/story-points/` lands on `verslografija.lt/archive/story-points/`; the root `visa.verslografija.lt/` lands on `verslografija.lt/archive/`.
- Spot-check three more slugs from the sitemap.

## Out of scope

- Updating links inside already-sent emails (immutable; the redirect is exactly what covers them).
- Changing how future emails are composed (a separate, optional follow-up: point new email "view in browser" / archive links at `verslografija.lt/archive/<slug>/`).
- Any change to the `siuncia.verslografija.lt` email domain or its DNS.

## Locked decisions

- Redirector: **GitHub Pages wildcard `404.html`** in a new repo `HackrsValv/visa-redirect`.
- DNS: **repoint `visa.` CNAME → `hackrsvalv.github.io`** at `domreg.lt` (owner-performed).
- Redirect type: **client-side** (acceptable; canonical + sitemap already in place).
- Rollback: **CNAME back to `custom-domains.buttondown.com`**.
