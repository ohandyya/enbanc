---
status: draft
updated: 2026-09-04
---

# Execution

**PLACEHOLDER — not yet designed.** This file exists to hold a design, and to
name what that design has to settle. Nothing below is a decision.

Required for `0.1.0`, in part. How a proceeding maps onto PydanticAI.
[`tribunal.md`](./tribunal.md) says what happens in a proceeding and
[`api.md`](./api.md) says what shape the result has; neither says how the loop
is built. Some of what belongs here is ordinary implementation and needs no
design doc — three pieces are design, and two of those are load-bearing.

## The load-bearing pieces

**1. Message history and the transcript.**
[`tribunal.md`](./tribunal.md#constraints-that-define-the-design) states that
each agent carries its own conversation across rounds and that the history "is
a representation of the transcript — never a second channel". That is the
invariant the audit claim rests on, and it has no mechanism yet. The concrete
question: in round 2 an advocate already holds its own round-1 messages *and*
needs the peer record that
[`0023`](../decisions/0023-advocates-argue-blind-and-rebut-informed.md) grants
it — so what exactly is appended, what is re-sent, and what keeps the two
representations from disagreeing? Getting this wrong breaks the guarantee
quietly, which is why it is designed rather than discovered.

**2. The ledgering toolset.**
[`evidence.md`](./evidence.md#how-a-source-becomes-an-exhibit) gives it one
paragraph — "a toolset `enbanc` owns wraps everything the advocate was given
and intercepts every call". It has to wrap `tools` *and* arbitrary `toolsets`
including MCP servers, assign ids monotonically per advocate across the whole
proceeding, write `Transcript.ledger`
([`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md)) and
`Transcript.failures`
([`0022`](../decisions/0022-tool-failures-are-recorded.md)), and rewrite what
the model sees so ids are citable. It is the hardest single piece of code in
the library.

**3. Round orchestration and usage capture.** The task-group shape, where
`max_concurrency`'s limiter sits, how "the first failure cancels the round"
([`0012`](../decisions/0012-a-failure-cancels-the-round.md)) is actually
effected, at what moment `filed_at` is stamped and an entry reaches the stream,
and how per-participant `RunUsage` accumulates across runs. That last one
decides what [`api.md`](./api.md#when-something-goes-wrong)'s "usage on a
failure is best-effort" concretely means — here the mechanism defines the
guarantee rather than the other way round.

## Also in scope

- One `Agent` per participant, constructed inside `hear()` and discarded when it
  returns — the split [`api.md`](./api.md#design-commitments) commits to under
  "Agents are reusable; a proceeding's state is not".
- Where the `Agent(retries=...)` budget is set, and whether it is configurable.
- How `hear()` is defined as `hear_stream()` driven to exhaustion
  ([`0010`](../decisions/0010-streaming-yields-the-record.md)), so the two
  entry points cannot come apart.
- Where the private-to-public conversions happen — `_Continuance` to
  `Continuance` with stamped ids
  ([`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)), and
  `_Exhibit` to `Exhibit` resolved against the ledger
  ([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)).
- Where `ConfigurationError` is raised, given it must fire at `Tribunal(...)`
  construction and not at `hear()`.

## Open questions

*Not yet opened.* The above is the agenda for writing this document.
