---
status: draft
updated: 2026-09-20
---

# `0.1.0`

**The PR that makes the library true.** Every design document above still opens
with *`status: draft` — none of this exists yet*, and by this point all of it
does. This PR proves the composition against a real provider and then makes the
documentation stop lying.

## Scope

The `e2e` tier: [`api.md`](../design/api.md#shape)'s example run start to finish
against a real provider and real Tavily, plus the `hear_stream` loop. The example
is not written again here — [`guides.md`](./guides.md) landed it as
`docs/guides/loan_assessment.py` and this tier executes that file, so the thing a
reader runs and the thing CI proves are one artifact. It asserts almost nothing
about content — a model may rule either way — and asserts that a `Hearing` came
back, that its transcript is coherent, and that its usage is non-zero. Its job is
to fail where every faked tier was too kind to notice.

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

- [`api.md` § Shape](../design/api.md#shape) — as an executable test, by
  running [`guides.md`](./guides.md)'s script
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  `e2e` row, whatever of it [`guides.md`](./guides.md) did not already fill
- [`CLAUDE.md` rule 2](../../CLAUDE.md) — the design-doc half of a behaviour
  change, paid here for every document the build made true

## Depends on

Every other document in the plan, [`guides.md`](./guides.md) included — the
`e2e` test has nothing to run until that script exists.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

- **How much of the `e2e` tier is left by the time this PR opens.**
  [`guides.md`](./guides.md) lands one test per guide that executes it, and the
  set of guides is that document's own open question — so what this PR still
  owes the tier is whatever a guide does not show. If the answer turns out to be
  nothing, this becomes the documentation-sweep PR and says so. Owned by
  `guides.md`, settled there, recorded here.
