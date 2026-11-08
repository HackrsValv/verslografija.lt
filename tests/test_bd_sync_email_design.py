"""Tests for scripts/bd_sync_email_design.py. No network: bd.request is monkeypatched."""

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "bd_sync_email_design.py"
SPEC = importlib.util.spec_from_file_location("bd_sync_email_design", MODULE_PATH)
bd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bd)


class FakeAPI:
    """Stands in for bd.request; records calls and holds fake newsletter state."""

    def __init__(self, newsletter, pending=None, apply_patch=True):
        self.newsletter = newsletter
        self.pending = pending or []
        self.apply_patch = apply_patch
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        if path == "/newsletters":
            # Real API shape: a paginated object, not a bare list.
            return {"results": [self.newsletter]}
        if path.startswith("/emails"):
            return {"results": self.pending}
        if method == "PATCH" and path == f"/newsletters/{bd.NEWSLETTER_ID}":
            if self.apply_patch:
                self.newsletter.update(payload)
            return self.newsletter
        raise AssertionError(f"unexpected API call: {method} {path}")


def current_like_desired(**overrides):
    current = bd.load_desired()
    current["id"] = bd.NEWSLETTER_ID
    current.update(overrides)
    return current


def methods(fake):
    return [method for method, _, _ in fake.calls]


def test_real_template_validates():
    assert bd.validate_template(bd.load_desired()["custom_email_template"]) == []


def test_missing_unsubscribe_fails():
    problems = bd.validate_template("<html>{{ email.subject }}{{ content }}</html>")
    assert any("unsubscribe_url" in p for p in problems)


def test_missing_content_placeholder_fails():
    problems = bd.validate_template("<html>{{ email.subject }}{{ unsubscribe_url }}</html>")
    assert any("content placeholder" in p for p in problems)


def test_content_placeholder_without_spaces_passes():
    html = "{{ unsubscribe_url }}{{content}}{{ email.subject }}"
    assert bd.validate_template(html) == []


def test_token_in_template_fails():
    html = "{{ unsubscribe_url }}{{ content }}{{ email.subject }} Token abcdefghijklmnopqrstuvwxyz1234"
    problems = bd.validate_template(html)
    assert any("token" in p.lower() for p in problems)


def test_plan_changes_ignores_trailing_whitespace():
    current = {"css": "a{}\n\n", "custom_email_template": "<x>1</x>", "template": "custom"}
    desired = {"css": "a{}", "custom_email_template": "<x>1</x>", "template": "custom"}
    assert bd.plan_changes(current, desired) == {}


def test_plan_changes_reports_real_diffs():
    desired = bd.load_desired()
    current = current_like_desired(css="body { color: red; }")
    changes = bd.plan_changes(current, desired)
    assert set(changes) == {"css"}
    assert changes["css"] == ("body { color: red; }", desired["css"])


def test_dry_run_never_patches(monkeypatch):
    fake = FakeAPI(current_like_desired(css="old css"))
    monkeypatch.setattr(bd, "request", fake)
    monkeypatch.setenv("BUTTONDOWN_API_KEY", "test-key")
    assert bd.main([]) == 0
    assert "PATCH" not in methods(fake)


def test_apply_refuses_with_pending_send(tmp_path, monkeypatch, capsys):
    fake = FakeAPI(current_like_desired(css="old css"), pending=[{"subject": "Nr. 42"}])
    monkeypatch.setattr(bd, "request", fake)
    monkeypatch.setenv("BUTTONDOWN_API_KEY", "test-key")
    assert bd.main(["--apply", "--backup-dir", str(tmp_path)]) == 1
    assert "PATCH" not in methods(fake)
    assert "Nr. 42" in capsys.readouterr().out


def test_apply_patches_only_changed_fields_and_writes_backup(tmp_path, monkeypatch):
    fake = FakeAPI(current_like_desired(css="old css"))
    monkeypatch.setattr(bd, "request", fake)
    monkeypatch.setenv("BUTTONDOWN_API_KEY", "test-key")
    assert bd.main(["--apply", "--backup-dir", str(tmp_path)]) == 0
    patches = [call for call in fake.calls if call[0] == "PATCH"]
    assert len(patches) == 1
    _, _, payload = patches[0]
    assert set(payload) == {"css"}
    assert payload["css"] == bd.load_desired()["css"]
    backups = list(tmp_path.glob("newsletter-*.json"))
    assert len(backups) == 1
    saved = json.loads(backups[0].read_text(encoding="utf-8"))
    assert saved["css"] == "old css"
    assert saved["template"] == "custom"
    assert saved["custom_email_template"] == fake.newsletter["custom_email_template"]


def test_apply_readback_mismatch_exits_1(tmp_path, monkeypatch, capsys):
    fake = FakeAPI(current_like_desired(css="old css"), apply_patch=False)
    monkeypatch.setattr(bd, "request", fake)
    monkeypatch.setenv("BUTTONDOWN_API_KEY", "test-key")
    assert bd.main(["--apply", "--backup-dir", str(tmp_path)]) == 1
    assert "PATCH" in methods(fake)
    assert "css" in capsys.readouterr().out


def test_missing_api_key_exits_2(monkeypatch):
    monkeypatch.delenv("BUTTONDOWN_API_KEY", raising=False)
    assert bd.main([]) == 2
