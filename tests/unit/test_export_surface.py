"""`__all__` is the contract, and this is what makes it a fact rather than a promise.

`docs/design/packaging.md` ("The export surface") fixes the list at twenty-nine names and
names this module in the paragraph that does it. Adding a public name is then a deliberate
act with a diff on it.

Both lists are whole and both are asserted literally below. `Proceeding` completed the
twenty-nine in `docs/implementations/proceeding-core.md`; before that this module pinned what
was assertable and said which name was still missing.
"""

import enbanc
import enbanc.tools


def test_every_exported_name_resolves() -> None:
    """A name in `__all__` that resolves to nothing is a `from enbanc import *` that fails
    for a user and passes for us."""
    missing = [name for name in enbanc.__all__ if not hasattr(enbanc, name)]
    assert missing == []


def test_the_list_is_sorted() -> None:
    """So a new name is inserted where it belongs and the diff shows one line."""
    assert list(enbanc.__all__) == sorted(enbanc.__all__)


def test_the_list_holds_no_duplicates() -> None:
    assert len(enbanc.__all__) == len(set(enbanc.__all__))


def test_nothing_exported_is_private() -> None:
    """The privacy of an emit-shape comes from the leading underscore on the *name*, which
    is what keeps `_Exhibit`, `_Interrogatory` and `_Continuance` off this surface."""
    assert [name for name in enbanc.__all__ if name.startswith("_")] == []


def test_the_list_is_the_one_packaging_md_fixes() -> None:
    """Twenty-nine names, asserted as a literal.

    This is `docs/design/packaging.md` ("The export surface") mirrored, which is what makes
    adding a public name a deliberate act with a diff on it rather than a side effect of an
    import. If this fails, either the document or the package moved — and whichever it was,
    the other one is now wrong.
    """
    assert list(enbanc.__all__) == [
        "Advocate",
        "Argument",
        "Case",
        "Concession",
        "ConfigurationError",
        "Continuance",
        "Deliberation",
        "EnbancError",
        "Entry",
        "Exhibit",
        "Filing",
        "Hearing",
        "Interrogatory",
        "Judge",
        "Outcome",
        "Proceeding",
        "ProceedingFailed",
        "ProceedingUnfinished",
        "Response",
        "Retrieval",
        "Ruling",
        "Source",
        "Statute",
        "ToolFailure",
        "Transcript",
        "Tribunal",
        "Undecided",
        "Verdict",
        "VerdictT",
    ]


def test_the_tools_namespace_holds_exactly_one_name() -> None:
    """`docs/design/packaging.md` ("The export surface") fixes `enbanc.tools.__all__` as
    `["web_search"]`, and unlike the top-level list this one is complete today: `web_search`
    is the only tool `0.1.0` ships.

    Importing `enbanc.tools` here does not weaken `test_import_is_inert.py`, which asks
    whether `import enbanc` reaches the subpackage in a subprocess that imports `enbanc` and
    nothing else. That it is a subprocess is exactly what keeps the two modules unrelated.
    """
    assert enbanc.tools.__all__ == ["web_search"]
    assert enbanc.tools.web_search is not None
