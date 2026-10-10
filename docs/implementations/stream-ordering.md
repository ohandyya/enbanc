---
status: draft
updated: 2026-10-10
---

# The stream never runs behind the record

**What the live handle promises, made true for a consumer that does real work.**
A consumer holding entry *N* finds *N* at `proceeding.transcript[-1]`, however
long it spends on it, and walking away leaves the record at what the consumer
had received.

## Scope

Found while planning [`failures.md`](./failures.md), in code merged with
[`proceeding-core.md`](./proceeding-core.md). The clerk appends an entry to the
transcript and then blocks on the rendezvous send. So while a consumer is busy
with entry *N*, for example `await`ing a database write, the clerk has already
appended *N*+1:

```text
slow consumer (len, entry is transcript[-1]): [(2, False), (3, False), (4, False), (4, True)]
abandoned after seeing 1, transcript holds: 2
```

[`0010`](../decisions/0010-streaming-yields-the-record.md)'s promise, that *the
entry just received is the last entry of `proceeding.transcript`*, holds today
only for a consumer whose loop body never `await`s. Every existing streaming
test is one of those, which is why none of them caught it.

This PR changes who appends an entry, or when, so that the promise holds for
any consumer, and so that abandoning leaves the transcript at the entry the
consumer last received. **The mechanism is not chosen.** It is
[`execution.md`'s open question](../design/execution.md#open-questions), and
settling it is that document's three moves: the answer goes into § The filing
clerk, an ADR records why and what was rejected, and the bullet leaves the list.
That happens before this PR's code is written, because the two options differ
in what the clerk owns, and so in what this PR touches.

Whichever mechanism is chosen, two things are fixed already and constrain it:

- **The filer's acknowledgment still means *in the record*.**
  [`0027`](../decisions/0027-an-advocate-answers-its-interrogatories-in-order.md)
  dispatches an advocate's next run on it, and
  [`round-loop.md`](./round-loop.md) built run 7's snapshot on the stamped entry
  the acknowledgment carries back.
- **One sequence for the record and the stream.** No sibling may append between
  another filer's entry and its delivery. A single owner already rules that out,
  and the fix must not reintroduce it.

**Not in this PR.** Anything about failure. [`failures.md`](./failures.md) leaves
the clerk alone, and this PR leaves the failure path alone. The one place they
meet is that a failed proceeding's transcript is also *what had been filed*, and
that follows from whatever this PR settles about abandonment.

## Implements

- [`execution.md` § The filing clerk](../design/execution.md#the-filing-clerk) —
  as amended by the answer to its open question
- [`api.md` § Watching it live](../design/api.md#watching-it-live) — *live: the
  entry just yielded is its last*, and what abandoning leaves behind
- [`outcomes.md` § 6. The same endings, watched live](../design/outcomes.md#6-the-same-endings-watched-live)
  — the walking-away case, for a consumer that awaits

## Depends on

[`proceeding-core.md`](./proceeding-core.md), merged as
[PR #26](https://github.com/ohandyya/enbanc/pull/26), which built the clerk and
the handle; and [`failures.md`](./failures.md), sequenced first only so the two
PRs do not both rewrite `proceed()` at once. Neither depends on the other's
behaviour.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.* The question that decides the mechanism is
[`execution.md`'s](../design/execution.md#open-questions), not this document's.
