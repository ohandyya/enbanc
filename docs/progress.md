---
status: current
updated: 2026-09-11
---

# Progress

**Where the work stands, and how it got here.** Written at the end of a working
session by the [`wrap-up`](../.claude/skills/wrap-up/SKILL.md) skill, and read
at the start of the next one.

Two halves, two different guarantees:

- `## Current state` is **current truth**, rewritten in place every session.
  Anything stale here is a bug.
- `## Log` is **history**, prepended newest-first and never edited. Entries are
  true as of their date and go stale by design.

The log says *what* changed and *where it stopped*. It does not say *why* —
that lives in [`journal/`](./journal/), linked from the entry. Neither half is a
spec: [`design/`](./design/) is.

## Current state

**Phase:** Design complete — including how the package itself is laid out — and
the test harness exists with a way to run against real providers from a pull
request. **Still no `enbanc` code**: `src/enbanc/__init__.py` is a `hello()`
stub, and the suite that runs green covers it plus one claim about
`pydantic-ai`. The published `0.0.4` on PyPI reserves the name and nothing more.

Settled and binding across
[`0001`](./decisions/0001-statute-carries-no-model.md)–[`0035`](./decisions/0035-testing-holds-technique-not-an-index.md).
Eight design documents under [`design/`](./design/) carry **no open questions**:
every public type, every way a proceeding can *end*, its *behaviour*, how
evidence becomes a checkable exhibit, everything a participant reads, how the
whole thing maps onto PydanticAI, how any of it is known to be true, and how it
is laid out as an importable package.
[`degenerate-deliberations.md`](./design/degenerate-deliberations.md) is the one
remaining placeholder and is not needed for `0.1.0`.

