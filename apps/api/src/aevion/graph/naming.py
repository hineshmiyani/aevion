"""Graph names for org graphs (ADR-0011): one FalkorDB graph per GitHub organisation."""

import re

GRAPH_PREFIX = "org:"

# GitHub logins: letters, digits and single hyphens, no leading/trailing hyphen, max 39 chars.
_GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


def graph_name_for(org: str) -> str:
    """Return the FalkorDB graph name for a GitHub organisation (or user) login.

    Every module that touches an org graph (ingest, tools, sync, MCP) calls this, so the
    same org must always map to the same graph. GitHub treats logins case-insensitively:
    "FalkorDB", "falkordb" and "FALKORDB" are one org, so the name is lowercased and data
    can never split across two graphs.
    """
    login = org.strip()
    if not _GITHUB_LOGIN.fullmatch(login):
        raise ValueError(f"Not a valid GitHub login: {org!r}")
    return GRAPH_PREFIX + login.lower()
