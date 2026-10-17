"""Keyword helpers shared by the tools that search FalkorDB's full-text indexes.

The indexes find candidates; ranking them by keyword *coverage* (how many of the query's
distinct keywords a text contains) is what makes "gate main on a merge queue" find the
decision about gating main, not one that only repeats "merge queue".
"""

import re

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    ]
)

_WORD = re.compile(r"[a-z0-9]+")


def keywords(text: str) -> list[str]:
    """Distinct lowercase words longer than two letters, minus stopwords, in order."""
    words = _WORD.findall(text.lower())
    return list(dict.fromkeys(w for w in words if len(w) > 2 and w not in STOPWORDS))


def stem(word: str) -> str:
    """Crude suffix stripping, enough to agree with the index's stemmer on common forms."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"  # queries -> query
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def keyword_stems(text: str) -> set[str]:
    return {stem(w) for w in keywords(text)}


def coverage(wanted: set[str], text: str | None) -> float:
    """Share of the wanted keyword stems that appear in text (0 to 1)."""
    if not wanted:
        return 0.0
    present = {stem(w) for w in _WORD.findall((text or "").lower())}
    return len(wanted & present) / len(wanted)