[`design/packaging.md`](./design/packaging.md) constrains the first modules
before they are written: `enbanc` and `enbanc.tools` are the only importable
namespaces and everything else is underscore-prefixed, `__all__` is a
twenty-nine-name contract whose list is [`api.md`](./design/api.md#schemas)
rather than a judgment made per name, and `import enbanc` may do no I/O, import
no provider SDK, and not reach `enbanc.tools`. `typing-extensions>=4.14.1` is
now declared in `pyproject.toml` ahead of the code that imports it — the 3.11
floor needs it for `TypeAliasType`.

[`design/testing.md`](./design/testing.md) describes a harness that exists: four
tier directories under `tests/`, each test's tier derived from its path, the two
offline tiers enforcing that with a socket guard, and live fixtures that name no
provider. `make test` is still the two offline tiers, and `ci.yml` is still
exactly `make check-all` with no secrets. The live tiers now also run in CI when
asked — [`live-tests.yml`](../.github/workflows/live-tests.yml), fired by a
`live-tests` label on a pull request or by `workflow_dispatch`
([`0033`](./decisions/0033-live-tiers-run-in-ci-on-demand.md)).

**Next up:** Write the `0.1.0` schemas from
[`design/api.md`](./design/api.md#schemas) into the module layout
[`design/packaging.md`](./design/packaging.md#the-modules) now fixes — the
verdict base, the inputs, the five filings, the judge's output and its private
emit-shapes, the record, and the result, landing in `_verdicts.py`,
`_inputs.py`, `_evidence.py`, `_filings.py`, `_transcript.py`, and
`_hearing.py`. They are the floor everything else stands on, and they come with
their own first test: `Filing`, `Deliberation`, and `Outcome` must be
`TypeAliasType`, and
[`api.md`](./design/api.md#a-note-on-generic-aliases) says why plainly — *a type
checker does not catch this; only running it does*.

Five things the next session should carry:

- **The schemas owe two tests `packaging.md` already specifies.**
  `tests/unit/test_export_surface.py` pins the twenty-nine-name `__all__`
  against a literal list, and `tests/unit/test_import_is_inert.py` asserts in a
  subprocess that `import enbanc` pulls in neither `tavily` nor a provider SDK —
  the one test sanctioned to step outside the socket guard
  ([`0035`](./decisions/0035-testing-holds-technique-not-an-index.md)). Neither
  can be written before there is a package to import.
- **`live-tests.yml` has never run.** The branch is unmerged, the `live-tests`
  label may not exist yet, and the `live-tests` GitHub environment holding
  `OPENAI_API_KEY`, `TAVILY_API_KEY`, and `ENBANC_TEST_MODEL` is one-time setup
  nobody has done. Until the workflow is on `main`, **Run workflow** does not
  appear and `gh` answers `404`; the label half can be exercised from the pull
  request itself. Both tiers are empty of tests anyway, so the first real signal
  comes when there is something live to run —
  [`testing.md`](./design/testing.md#triggering-a-live-run-in-ci) has the steps.
- **Seven of the eight probes are still not tests.**
  [`design/execution.md`](./design/execution.md#what-pydanticai-already-does)
  makes eight runnable claims about `pydantic-ai 2.36.0`.
  `tests/contract/` now exists to hold them and pins one — `max_concurrency` is
  an `__init__` parameter. The rest are still throwaway scratch files, and a
  version bump falsifies the document silently until they land.
- **Piece 2 is small and piece 3 is not.** The ledgering toolset is a
  `WrapperToolset` with `call_tool` overridden. Round orchestration is the
  largest piece: the filing clerk, the task group, the snapshot construction,
  and the round loop.
- **The network guard is a tripwire, not a sandbox.** It catches `asyncio`, and
  so every HTTP client the library will actually use, but raw `_socket`,
  subprocesses, and anything connecting at import time go straight past it. The
  import-time half now has a rule and a test named for it in
  [`packaging.md`](./design/packaging.md#what-import-enbanc-may-do); the rest of
  the gap stands.

**Open questions:**

- None, anywhere in [`design/`](./design/).
- Whether the `0.1.0` scope line — now just
  [`degenerate-deliberations.md`](./design/degenerate-deliberations.md) —
  deserves an ADR, or stays recorded in the placeholder itself.
- `procedure` version `p1` is authored but unshipped, so its changelog row in
  [`prompting.md`](./design/prompting.md#procedure-versions) has nothing to
  compare against yet. The first prompt edit after `0.1.0` ships is the one that
  tests whether the bump discipline holds.

## Log

### 2026-09-11 — where a document's test mirror is recorded

**Did:** Settled the one drift the checkpoint had parked: a design document names
its own mirror beside the claim it pins, and
[`design/testing.md`](./design/testing.md) holds technique rather than an index of
what tests what — with `outcomes.md`'s table kept as a stated exception, because
that document cannot host its own mapping without losing the readability
[`0032`](./decisions/0032-a-design-doc-is-mirrored-by-tests.md) protects. The one
piece that *was* technique moved: `testing.md`'s offline-guarantee section now
names `test_import_is_inert.py` as the single sanctioned subprocess and says why
a second would need the argument made again.

**Why this way:**
[`decisions/0035`](./decisions/0035-testing-holds-technique-not-an-index.md).

### 2026-09-11 — packaging is designed, and the layout is chosen before the code

**Did:** Took [`design/packaging.md`](./design/packaging.md) from placeholder to
spec: two importable namespaces with every other module underscore-prefixed,
[`api.md`](./design/api.md) as the export list behind a twenty-nine-name
`__all__`, a module map keyed to the design document each module implements, the
one forced import cycle between the renderer and `Transcript.render()`, three
invariants on what `import enbanc` may do, and why there is one distribution
rather than a slim/meta pair. Declared `typing-extensions>=4.14.1` as a core
dependency, which the 3.11 floor forces for `TypeAliasType`.

**Stopped at:** Clean. The dependency is declared and nothing imports it yet;
that closes when the schemas land.

**Why this way:**
[`decisions/0034`](./decisions/0034-the-export-surface-is-the-package.md). No
journal entry — everything settled this session binds future work, so all of it
is ADR or spec material, the same call the 2026-09-02 entry records.

**Commits:** `71cd7eb`, `1c2c880`

### 2026-09-10 — the live tiers get a way into CI, on a label

**Did:** Added [`.github/workflows/live-tests.yml`](../.github/workflows/live-tests.yml)
so the integration and e2e tiers can run in CI, but only when a maintainer asks —
a `live-tests` label on a pull request, or a `workflow_dispatch` with a tier
picker. Credentials sit in a `live-tests` GitHub environment, and a preflight
step turns an unset one into a failure, since the fixtures' laptop-correct skip
would otherwise report a run that tested nothing as green. `ci.yml` and
`make test` are untouched. Also extended the `create-pr-summary` skill with a
confirmed step that puts the title and body onto GitHub.

**Stopped at:** Clean, but nothing has exercised the workflow: the branch is
unmerged, so `workflow_dispatch` is not yet offered, and the `live-tests`
environment and label are one-time setup still to do.

**Why this way:**
[`decisions/0033`](./decisions/0033-live-tiers-run-in-ci-on-demand.md).

**Commits:** `56a2bca`, `6f1b6a4`, `f2bc849`

### 2026-09-09 — testing is designed, and the harness is built before the code it will test

**Did:** Rewrote [`design/testing.md`](./design/testing.md) from placeholder to
spec — four tiers rather than three, the offline guarantee enforced instead of
promised, the transcript invariant as an assertion every proceeding-level test
can call, and [`outcomes.md`](./design/outcomes.md) mirrored section for section.
Built the harness it describes, so all four `make` targets run against an
essentially empty suite. Fixed two `UsageLimits` examples in
[`design/api.md`](./design/api.md) that
[`0029`](./decisions/0029-a-budgets-request-limit-must-be-chosen.md) had made
raise, and repaired this file — an unclosed backtick from the 2026-09-05 wrap-up
had swallowed its own `Current state` block and left the 2026-09-04 one
rendering in its place.

**Stopped at:** Clean. `tests/contract/` holds one of the eight `pydantic-ai`
claims [`design/execution.md`](./design/execution.md) makes; the other seven are
still scratch files.

**Why this way:**
[`journal/2026-09-09-building-the-harness-found-three-constraints.md`](./journal/2026-09-09-building-the-harness-found-three-constraints.md)
for what running it caught that designing it had not,
[`decisions/0031`](./decisions/0031-tests-are-tiered.md),
[`0032`](./decisions/0032-a-design-doc-is-mirrored-by-tests.md).

**Commits:** `f6b9bf3`, `f3e7320`

### 2026-09-05 — execution is designed, and the dependency is verified rather than read

**Did:** Wrote [`design/execution.md`](./design/execution.md), the last document
required before code — the proceeding written out as literal messages, then the
three pieces that read off it. Every claim it makes about `pydantic-ai 2.36.0`
was established by running the library, which turned up five defects in
already-settled documents (one in an accepted ADR) and two findings that made the
design smaller. All five were fixed in the same commit under rule 2, with three
ADRs and a fourth `ConfigurationError` case.

**Stopped at:** Clean, and `docs/design/` carries no open questions in any of its
six documents for the first time. The five probe scripts behind
`execution.md`'s dependency claims are still throwaway scratch files under
`/private/tmp/…/scratchpad/`; they belong in `tests/` before a `pydantic-ai`
bump can falsify the document silently.

**Why this way:**
[`journal/2026-09-05-the-probe-found-the-holes.md`](./journal/2026-09-05-the-probe-found-the-holes.md)
for what the probes caught and why review could not,
[`decisions/0028`](./decisions/0028-usage-accumulates-per-participant.md),
[`0029`](./decisions/0029-a-budgets-request-limit-must-be-chosen.md),
[`0030`](./decisions/0030-the-retry-budgets.md).

**Commits:** `03532f3`

### 2026-09-04 — prompting is designed, and the invariant turns out to have had three holes

**Did:** Wrote [`design/prompting.md`](./design/prompting.md) in full: one
renderer with three viewpoints, both procedural prompts verbatim, the four turn
templates, the ledger-id format, and what `Transcript.render()` emits. Building
its context-traceability table found that `guidance` and `enbanc`'s own
procedural prompt had both been reaching every agent with no transcript holding
them — two unnamed exceptions predating
[`0021`](./decisions/0021-retry-prompts-are-outside-the-invariant.md), which
exists to forbid a second. Closing them put four standing fields on `Transcript`
(`verdicts`, `max_rounds`, `guidance`, `procedure`) and propagated through
`api.md`, `tribunal.md`, `outcomes.md`, `evidence.md` and the glossary. Then
recorded verified PydanticAI mechanics in
[`design/execution.md`](./design/execution.md) — `message_history`, instruction
re-resolution, what lands in history that no rendered turn contains — as
observations, leaving that document undesigned. Finally settled its one open
question: an advocate asked two interrogatories answers them sequentially.

**Stopped at:** Clean, and `prompting.md` carries no open questions.
`design/execution.md` is the last required design and is still a placeholder;
its three load-bearing pieces are unchanged, but `0027` has since fixed the
task-group shape it must respect, and the PydanticAI findings it now carries
remove most of what piece 1 had left to settle.

**Why this way:**
[`decisions/0025`](./decisions/0025-the-record-includes-what-steered-it.md),
[`0026`](./decisions/0026-one-renderer-serves-both-audiences.md),
[`0027`](./decisions/0027-an-advocate-answers-its-interrogatories-in-order.md),
and
[`journal/2026-09-04-writing-the-prompt-found-the-holes.md`](./journal/2026-09-04-writing-the-prompt-found-the-holes.md)
for why all three findings arrived from the artifact rather than from reviewing
the rule — the second instance of a pattern already recorded here.

**Commits:** `7ed129b`, `9be484e`, `631c574`

### 2026-09-04 — the design docs get audited, and five placeholders

**Did:** Surveyed `docs/design/` against what implementing it would actually
require, and found the gap: the public surface is fully specified, the library's
own internals are not designed at all. Four places in `api.md` and one ADR defer
to a prompting document that never existed, and the ledgering toolset — the
hardest piece of code in the library — had one paragraph. Added five
placeholders under `docs/design/`, each naming what its design must settle
rather than settling it: `prompting.md` and `execution.md` marked required for
`0.1.0`; `degenerate-deliberations.md`, `testing.md` and `packaging.md` marked
left for future. Indexed all five in `docs/README.md`, and cut the README's
claim that the design was settled.

**Stopped at:** Clean, but nothing is *designed* — all five are stubs.
`Current state` had claimed design was complete with no design work queued,
which was true of the schemas and false of the library; it is rewritten above.

**Commits:** `29b8e63`

### 2026-09-04 — evidence, and the behaviour of a proceeding

**Did:** Settled how an advocate gathers evidence and what a proceeding may do,
in nine ADRs. Added [`design/evidence.md`](./design/evidence.md): a tool is a
plain async function, sources carry references, and the tribunal stamps every
field an exhibit's integrity depends on
([`0016`](./decisions/0016-exhibits-are-stamped-citations.md)). Read-only became
a stated contract rather than a claimed guarantee
([`0017`](./decisions/0017-read-only-is-a-contract.md)); `tavily-python` became
a core dependency so the default tool imports on a plain install
([`0018`](./decisions/0018-the-search-client-is-a-core-dependency.md)). The
ledger joined the record, closing the hole `0006` had accepted
([`0019`](./decisions/0019-the-ledger-is-part-of-the-record.md)), and tool
timeouts, retry prompts, and tool failures each got their place
([`0020`](./decisions/0020-tool-timeouts-ride-on-the-tool.md)–[`0022`](./decisions/0022-tool-failures-are-recorded.md)).
Then the last two behavioural questions: an advocate argues blind and rebuts
informed ([`0023`](./decisions/0023-advocates-argue-blind-and-rebut-informed.md)),
and a budget stops a proceeding between rounds
([`0024`](./decisions/0024-a-budget-stops-the-proceeding-between-rounds.md)).

**Stopped at:** Clean. Logged retroactively at the next session's wrap-up —
`Current state` was kept current through the day, but no log entry was
prepended.

**Why this way:**
[`decisions/0016`](./decisions/0016-exhibits-are-stamped-citations.md)–[`0024`](./decisions/0024-a-budget-stops-the-proceeding-between-rounds.md).

**Commits:** `6177a57`, `39b8630`, `1e474ba`, `ddf54b9`, `ea38a80`, `a44550e`,
`10161c2`, `2586b98`

### 2026-09-02 — four ADRs, and `api.md` runs out of questions

**Did:** Closed the last four unsettled pieces of the `0.1.0` surface, one ADR
each: the first failure cancels the round rather than draining it
([`0012`](./decisions/0012-a-failure-cancels-the-round.md)), `Case` is a
subclassable base rather than a second type parameter on every generic
([`0013`](./decisions/0013-a-case-is-a-subclassable-base.md)), a `Hearing`
carries `usage_by_participant` as the stored fact with `usage` as its sum
([`0014`](./decisions/0014-usage-is-broken-down-per-participant.md)), and the
tribunal stamps `r{round}-q{n}` onto an interrogatory when it files the
continuance instead of asking the judge to invent it
([`0015`](./decisions/0015-interrogatory-ids-are-stamped-on-filing.md)).
`design/api.md` now lists no open questions; both survivors are in
`design/tribunal.md` and both are about behaviour, not shape.

**Stopped at:** Clean. `README.md` and the glossary were swept here — the README
still claimed `api.md` carried open questions and its sample predated
`usage_by_participant`; the glossary described a `Hearing`'s usage as merely
aggregate and had no row for *participant*, which `0012` and `0014` both lean
on.

**Why this way:**
[`decisions/0012`](./decisions/0012-a-failure-cancels-the-round.md)–[`0015`](./decisions/0015-interrogatory-ids-are-stamped-on-filing.md);
no journal entry — every choice this session binds future work, so all of it is
ADR material and none of it is session narrative.

**Commits:** `26c2c16`, `329b897`, `db7ac7d`, `d4bd74f`, `f8c711c`

### 2026-09-02 — streaming, and what happens when there is no verdict

**Did:** Added `hear_stream()` as a live view of the transcript
([`0010`](./decisions/0010-streaming-yields-the-record.md)), then settled how a
proceeding reports *not* ruling. Exhaustion is now a recorded `Undecided`
outcome on `Hearing.outcome`; provider, tool, and validation failures raise
`ProceedingFailed` carrying the partial transcript. `Hearing.ruling` is gone,
and with it the last open question that was blocking a type. Added
[`design/outcomes.md`](./design/outcomes.md) — every ending written out as
concrete values — which is what caught two defects in the schemas above it.

**Stopped at:** Clean. `docs/design/` and the README match the new surface.

**Why this way:**
[`decisions/0010`](./decisions/0010-streaming-yields-the-record.md),
[`decisions/0011`](./decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md),
and
[`journal/2026-09-02-values-before-schemas.md`](./journal/2026-09-02-values-before-schemas.md)
for why the examples doc found what schema review did not.

**Commits:** `231358c`, `eee4dca`, `3ccdad7`

### 2026-09-02 — the schemas, and six ADRs

**Did:** Took `design/api.md` from a sketch to a full schema spec — verdicts as
a `StrEnum` base, the five filings and their `Entry` envelope, a self-contained
`Transcript`, and `hear()` returning a `Hearing` that wraps the judge's
`Ruling` — and settled six binding pieces as ADRs
[`0004`](./decisions/0004-verdicts-are-a-strenum.md)–[`0009`](./decisions/0009-model-settings-live-on-the-model.md).
Propagated the vocabulary through `design/tribunal.md` and the glossary
(*round*, *filing*, *response*, *entry*, *hearing*), narrowed the
"nothing enters an agent's context" invariant to *nothing from outside itself*
so an advocate's unfiled tool results are legal, and added rule 7 to
`CLAUDE.md` fixing what it takes to resolve an open question.

**Why this way:**
[`decisions/0004`](./decisions/0004-verdicts-are-a-strenum.md)–[`0009`](./decisions/0009-model-settings-live-on-the-model.md);
no journal entry — the only build-time constraint found (Pydantic collapsing a
generic alias parameterized by a bare `TypeVar`) is recorded as spec in
[`design/api.md`](./design/api.md#a-note-on-generic-aliases).

**Commits:** `b8eb899`, `87f6595`, `c363992`, `d4aa820`, `420abc3`, `6934205`,
`96f9615`, `9625fc4`

### 2026-09-01 — the statute is inert; first ADR

**Did:** Settled the first binding piece of the `0.1.0` surface — a `Statute`
carries no model and `Statute.draft()` is cut — and propagated it through
`design/api.md`, the glossary, and the `docs/README.md` index. Sharpened the
journal-vs-ADR split in `CLAUDE.md`, `docs/journal/README.md`, and the `wrap-up`
skill: the journal records how a session went, `decisions/` records what the
project is committed to. Documented in `pyproject.toml` that `uv_build` ships an
allowlist, not everything git tracks — `notes/` and `docs/` stay out of the
sdist only because that section stays bare. Released the `0.0.4` placeholder.

**Stopped at:** Two open questions were dropped into
[`design/api.md`](./design/api.md#open-questions) as raw first-person notes
rather than design prose — the missing `Judge` role, and how `instructions` and
a PydanticAI `Model` are injected into each agent. They need writing up before
they can be settled.

**Why this way:**
[`docs/decisions/0001-statute-carries-no-model.md`](./decisions/0001-statute-carries-no-model.md)

**Commits:** `183fe8a`, `be2b72b`, `045af5a`, `131c94a`, `333b338`, `9b0e08d`,
`e2fa55b`

### 2026-08-29 — documentation structure and the wrap-up skill

**Did:** Established the `docs/` layout and the rules that govern it
(`CLAUDE.md`): `design/` as spec, `decisions/` as immutable ADRs, `journal/` as
dated and stale-by-design, `notes/`/`local/` denied to agents. Added this file
and the `wrap-up` skill that maintains it. Earlier in the day: uv + ruff +
pyright + pytest tooling, pre-commit hooks enforced in CI, the release workflow
with its tag-vs-version check, and the `0.0.3` placeholder release.

**Stopped at:** Clean. `docs/decisions/` and `docs/guides/` are still empty, by
design — nothing has been decided or shipped that needs them.

**Commits:** `f795ae0`, `71ebadc`, `9eb7d33`, `0ea8a40`, `f387674`, `cd05dec`
