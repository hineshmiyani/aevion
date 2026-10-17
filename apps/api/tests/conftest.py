import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / "github" / name).read_text())
    return data


@pytest.fixture
def pr_page() -> dict[str, Any]:
    return _fixture("pull_requests_page.json")


@pytest.fixture
def issue_page() -> dict[str, Any]:
    return _fixture("issues_page.json")
