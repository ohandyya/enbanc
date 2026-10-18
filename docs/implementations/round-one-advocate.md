---
status: draft
updated: 2026-10-18
---

# Round 1 stops asking the model who it is

**An advocate's round-1 filing is stamped with the advocate that actually ran.**
Today `_Argument` and `Concession` carry `advocate: VerdictT`, the model fills
it in, and the clerk files it as written. An advocate that names a peer either
stamps the peer's ledger row under the same id, which is a wrong citation with
no error, or reaches the `AssertionError` that `_stamp` calls unreachable. This
is the one known defect in `0.1.0` that can put a wrong citation in a released
transcript. It ships alone as `0.1.1`.

## Scope

**Settle [`execution.md`'s open question](../design/execution.md#open-questions).**
It names two fixes:

- **Drop the field from what round 1 asks for** and stamp it from the dispatch,
  as round 2 already does
  ([`0039`](../decisions/0039-a-response-is-asked-for-its-answer-alone.md)).
  This is the one proposed. It removes the failure instead of catching it, and
  it makes rounds 1 and 2 follow one rule.
- **Keep asking, and reject a mismatch as a `ModelRetry`.** This spends the
  model's retries on a question the tribunal already knows the answer to.

The choice is made when the PR starts, and recorded in an ADR.

**The public `Argument` and `Concession` keep their `advocate` field.** Only
the private emit shape changes, so this needs a patch release, not a minor one.

**It is a procedure change.** Removing a field from round 1's output schema
changes what the model is asked for, so it is `p2`, with a row in
[`prompting.md` → Procedure versions](../design/prompting.md#procedure-versions).
[`ruling-cites-evidence.md`](./ruling-cites-evidence.md) is also a prompting
change. If `0.1.1` ships first, as planned, that one is `p3`.

**Not in this PR:** anything else from the post-`0.1.0` plan.

## Implements

- [`execution.md` § Open questions](../design/execution.md#open-questions):
  the round-1 `advocate` bullet, settled under `CLAUDE.md` rule 7 (prose, ADR,
  bullet removed).
- [`execution.md` § The filing clerk](../design/execution.md#the-filing-clerk)
  and [§ The citation check resolves ids](../design/execution.md#the-citation-check-resolves-ids):
  where the advocate comes from when a filing is stamped.
- [`prompting.md` § Procedure versions](../design/prompting.md#procedure-versions):
  the `p2` row.

## Depends on

Nothing open. It changes work that has merged:
[`proceeding-core.md`](./proceeding-core.md) (#26) and
[`round-loop.md`](./round-loop.md) (#28).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
