"""`__all__` is the contract, and this is what makes it a fact rather than a promise.

`docs/design/packaging.md` ("The export surface") fixes the list at twenty-nine names and
names this module in the paragraph that does it. Adding a public name is then a deliberate
act with a diff on it.

**Partial, deliberately.** Four of the twenty-nine — `Tribunal`, `Judge`, `Advocate`,
`Proceeding` — do not exist yet, so the literal-list assertion cannot land until
`docs/implementations/proceeding-core.md` completes the surface. What lands here is the half
that is assertable today and catches a typo in a re-export the moment it is made.

The *second* list is whole, and asserted literally below.
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


def test_the_four_names_that_do_not_exist_yet_are_not_claimed() -> None:
    """The list grows in `proceeding-core.md`, not by accident before it."""
    for name in ("Tribunal", "Judge", "Advocate", "Proceeding"):
        assert name not in enbanc.__all__
        assert not hasattr(enbanc, name)


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
