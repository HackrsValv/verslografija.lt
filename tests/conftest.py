import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_emails():
    return json.loads((FIXTURES / "emails_sample.json").read_text())


@pytest.fixture
def plain_email(sample_emails):
    return next(e for e in sample_emails if e["slug"] == "pasaku-taskai")


@pytest.fixture
def fancy_email(sample_emails):
    return next(e for e in sample_emails if e["slug"] == "ziurek-ka-darau")
