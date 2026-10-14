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

**The documentation sweep, and nothing else.** The `e2e` tier is already full:
[`guides.md`](./guides.md) landed `docs/guides/loan_assessment.py`, which runs
[`api.md` § Shape](../design/api.md#shape) through `hear()`, and
[`content-moderation-guide.md`](./content-moderation-guide.md) landed
`docs/guides/content_moderation.py`, which runs the `hear_stream` loop.
`tests/e2e/test_guides.py` executes both, so the examples a reader runs and the
things CI proves are one set of artifacts, and this PR owes the tier nothing.

Then the sweep: `status: draft` → `current` across `api.md`, `evidence.md`,
`execution.md`, `prompting.md` and `testing.md` and the removal of each
*none of this exists yet* banner, `README.md`'s pre-`0.1.0` caveats, a
`CHANGELOG.md` entry, and the version in `pyproject.toml`.

**The `CHANGELOG.md` entry names two things that landed late.**
`Argument`, `Response` and `Ruling` carry a required `confidence` in `[0, 1]`
([`confidence.md`](./confidence.md),
[`0043`](../decisions/0043-filings-carry-a-confidence.md)), and every ledger row
carries the `call` that produced it
([`0042`](../decisions/0042-a-retrieval-names-its-call.md)). Both are required
fields with no default, so a transcript serialized during development before
either one does not validate under `0.1.0`. No released version ever produced
one, so this is a note rather than a migration. The entry should also say that
the `p1` that ships is `p1` as amended by those two ADRs, and that from this
release on any change to the prompting surface is a new procedure version.

**Not in this PR.** Tagging and publishing. That is the
[`create-new-release`](../../.claude/skills/create-new-release/SKILL.md) skill,
run after this merges. Nor the guides themselves — [`guides.md`](./guides.md)
writes them one PR earlier, deliberately, so that the exercise of making the
examples actually run happens *before* this PR declares five design documents
true.

## Implements

- [`CLAUDE.md` rule 2](../../CLAUDE.md) — the design-doc half of a behaviour
  change, paid here for every document the build made true

## Depends on

Every other document in the plan. The sweep declares the design documents true,
so it runs last, after both guides have made the examples execute.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

None. Whether the `hear_stream` test would become a guide was answered by
[`content-moderation-guide.md`](./content-moderation-guide.md): it did.
