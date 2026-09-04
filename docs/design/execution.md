---
status: draft
updated: 2026-09-04
---

# Execution

**PLACEHOLDER — not yet designed.** This file exists to hold a design, and to
name what that design has to settle. Nothing below is a decision — the findings
recorded under [What PydanticAI already does](#what-pydanticai-already-does) are
observations about the framework `enbanc` builds on, and they narrow the design
without being it.

Required for `0.1.0`, in part. How a proceeding maps onto PydanticAI.
[`tribunal.md`](./tribunal.md) says what happens in a proceeding and
[`api.md`](./api.md) says what shape the result has; neither says how the loop
is built. Some of what belongs here is ordinary implementation and needs no
design doc — three pieces are design, and two of those are load-bearing.

## What PydanticAI already does

Verified against **`pydantic-ai 2.36.0`**, the floor pinned in `pyproject.toml`,
by reading the installed source and capturing wire traffic with `FunctionModel`.
Recorded here so the finding is not re-derived, and so it is falsifiable: these
are claims about a dependency, and they are worth re-checking when the pin moves.

None of it is a decision. It is the shape of the thing the design has to be built
on, and most of what looked like work for piece 1 turns out to be the framework's
already.

### Carrying a conversation is a parameter, not a subsystem

`Agent.run()` takes `message_history: Sequence[ModelMessage] | None`, and
`result.all_messages()` hands the conversation back. Keeping each participant's
conversation across rounds is a dict:

```python
history: dict[Participant, list[ModelMessage]] = {}

async def turn(p, agent, prompt: str):
    result = await agent.run(prompt, message_history=history.get(p))
    history[p] = result.all_messages()
    return result.output
```

A participant running for the first time — every advocate in round 1, the judge
at deliberation 1 — passes `None`, which is what "the judge has no history in
round 1" means mechanically.

### Instructions are re-resolved every run and never enter history

Captured from the wire. The agent was built with two `InstructionPart`s; the
second run was given the first run's messages as `message_history`:

```text
request 1: 1 message
  ModelRequest   instructions='PROCEDURAL...\n\nSTATUTE: DTI < 0.43'
       UserPromptPart('ROUND 1: three arguments were filed ...')

request 2: 3 messages
  ModelRequest   instructions='PROCEDURAL...\n\nSTATUTE: DTI < 0.43'
       UserPromptPart('ROUND 1: three arguments were filed ...')
  ModelResponse  TextPart('ok')
  ModelRequest   instructions='PROCEDURAL...\n\nSTATUTE: DTI < 0.43'
       UserPromptPart('ROUND 2: two responses were filed ...')
```

Two consequences worth holding on to:

- **Instructions are not frozen at the first run.** They are re-resolved from the
  agent each time, so changing an agent's instructions between runs would apply
  retroactively to the whole conversation. `enbanc` cannot reach that state —
  agents are built inside `hear()` and discarded
  ([`api.md`](./api.md#design-commitments)) — but it is another reason that split
  has to hold, and it would be a real hazard for any future agent reuse.
- **For Anthropic the parts hoist once to the top-level `system` parameter**
  rather than being re-emitted per historical request (`models/anthropic.py`,
  `_map_message`: "only the opening `SystemPromptPart`s in the first request …
  hoist to the top-level `system` parameter"). That is what makes
  [`prompting.md`](./prompting.md#how-an-agent-is-assembled)'s shared-cache-prefix
  claim true rather than aspirational.

### Three channels reach a model, and `enbanc` writes one of them

| What the agent needs | Channel | Supplied by |
|---|---|---|
| Role, process, question, statute, assignment, guidance | `instructions` | `enbanc`, re-sent automatically every run |
| Its **own** past turns, tool calls, and tool results | `message_history` | PydanticAI, for free |
| **Other participants'** filings, the interrogatory, the case | `user_prompt` | `enbanc` — the rendered delta |

This is the answer to "how does the judge see what the advocates filed?", and it
is two different answers. A participant's own prior output — the judge's last
`Continuance`, an advocate's round-1 argument — is already in its history and
needs no rendering. Another participant's output is not, and nothing in
PydanticAI moves it. That gap is exactly what
[`prompting.md`](./prompting.md#the-turns) fills, and it is why a turn renders a
*delta* rather than the whole record: the rest is already there.

### What lands in history that no rendered turn contains

The reason the invariant needs the qualifications it has, visible in the data
structure:

- **Tool calls and their results**, as `ToolCallPart` and `ToolReturnPart`. An
  advocate's round-1 retrievals are in its round-3 context whether or not it
  filed them — which is precisely why
  [`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md) had to put the
  ledger in the transcript.
- **Retry prompts**, as `RetryPromptPart`. They cannot be filtered out without
  giving up retries, which is
  [`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md)'s
  exception showing up as a message part.
- **The agent's own pre-stamp output.** An advocate emits a private `_Exhibit` —
  a bare ledger id and an excerpt — while the transcript holds the stamped public
  `Exhibit` ([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)). The
  transcript row is a superset, so the invariant holds, but the two are not
  byte-identical and an advocate therefore sees its own round-1 filing twice in
  round 2: once as it wrote it, once as it entered the record.

## The load-bearing pieces

**1. Message history and the transcript.**
[`tribunal.md`](./tribunal.md#constraints-that-define-the-design) states that
each agent carries its own conversation across rounds and that the history "is
a representation of the transcript — never a second channel". That is the
invariant the audit claim rests on.

[`prompting.md`](./prompting.md) has since settled **what** is sent: each turn
carries only the filings a participant has not been shown, rendered from a
snapshot of the transcript taken at dispatch, and every agent view is a filtered
projection of the reviewer's
([`0026`](../decisions/0026-one-renderer-serves-both-audiences.md)). What is left
here is **how**, and the section above narrows it further: carrying a
conversation is `message_history` plus a dict, so what is left is where the
snapshot is taken, how `since` is tracked per participant across rounds, and what
happens to an agent's history when a run is cancelled mid-round
([`0012`](../decisions/0012-a-failure-cancels-the-round.md)) — there is no result
object to read `all_messages()` off, and whether that matters depends on whether
anything resumes. Getting this wrong breaks the guarantee quietly, which is why
it is designed rather than discovered.

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

**3. Round orchestration and usage capture.** The task-group shape — now bounded
by [`0027`](../decisions/0027-an-advocate-answers-its-interrogatories-in-order.md),
which fixes it at one task per *addressed advocate* with that advocate's
interrogatories queued sequentially inside it, rather than one task per
interrogatory — where `max_concurrency`'s limiter sits, how "the first failure cancels the round"
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
