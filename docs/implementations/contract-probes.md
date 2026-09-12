---
status: draft
updated: 2026-09-12
---

# The contract probes

**The `pydantic-ai` findings `execution.md` rests on, turned from scratch files
into tests.** Six of the eight probes behind
[what PydanticAI already does](../design/execution.md#what-pydanticai-already-does)
are still throwaway scripts, so a version bump falsifies that document silently.

## Scope

`tests/contract/`, and nothing else. No `enbanc` code, no design change — this
tier is not about `enbanc` at all
([`testing.md` § The four tiers](../design/testing.md#the-four-tiers)), and a red
test here means the dependency moved.

Two of the ten findings are derivations rather than probes and get no module:
*Three channels reach a model* summarizes the two above it, and *What lands in
history* is the whitelist the invariant helper encodes, tested in
[`proceeding-core.md`](./proceeding-core.md).

Two are already pinned — `max_concurrency` at construction, and a failing output
schema spending the `output` budget — so six remain.

**Not in this PR.** Anything that imports `enbanc`.

## Implements

- [`execution.md` § What PydanticAI already does](../design/execution.md#what-pydanticai-already-does)
  — the six unpinned findings
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  finding-to-assertion table is the checklist for this PR

## Depends on

Nothing. Independent of every other PR in the plan, and mergeable at any point.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
