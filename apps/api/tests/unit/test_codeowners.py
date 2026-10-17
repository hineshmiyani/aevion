"""CODEOWNERS parsing and pattern-to-Component mapping."""

import pytest

from aevion.ingest.codeowners import owner_kind, parse_codeowners, pattern_component_path

FALKORDB_CODEOWNERS = """
# Paths whose contents EXECUTE with this repository's credentials
/build/          @FalkorDB/falkordb-core
/.github/        @FalkorDB/falkordb-core

# Listed so weakening the rules above needs the same approval they do.
/CODEOWNERS      @FalkorDB/falkordb-core
src/graph/       @alice @bob  # inline comment
*.md             docs@example.com
"""


def test_parse_skips_comments_and_blank_lines() -> None:
    rules = parse_codeowners(FALKORDB_CODEOWNERS)
    assert [r.pattern for r in rules] == [
        "/build/",
        "/.github/",
        "/CODEOWNERS",
        "src/graph/",
        "*.md",
    ]
    assert rules[3].owners == ("@alice", "@bob")


@pytest.mark.parametrize(
    ("pattern", "depth", "expected"),
    [
        ("/build/", 2, "build"),
        ("/.github/", 2, ".github"),
        ("/src/execution_plan/ops/", 2, "src/execution_plan"),
        ("src/graph/", 2, "src/graph"),
        ("docs/**/*.md", 1, "docs"),
        ("/src/x.c", 2, "src"),
        ("/CODEOWNERS", 2, "(root)"),
        ("*.md", 2, None),
        ("*", 2, None),
    ],
)
def test_pattern_component_path(pattern: str, depth: int, expected: str | None) -> None:
    assert pattern_component_path(pattern, depth) == expected


def test_owner_kind() -> None:
    assert owner_kind("@FalkorDB/falkordb-core") == "team"
    assert owner_kind("@alice") == "person"
    assert owner_kind("docs@example.com") is None


def test_ownership_intervals_track_added_and_removed_owners() -> None:
    from aevion.ingest.codeowners import Ownership, ownership_intervals

    versions = [
        (100, "/src/graph/ @alice\n/build/ @FalkorDB/core"),
        (200, "/src/graph/ @alice @bob\n/build/ @FalkorDB/core"),
        (300, "/src/graph/ @bob\n/build/ @FalkorDB/core"),
    ]
    assert ownership_intervals(versions, depth=2) == [
        Ownership("FalkorDB/core", "team", "build", 100, None),
        Ownership("alice", "person", "src/graph", 100, 300),
        Ownership("bob", "person", "src/graph", 200, None),
    ]
