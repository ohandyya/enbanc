---
status: draft
updated: 2026-09-12
---

# The round loop

**What a continuance starts.** Round 2 and after: ids stamped on filing,
interrogatories dispatched to the advocates they name, an advocate's own
questions answered in order, and the two ways a proceeding ends without ruling.

## Scope

The loop itself, and the state that moves per round: the `_Continuance` →
`Continuance` conversion with `r{round}-q{n}` stamped in emission order, one task
per *addressed advocate* with its interrogatories queued inside it,
`Response.answering` filled from the dispatch, the per-run advance of `since`,
the snapshot extension that makes run 7 of
[the worked proceeding](../design/execution.md#since-and-the-snapshot-run-by-run)
correct, the `max_rounds` check, and the budget check whose
`UsageLimitExceeded` is a stop signal rather than an error.

**Not in this PR.** Failure handling — [`failures.md`](./failures.md).

## Implements

- [`execution.md` § The round loop](../design/execution.md#the-round-loop)
- [`execution.md` § The budget check](../design/execution.md#the-budget-check)
- [`execution.md` § A snapshot is constructed, not sliced](../design/execution.md#a-snapshot-is-constructed-not-sliced)
  — run 7 is the case that constrains the implementation
- [`prompting.md` § An advocate asked two questions answers them in order](../design/prompting.md#an-advocate-asked-two-questions-answers-them-in-order)
- [`api.md` § Where ids come from](../design/api.md#where-ids-come-from) — the
  stamping seam, both directions
- [`outcomes.md` § 1. The judge rules](../design/outcomes.md#1-the-judge-rules)
  and [§ 3. The envelope is spent](../design/outcomes.md#3-the-envelope-is-spent)
  — the acceptance tests, including the suppression join

## Depends on

[`proceeding-core.md`](./proceeding-core.md).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
