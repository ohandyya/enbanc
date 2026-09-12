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
| *(none yet)* | | | | |

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

## Status, and what it means

The standard frontmatter carries the state of the work:

- `draft` — planned, not merged. The document is a proposal and may change.
- `current` — merged. The document records what was built in that PR.
- `superseded` — the approach was abandoned or replaced. Leave the file in
  place with a line naming the document that replaced it.

A merged implementation doc is **history, not spec**. After the PR lands, the
code is the truth about the code and `../design/` is the truth about the
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
