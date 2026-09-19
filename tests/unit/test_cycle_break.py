"""The package's one forced import cycle, and the half of the break a test can see.

`docs/decisions/0026-one-renderer-serves-both-audiences.md` puts one renderer behind both the
agents' views and `Transcript.render()`, so the renderer needs `Transcript` for its signature
and `Transcript` needs the renderer for its method. `docs/design/packaging.md` ("What imports
what") breaks it in one direction: `_transcript` imports `_prompting` for real, and
`_prompting` imports `_transcript` under `TYPE_CHECKING` only.

**This test is one half of the guarantee.** That the name is not bound at runtime is what it
asserts; that the annotation still resolves is `make typecheck`'s, and pyright runs in
`check-all` and in CI. A subprocess that imported `_prompting` alone would prove more and
cannot be written — importing it goes through `enbanc/__init__.py`, which imports
`_transcript` regardless.
"""

from typing import Any

import enbanc._prompting as prompting
from enbanc import Transcript
from enbanc._prompting import ReviewerView, render


def test_the_renderer_binds_no_transcript_at_runtime() -> None:
    """The `TYPE_CHECKING` guard, observed from outside. `Entry` and the two ledger row types
    are under the same guard for the same reason."""
    for name in ("Transcript", "Entry", "Retrieval", "ToolFailure"):
        assert not hasattr(prompting, name), f"_prompting bound {name} at runtime"


def test_the_renderer_dispatches_on_filings_which_it_does_import() -> None:
    """The other side of the same rule: `_filings` is a real import, because the renderer
    matches on filing type. That is what keeps the `_transcript` import annotation-only —
    nothing here dispatches on a transcript type."""
    for name in ("Argument", "Concession", "Response", "Continuance", "Ruling"):
        assert hasattr(prompting, name)


def test_transcript_render_delegates_rather_than_importing_inside_the_method(
    proceeding: Transcript[Any],
) -> None:
    """`Transcript.render()` is a delegation, not a function-local import apologizing for a
    cycle. The two calls are the same renderer reached two ways."""
    assert proceeding.render() == render(proceeding, ReviewerView())
