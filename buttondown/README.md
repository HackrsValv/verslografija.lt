# Buttondown email design

The newsletter stays on Buttondown's "modern" template. The synced source of
truth is:

- `theme.css` — custom CSS for newsletter emails (Pulp Press theme).
- `footer.md` — newsletter footer (plain markdown/HTML). The sync refuses
  `{{ }}` tags here because Buttondown does not document tag rendering in the
  footer field.

These two files are synced to the newsletter by the GitHub Actions workflow
`.github/workflows/sync-email-design.yml` (via
`scripts/bd_sync_email_design.py`):

- Pull request → dry run (validates the footer and prints the diff, writes nothing).
- Merge to `main` → applies the changes to the newsletter.
- Manual run (`workflow_dispatch`) → dry run, or apply when the `apply` input is checked.

`email-template.html` is the Pulp Press custom wrapper. It is **not** synced:
the current Buttondown plan does not include the Naked (custom) email template,
so the newsletter cannot use it. The file is kept for when the plan allows
custom templates — to activate it later, re-add it to `load_desired()` in
`scripts/bd_sync_email_design.py` and set `template` to `"custom"` there.

Requires the repository secret `BUTTONDOWN_WRITE_API_KEY` — a Buttondown API
key allowed to edit newsletter settings. Fork PRs get no secrets, so the sync
steps skip them ("no key, skipping").

Rollback: download the `bd-backup` artifact from the apply run (it holds the
previous remote values of the synced fields — css, footer, template — plus the
custom template), put those values back (re-apply via a manual run after
restoring the files, or set them in the Buttondown dashboard), or revert the
commit and merge the revert.

Note: `{{ content }}` is not documented by Buttondown. If a test send shows an
empty body, switch to `{{ body }}` (or `{{ email.body }}`) in
`email-template.html`.
