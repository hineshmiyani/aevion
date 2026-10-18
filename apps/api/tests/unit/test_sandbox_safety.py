"""Nothing posted on the sandbox may notify people or reference other repos' issues."""

from aevion.sandbox.safety import (
    defuse_mentions,
    foreign_references,
    inert_references,
    qualify_bare_refs,
    safe_for_sandbox,
)

SANDBOX = "hineshmiyani/aevion-sandbox"


def test_mentions_become_profile_links() -> None:
    assert defuse_mentions("thanks @gkorland!") == "thanks [gkorland](https://github.com/gkorland)!"
    assert defuse_mentions("mail me@example.com, or `@x`") == "mail me@example.com, or `@x`"


def test_foreign_references_become_code_and_ours_stay_links() -> None:
    text = (
        "Dup of FalkorDB/FalkorDB#12, see [the fix](https://github.com/FalkorDB/FalkorDB/pull/13)"
        " and https://github.com/FalkorDB/docs/issues/14#issuecomment-1. Ours: "
        f"{SANDBOX}#3 and https://github.com/{SANDBOX}/issues/4"
    )
    assert inert_references(text, SANDBOX) == (
        "Dup of `FalkorDB/FalkorDB#12`, see `FalkorDB/FalkorDB#13`"
        " and `FalkorDB/docs#14`. Ours: "
        f"{SANDBOX}#3 and https://github.com/{SANDBOX}/issues/4"
    )


def test_code_is_left_alone() -> None:
    text = "```\nFalkorDB/FalkorDB#1 @bob\n```\nand `x/y#2`"
    assert safe_for_sandbox(text, SANDBOX) == text


def test_bare_refs_in_copied_text_mean_the_original_repo() -> None:
    copied = qualify_bare_refs("Regression from #3301, not `#9`, see &#39;", "FalkorDB/FalkorDB")
    assert copied == "Regression from FalkorDB/FalkorDB#3301, not `#9`, see &#39;"
    assert safe_for_sandbox(copied, SANDBOX) == (
        "Regression from `FalkorDB/FalkorDB#3301`, not `#9`, see &#39;"
    )


def test_links_with_code_text_and_autolinks_are_made_inert() -> None:
    # Seen in production: link text in a code span, which split the link in two.
    text = (
        "fixed by [`FalkorDB/FalkorDB#2279`](https://github.com/FalkorDB/FalkorDB/pull/2279), "
        "see <https://github.com/FalkorDB/docs/issues/9> and [ours](https://github.com/"
        f"{SANDBOX}/issues/2)"
    )
    out = inert_references(text, SANDBOX)
    assert "github.com/FalkorDB" not in out
    assert out.startswith("fixed by `FalkorDB/FalkorDB#2279`, see <`FalkorDB/docs#9`>")
    assert f"[ours](https://github.com/{SANDBOX}/issues/2)" in out


def test_foreign_references_finds_what_would_leak() -> None:
    risky = "cc @bob, see FalkorDB/FalkorDB#1 and https://github.com/FalkorDB/docs/pull/2"
    assert foreign_references(risky, SANDBOX) == ["@bob", "FalkorDB/docs#2", "FalkorDB/FalkorDB#1"]
    assert foreign_references(safe_for_sandbox(risky, SANDBOX), SANDBOX) == []
    assert foreign_references(f"`@x` and {SANDBOX}#4", SANDBOX) == []
