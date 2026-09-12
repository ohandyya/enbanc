---
status: draft
updated: 2026-09-12
---

# `0.1.0`

**The PR that makes the library true.** Every design document above still opens
with *`status: draft` — none of this exists yet*, and by this point all of it
does. This PR proves the composition against a real provider and then makes the
documentation stop lying.

## Scope

The `e2e` tier: [`api.md`](../design/api.md#shape)'s example run start to finish
against a real provider and real Tavily, plus the `hear_stream` loop. It asserts
almost nothing about content — a model may rule either way — and asserts that a
`Hearing` came back, that its transcript is coherent, and that its usage is
non-zero. Its job is to fail where every faked tier was too kind to notice.

Then the sweep: `status: draft` → `current` across `api.md`, `evidence.md`,
`execution.md`, `prompting.md` and `testing.md` and the removal of each
*none of this exists yet* banner, `README.md`'s pre-`0.1.0` caveats, a
`CHANGELOG.md` entry, and the version in `pyproject.toml`.

**Not in this PR.** Tagging and publishing. That is the
[`create-new-release`](../../.claude/skills/create-new-release/SKILL.md) skill,
run after this merges. Nor `docs/guides/`, which no design document requires for
`0.1.0`; [`packaging.md`](../design/packaging.md#stability-before-10) already
names it as the map of a task rather than of the package.

## Implements

- [`api.md` § Shape](../design/api.md#shape) — as an executable test
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  `e2e` row, the last tier with nothing in it
- [`CLAUDE.md` rule 2](../../CLAUDE.md) — the design-doc half of a behaviour
  change, paid here for every document the build made true

## Depends on

Every other document in the plan.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
