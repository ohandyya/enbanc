---
status: draft
updated: 2026-09-12
---

# A proceeding that runs once

**The first half of `execution.md`'s piece 3: everything needed to run round 1
and one deliberation, end to end, offline.** After this PR a tribunal whose judge
rules immediately produces a real `Hearing`.

## Scope

`_proceeding.py`, up to a single-round proceeding: one `Agent` per participant
built inside the proceeding and discarded with it, the ledgering toolset wired in
per advocate, the shared concurrency limiter, one `RunUsage` per participant, the
history dict, the `since` dict, the base snapshot, the filing clerk that owns the
transcript, and the `Proceeding` handle behind `hear_stream()` — with `hear()`
defined as that stream driven to exhaustion, literally.

**`__all__` completes here.** `Tribunal`, `Judge`, `Advocate` and `Proceeding`
are all exported by the end of this PR, so
`tests/unit/test_export_surface.py` ([`packaging.md`](../design/packaging.md#the-export-surface))
lands with it and pins the twenty-nine-name list for the first time.

**Not in this PR.** The round loop and everything a continuance starts — that is
[`round-loop.md`](./round-loop.md). Failure handling and cancellation are
[`failures.md`](./failures.md); the task group here is the plain one, and gains
its first-failure slot there.

## Implements

- [`execution.md` § Piece 1 — message history and the transcript](../design/execution.md#piece-1--message-history-and-the-transcript)
  — all three rules
- [`execution.md` § The filing clerk](../design/execution.md#the-filing-clerk)
- [`execution.md` § The round's task group](../design/execution.md#the-rounds-task-group)
  — the fan-out and the shared limiter
- [`execution.md` § Usage](../design/execution.md#usage) and
  [§ Also in scope](../design/execution.md#also-in-scope) — the retry budgets,
  and what is deliberately not passed into a run
- [`api.md` § Watching it live](../design/api.md#watching-it-live)
- [`outcomes.md` § 2. The judge rules in round 1](../design/outcomes.md#2-the-judge-rules-in-round-1)
  — the acceptance test
- [`testing.md` § The transcript invariant](../design/testing.md#the-transcript-invariant)
  — `assert_invariant_held` lands here, and every later proceeding test calls it

## Depends on

[`tribunal-construction.md`](./tribunal-construction.md),
[`ledgering-toolset.md`](./ledgering-toolset.md).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
