---
status: current
updated: 2026-09-12
---

# Implementations

**How the design gets built, one PR at a time.** Each document here is the
implementation detail for a single pull request: what that PR touches, the
order the pieces land in, the modules and tests it adds, and the decisions that
are small enough to make inside a PR rather than in an ADR.

`../design/` says what the system should be. These say how one slice of it gets
written. **Where the two disagree, `../design/` wins** — it is the target, and
an implementation doc that contradicts it is describing a mistake, not a
change. If the code genuinely needs to diverge, the design doc is what is
wrong, and fixing it is part of the same commit (`CLAUDE.md` rule 2).

## The plan

**This table is the order.** The filenames carry no number, so resequencing the
plan or splitting one PR into two is an edit here rather than a rename and a
hunt for inbound links.

| # | Doc | Depends on | PR | Status |
|---|---|---|---|---|
| 1 | [`schemas.md`](./schemas.md) | — | 19 | `current` |
| 2 | [`contract-probes.md`](./contract-probes.md) | — | 20 | `current` |
| 3 | [`web-search-tool.md`](./web-search-tool.md) | 1 | | `draft` |
| 4 | [`rendering.md`](./rendering.md) | 1 | | `draft` |
| 5 | [`tribunal-construction.md`](./tribunal-construction.md) | 1, 4 | | `draft` |
| 6 | [`ledgering-toolset.md`](./ledgering-toolset.md) | 1, 4 | | `draft` |
| 7 | [`proceeding-core.md`](./proceeding-core.md) | 5, 6 | | `draft` |
| 8 | [`round-loop.md`](./round-loop.md) | 7 | | `draft` |
| 9 | [`failures.md`](./failures.md) | 7, 8 | | `draft` |
| 10 | [`zero-one-zero.md`](./zero-one-zero.md) | all | | `draft` |

## Naming

Named for the subject, no numbers: `package-skeleton.md`,
`transcript-types.md`, `round-loop.md` — the same convention as
[`../design/`](../design/), for the same reason. `../decisions/` numbers its
files because an ADR is immutable and never reorders; a build plan reorders,
which is exactly what a number in a filename cannot survive.

**The GitHub PR number is not knowable when the document is written** — the doc
is authored before the PR exists and lands inside it. It goes into the
frontmatter as `pr:` once the PR is open, and into the table above:

```yaml
---
status: current
updated: 2026-09-20
pr: 17
---
```

## What one contains

Enough that the PR could be written by someone who has read `../design/` and
nothing else about the work in flight:

- **Scope** — what lands in this PR, and explicitly what does not.
- **Which design documents it implements**, by section. A PR that implements
  nothing in `../design/` is a PR with no spec.
- **The files it adds or changes**, and what goes in each.
- **The tests it brings**, and the tier each lives in — a PR whose behaviour is
  untested in `tests/` has not landed (`CLAUDE.md` → Tests).
- **What it depends on** — the documents that must land first, by name. The
  table above orders the plan; each document states its own dependencies, so a
  reader who opens one in the middle is not required to read the index first.
- **Open questions** for that PR, resolved before it merges.

**Three of those six are written later.** `Scope`, `Implements`, and
`Depends on` are drawn from [`../design/`](../design/), which is settled: they
are as knowable the day the plan is written as they will ever be, and every
document here carries them from the start. The files, the tests, and the open
questions are drawn from code that does not exist yet. Written before the PR
begins they are guesses, and a guess in this directory does not sit quietly —
it reads as authority to whoever builds the eighth PR, and steers the work it
was only meant to describe. So those three sections stand as *Filled in when
this PR starts.* until the PR opens. **The empty section is the plan working,
not a gap to close.**

## Status, and what it means

The standard frontmatter carries the state of the work:

- `draft` — planned. No PR is open, and the document is a proposal that may
  change.
- `current` — built. A PR is open and expected to merge as it stands, and the
  document records what that PR contains.
- `superseded` — the approach was abandoned or replaced. Leave the file in
  place with a line naming the document that replaced it.

**`current` is stamped when the PR opens, not when it merges**, and that is a
deliberate trade. The number and the built-or-planned fact become knowable at
the same moment — the moment the PR is opened — and that is the one session
holding both. Waiting for the merge splits the edit across two sessions, and
the second one never happens: nothing fires on a merge, which is how a plan
directory ends up full of `draft` documents describing shipped code.

What it costs is an assumption: that the PR merges essentially as it stands. It
is stated out loud whenever the stamp is applied, and it is wrong sometimes. A
PR that changes shape under review is a document that needs correcting before
it lands — the same obligation `CLAUDE.md` rule 2 puts on a design doc, and the
review is where it gets caught.

**Opening a PR edits three things besides the code.** The document's `status`
becomes `current` and its frontmatter gains the `pr:` number; the table above
gains that number too; and the `Scope` of every document listing this one under
`Depends on` is re-read and corrected wherever the build has invalidated it.
That third edit is what earns the deferral above: deciding the files and tests
late only pays if what the build taught is carried into the documents still
ahead. Skipping it leaves the rest of the plan derived from the design alone —
which is where it already was.

The [`create-pr-summary`](../../.claude/skills/create-pr-summary/SKILL.md)
skill makes the first two edits and asks about the third, which keeps all three
in one place rather than in three habits.

A `current` implementation doc is **history, not spec**. Once the PR is written
the code is the truth about the code and `../design/` is the truth about the
intent; the implementation doc is kept as the record of how that slice was cut.
Do not read one to learn how the system currently behaves.

## What does not belong here

- **A decision that binds future work** — that is an ADR in
  [`../decisions/`](../decisions/), even if it was made while writing the PR.
- **A change to how the system behaves** — that edits [`../design/`](../design/)
  in the same commit.
- **How an episode of work actually went** — the constraint found only by
  building, the dead end worth not repeating — that is
  [`../journal/`](../journal/).
- **Session state** — where the work stands overall is
  [`../progress.md`](../progress.md).
