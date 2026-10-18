"""Derive Components from file paths (ADR-0011: Components are directory prefixes)."""

from collections.abc import Mapping
from pathlib import PurePosixPath

ROOT_COMPONENT = "(root)"
_DOC_SUFFIXES = {".md", ".mdx", ".rst"}


def component_path(path: str, depth: int, overrides: Mapping[str, int] | None = None) -> str:
    """The first `depth` directories of `path`; files at the repo root map to "(root)".

    `overrides` maps a directory prefix to a deeper depth for repos that nest their code,
    e.g. {"graphrag_sdk/src/graphrag_sdk": 4}; the longest matching prefix wins.

    >>> component_path("src/execution_plan/ops/op_filter.c", 2)
    'src/execution_plan'
    >>> component_path("falkordb/graph.py", 2)
    'falkordb'
    >>> component_path("README.md", 2)
    '(root)'
    """
    directories = PurePosixPath(path).parts[:-1]
    for prefix in sorted(overrides or {}, key=len, reverse=True):
        if path.startswith(prefix.rstrip("/") + "/"):
            depth = overrides[prefix]  # type: ignore[index]
            break
    return "/".join(directories[:depth]) or ROOT_COMPONENT


def component_key(
    repo_full_name: str, path: str, depth: int, overrides: Mapping[str, int] | None = None
) -> str:
    return f"{repo_full_name}:{component_path(path, depth, overrides)}"


def is_doc(path: str) -> bool:
    pure = PurePosixPath(path)
    return pure.suffix.lower() in _DOC_SUFFIXES or (pure.parts[:1] == ("docs",))
