---
status: draft
updated: 2026-10-14
---

# `0.1.0`

**The PR that makes the library true.** Every design document above still opens
with *`status: draft` — none of this exists yet*, and by this point all of it
does. This PR proves the composition against a real provider and then makes the
documentation stop lying.

## Scope

The rest of the `e2e` tier: **the `hear_stream` loop**, run against a real provider. The
example itself is already covered — [`guides.md`](./guides.md) landed it as
`docs/guides/loan_assessment.py`, and `tests/e2e/test_guides.py` runs that file, so the thing
a reader runs and the thing CI proves are one artifact. That guide calls `hear()`; watching a
proceeding live is what no guide exercises yet, so it is what this PR still owes the tier.
Like the guide's test, it asserts almost nothing about content and asserts that the stream
yielded the entries the `Hearing` holds, in order, and that usage is non-zero.

Then the sweep: `status: draft` → `current` across `api.md`, `evidence.md`,
`execution.md`, `prompting.md` and `testing.md` and the removal of each
*none of this exists yet* banner, `README.md`'s pre-`0.1.0` caveats, a
`CHANGELOG.md` entry, and the version in `pyproject.toml`.

**Not in this PR.** Tagging and publishing. That is the
[`create-new-release`](../../.claude/skills/create-new-release/SKILL.md) skill,
run after this merges. Nor the guides themselves — [`guides.md`](./guides.md)
writes them one PR earlier, deliberately, so that the exercise of making the
examples actually run happens *before* this PR declares five design documents
true.

## Implements

- [`api.md` § Watching it live](../design/api.md#watching-it-live) — the `hear_stream`
  loop, against a real provider
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  `e2e` row, whatever of it [`guides.md`](./guides.md) did not already fill
- [`CLAUDE.md` rule 2](../../CLAUDE.md) — the design-doc half of a behaviour
  change, paid here for every document the build made true

## Depends on

Every other document in the plan, [`guides.md`](./guides.md) included — the
stream test sits beside the guide's in `tests/e2e/` and reuses its harness.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

- **Whether the `hear_stream` test becomes a guide.** If the second guide
  [`guides.md`](./guides.md) leaves open turns out to be the one that watches a proceeding
  live, its test covers the stream and this PR becomes the documentation-sweep PR alone, and
  says so.
