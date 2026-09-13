---
status: draft
updated: 2026-09-13
---

# Testing

How a library whose behaviour is LLM-driven is asserted on deterministically.
[`api.md`](./api.md) says what shape the result has, [`outcomes.md`](./outcomes.md)
says what values it holds, [`prompting.md`](./prompting.md) says what text each
participant reads, and [`execution.md`](./execution.md) says how the loop is
built; this says how any of it is known to be true.

> `status: draft` — the harness exists and the tests do not. `tests/` carries
> the four tier directories, the marker-by-path wiring, the offline guard, and
> the live fixtures described below; what they hold is three placeholders and
> one pinned `pydantic-ai` claim, because there is no `enbanc` to test yet.

The question is tractable because of a decision made elsewhere.
[`0003`](../decisions/0003-models-and-guidance-are-injected.md) makes the model
an injected `pydantic_ai.models.Model`, required at the tribunal and overridable
per agent, so PydanticAI's `TestModel` and `FunctionModel` drop straight in and a
whole proceeding runs with no provider in the loop — including a proceeding where
the judge and each advocate behave differently. Nearly everything this library
does is therefore assertable offline, at no cost, deterministically. The tiers
below exist to keep it that way.

## The four tiers

| Tier | Subject | Third parties | Runs in CI |
|---|---|---|---|
| `unit` | `enbanc`'s own behaviour | none, enforced | yes |
| `contract` | claims `execution.md` makes about `pydantic-ai` | none, enforced | yes |
| `integration` | that the plumbing to a real service works | a provider, Tavily | on demand |
| `e2e` | that [`api.md`](./api.md)'s example works as written | a provider, Tavily | on demand |

**`unit` is the bulk of the suite and the only tier that tests edge cases.** It
covers everything from `Tribunal.__init__` validation through a complete
multi-round proceeding, because a complete proceeding is offline. Where a
component reaches a third party — `web_search` calling Tavily — the unit test
drives the pre- and post-processing around a faked client, which is what makes
the awkward paths reachable at all: a real Tavily cannot be asked to return a
result with no `url`.

