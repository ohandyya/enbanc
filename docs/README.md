---
status: current
updated: 2026-09-05
---

# Documentation

Everything under `docs/` is readable by AI agents. Human-only material lives in
`notes/` (versioned) or `local/` (gitignored), both of which are blocked in
`.claude/settings.json`.

The split that matters is **current truth vs. dated record**:

- `design/` and `decisions/` describe the system as it is meant to work now.
- `journal/` records what happened on a given day and is never updated after.
- `progress.md` straddles the two on purpose: its `Current state` block is
  rewritten every session, its `Log` is never edited.

If the two disagree, `design/` wins. See [`../CLAUDE.md`](../CLAUDE.md) for the
full ruleset.

## Index

| Doc | What it covers |
|---|---|
| [`progress.md`](./progress.md) | Where the work stands right now, and a dated trail of how it got here. Start here |
| [`glossary.md`](./glossary.md) | Courtroom vocabulary — tribunal, statute, advocate, ruling |

### Design — how the system should work

| Doc | What it covers |
|---|---|
| [`design/tribunal.md`](./design/tribunal.md) | The proceeding: rounds, interrogatories, concession, and the constraints that make the transcript complete |
| [`design/api.md`](./design/api.md) | The public surface being designed toward `0.1.0` |
| [`design/evidence.md`](./design/evidence.md) | Tools: what one is, how you add your own, and how what it returns becomes an exhibit a reviewer can check |
| [`design/outcomes.md`](./design/outcomes.md) | Every way a proceeding can end, worked through with concrete values: a ruling, a spent round limit, a spent budget, a downed provider, a misconfigured tribunal |
| [`design/prompting.md`](./design/prompting.md) | How `enbanc` turns its types into text a model reads, and a proceeding back into text a human reads: the two procedural prompts in full, how an agent's instructions are assembled, the four turn templates, how ledger ids reach the model, and what `Transcript.render()` produces |
| [`design/execution.md`](./design/execution.md) | How a proceeding maps onto PydanticAI: verified findings about what the framework already does, the whole proceeding written out as literal messages, then the three pieces — message history against the transcript, the ledgering toolset, and round orchestration with the filing clerk, the failure pattern, and usage capture |
| [`design/degenerate-deliberations.md`](./design/degenerate-deliberations.md) | **Placeholder, left for future.** Behaviours the schemas admit and no document rules on — an empty continuance, an interrogatory to a conceded advocate. Not needed for `0.1.0` |
| [`design/testing.md`](./design/testing.md) | **Placeholder, left for future.** How an LLM-driven library is asserted on deterministically. Not needed for `0.1.0` |
| [`design/packaging.md`](./design/packaging.md) | **Placeholder, left for future.** Module layout, export surface, where the errors live, the Python floor. Not needed for `0.1.0` |

### Decisions — ADRs

