---
status: current
updated: 2026-09-25
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

**Phase:** Design complete, and six of the ten-PR plan's PRs are `current`
and merged: [`schemas.md`](./implementations/schemas.md)
([PR #19](https://github.com/ohandyya/enbanc/pull/19)),
[`contract-probes.md`](./implementations/contract-probes.md)
([PR #20](https://github.com/ohandyya/enbanc/pull/20)),
[`web-search-tool.md`](./implementations/web-search-tool.md)
([PR #21](https://github.com/ohandyya/enbanc/pull/21)),
[`rendering.md`](./implementations/rendering.md)
([PR #23](https://github.com/ohandyya/enbanc/pull/23)),
[`tribunal-construction.md`](./implementations/tribunal-construction.md)
([PR #24](https://github.com/ohandyya/enbanc/pull/24)), and
[`ledgering-toolset.md`](./implementations/ledgering-toolset.md)
([PR #25](https://github.com/ohandyya/enbanc/pull/25)) — #25 merged since the
last entry. [`proceeding-core.md`](./implementations/proceeding-core.md)'s
code is done too: `Proceeding`, `Tribunal.hear()`, and `Tribunal.hear_stream()`
now exist and run a proceeding for real — round 1's fan-out, the filing clerk,
and the judge's first deliberation. [PR #26](https://github.com/ohandyya/enbanc/pull/26)
is open against it, stamped `current`, but has not merged yet. A judge that
continues rather than rules still raises `NotImplementedError` naming
[`round-loop.md`](./implementations/round-loop.md) — that boundary is
deliberate, not a gap found late. `make test` passes at 375 (303 → 375 this
session); re-verified by running the suite. **`__all__` is complete at
twenty-nine names** — `Proceeding` was the last one, and
`test_export_surface.py` pins the full literal rather than the placeholder
count. The README's WIP banner is still accurate for an outside reader: the
published `0.0.5` on PyPI is unchanged and reserves the name and nothing more,
`0.1.0` hasn't shipped, and the round-2 case the "A taste" sample's
`max_rounds=5` implies still raises `NotImplementedError` from source — so the
banner was left as it is rather than partially walked back.

Settled and binding across
[`0001`](./decisions/0001-statute-carries-no-model.md)–[`0038`](./decisions/0038-the-citation-check-rides-on-the-output-type.md).
[`0038`](./decisions/0038-the-citation-check-rides-on-the-output-type.md) is
new this session: the citation check moved from an agent-level output
validator to an output function riding on the output type, because PydanticAI
refuses any per-run `output_type` override once an agent carries a validator —
found while building PR 7, where it collided head-on with *one agent per
participant*. Eight design documents under [`design/`](./design/) still carry
**no open questions**. [`execution.md`](./design/execution.md#what-pydanticai-already-does)
now records **thirteen** `pydantic-ai` findings rather than twelve — the
output-validator-vs-per-run-`output_type` refusal above — and every
probe-shaped one has a `tests/contract/` module pinning it. There are **no
placeholders left** — `degenerate-deliberations.md` was deleted once its three
holes were answered by
[`0036`](./decisions/0036-a-continuance-carries-at-least-one-interrogatory.md),
[`0037`](./decisions/0037-a-conceded-advocate-stays-addressable.md), and
[`0027`](./decisions/0027-an-advocate-answers-its-interrogatories-in-order.md),
which had already settled the third on the day the placeholder was written.

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

The path from here to `0.1.0` is a ten-PR plan in
[`implementations/`](./implementations/), ordered by
[its README table](./implementations/README.md#the-plan). PRs 1–6 are
`current` and merged; #26 (PR 7) is open but not yet merged; the other three
are still `draft` with no plan or code.

**Next up:** Get #26 reviewed and merged, then start PR 8,
[`round-loop.md`](./implementations/round-loop.md) — what a continuance
starts: the `_Continuance` → `Continuance` conversion with `r{round}-q{n}`
stamped in emission order, one task per *addressed* advocate with its
interrogatories queued and answered in order, `Response.answering` filled
from the dispatch, `since`'s per-run advance, the snapshot extension that run
7 of [the worked proceeding](./design/execution.md#since-and-the-snapshot-run-by-run)
needs, the `max_rounds` check, and the budget check whose
`UsageLimitExceeded` is a stop signal rather than an error. Its own `Scope`
was checked against what PR 7's build actually produced this session and
still reads true as written — PR 7 deliberately built the plain task group
and left the first-failure slot to [`failures.md`](./implementations/failures.md)
(PR 9), exactly as `round-loop.md` and `failures.md` both assume. One thing
PR 8 gets for free rather than having to build: the advocate agent, the
`_filing_output()` output-function pattern, and the `DynamicToolset` callable
wrapper already exist in `_proceeding.py` — dispatching a `_Response` is a
per-run `output_type` override on the *same* `advocate_agents[verdict]`
([`0038`](./decisions/0038-the-citation-check-rides-on-the-output-type.md)),
not a new agent or a new mechanism.

Things the next session should carry:

- **The output-function pattern is now load-bearing for every future
  per-run output shape, not just round 1's.** `_filing_output()` in
  `_proceeding.py` is what let one agent survive a per-round output-shape
  change at all
  ([`0038`](./decisions/0038-the-citation-check-rides-on-the-output-type.md)).
  A `_Response` output type for round 2 needs the same two traps respected:
  the annotation assigned from the tribunal's resolved verdict enum (a
  literal `_Response[VerdictT]` collapses to `enum: []`), and no docstring on
  the wrapping function (PydanticAI surfaces one as the tool's description).
- **`live-tests.yml` has now run for real, on both triggers.** A
  `workflow_dispatch` on `main` (2026-09-10) and the `live-tests` label on
  [PR #21](https://github.com/ohandyya/enbanc/pull/21) (2026-09-13) both went
  green — the GitHub environment holding `OPENAI_API_KEY`, `TAVILY_API_KEY`,
  and `ENBANC_TEST_MODEL` is set up, and the label exists. The integration
  tier is no longer empty: `test_web_search.py` ran one real Tavily call and
  passed. The e2e tier is still `test_placeholder.py` — it only asserts the
  runner's model builds, and waits on `api.md`'s example to exist.
- **Piece 3's round-1 half is done; the round loop itself is not.** The
  filing clerk, the round's task group, round 1's fan-out, and the first
  deliberation are built and tested. What is left of piece 3 is entirely
  round 2 and after — PR 8's scope above.
- **The network guard is a tripwire, not a sandbox.** It catches `asyncio`, and
  so every HTTP client the library will actually use, but raw `_socket`,
  subprocesses, and anything connecting at import time go straight past it. The
  import-time half now has a rule and a test named for it in
  [`packaging.md`](./design/packaging.md#what-import-enbanc-may-do); the rest of
  the gap stands.
- **The shared conftest pattern held up again.** `tests/unit/conftest.py` now
  also has the capturing `FunctionModel` and `assert_invariant_held`, the
  transcript-invariant helper [`testing.md`](./design/testing.md#the-transcript-invariant)
  specified with no caller until this session. `test_proceeding.py` and
  `outcomes/test_02_rules_in_round_1.py` both call it, so every proceeding
  test written after this PR gets the invariant checked for free. PR 8 varies
  the same bench further into round 2; grow these fixtures rather than
  rebuilding them.

**Open questions:**

- None, anywhere in [`design/`](./design/).
- `procedure` version `p1` is pinned by goldens and now actually runs a
  proceeding under `hear()`/`hear_stream()` for the first time — but only the
  round-1-through-first-ruling slice of it, driven by scripted
  `FunctionModel`s in the test suite, not yet by a live model. The parts of
  `p1` that talk about interrogatories, responses, and later rounds stay
  unexercised until [`round-loop.md`](./implementations/round-loop.md) lands,
  and its changelog row in
  [`prompting.md`](./design/prompting.md#procedure-versions) still has
  nothing to compare against — that needs `0.1.0` shipped and a real prompt
  edit after it. The bump-discipline question stays open until then.

## Log

### 2026-09-25 — PR 7: the proceeding runs, round 1 through a ruling

**Did:** Implemented [`proceeding-core.md`](./implementations/proceeding-core.md)
— `_proceeding.py`: one `Agent` per participant built inside the proceeding
and discarded with it, the filing clerk coroutine that is the sole writer of
`Transcript.entries`, the round-1 fan-out, and the judge's first
deliberation. `Tribunal.hear()` and `hear_stream()` now exist; `hear()` is
`hear_stream()` driven to exhaustion, literally. The citation check moved off
`agent.output_validator` onto an output function riding on the output type,
because PydanticAI refuses a per-run `output_type` override once an agent
carries a validator — a collision with *one agent per participant* found
while building this PR, not anticipated by the design. `__all__` completes at
twenty-nine names with `Proceeding`. A judge continuance still raises
`NotImplementedError` naming `round-loop.md`, by design. 72 new tests,
303 → 375. [PR #26](https://github.com/ohandyya/enbanc/pull/26) opened for
this work and is stamped `current` in the implementation doc and the plan
table; #25 (ledgering toolset) merged since the last entry.

**Why this way:** [`0038`](./decisions/0038-the-citation-check-rides-on-the-output-type.md)
— the output-function decision, with a second agent per advocate and an
always-offered three-shape union both written out and rejected.

**Commits:** 3f6c120, 0fcb2ab, 42a05f8, 23362cd.

### 2026-09-20 — PR 6: the ledgering toolset

**Did:** Implemented [`ledgering-toolset.md`](./implementations/ledgering-toolset.md)
— `_ledgering.py`: `Ledgering` (one `WrapperToolset` per advocate over one
`CombinedToolset`), `as_sources`'s shape-sniff, `render_call`/`render_results`,
and the `check_citations` output validator. `_filings.py` gained `_Argument`
and `_Response`, the advocate's private emit-shapes `_Exhibit` had been waiting
for since `schemas.md`. Verified against the installed `pydantic-ai` that
`CombinedToolset.for_run` rebuilds the toolset on every run, which forced the
ledger id to be counted out of the shared list rather than held in a counter
field — recorded as `execution.md`'s twelfth finding, with a new
`tests/contract/` module pinning it. 56 new tests, 247 → 303. `__all__` stays
at 28; `Ledgering` is internal. PR #24 (tribunal construction) merged since the
last entry. PR #25 opened for this work and is stamped `current` in the
implementation doc and the plan table.

**Why this way:** The `pydantic-ai` finding and the reasoning for rejecting
`for_run`-identity-pinning as a fix are written into
[`execution.md` § A wrapper toolset is rebuilt for every run](./design/execution.md#a-wrapper-toolset-is-rebuilt-for-every-run)
rather than a separate journal entry — it binds how every future
`WrapperToolset`-based module in this package must hold state, which made it
design prose rather than session narrative.

**Commits:** a965202, 6139623, e91ffb8, 394778b, e3af203

### 2026-09-19 — PR 5: tribunal construction

**Did:** Implemented [`tribunal-construction.md`](./implementations/tribunal-construction.md)
— `Tribunal`, `Judge`, `Advocate` in a new `_tribunal.py`, the four
`ConfigurationError` checks that run at construction (in order: reserved verdict,
missing/unknown bench keys, inherited `request_limit`), and
`instructions_for(participant)`. The assembly itself —
`instruction_parts()`, the four instruction headings, and `statute_heading()` —
landed in `_prompting.py` instead, since that text is `p1` surface and splitting
it across two files would make `_prompting.py`'s own module docstring false.
43 new tests across three files (`test_tribunal.py`, `test_instructions.py`,
`outcomes/test_05_misconfigured.py`), plus a `outcomes_kwargs` fixture in
`tests/unit/conftest.py`. Corrected `packaging.md`, `prompting.md`, and
`testing.md` in the same commit. Opened [PR #24](https://github.com/ohandyya/enbanc/pull/24)
and stamped the implementation doc `current`.

**Commits:** 1e41e86, 306103d, b658a79, 46765af.

### 2026-09-19 — PR 4: rendering

**Did:** Implemented [`rendering.md`](./implementations/rendering.md) — `_prompting.py`
(both procedural prompts, `ReviewerView`/`JudgeView`/`AdvocateView`, the `since` filter,
`render()`, and the three functions covering all four turn templates), `Transcript.render()`
and the one forced import cycle it breaks, and a shared eight-entry proceeding fixture in
`tests/unit/conftest.py` that later PRs can extend instead of rebuilding. Six new test
modules; `make check-all` moved from 151 to 204 passing. Corrected two design docs in the
same commit, as `CLAUDE.md` rule 2 requires: `packaging.md`'s stale cycle-break snippet, and
`prompting.md`'s under-specified no-label source row, its four sections that vary with what a
proceeding holds, and the per-line indentation rule. No `PROCEDURE` bump — the prompting
surface's *text* did not change, only the cases the doc had not yet spelled out for it.

**Commits:** 65fda81, b39408b.

### 2026-09-13 — PR 3: the web search tool

**Did:** Implemented `enbanc.tools.web_search` — `tools/_web_search.py` and
`tools/__init__.py`, the first code below the `enbanc.tools` namespace and the
first tool the package ships. A plain async factory over `AsyncTavilyClient`
mapping three Tavily fields onto `Source` and dropping the rest, per
`evidence.md`. Added the unit suite (mapping edge cases against a fake client)
and the integration test (one real call to Tavily), plus a
`CLAUDE.md` credentials section for the `.env` variables live tests need.
Writing the integration test against the real API — not the unit tests' canned
response — surfaced three things about Tavily's response shape `evidence.md`
had assumed rather than observed; corrected in the same commit. `make
check-all` is green at 151 tests. Opened
[PR #21](https://github.com/ohandyya/enbanc/pull/21).

**Why this way:** [`journal/2026-09-13-tavily-response-shape-found-by-hitting-it.md`](./journal/2026-09-13-tavily-response-shape-found-by-hitting-it.md).

**Commits:** `0432d82`, `8868ade`, `3d70506`, `2ce1fc2`

### 2026-09-13 — PR 2: the contract probes

**Did:** Wrote the seven remaining `tests/contract/` modules `contract-probes.md`
scoped, each pinning one `execution.md` finding about `pydantic-ai` directly
(conversation-as-parameter, instructions re-resolved, filing-as-tool-call,
tool-call interception, usage accumulation, two retry budgets, fan-out without
an `ExceptionGroup`) — every probe-shaped finding in `execution.md` now has a
module. Writing the fan-out module found `execution.md`'s own scenario
non-discriminating — both variants of the cancelled-exception re-raise behaved
identically under a child failure — so the doc was wrong about what the
re-raise protects (external cancellation, not a failing child); corrected in
the same commit along with `testing.md`'s checklist table (ten findings to
eleven). `make contract-tests` is green at 36 tests. No `enbanc` code touched —
this PR is independent and mergeable on its own.

**Stopped at:** Work is on the `contract-probes` branch, committed and clean,
but `docs/implementations/contract-probes.md` is still `status: draft` — no PR
opened yet.

**Commits:** `229989d`, `bfe88c4`

### 2026-09-12 — PR 1: the schemas, `enbanc`'s first code

**Did:** Wrote the seven modules `schemas.md` scoped —
`_verdicts.py`, `_inputs.py`, `_evidence.py`, `_filings.py`, `_transcript.py`,
`_hearing.py`, `_errors.py` — and `__init__.py` re-exporting twenty-five of the
twenty-nine `__all__` names, deleting `hello()` and its placeholder test.
Added the unit suite for all seven modules plus `test_export_surface.py` and
`test_import_is_inert.py`, both specified in `packaging.md` in advance of the
package existing. Gave `api.md` the one-line edit `schemas.md` owed it —
`Hearing.usage` noted as computed — in the same commit as the code. Opened
[PR #19](https://github.com/ohandyya/enbanc/pull/19); `make check-all` is
green at 103 tests. Also expanded `schemas.md` itself before writing code
against it, and clarified the `create-pr-summary` skill and
`docs/implementations/README.md` on when `status`/`pr:` get stamped.

**Stopped at:** PR #19 is open, not merged. PR 2 (`contract-probes.md`) is
next and has no dependency on this one merging first.

**Commits:** `fc52d1a`, `553662f`, `e84cdf7`, `72fda3a`, `33c7036`

### 2026-09-12 — the build plan: ten PRs from schemas to `0.1.0`

**Did:** Broke `docs/design/` into a ten-document build plan under
[`implementations/`](./implementations/), one doc per PR
(`schemas` → `contract-probes` → `web-search-tool` / `rendering` →
`tribunal-construction` / `ledgering-toolset` → `proceeding-core` →
`round-loop` → `failures` → `zero-one-zero`), each stating its scope, the
design sections it implements, and its dependencies, ordered by
[the README table](./implementations/README.md#the-plan) rather than a number
in the filename. Added CLAUDE.md rule 8 and the `docs/implementations/` naming
convention, and indexed all ten in `docs/README.md`. All ten are still `draft`
— no PR has been opened against any of them yet.

**Why this way:** No ADR or journal entry — the directory's shape (unnumbered,
table-ordered, `pr:` filled in once opened) mirrors the existing
`docs/design/` convention rather than settling anything new about the library
itself, and nothing here was discovered by building.

**Commits:** `20ba87b`, `8c4f259`

### 2026-09-11 — the last placeholder is answered and deleted

**Did:** Closed the three holes `design/degenerate-deliberations.md` had parked
and deleted the document, leaving [`design/`](./design/) with no placeholders
left. An empty continuance is now unrepresentable rather than tolerated —
`min_length=1` on both the judge's emit-shape and the public `Continuance`, which
makes the zero-task round unreachable and the round loop's guard unnecessary. A
conceded advocate stays seated, may be addressed again, and may argue its verdict
afresh on evidence filed since. The third hole needed no answer: `0027` had
settled it on the day the placeholder was written.
[`design/execution.md`](./design/execution.md#a-failing-output-schema-spends-the-output-budget)
gained the probe finding the first of those rests on, and `tests/contract/` pins
it. Also added CLAUDE.md's rules for how questions are put to me.

**Why this way:**
[`decisions/0036`](./decisions/0036-a-continuance-carries-at-least-one-interrogatory.md),
[`decisions/0037`](./decisions/0037-a-conceded-advocate-stays-addressable.md). No
journal entry — everything settled this session binds future work, so all of it is
ADR or spec material.

**Commits:** `32059be`, `b79cc29`

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
