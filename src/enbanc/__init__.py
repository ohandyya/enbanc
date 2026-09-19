"""Adversarial multi-agent adjudication for structured decisions.

Two advocates argue opposite sides of a question against a rule you wrote, a judge asks
follow-up questions until it can decide, and what comes back is the decision *and* the
complete record of how it was reached.

    from enbanc import Tribunal, Judge, Advocate, Statute, Case, Verdict, Ruling, Undecided
    from enbanc.tools import web_search

`enbanc` and `enbanc.tools` are the package. Every other module is underscore-prefixed and
there is no supported path to anything inside one: internal reorganization cannot break a
caller, because there was never a name for the caller to reach. `__all__` below is the
contract, and `docs/design/api.md` is the list.

**This is a partial surface.** `Proceeding` is the last of the twenty-nine names
`docs/design/packaging.md` fixes that does not exist yet, and the `Tribunal` exported here
has no `hear()` — a caller can build one, read `instructions_for()`, and do nothing else. See
`docs/implementations/` for the order the rest arrives in.

Importing this module does no I/O, imports no provider SDK, and does not reach
`enbanc.tools`. That is a packaging rule rather than a convention, because an import happens
at collection time, before any test fixture can guard it — see `docs/design/packaging.md`
("What `import enbanc` may do") and `tests/unit/test_import_is_inert.py`.
"""

from ._errors import (
    ConfigurationError,
    EnbancError,
    ProceedingFailed,
    ProceedingUnfinished,
)
from ._evidence import Exhibit, Source
from ._filings import (
    Argument,
    Concession,
    Continuance,
    Deliberation,
    Filing,
    Interrogatory,
    Response,
    Ruling,
)
from ._hearing import Hearing, Outcome, Undecided
from ._inputs import Case, Statute
from ._transcript import Entry, Retrieval, ToolFailure, Transcript
from ._tribunal import Advocate, Judge, Tribunal
from ._verdicts import Verdict, VerdictT

# Re-export is `from ._module import Name` plus membership here; pyright treats the second as
# the re-export declaration, so no `as` aliasing is needed. Adding a public name is a
# deliberate act with a diff on it — `tests/unit/test_export_surface.py` is what makes that
# true rather than merely intended.
__all__ = [
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