| Doc | What it covers |
|---|---|
| [`decisions/0001-statute-carries-no-model.md`](./decisions/0001-statute-carries-no-model.md) | Why a `Statute` is inert rule text with no model attached, why `Statute.draft()` is cut from `0.1.0`, and why it stays a type rather than a `str` |
| [`decisions/0002-the-judge-is-a-role.md`](./decisions/0002-the-judge-is-a-role.md) | Why `Judge` is a concrete `enbanc`-owned class rather than a protocol, why per-proceeding state lives in a sitting instead of on the injected agent, and the invariant that keeps message history inside the transcript |
| [`decisions/0003-models-and-guidance-are-injected.md`](./decisions/0003-models-and-guidance-are-injected.md) | Why the caller constructs and injects a PydanticAI `Model`, how `Tribunal`'s default and per-agent overrides interact, and why the per-agent steer is `guidance` that augments rather than `instructions` that replaces |
| [`decisions/0004-verdicts-are-a-strenum.md`](./decisions/0004-verdicts-are-a-strenum.md) | Why the verdict enum is a `StrEnum` subclassed from an `enbanc` base, why it parameterizes every other type in the library, and why the `advocates` mapping must cover every value |
| [`decisions/0005-hear-returns-a-hearing.md`](./decisions/0005-hear-returns-a-hearing.md) | Why `hear()` hands back a `Hearing` that wraps the judge's `Ruling` rather than widening it, and why round-limit exhaustion is what forced the choice |
| [`decisions/0006-the-transcript-schema.md`](./decisions/0006-the-transcript-schema.md) | What a transcript holds — five filings, an entry envelope, a self-contained record — and why raw advocate tool traffic stays out of it, narrowing the invariant `0002` states absolutely |
| [`decisions/0007-a-statute-is-opaque-text.md`](./decisions/0007-a-statute-is-opaque-text.md) | Why a `Statute` is `text` plus an optional `name` and nothing more, why `enbanc` holds no assumption about the text's format or content, why named criteria were rejected, and why that makes `Statute.draft()` moot rather than deferred |
| [`decisions/0008-guidance-is-human-written.md`](./decisions/0008-guidance-is-human-written.md) | Why `guidance` is prose a human writes and `enbanc` never generates, rewrites, or tunes, why a guidance optimizer and a labeled corpus stay out of the library, and which of `0003`'s rationales this withdraws |
| [`decisions/0009-model-settings-live-on-the-model.md`](./decisions/0009-model-settings-live-on-the-model.md) | Why there is no `settings=` on `Tribunal`, `Judge`, or `Advocate`, why `enbanc` passes no per-request model settings of its own, and where each half of "retries" actually lives |
| [`decisions/0010-streaming-yields-the-record.md`](./decisions/0010-streaming-yields-the-record.md) | Why `hear_stream()` yields transcript entries and nothing else, why it is a context manager over a live `Proceeding` rather than a bare generator, and why `hear()` is that stream consumed |
| [`decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md`](./decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md) | Why a spent round limit is a recorded `Undecided` outcome while a provider or tool failure raises `ProceedingFailed`, why one advocate's failure ends the whole proceeding, and why the exception names drop the courtroom metaphor |
| [`decisions/0012-a-failure-cancels-the-round.md`](./decisions/0012-a-failure-cancels-the-round.md) | Why the first failure cancels the advocates still in flight rather than draining them, why a failed transcript is what was filed rather than what the round contained, and why `participant` stays singular |
| [`decisions/0013-a-case-is-a-subclassable-base.md`](./decisions/0013-a-case-is-a-subclassable-base.md) | Why `Case` is an open base class users subclass rather than a second type parameter on `Transcript` and `Hearing`, why the base allows extra fields, and why `Transcript.case` must be `SerializeAsAny` |
| [`decisions/0014-usage-is-broken-down-per-participant.md`](./decisions/0014-usage-is-broken-down-per-participant.md) | Why a `Hearing` splits its spend per advocate and judge as well as reporting a total, why the breakdown is the stored fact and the total its sum, and why `judge` becomes a reserved verdict value |
| [`decisions/0015-interrogatory-ids-are-stamped-on-filing.md`](./decisions/0015-interrogatory-ids-are-stamped-on-filing.md) | Why the judge emits an id-less interrogatory and the tribunal stamps `r{round}-q{n}` when it files the continuance, why the recorded type's `id` is required with no default, and why `Response.answering` is stamped from the dispatch too |
| [`decisions/0016-exhibits-are-stamped-citations.md`](./decisions/0016-exhibits-are-stamped-citations.md) | Why an advocate cites a ledgered source id instead of writing a reference, what a tool may return and why `Source` is opt-in, why the excerpt stays model-authored while everything around it is stamped, and why the shipped `web_search` is written against Tavily's SDK rather than wrapping PydanticAI's |
| [`decisions/0017-read-only-is-a-contract.md`](./decisions/0017-read-only-is-a-contract.md) | Why `enbanc` cannot enforce read-only tools at the tool boundary as `tribunal.md` once claimed, why a declared-read-only flag and an approval-gated toolset were both rejected, and what real enforcement would cost |
| [`decisions/0018-the-search-client-is-a-core-dependency.md`](./decisions/0018-the-search-client-is-a-core-dependency.md) | Why `tavily-python` is a core dependency rather than the `enbanc[web]` extra `0016` called for, what the install actually costs once `pydantic-ai`'s tree is accounted for, and why this is not precedent for a second provider SDK |
| [`decisions/0019-the-ledger-is-part-of-the-record.md`](./decisions/0019-the-ledger-is-part-of-the-record.md) | Why every source an advocate's tools returned is recorded verbatim on `Transcript.ledger`, reversing the suppression-invisibility cost `0006` accepted; why references without content and an opt-out flag were both rejected; and what unbounded transcript size and travelling content now cost |
| [`decisions/0020-tool-timeouts-ride-on-the-tool.md`](./decisions/0020-tool-timeouts-ride-on-the-tool.md) | Why a tool's timeout goes on `pydantic_ai.Tool` rather than on any `enbanc` type, why per-advocate and tribunal-wide defaults and a built-in default were all rejected, why the unbounded bare function is accepted, and why `max_concurrency` was never a tool setting |
| [`decisions/0021-retry-prompts-are-outside-the-invariant.md`](./decisions/0021-retry-prompts-are-outside-the-invariant.md) | Why the transcript invariant excludes `enbanc`'s own retry prompts, why naming the exception beats an invariant known to be false, and the cost accepted — a record that cannot tell a weak argument from a degraded one |
| [`decisions/0022-tool-failures-are-recorded.md`](./decisions/0022-tool-failures-are-recorded.md) | Why a tool call that returned nothing gets a row on `Transcript.failures`, why it carries no id and lives outside the ledger rather than as an `outcome` flag on `Retrieval`, why `enbanc` records the gap instead of acting on it, and how this narrows `0021` |
| [`decisions/0023-advocates-argue-blind-and-rebut-informed.md`](./decisions/0023-advocates-argue-blind-and-rebut-informed.md) | Why an advocate sees no peer filing in round 1 but reads the record from round 2, why sequencing the round and a two-phase argue-then-rebut round were both rejected, why concession stays a round-1 filing, and why visibility is a rule rather than a knob |
| [`decisions/0024-a-budget-stops-the-proceeding-between-rounds.md`](./decisions/0024-a-budget-stops-the-proceeding-between-rounds.md) | Why a proceeding-wide `budget` is checked between rounds rather than inside one, why that makes a budget stop an `Undecided` outcome with a `reason` rather than an exception or a third outcome type, why a shared usage accumulator and an `enbanc` budget type were rejected, and what `max_concurrency` actually bounds |
| [`decisions/0025-the-record-includes-what-steered-it.md`](./decisions/0025-the-record-includes-what-steered-it.md) | Why `guidance`, the prompting surface, the verdict set, and the round limit become standing `Transcript` fields — closing two exceptions to the context invariant that predate `0021` — why the judge is told which deliberation this is and never what the budget has left, and why the procedural prompt is recorded by version rather than by text |
| [`decisions/0026-one-renderer-serves-both-audiences.md`](./decisions/0026-one-renderer-serves-both-audiences.md) | Why one renderer feeds the agents and the reviewer, why every agent viewpoint is a strict subset of the reviewer's rather than a separately tuned format, why a view is taken against a snapshot, and what that costs the readability of `Transcript.render()` |
| [`decisions/0027-an-advocate-answers-its-interrogatories-in-order.md`](./decisions/0027-an-advocate-answers-its-interrogatories-in-order.md) | Why an advocate asked two questions answers them sequentially rather than in two concurrent runs — a forked message history and nondeterministic ledger ids, not just self-contradiction — why the cross-advocate fan-out is untouched and `0023`'s objection to sequencing does not reach it, and why answering every question in one run was rejected |
| [`decisions/0028-usage-accumulates-per-participant.md`](./decisions/0028-usage-accumulates-per-participant.md) | Why `enbanc` mints one `RunUsage` per participant and passes it into every run rather than reading a figure off each result, why that lets a `ProceedingFailed` name every participant that was dispatched — so absence means *never dispatched* rather than *did not report* — and why the total is still a floor |
| [`decisions/0029-a-budgets-request-limit-must-be-chosen.md`](./decisions/0029-a-budgets-request-limit-must-be-chosen.md) | Why a `budget` whose `request_limit` is still `UsageLimits`' default of 50 is a `ConfigurationError` rather than a field `enbanc` honours or ignores, why the field is worth keeping when `cost_limit` silently enforces nothing on an unpriceable model, and why this adds a guard to `0024` rather than changing its mechanism |
| [`decisions/0030-the-retry-budgets.md`](./decisions/0030-the-retry-budgets.md) | Why `Agent(retries=...)` is two independent budgets rather than the one three documents described, what numbers `enbanc` sets and why `outcomes.md` §1 is what pins them, and why a tool's `max_retries` rides on the `Tool` beside its timeout while the output budget stays the library's |

