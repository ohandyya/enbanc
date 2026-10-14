---
status: current
updated: 2026-10-14
pr: 35
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

- `docs/design/api.md`, `evidence.md`, `execution.md`, `prompting.md`,
  `testing.md` — the `status: draft` banner removed, `updated:` stamped.
  `api.md`'s opening line stops calling itself the surface *being designed
  toward* `0.1.0`. Every frontmatter `status:` was already `current`. The banner
  was the only thing that still said draft.
- `docs/design/outcomes.md`, `tribunal.md` — the same banner, which the scope
  above did not list. Both described themselves as unimplemented, so leaving
  them would have left two design documents still saying it.
- `README.md` — the not-released warning, the *wait for `0.1.0`* install note
  and the source-checkout caveat on the example are gone; the example points at
  `docs/guides/`; `Status` says what `0.1.0` is and what pre-1.0 permits.
- `docs/README.md` — `api.md`'s index row, reworded like the line itself.
- `CHANGELOG.md` — the `0.1.0` entry, with the two late changes and the end of
  the `p1` exception called out under `Note`.
- `pyproject.toml`, `uv.lock` — `0.1.0`, by `uv version 0.1.0`; the trove
  classifier moves from `Pre-Alpha` to `Alpha`, matching the README.
- `CLAUDE.md`, `.claude/skills/wrap-up/SKILL.md` — both told an agent that the
  public API does not exist yet.

## Tests

None added: nothing here changes behaviour. `make check-all` is the gate. The
`e2e` tier already runs both guides, and this PR does not change them.

## Open questions

None. Whether the `hear_stream` test would become a guide was answered by
[`content-moderation-guide.md`](./content-moderation-guide.md): it did.
