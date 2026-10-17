"""Reference and closing-keyword parsing."""

import pytest

from aevion.ingest.references import find_closing_references, find_references

REPO = "FalkorDB/falkordb-py"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("See #12 and #13.", {f"{REPO}#12", f"{REPO}#13"}),
        ("Related: FalkorDB/FalkorDB#1200", {"FalkorDB/FalkorDB#1200"}),
        (
            "https://github.com/FalkorDB/GraphRAG-SDK/pull/45 and https://github.com/FalkorDB/docs/issues/7",
            {"FalkorDB/GraphRAG-SDK#45", "FalkorDB/docs#7"},
        ),
        ("Colour `#123` and ```\nline #9\n``` are code", set()),
        ("issue#5 is not a mention, but (#6) is", {f"{REPO}#6"}),
        ("", set()),
        (None, set()),
    ],
)
def test_find_references(text: str | None, expected: set[str]) -> None:
    assert find_references(text, REPO) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Fixes #90", {f"{REPO}#90"}),
        ("closes FalkorDB/FalkorDB#12, resolves #3", {"FalkorDB/FalkorDB#12", f"{REPO}#3"}),
        ("Fixed: https://github.com/FalkorDB/docs/issues/7", {"FalkorDB/docs#7"}),
        ("RESOLVED #4", {f"{REPO}#4"}),
        ("See #90 (doesn't fix it)", set()),
        ("prefix #1", set()),
    ],
)
def test_find_closing_references(text: str, expected: set[str]) -> None:
    assert find_closing_references(text, REPO) == expected
