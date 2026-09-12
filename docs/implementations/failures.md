---
status: draft
updated: 2026-09-12
---

# When a participant cannot be heard

**The failure half of piece 3.** A round that loses a participant cancels the
rest where they stand, names the one that failed, and raises with the record
intact.

## Scope

The task group gains its first-failure slot and its cancelled-exception
re-raise — which comes *first*, and is load-bearing: without it a cancelled
sibling can win the race and `ProceedingFailed` names an advocate that was merely
stopped. The group then exits cleanly and the orchestrator raises afterwards with
the original error as `__cause__`, so `participant` is singular by construction
rather than by picking one out of an `ExceptionGroup`.

Also here: `ProceedingUnfinished` from `Proceeding.hearing`, and what abandoning
a stream leaves behind.

**Not in this PR.** Any classification of provider errors. `enbanc` wraps and
does not taxonomize.

## Implements

- [`execution.md` § The round's task group](../design/execution.md#the-rounds-task-group)
  — the failure pattern in full
- [`execution.md` § A failing fan-out need not raise an `ExceptionGroup`](../design/execution.md#a-failing-fan-out-need-not-raise-an-exceptiongroup)
- [`api.md` § When something goes wrong](../design/api.md#when-something-goes-wrong)
- [`evidence.md` § What tools may do](../design/evidence.md#what-tools-may-do) —
  the timeout ladder, and where it ends
- [`outcomes.md` § 4. A participant cannot be heard](../design/outcomes.md#4-a-participant-cannot-be-heard)
  and [§ 6. The same endings, watched live](../design/outcomes.md#6-the-same-endings-watched-live)
- [`testing.md` § What must not be asserted](../design/testing.md#what-must-not-be-asserted)
  — how many entries survive a cancelled round is not a test, and exact usage
  after a failure is not either

## Depends on

[`proceeding-core.md`](./proceeding-core.md), [`round-loop.md`](./round-loop.md).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
