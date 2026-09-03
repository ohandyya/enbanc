---
status: accepted
updated: 2026-09-02
---

# 0010. Streaming yields the record, entry by entry

## Context

[`../design/api.md`](../design/api.md) carried the question of "whether `hear()`
has a streaming counterpart for observing rounds live" with nothing behind it in
either direction.

The pressure for one is structural rather than cosmetic. A proceeding is minutes
long, not seconds: every round fans out across advocates, each of which makes
its own tool calls, and `max_rounds` of those run before a ruling exists. An
awaited `hear()` gives a caller nothing at all until the whole thing is over —
no first argument, no concession, no interrogatory — and there is no technical
reason for that. The transcript is being written incrementally inside the run
already. Holding it back until the end is a decision, not a constraint.

Two commitments bound the shape of the answer.
[`0005`](./0005-hear-returns-a-hearing.md) put the aggregate usage and the round
count on `Hearing` rather than on any filing, so a channel that carries only
filings cannot replace what `hear()` returns — whatever streams has to hand the
`Hearing` back at the end.
[`0006`](./0006-the-transcript-schema.md) made the transcript the audit
artifact and the complete account of what the ruling rests on, which constrains
what a live channel is allowed to show: anything a viewer sees that the record
does not contain is a fact about the proceeding with no home in the artifact.

## Decision

**`hear_stream(case)` exists, as an async context manager over a live
`Proceeding`.**

```python
async with tribunal.hear_stream(case) as proceeding:
    async for entry in proceeding:
        ...

hearing = proceeding.hearing
```

**The unit is the `Entry`.** Each value yielded is the entry appended to the
transcript at that moment — the same object, in filing order. The entry just
received is the last entry of `proceeding.transcript`.

**Nothing streams that is not in the record.** No lifecycle events, no partial
filings, no token deltas. The stream is a view of the transcript being written,
not a second channel alongside it.

**`hear()` is `hear_stream()` consumed to exhaustion.** One implementation, and
the two entry points cannot drift into producing different proceedings.

**`Proceeding` is a handle, not a record.** It is the only type on this surface
that is not a Pydantic model: it holds no fact of its own, is never serialized,
and never appears on a result. What it exposes — `transcript`, `hearing`, and
async iteration — are views of things that already exist.

**Abandonment is defined.** Break out of the loop and the block exits: the
in-flight advocate and judge runs are cancelled, `proceeding.transcript` holds
everything filed up to that point, and `proceeding.hearing` raises
`ProceedingUnfinished`. A provider failure behaves the same way — the exception
propagates out of the `async with`, and the partial transcript survives it.

## Consequences

**Rejected: a bare async generator over entries.** `async for entry in
tribunal.hear_stream(case)` is the shortest thing to type and the obvious first
sketch. It has no place to put the `Hearing`. A caller would have to scrape the
terminal `Ruling` back out of the last entry and would lose `usage` and `rounds`
outright — the two facts [`0005`](./0005-hear-returns-a-hearing.md) put on
`Hearing` precisely because nothing else can carry them. The streaming path
would return strictly less than `hear()` does, which makes it a debug tap rather
than a counterpart.

**Rejected: a generator whose final value is the `Hearing`.** It solves that by
widening the yield type to `Entry | Hearing`, which puts an `isinstance` check
inside every loop body to find the one iteration that is not an entry. Returning
it via `StopAsyncIteration` instead is worse: `async for` swallows the return
value, so the caller cannot reach it without driving `__anext__` by hand. This
is the same failure as the widened `Ruling` in `0005` — two things sharing one
slot, and every consumer paying to tell them apart.

**Rejected: `hear(case, on_entry=...)`.** A callback inverts control for no
gain: the caller cannot stop the proceeding from inside one, exceptions raised
there have nowhere sensible to go, and an `async for` body already does
everything a callback body can. It also contradicts what the design commitments
say about the transcript — that it is not something you install a hook to
observe.

**Rejected: token deltas and partial filings.** The finest-grained thing there
is, and what a chat UI would want. But a half-written argument is not an entry,
never enters the transcript, and may never exist as filed — output validation
can reject it and the agent retries. Streaming it shows a viewer content that
the audit artifact does not contain and cannot be reconciled against, which is
the one property `0006` exists to protect. If a finer channel is ever added it
has to be a separate, explicitly-not-the-record surface; it is not this one, and
it is not free to be added quietly.

**Rejected: lifecycle events.** `RoundStarted`, `AdvocateFiling`,
`DeliberationBegan` — a richer event union, which is what most agent frameworks
ship. Every boundary they would announce is already derivable from the values
themselves: `entry.round` names the round, and a round is closed by a
`Continuance` or a `Ruling`, so both edges are visible in the filings. The
events would be a second vocabulary describing the same proceeding, kept in sync
with the record by hand.

**Backpressure is not a question here.** A consumer slower than the tribunal
means entries wait in memory — but every one of them is retained in the
transcript regardless, so a slow reader costs nothing that the proceeding was
not already paying. There is no bound to configure and no drop policy to invent.

**`ProceedingUnfinished` is the first exception `enbanc` names.** Returning
`None` from `proceeding.hearing` was the alternative, and it would put an
optional in front of every caller for a state that is a bug rather than an
outcome — the same trade `0005` recorded against `Hearing.ruling`, without the
excuse that a real proceeding can land there. Whether it hangs off a shared base
class is not settled: round-limit exhaustion in
[`../design/tribunal.md`](../design/tribunal.md#open-questions) is the other
candidate for an exception, and if it becomes one, the two get a common
ancestor at that point.

**This decides nothing about exhaustion.** If exhaustion resolves toward an
exception, `async for` raises it where the proceeding ends and the `Hearing`
rides on the exception; if it resolves toward `None`, `proceeding.hearing.ruling`
is `None` exactly as `hear()`'s would be. The stream's shape is the same either
way, which is why this ADR does not wait on that one.

**A `Bench` would not change the shape.** [`0002`](./0002-the-judge-is-a-role.md)
leaves room for more than one judge; several deliberation filings per round are
still entries, arriving in filing order, and the stream carries them without a
new type.

**Cost: two entry points and a ceremony.** `async with` plus `async for` where
`await` would have done, and a `Proceeding` name on a surface that otherwise
contains only records. Accepted because the alternative that avoids both — the
bare generator — returns less than `hear()`, and a streaming API that is not a
full substitute for the blocking one is a second-class path that callers get
stuck on.
