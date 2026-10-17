import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def pr_page() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / "github" / "pull_requests_page.json").read_text())
    return data