**`contract` is not about `enbanc`.** [`execution.md`](./execution.md#what-pydanticai-already-does)
records eleven findings about `pydantic-ai 2.36.0`, verified by reading the
installed source and running it, and says outright that "these are claims about a
dependency, and they are worth re-checking when the pin moves." They were
verified by throwaway scripts. This tier is where those scripts live so a version
bump cannot falsify the document silently. It is separated from `unit` because
its failures mean something different: a red `contract` test says the dependency
moved, not that `enbanc` broke, and the fix is usually to change a design
document rather than to change code.

Two of the eleven findings are derivations rather than probes and have no module
here. *Three channels reach a model* is a summary of the two findings above it.
*What lands in history that no rendered turn contains* is the whitelist the
invariant helper encodes, and is tested [there](#the-transcript-invariant)
instead.

| `execution.md` finding | Asserts |
|---|---|
| Carrying a conversation is a parameter | `run(message_history=…)`, `result.all_messages()` round-trips |
| Instructions are re-resolved every run | Instructions reappear per request and never enter history |
| A filing lands in history as a tool call | One output tool per union member, named from the class; no `TextPart` on the path |
| Intercepting a tool call is one method | `WrapperToolset.call_tool` return becomes `ToolReturnPart` verbatim; a `Tool` timeout surfaces as `ModelRetry` inside it; `FunctionToolset(tools=…)` takes bare functions and `Tool`s alike |
| Usage accumulates into an object the caller owns | `run(usage=u)` mutates in place, `result.usage is u`, and a run that dies mid-flight leaves its partial spend |
| Two retry budgets, not one | Both default to `1`, they are independent, tool retries key on tool name, `Tool(max_retries=…)` overrides |
| A failing output schema spends the `output` budget | Attempts track `output` alone; the constraint reaches the model as `minItems` |
| `max_concurrency` is set at construction | It is an `__init__` parameter, not a `run()` argument |
| A failing fan-out need not raise an `ExceptionGroup` | A child that records and cancels lets the group exit cleanly; the cancelled-exception re-raise is what keeps an *external* cancellation from naming a participant |

**`integration` proves the wire, not the logic.** One happy path per external
seam: `web_search` against real Tavily returning real `Source`s, and one short
run against a real provider. If an edge case is being tested here it is in the
wrong tier — the point is to catch the failures a fake cannot have, which are a
moved API shape, a changed auth flow, a response that no longer parses.

**`e2e` proves the product.** [`api.md`](./api.md#shape)'s example, run
start to finish against a real provider, plus the `hear_stream` loop. It asserts
almost nothing about content — a model is free to rule either way — and asserts
that a `Hearing` came back, its transcript is coherent, and its usage is
non-zero. Its job is to fail when the composition is broken in a way every faked
tier was too kind to notice.

## Layout, and how a tier is selected

```text
tests/
  conftest.py            markers by path; the outcomes.md tribunal
  unit/
    conftest.py          the offline guarantee
    ...
  contract/
    conftest.py          the offline guarantee
    ...
  integration/
    conftest.py          skips the tier when keys are absent
  e2e/
    conftest.py          skips the tier when keys are absent
```

**A test's tier is its directory.** The Make targets select by path, and
`tests/conftest.py` applies the matching marker in `pytest_collection_modifyitems`
so `-m unit` also works. Nothing is decorated by hand, so nothing can be
forgotten — a test file in `tests/unit/` is a unit test whether or not its author
thought about tiers.

This is what makes the offline guarantee below possible at all: a fixture cannot
key off a marker that a test may or may not carry, but it can key off the
directory the file is in.

It also fixes the import mode. The same subject gets tested from more than one
tier — `test_web_search.py` belongs in both `unit/` and `integration/` — and
under pytest's default `prepend` mode two files with one basename share a
top-level module name and collection fails. `--import-mode=importlib` names each
module from its full path, so tier directories can mirror each other freely.

## The offline guarantee, enforced

An autouse fixture in `tests/unit/conftest.py` and `tests/contract/conftest.py`
replaces `socket.socket.connect` with a stub that raises.
Any test in either tier that reaches the network fails, loudly, naming itself.

It is enforced rather than promised because the alternative is a rule nobody can
verify and whose failure mode is silent. A unit test that quietly acquired a live
provider call still passes; it is just slower, flakier, nondeterministic, and
billed. Nothing about the green run says so. The blocker converts that into an
error at the first byte.

Loopback is allowed, so a test may stand up a local server; the block is on
reaching a third party.

**It is a tripwire, not a sandbox**, and one test deliberately steps outside it.
`tests/unit/test_import_is_inert.py` checks what
[`packaging.md`](./packaging.md#what-import-enbanc-may-do) requires of
`import enbanc` — no I/O, no provider SDK, no `enbanc.tools` — and it can only ask
that question in a **subprocess**, because by the time a test function runs,
pytest has imported half the tree in-process and an autouse fixture has not yet
existed at any point an import happened. A child process carries none of the
guard. That is acceptable here and nowhere else: what the child does is
`import enbanc` and read `sys.modules`, and the assertion is precisely that it
reached nothing. A second subprocess test would need the same argument made
again, from scratch.

## How the model is faked

Three shapes, in increasing order of what they cost to write.

**`TestModel`** for anything that only needs a well-formed filing to exist —
`Tribunal` construction, wiring, the shape of a transcript. It fabricates a valid
instance of the output type and asks nothing of the test.

**`FunctionModel`** for behaviour: a judge that issues a continuance in round 1
and rules in round 2, an advocate that concedes, an advocate whose second
response cites a ledger id no tool returned. This is the workhorse for
[`outcomes.md`](./outcomes.md)'s endings, because every one of them is a
statement about *what the participants did*.

**A capturing `FunctionModel`** for the invariant. It records every
`ModelMessage` handed to it, keyed by participant, and then behaves as a
`FunctionModel` would. What it records is the exact context each participant ran
under, which is the only thing that can settle whether the invariant held.

Provider failure is faked by a `FunctionModel` that raises — an
`anthropic.APIConnectionError` for
[`outcomes.md`](./outcomes.md#an-advocates-provider-is-down)'s downed provider —
and tool failure by a tool that raises. Neither needs a provider to be down.

## The transcript invariant

*Nothing enters an agent's context that is not also in the transcript* is what
the product is sold on, and
[`0026`](../decisions/0026-one-renderer-serves-both-audiences.md) already made it
true by construction: there is one renderer, agent viewpoints are strict subsets
of the reviewer's, and no code path can render for an agent something the
transcript does not hold. So the tests are not trying to establish the property
from nothing. They guard the two places it can still be lost.

**The projections, tested directly.** `0026` says where the risk moved: "a wrong
`since`, or a filter that forgets to drop the ledger, breaks the invariant as
thoroughly as a second renderer could. What changes is that the mistake is in one
small, enumerable place." Enumerable is the operative word — these are the
highest-value tests in the suite.

- `JudgeView` and `AdvocateView` output never contains the ledger, the failures,
  or another advocate's retrievals.
- Every line an agent view emits appears in the `ReviewerView` of the same
  transcript. The subset property, asserted rather than assumed.
- `since` selects the right delta. The eight-row table in
  [`execution.md`](./execution.md#since-and-the-snapshot-run-by-run) is the
  fixture, and **run 7 is the case that constrains everything**: its snapshot
  holds entry 6 and must not hold entry 5, even when entry 5 landed first.

**The whole context, checked against the record.** A helper —
`assert_invariant_held(captured, transcript)` — takes what the capturing model
recorded and the transcript that resulted, and requires every message part to be
either derivable from `render(transcript, view)` and
`tribunal.instructions_for(participant)`, or one of the four escapes
[`execution.md`](./execution.md#what-lands-in-history-that-no-rendered-turn-contains)
enumerates:

1. `RetryPromptPart` — [`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md)'s
   sole exception, showing up as a message part.
2. `ToolCallPart` / `ToolReturnPart` traffic — covered by `Transcript.ledger`
   under [`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md), but not
   byte-identical to it.
3. `ToolReturnPart('Final result processed.')` — the receipt for the output tool.
4. **The agent's own pre-stamp output.** An advocate emits a private `_Exhibit`
   holding a bare ledger id and an excerpt; the transcript holds the stamped
   public `Exhibit` ([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)).

The fourth is why this cannot be a substring test. The transcript row is a
*superset* of what the agent wrote, so a byte-for-byte containment check fails on
a proceeding that is perfectly correct. The helper compares the stamped fields it
can and accepts the rest as accounted for.

**This is an assertion, not a test.** Any proceeding-level test can call it, and
the ones covering `outcomes.md` do. One dedicated invariant test proves the
property on one path; making it available everywhere means every future test of
every other behaviour also happens to check that nothing leaked. That is the
point of writing it as a helper.

## `outcomes.md` is the spine

[`outcomes.md`](./outcomes.md) already reads as a test plan: a fixed tribunal,
then every ending written out as concrete values, including a downed provider, a
raising tool, and a misconfigured tribunal. The suite mirrors it, section for
section.

`tests/conftest.py` holds one factory building the tribunal from
[`outcomes.md`](./outcomes.md#the-tribunal-these-examples-use) — three verdicts,
`max_rounds=5`, `psql` and `web_search` faked — and each module below varies only
what its section varies.

| `outcomes.md` § | Module |
|---|---|
| §1 The judge rules | `tests/unit/outcomes/test_01_judge_rules.py` |
| §2 The judge rules in round 1 | `tests/unit/outcomes/test_02_rules_in_round_1.py` |
| §3 The envelope is spent | `tests/unit/outcomes/test_03_envelope_spent.py` |
| §4 A participant cannot be heard | `tests/unit/outcomes/test_04_cannot_be_heard.py` |
| §5 The tribunal is misconfigured | `tests/unit/outcomes/test_05_misconfigured.py` |
| §6 The same endings, watched live | `tests/unit/outcomes/test_06_watched_live.py` |
| §7 Persisting a hearing and reading it back | `tests/unit/outcomes/test_07_round_trip.py` |

**The doc is mirrored by the tests, never executed as them.** Its examples are
`repr` forms with elision and inline commentary — `<LoanDecision.DENY: 'deny'>`,
`entries=[...]`, `# never cited by APPROVE` — written to be read. Nothing extracts
and runs them. What keeps the two in step is rule 2 in
[`../../CLAUDE.md`](../../CLAUDE.md): a change to behaviour updates the design doc
in the same commit, and a change to behaviour is exactly what breaks these tests.
See [`0032`](../decisions/0032-a-design-doc-is-mirrored-by-tests.md).

The assertion snippets inside each section are directly usable as written, and
are where each module starts:

```python
hearing.rounds                                       # 2 — not 5, the budget
len(hearing.transcript)                              # 7
hearing.outcome is hearing.transcript[-1].filing     # True — a pointer, not a copy
len(hearing.transcript.ledger)                       # 5 retrieved, 4 filed
```

Two things `outcomes.md` specifies are worth naming as tests in their own right
because nothing else would reach them. **The three `ConfigurationError` messages**
in §5 are asserted as text, not just as a raised type — each one exists because
the mistake it catches looks ordinary
([`0029`](../decisions/0029-a-budgets-request-limit-must-be-chosen.md)), and the
message is the whole remedy. And **the suppression join** in §1 — the sources a
tool returned that no filing cited — is the one place `0019`'s ledger earns its
keep, so it is asserted over a proceeding built to have exactly one.

### The table is the exception, not the pattern

This is the only doc-to-module map in this document, and it is here because
`outcomes.md` cannot hold it. That document is worked values written to be read,
and [`0032`](../decisions/0032-a-design-doc-is-mirrored-by-tests.md) protects
exactly that property — threading `# see tests/unit/outcomes/test_03_...` through
seven sections of `repr` prose would damage the thing whose readability is its
whole value.

**Otherwise a design document names its own mirror, beside the claim it pins.**
[`packaging.md`](./packaging.md#the-export-surface) names
`tests/unit/test_export_surface.py` in the paragraph that fixes `__all__`, and
[`test_import_is_inert.py`](./packaging.md#what-import-enbanc-may-do) in the one
that lists the import-time invariants. Neither belongs in a table here.

**This document holds technique, not inventory.** How a model is faked, how a
prompt is pinned, how Tavily is faked, how the transcript invariant is asserted,
and what must not be asserted at all — every section here exists because
something was hard to test, and says how. A claim that needs no technique —
`sorted(enbanc.__all__) == [...]` needs none — has nothing to say to this
document, and an index row for it would be a second place to keep true whose
failure mode is silence: a document gains a test, the index does not, and
nothing catches it. That is the same objection this library makes to
`position` on an `Argument` and to `cited` on a `Retrieval`. See
[`0035`](../decisions/0035-testing-holds-technique-not-an-index.md).

## Pinning the prompting surface

[`prompting.md`](./prompting.md#procedure-versions) states the hazard plainly: "A
prompt edited without a version bump makes every transcript that claims `p1` a
false record of what ruled." Nothing in the type system can catch that. A golden
does.

`inline-snapshot` pins the full text of everything `Transcript.procedure`
covers — both procedural prompts, all four turn templates, the tool-result
format, and `Transcript.render()`'s output — with `p1` named in each test. Editing
any of that text fails the golden, and the failure is the reminder that the edit
is three moves in one commit: the text in `prompting.md`, a new row in its version
table, and the constant `enbanc` stamps.

`inline-snapshot` rather than a snapshot directory because the expected text sits
in the test file, so a prompt change shows up as a prompt diff in the file under
review rather than in a generated artifact one step away. It is also what
`pydantic-ai` itself uses, which keeps one idiom across the dependency boundary.

`tribunal.instructions_for(participant)` is the seam these tests run through. It
is synchronous, provider-free, and assembles the same instruction string the
agent is built with, which makes the entire instructions channel testable without
a proceeding at all.

## Faking Tavily

The unit tests for `web_search` monkeypatch the Tavily client class in the module
that defines the tool, and drive the real factory. What they assert is the
mapping [`evidence.md`](./evidence.md#the-default-tool) specifies — `url` to
`reference`, `title` to `label`, `content` to `content`, and `score`, `id`,
`raw_content`, `favicon`, and the top-level `answer` dropped — together with the
paths a live service will not produce on demand: an empty result set, a missing
field, a non-`200`, a timeout.

**The public factory does not grow a seam for the tests.**
[`evidence.md`](./evidence.md) fixes the signature as `web_search(api_key=...)`,
and a `client=` parameter would be API surface that exists for one caller who is
not a user. Monkeypatching a module-level name costs the tests one line and costs
the design nothing.

The same rule holds generally: no design document changes to make something
testable. If a thing cannot be tested without changing the public surface, that
is an argument to be had in the document that owns the surface, and settled
there.

## What must not be asserted

Four things look like tests and are not.

**Read-only tools.** [`0017`](../decisions/0017-read-only-is-a-contract.md)
records that `enbanc` cannot enforce this at the tool boundary. A test asserting
it would be asserting something the library does not do.

**How many entries survive a cancelled round.**
[`0012`](../decisions/0012-a-failure-cancels-the-round.md) makes the first failure
cancel the advocates still in flight, and
[`api.md`](./api.md#when-something-goes-wrong) says two runs of the same outage
can leave different numbers of entries behind. Assert *which participant*
`ProceedingFailed` names, never the length of what it carries.

**Exact usage after a failure.**
[`0028`](../decisions/0028-usage-accumulates-per-participant.md) makes the total a
floor. Assert that every dispatched participant has a key — absence means never
dispatched — and compare with `>=`, not `==`.

**That `procedure` reproduces the prompt.** It names a version and deliberately
does not store the text; [`prompting.md`](./prompting.md#the-invariant-accounted-for)
calls that "a deliberate weakening." The golden above is what covers the text.
A test asserting the transcript holds the prompt would be asserting a design
`0025` rejected.

## Running the tiers

```text
make unit-tests          enbanc's own behaviour, offline
make contract-tests      what execution.md claims about pydantic-ai, offline
make integration-tests   real Tavily and a real provider
make e2e-tests           api.md's example, end to end

make test                both offline tiers — the gate check-all runs
```

One target per tier, and `make test` is the two offline ones together. That
keeps `check-all` and `.github/workflows/ci.yml` at exactly the composition they
already have: the live tiers are additive, and nothing that passes today starts
costing money.

**The live tiers run in CI only when asked.** Locally they read `.env` and are
run by hand. In CI they are `.github/workflows/live-tests.yml`, which fires two
ways and neither of them is automatic: adding the **`live-tests` label** to a pull
request runs both tiers and reports as a check on that pull request, and
**`workflow_dispatch`** runs either tier against any branch from the Actions tab.
Nothing runs on push, on an unlabelled pull request, or on a schedule, so no job
spends money unattended and [`ci.yml`](../../.github/workflows/ci.yml) keeps its
contract of being exactly `make check-all` with no secrets.
[Below](#triggering-a-live-run-in-ci) is how to fire either one.

The credentials sit in a `live-tests` GitHub environment rather than in
repository secrets — `OPENAI_API_KEY` and `TAVILY_API_KEY` as secrets,
`ENBANC_TEST_MODEL` as a variable, since a model name is not one and a run that
names the model it tested is worth more than one that hides it. Only a job
declaring that environment can read them, and each run lands in the deployments
log. [`0033`](../decisions/0033-live-tiers-run-in-ci-on-demand.md) records why the
trigger stays manual, and why a fork pull request cannot run these at all: it
gets no secrets, so labelling one fails rather than passing.

That environment does name a provider, and so does the workflow that reads it.
This is the same choice a populated `.env` makes on a laptop and it is made in
the same place — configuration, not the harness. What the section below fixes is
that nothing in `tests/` knows which provider was chosen; swapping the CI
environment to another one is two secrets and a variable, and no test changes.

The cost [`0031`](../decisions/0031-tests-are-tiered.md) accepted is unchanged —
provider drift still surfaces when someone asks, not within a day of it
happening. What the workflow buys is that asking is a click on the pull request
under review. A nightly job remains the obvious next move and is now a
`schedule:` block away.

**The harness names no provider, because the library does not.**
[`api.md`](./api.md#design-commitments) commits to working with any
`pydantic_ai.models.Model` the caller constructs, and a live tier that could only
run against one provider would be testing less than that. So `ENBANC_TEST_MODEL`
holds a PydanticAI model string — `anthropic:claude-sonnet-5`,
`openai:gpt-5`, whatever the runner has — and the `live_model` fixture builds it
with `infer_model`. The credentials are that provider's own, under that
provider's own variable name, resolved by PydanticAI rather than enumerated here.

This is test configuration and not a reopening of
[`0003`](../decisions/0003-models-and-guidance-are-injected.md): what that ADR
rejects is `Tribunal` accepting a model string. Nothing here changes what
`Tribunal` takes, and the fixture hands `hear()` a constructed `Model` exactly as
a caller would.

`TAVILY_API_KEY` is the one provider the harness does name, because
[`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md) already
named it: `web_search` is written against Tavily's SDK and ships in the core
dependencies, so it is the library's choice rather than the runner's.

**There is no tier-wide gate.** A test asks for what it needs — `live_model` for
a provider, `tavily_api_key` for search — and skips itself when that is missing,
so a Tavily test still runs on a machine with no model configured and
`make integration-tests` on a fresh clone reports why rather than erroring.

**Unset skips; set-but-unusable fails.** An absent `ENBANC_TEST_MODEL` means the
machine is not configured for live runs, which is the ordinary state and not a
result. A model string that is set and cannot be built means a live run was asked
for and did not happen — a typo, an uninstalled provider SDK, or a missing
credential — and skipping would hide all three behind the same green dot.
PydanticAI's own message names the variable or the package, so it is passed
through rather than re-worded.

**In CI, unset is a failure too.** The skip above is right for a laptop, where an
absent key means the machine was never set up for live runs. In a run someone
asked for it means the opposite — the run happened and proved nothing, which is
the one thing a live tier exists to rule out, and it reports green. So
`live-tests.yml` opens with a preflight step that fails when any of the three
values is empty. The fixtures are untouched; the rule differs by where it runs,
and the step that makes it differ says so.

### Triggering a live run in CI

Two ways, and which one to reach for depends on what is being checked.

**The label, for a change under review.** Add `live-tests` to the pull request.
Both tiers run, and the result reports as a check on that pull request alongside
`ci.yml`'s. Removing and re-adding it runs them again; `concurrency` cancels
whatever was in flight rather than billing twice for one commit.

```text
gh pr edit <number> --add-label live-tests
```

The label has to exist in the repository before it can be applied to anything —
`gh label create live-tests -d "Run the live test tiers on this PR"`, once ever.
Creating it triggers nothing; the event is a label being *added to a pull
request*.

**The dispatch, for everything else.** Actions → **Live tests** → **Run
workflow**, then choose a branch and a tier. This is the only way to run one tier
alone, and the only way to run with no pull request in the picture — a re-check
against `main` after a provider outage, or after a `pydantic-ai` bump.

```text
gh workflow run "Live tests" -f tier=integration
gh workflow run "Live tests" --ref <branch> -f tier=both
```

`tier` defaults to `both`, and on the label event it is empty, which is why a
label runs both tiers.

**A `workflow_dispatch` is read from the default branch.** Worth stating because
it is not guessable and it presents as a broken workflow: until `live-tests.yml`
is on `main`, the **Run workflow** button does not exist and
`gh run list --workflow=live-tests.yml` answers `404 … not found on the default
branch`. The label is unaffected, because `pull_request` events use the workflow
file from the pull request's own head branch. So a change to this workflow can be
exercised on the pull request that makes it, and only the dispatch half has to
wait for the merge.

**The one-time setup.** A `live-tests` environment under Settings → Environments,
holding `OPENAI_API_KEY` and `TAVILY_API_KEY` as environment secrets and
`ENBANC_TEST_MODEL` as an environment variable. Nothing else — no repository
secret, and no protection rule, since the label and the dispatch are themselves
the manual gate. A run that finds any of the three empty fails at the preflight
rather than skipping green.

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. See rule 7 in [`../../CLAUDE.md`](../../CLAUDE.md).

*None open.* The one this document opened — how the tiers separate structurally —
is answered above under [layout](#layout-and-how-a-tier-is-selected), and
[`0031`](../decisions/0031-tests-are-tiered.md) records why directories beat
markers and why `e2e` stayed inside pytest.
