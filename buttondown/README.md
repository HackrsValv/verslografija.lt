# Buttondown email design

- `theme.css` — custom CSS for newsletter emails (Pulp Press theme).
- `email-template.html` — custom email wrapper template (Django-style `{{ }}` tags).

These two files are the source of truth for the Buttondown email design. The
GitHub Actions workflow `.github/workflows/sync-email-design.yml` (via
`scripts/bd_sync_email_design.py`) syncs them to the newsletter:

- Pull request → dry run (validates the template and prints the diff, writes nothing).
- Merge to `main` → applies the changes to the newsletter.
- Manual run (`workflow_dispatch`) → dry run, or apply when the `apply` input is checked.

Requires the repository secret `BUTTONDOWN_WRITE_API_KEY` — a Buttondown API
key allowed to edit newsletter settings. Fork PRs get no secrets, so the sync
steps skip them ("no key, skipping").

Rollback: download the `bd-backup` artifact from the apply run (it holds the
previous remote values of the three synced fields), put those values back
(re-apply via a manual run after restoring the files, or set them in the
Buttondown dashboard), or revert the commit and merge the revert.

Note: `{{ content }}` is not documented by Buttondown. If a test send shows an
empty body, switch to `{{ body }}` (or `{{ email.body }}`) in
`email-template.html`.
