"""Sync the Buttondown newsletter email design (custom CSS + wrapper template) from repo files.

The source of truth is buttondown/theme.css and buttondown/email-template.html;
this script pushes them to the newsletter via the Buttondown API. Dry run by
default (validate + diff); --apply writes, but refuses while an email is
mid-send so a queued issue never ships with a half-old design.
"""

import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_ROOT = "https://api.buttondown.com/v1"
NEWSLETTER_ID = "f1962486-73ba-43e9-b67e-81b87118f888"
NEWSLETTER_USERNAME = "verslografija"

ROOT = Path(__file__).resolve().parent.parent
THEME_CSS = ROOT / "buttondown" / "theme.css"
EMAIL_TEMPLATE = ROOT / "buttondown" / "email-template.html"

FIELDS = ("css", "custom_email_template", "template")

# Emails in these statuses are queued to go out; --apply refuses while any
# exist so a pending issue doesn't ship with a mismatched design.
PENDING_STATUSES = ("scheduled", "about_to_send", "in_flight")

CONTENT_PLACEHOLDER = re.compile(r"\{\{\s*(content|body|email\.body)\s*\}\}")
SECRET_IN_TEMPLATE = re.compile(r"Token [A-Za-z0-9]{20,}")


class SyncError(Exception):
    """An API call failed. Message carries method/path/status, never the token."""


def request(method, path, token, payload=None):
    """One API call, JSON in/out. Raises SyncError on HTTPError (with JSON detail)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "X-Buttondown-Newsletter": NEWSLETTER_USERNAME,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read()).get("detail", "")
        except Exception:
            pass
        message = f"{method} {path} -> HTTP {e.code}"
        if detail:
            message += f": {detail}"
        raise SyncError(message) from e
    return json.loads(body) if body else None


def load_desired():
    """The repo files as they should exist on Buttondown."""
    return {
        "css": THEME_CSS.read_text(encoding="utf-8"),
        "custom_email_template": EMAIL_TEMPLATE.read_text(encoding="utf-8"),
        "template": "custom",
    }


def validate_template(html):
    """List of problems with the wrapper template (empty = ok)."""
    problems = []
    if not re.search(r"\{\{\s*unsubscribe_url\s*\}\}", html):
        problems.append("missing required {{ unsubscribe_url }}")
    if not CONTENT_PLACEHOLDER.search(html):
        problems.append(
            "missing content placeholder ({{ content }} / {{ body }} / {{ email.body }})"
        )
    if not re.search(r"\{\{\s*email\.subject\s*\}\}", html):
        problems.append("missing required {{ email.subject }}")
    for forbidden in ("buttondown-key", "api_key"):
        if forbidden in html:
            problems.append(f"template contains forbidden string {forbidden!r}")
    if SECRET_IN_TEMPLATE.search(html):
        problems.append('template contains what looks like an API token ("Token " + 20+ alphanumerics)')
    return problems


def fetch_current(token):
    """The newsletter object with our id (SyncError if the API doesn't list it)."""
    data = request("GET", "/newsletters", token)
    for newsletter in data.get("results", []):
        if newsletter.get("id") == NEWSLETTER_ID:
            return newsletter
    raise SyncError(f"GET /newsletters did not include newsletter {NEWSLETTER_ID}")


def pending_sends(token):
    """Subjects of emails queued to send right now."""
    subjects = []
    for status in PENDING_STATUSES:
        data = request("GET", f"/emails?status={status}&page_size=100", token)
        subjects.extend(str(e.get("subject") or "(no subject)") for e in data.get("results", []))
    return subjects


def plan_changes(current, desired):
    """{field: (old, new)} for fields that differ; trailing whitespace alone is not a change."""
    changes = {}
    for field, new in desired.items():
        old = current.get(field) or ""
        if old.rstrip() != new.rstrip():
            changes[field] = (old, new)
    return changes


def _print_changes(changes):
    for field, (old, new) in changes.items():
        print(f"changed: {field} ({len(old)} -> {len(new)} chars)")
        diff = difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"current/{field}",
            tofile=f"desired/{field}",
            lineterm="",
        )
        for i, line in enumerate(diff):
            if i >= 80:
                print("... diff truncated ...")
                break
            print(line)


def _write_backup(current, backup_dir):
    """Snapshot the remote values about to be overwritten."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"newsletter-{stamp}.json"
    path.write_text(
        json.dumps({field: current.get(field) for field in FIELDS}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"backup written: {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write to Buttondown (default: dry run)")
    parser.add_argument("--backup-dir", default=".bd-backup/", help="where --apply backups go")
    args = parser.parse_args(argv)

    token = os.environ.get("BUTTONDOWN_API_KEY")
    if not token:
        print("BUTTONDOWN_API_KEY is not set; cannot sync email design", file=sys.stderr)
        return 2

    desired = load_desired()
    problems = validate_template(desired["custom_email_template"])
    if problems:
        for problem in problems:
            print(f"invalid template: {problem}")
        return 1

    try:
        current = fetch_current(token)
        changes = plan_changes(current, desired)
        if changes:
            _print_changes(changes)
        else:
            print("no changes")

        if not args.apply:
            print("dry run; re-run with --apply to write")
            return 0

        queued = pending_sends(token)
        if queued:
            print("refusing to apply, these emails are pending send:")
            for subject in queued:
                print(f"  - {subject}")
            return 1

        _write_backup(current, args.backup_dir)
        if changes:
            request(
                "PATCH",
                f"/newsletters/{NEWSLETTER_ID}",
                token,
                payload={field: new for field, (old, new) in changes.items()},
            )
            updated = fetch_current(token)
            mismatched = [
                field
                for field, (old, new) in changes.items()
                if (updated.get(field) or "").rstrip() != new.rstrip()
            ]
            if mismatched:
                print("verification failed, field(s) did not update: " + ", ".join(mismatched))
                return 1
        print("applied and verified")
        return 0
    except SyncError as e:
        print(f"sync error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
