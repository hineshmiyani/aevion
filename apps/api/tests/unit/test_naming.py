"""Org logins map to exactly one graph name, whatever their case or spelling."""

import pytest

from aevion.graph.naming import graph_name_for


@pytest.mark.parametrize("org", ["FalkorDB", "falkordb", "FALKORDB", "  FalkorDB  "])
def test_same_org_always_maps_to_one_graph(org: str) -> None:
    assert graph_name_for(org) == "org:falkordb"


def test_hyphenated_login() -> None:
    assert graph_name_for("aevion-sandbox") == "org:aevion-sandbox"


@pytest.mark.parametrize(
    "org",
    ["", "   ", "-leading", "trailing-", "double--hyphen", "has space", "org/repo", "a" * 40],
)
def test_invalid_logins_are_rejected(org: str) -> None:
    with pytest.raises(ValueError):
        graph_name_for(org)


def test_longest_valid_login() -> None:
    assert graph_name_for("a" * 39) == "org:" + "a" * 39
