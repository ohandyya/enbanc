---
status: current
updated: 2026-09-19
---

# Packaging

How `enbanc` is laid out as a Python package: what a user may import, what sits
behind that, which way the imports run, and what an `import enbanc` is allowed to
do. [`api.md`](./api.md) specifies *what* the public types are; this document
specifies *where they live and how they are reached*.

The layout is chosen before the first module is written, because a layout is
otherwise never chosen — it accretes, and the first user to `import` something
private makes it public retroactively. See
[`0034`](../decisions/0034-the-export-surface-is-the-package.md).

## Two namespaces, and nothing else

**`enbanc` and `enbanc.tools` are the package.** Every other module is
underscore-prefixed, and there is no supported path to anything inside one.

```python
from enbanc import Tribunal, Judge, Advocate, Statute, Case, Verdict
from enbanc.tools import web_search
```

This is the same move the library makes everywhere else: make the guarantee
structural rather than documented. A `PUBLIC_API.md` listing what may be imported
is a promise; a package whose only importable modules *are* the public API is a
fact. Internal reorganization cannot break a caller, because there was never a
name for the caller to reach.

Two namespaces rather than one because [`evidence.md`](./evidence.md#the-default-tool)
already spells the tool import separately, and because keeping tools in their own
module is what makes [`import enbanc` inert](#what-import-enbanc-may-do).

## The modules

```text
src/enbanc/
  __init__.py        the export surface
  _verdicts.py       Verdict, VerdictT, the reserved "judge", Participant
  _inputs.py         Statute, Case
  _evidence.py       Source, Exhibit, _Exhibit
  _filings.py        the five filings, the judge's private emit-pair,
                       Filing, Deliberation
  _prompting.py      procedure p1, both procedural prompts, the instruction
                       parts, the turn templates, the three viewpoints, and
                       Transcript.render()'s body
  _transcript.py     Entry, Retrieval, ToolFailure, Transcript
  _hearing.py        Undecided, Outcome, Hearing
  _errors.py         EnbancError and its three subclasses
  _ledgering.py      Ledgering, as_sources, render_call, render_results
  _tribunal.py       Tribunal, Judge, Advocate
  _proceeding.py     Proceeding, the filing clerk, the round's task group,
                       the round loop, the budget check
  tools/
    __init__.py      re-exports web_search
    _web_search.py
  py.typed
```

**A module is named for the design document that specifies it.** `_prompting.py`
is [`prompting.md`](./prompting.md); `_ledgering.py` is
[`execution.md`](./execution.md#piece-2--the-ledgering-toolset)'s piece 2;
`_proceeding.py` is [its piece 3](./execution.md#piece-3--round-orchestration).
The mapping runs both ways on purpose — rule 2 in
[`../../CLAUDE.md`](../../CLAUDE.md) says a change to behaviour updates the design
doc in the same commit, and a filename that names the doc is the cheapest
possible reminder of which one.

**The internals are laid out because tests import them, not only because code
does.** `tests/unit/` is `enbanc`'s own behaviour
([`0031`](../decisions/0031-tests-are-tiered.md)), so the ledgering toolset is
constructed and called directly by a test, and so is the round loop. These paths
are part of the layout whether or not a user may reach them.

**Each private emit-shape sits beside its public counterpart.** `_Exhibit` is in
`_evidence.py` with `Exhibit`; `_Interrogatory` and `_Continuance` are in
`_filings.py` with `Interrogatory` and `Continuance`. The conversion between them
happens at one seam — [the filing clerk](./execution.md#the-filing-clerk) — and
holding both shapes of one concept in one file is what keeps the pair from
drifting apart. Splitting them into a `_private.py` would put the two halves of
[`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md) and
[`0016`](../decisions/0016-exhibits-are-stamped-citations.md) in different files
for no gain: the privacy comes from the leading underscore on the *name*, which
already keeps them off [the export surface](#the-export-surface).

**`Participant` is private.** [`api.md`](./api.md) never names it as a type — it
spells `VerdictT | Literal["judge"]` inline at every appearance — while
[`execution.md`](./execution.md#piece-1--message-history-and-the-transcript) uses
it for the history and `since` dicts. It lives in `_verdicts.py` beside the
reserved `"judge"` string it is half of, and it stays off `__all__` because
[the export rule](#the-export-surface) is only worth having while it is exact.

## What imports what

Runtime imports run down the list above and never back up it, with **one
exception**, and the exception is forced.

[`0026`](../decisions/0026-one-renderer-serves-both-audiences.md) puts one
renderer behind both the agents' views and `Transcript.render()`. So the renderer
needs `Transcript` for its signature, and `Transcript` needs the renderer for its
method — a cycle if both are ordinary imports. The break:

```python
# _prompting.py
from typing import TYPE_CHECKING

from ._filings import Argument, Concession, Continuance, Response, Ruling   # runtime

if TYPE_CHECKING:
    from ._transcript import Transcript                                     # annotation only

def render(transcript: "Transcript[Any]", view: View) -> str: ...
```

```python
# _transcript.py
from ._prompting import ReviewerView, render                                # runtime

class Transcript(BaseModel, Generic[VerdictT]):
    def render(self) -> str:
        return render(self, ReviewerView())
```

`_prompting` imports `_filings` for real, because it dispatches on filing type;
it imports `_transcript` only for annotations. `_transcript` imports `_prompting`
for real. One direction at runtime, and `Transcript.render()` is a delegation
rather than a function-local import apologizing for a cycle.

This is the same register as
[the note on generic aliases](./api.md#a-note-on-generic-aliases): a detail
forced by the tools, written down because the alternative is someone
rediscovering it as an `ImportError` and reaching for the wrong fix.

**`_proceeding.py` takes the pieces, not the `Tribunal`.** The orchestrator
receives the question, the statute, the judge, the advocates, the model, and the
limits as parameters. So `_tribunal` imports `_proceeding` and never the reverse,
and the round loop is constructible from a test without building a `Tribunal`
first.

## The export surface

**`__all__` is the contract, and [`api.md`](./api.md) is the list.** Every name in
its [`Shape`](./api.md#shape) block and its [`Schemas`](./api.md#schemas) blocks is
public, plus `Source`, which [`evidence.md`](./evidence.md#adding-your-own-tool)
spells `from enbanc import Source`. Nothing else is public, and the rule is
mechanical rather than a judgment made per name:

```python
__all__ = [
    "Advocate", "Argument", "Case", "Concession", "ConfigurationError",
    "Continuance", "Deliberation", "EnbancError", "Entry", "Exhibit", "Filing",
    "Hearing", "Interrogatory", "Judge", "Outcome", "Proceeding",
    "ProceedingFailed", "ProceedingUnfinished", "Response", "Retrieval",
    "Ruling", "Source", "Statute", "ToolFailure", "Transcript", "Tribunal",
    "Undecided", "Verdict", "VerdictT",
]
```

Twenty-nine names, and `enbanc.tools.__all__` is `["web_search"]`.

Re-export is `from ._module import Name` plus membership in `__all__`; pyright
treats the second as the re-export declaration, so no `as` aliasing is needed.

**The list is mirrored by a test, not only by this document.**
`tests/unit/test_export_surface.py` asserts the sorted `__all__` against the
literal list, and that every name in it resolves. Adding a public name is then a
deliberate act with a diff on it, which is the point — this is
[`0032`](../decisions/0032-a-design-doc-is-mirrored-by-tests.md)'s pattern applied
to a document whose worked value is a list of strings.

**`Deliberation` is exported although nothing public returns one.** The judge's
real `output_type` is `Ruling[VerdictT] | _Continuance[VerdictT]`, and a
transcript holds [`Filing`](./api.md#the-record) — so the alias appears on no
public signature. It is exported because it is in `api.md`, and a rule that is
mechanical is worth more than one alias pruned by hand. If it should not be
public, the fix is to cut it from `api.md`.

## Where the errors live

`_errors.py`, and it sits *below* `_transcript.py` rather than at the top of the
package: `ProceedingFailed` carries a `Transcript` and a per-participant usage
mapping ([`api.md`](./api.md#when-something-goes-wrong)), so it imports the record
it carries. Nothing in the record imports back.

`ProceedingFailed` is `Generic[VerdictT]` and an `Exception`, which is legal and
has one consequence worth knowing: `except ProceedingFailed[LoanDecision]` is a
`TypeError` at runtime — Python matches exceptions on the class, not the
parameterization. Catch the bare class and read `.participant`, which is typed.

`ConfigurationError` is raised only from `Tribunal(...)`
([four cases](./execution.md#configurationerror-has-four-cases)) and
`ProceedingUnfinished` only from `Proceeding.hearing`, but both live here with the
base rather than beside their raiser. An error hierarchy a caller catches on is
one thing to import, and splitting it across three modules would make
`EnbancError`'s subclass list something you assemble rather than read.

## What `import enbanc` may do

Three invariants, checked by `tests/unit/test_import_is_inert.py`:

1. **It performs no I/O.** No client is constructed, no connection opened, no file
   read, no environment variable required.
2. **It does not import `enbanc.tools`.** The top-level package re-exports no
   tool, which is why [`api.md`](./api.md#shape) spells that import separately.
3. **It imports no provider SDK.** [`0003`](../decisions/0003-models-and-guidance-are-injected.md)
   makes the model injected and `enbanc` has no provider concept; a module
   importing `anthropic` or `openai` would contradict that silently.

The first exists because the offline guarantee in
[`testing.md`](./testing.md) is a socket guard installed as an autouse
fixture, and **an import happens at collection, before any fixture runs**. A
module-level client that connects eagerly would go straight past it — which
`docs/progress.md` already names as the realistic gap in the guard. This
invariant is what closes it, and it is a packaging rule rather than a testing one
because the thing it constrains is module-level code.

The test runs `import enbanc` in a **subprocess** and inspects `sys.modules`,
because by the time a test function runs, pytest has imported half the tree
in-process and the question is no longer askable. A subprocess carries none of
the socket guard, and
[`testing.md`](./testing.md#the-offline-guarantee-enforced) sanctions *this test
by name* rather than subprocesses in general: the child does `import enbanc` and
reads `sys.modules`, and the assertion is precisely that it reached nothing. A
second subprocess test would need that argument made again from scratch.

The second is what keeps `tavily` off the `import enbanc` path. It changes no
install — `tavily-python` is core
([`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md)) — but it
is what makes [a later split](#one-distribution) a change to one module rather
than a search through the package.

## The dependency floor

**Python `>=3.11`**, as `pyproject.toml` already declares. `ci.yml`'s 3.11 matrix
leg is the only thing in the repository that verifies the claim; ruff's
`target-version` and pyright's `pythonVersion` are assertions that leg checks.

Two consequences, and both are temporary:

- **`TypeAliasType` comes from `typing_extensions`, not `typing`.**
  `typing.TypeAliasType` is 3.12+, and `Filing`, `Deliberation`, and `Outcome`
  need it at the floor for the reason
  [`api.md`](./api.md#a-note-on-generic-aliases) gives.
- **`typing-extensions>=4.14.1` is a declared dependency.** It arrives anyway
  through pydantic, which pins exactly that floor — but `enbanc` imports it
  directly, and a package declares what it imports rather than relying on a
  transitive it does not control.

Both lines disappear when the floor moves to 3.12 and the three aliases become
`type Filing[V: Verdict] = ...`. Nothing else in the library is 3.12-shaped;
`StrEnum` ([`0004`](../decisions/0004-verdicts-are-a-strenum.md)) is 3.11.

`tavily-python` is core, and [`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md)
is why. What actually ships in the sdist and the wheel is an allowlist, not a
gitignore filter — the comment on `[build-system]` in `pyproject.toml` has the
detail and the command that checks it, and is the authority on it rather than
this document.

## One distribution

`enbanc` is one package on PyPI and `0.1.0` does not split.

The split that would be available is the meta-package pattern — a core
distribution plus a thin one that depends on it and on the extras — and it is
proven in this project's own dependency tree, since `pydantic-ai` is exactly
that over `pydantic-ai-slim`. Extras cannot express it, because an extra only
adds: there is no `enbanc[minimal]` that *removes* a core dependency.

It is not taken now because the thing it would remove is three packages
(`requests`, `httpx`, `tiktoken`, of which the first two arrive with
`pydantic-ai` regardless), and the price is two distributions, two version
numbers that must move together, and a release path twice as long as the one the
`create-new-release` skill runs today.

**What would reopen it.** [`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md)
already wrote half of it — that decision *"is not precedent for a second provider
SDK"*. The rest: a second SDK becoming core, or `tavily-python`'s own tree
growing past what a tribunal with no web advocate should carry. Until then the
hatch is held open by the module rule above: `tavily` is imported from exactly
one module, reached through exactly one namespace, so the day the split is worth
making, it is a change to packaging metadata rather than to code.

## Stability, before 1.0

**`__all__` is what is promised; the underscore modules promise nothing.** A name
in `__all__` keeps its meaning until a release says otherwise. A name behind an
underscore may move, change shape, or vanish in a patch release, and no changelog
entry is owed for it.

At `0.x` there is no major version to signal a break with, so **a name leaving
`__all__`, or changing shape within it, is a minor bump** — `0.1.x` → `0.2.0` —
with a `CHANGELOG.md` entry that says what broke and what to do instead. The
release mechanics are the [`create-new-release`](../../.claude/skills/create-new-release/SKILL.md)
skill's, not this document's.

The user-facing half of the surface — how to do a thing, rather than what exists
— is [`../guides/`](../guides/), which is still empty. This document is the map
of the package; a guide is the map of a task.

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. See rule 7 in [`../../CLAUDE.md`](../../CLAUDE.md).

*None open.*