### Guides — user-facing how-to

*(none yet)*

### Journal — implementation records

| Doc | What it covers |
|---|---|
| [`journal/2026-09-02-values-before-schemas.md`](./journal/2026-09-02-values-before-schemas.md) | Why writing `design/outcomes.md` as concrete values caught a redundant field and an unanswerable gap that reviewing the schemas — and writing an ADR about them — did not |
| [`journal/2026-09-04-writing-the-prompt-found-the-holes.md`](./journal/2026-09-04-writing-the-prompt-found-the-holes.md) | Why writing the procedural prompts found two unnamed exceptions to the context invariant, a self-contradicting `since` definition, and a premise a new decision would have falsified — none of which reviewing the rule had caught; the second instance of the pattern `2026-09-02` records |
| [`journal/2026-09-05-the-probe-found-the-holes.md`](./journal/2026-09-05-the-probe-found-the-holes.md) | Why running `pydantic-ai` found five defects in *accepted* documents that reading it had not — a budget enforcing a limit nobody set, a retry default that made a worked example unreachable, a promise that under-described its own mechanism, a missing interrogatory, and an id format nothing explained; the third instance of the pattern, and the first where the artifact was code |

## Adding a doc

1. Put it in the directory whose guarantee matches it (table in `CLAUDE.md`).
2. Give it the standard frontmatter: `status` and `updated`.
3. Add a row to the index above. An unindexed doc is one nobody finds.
