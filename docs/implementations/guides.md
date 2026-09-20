---
status: draft
updated: 2026-09-20
---

# Guides that run

**`docs/guides/` stops being an empty directory of pages that were never
written, and becomes a small set of single-file Python scripts a reader can
execute.** A guide here is not a page about `enbanc`; it is the shortest program
that uses `enbanc` to do one real thing, and it is verified by running it.

## Scope

**One use case, one file, no supporting cast.** Each guide is a single `.py`
under `docs/guides/`, runnable as it stands — `uv run docs/guides/<name>.py` —
with no local imports, no CLI arguments, no helper module beside it, and nothing
in it that is not needed to show the use case. The moment a guide grows a second
file it has stopped being an example and become a small application, which is a
thing a reader must understand before they can learn anything from it.

**The first guide is `loan_assessment.py`**: [`api.md` § Shape](../design/api.md#shape)
made executable. That block is written as prose today — `psql` is undefined, the
case fields are `...`, the search key is `api_key=...` — so the guide is not a
copy of it but the runnable version of the same example, with a real `Case`, a
real tool list, and a `match` on the outcome that prints both arms.

**Which guides follow it is an open question below**, deliberately. The set is
the part of this work that is a judgement about teaching rather than a
consequence of [`../design/`](../design/), and guessing at it now would put a
list in this directory that reads as authority (`README.md` → *What one
contains*).

**A guide is executed by the `e2e` tier.** A script that nothing runs is a
snippet, and it rots on the first signature change — which is the whole reason
[`../../CLAUDE.md`](../../CLAUDE.md) makes `tests/` the thing that is actually
verified. The tier directory already exists (`tests/e2e/conftest.py`, plus a
placeholder), so this PR adds tests to it rather than building it, and the
scripts are the only new runnable surface.

**Three edits ride along, and none of them are optional.**

- [`../guides/README.md`](../guides/README.md) is rewritten. It currently
  promises *"the pages that would seed a documentation site"* and says the
  directory is *"empty until there is something that runs"* — both stop being
  true here. It becomes the index of the scripts and the statement of the
  contract above.
- [`packaging.md` § Stability, before 1.0](../design/packaging.md#stability-before-10)
  says `../guides/` *"is still empty"*. It is a design document describing
  behaviour this PR changes, so it is corrected in the same commit
  ([`../../CLAUDE.md`](../../CLAUDE.md) rule 2). *"A guide is the map of a
  task"* survives the edit — that sentence is why this PR exists.
- `pyproject.toml`'s `[tool.pyright]` gains `docs/guides` in `include`, which is
  today `["src", "tests"]`. Ruff needs nothing: `make lint` and `make format`
  already run over `.`, so a guide script is linted and formatted the day it
  lands.

**Not in this PR.**

- **A documentation site.** No mkdocs, no rendered HTML, no navigation config.
  These are files in a repository that a reader can open and run.
- **Prose guides.** Where a guide needs narrative it gets comments in the
  script. A page with no runnable script is not a guide under this document.
- **Shipping guides in the wheel.** `pyproject.toml`'s build-backend section
  stays bare on purpose, and `docs/` is not packaged. A guide is read in the
  repository, not imported from site-packages.
- **The `draft` → `current` sweep, `CHANGELOG.md`, and the version bump** —
  [`zero-one-zero.md`](./zero-one-zero.md).

## Implements

- [`api.md` § Shape](../design/api.md#shape) — as a file a reader runs, which is
  the same claim [`zero-one-zero.md`](./zero-one-zero.md)'s `e2e` test makes
  about it. Landing the guide first is what lets that test run this script
  instead of carrying a second copy of the example.
- [`api.md` § When something goes wrong](../design/api.md#when-something-goes-wrong)
  — the `Ruling` / `Undecided` `match` is in the guide because a caller who
  copies an example that ignores the second arm has copied a bug.
- [`packaging.md` § Stability, before 1.0](../design/packaging.md#stability-before-10)
  — *"a guide is the map of a task"*. This is the first task mapped, and the
  sentence saying the directory is empty is retired by it.
- [`evidence.md` § Adding your own tool](../design/evidence.md#adding-your-own-tool)
  — three steps that exist only as prose. Whichever guide shows a custom tool is
  the runnable form of them.
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  `e2e` row gains its first real occupants, one per guide.

## Depends on

[`failures.md`](./failures.md), and through it every document before it. **PR 9
is the last one that changes the public surface** — `__all__` completes in
[`proceeding-core.md`](./proceeding-core.md), the endings complete in
[`round-loop.md`](./round-loop.md), and the error types complete in
`failures.md`. A guide written before that is a map of a target that is still
moving, and it would be rewritten by every PR that landed after it.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

Resolved before this PR merges.

- **Which guides make up the set, beyond `loan_assessment.py`.** The criterion
  is what a guide *teaches that the previous one did not* — a second script that
  demonstrates the same three calls with a different noun is a file to maintain
  for nothing. The candidates the design already supports are a custom tool
  ([`evidence.md` § Adding your own tool](../design/evidence.md#adding-your-own-tool)),
  watching a proceeding live ([`api.md` § Watching it live](../design/api.md#watching-it-live)),
  and reading a persisted hearing back
  ([`outcomes.md` § 7](../design/outcomes.md#7-persisting-a-hearing-and-reading-it-back)).
  Whether all three earn a file, or some collapse into `loan_assessment.py`, is
  not decided.
- **Whether every guide runs on every live run.** A guide calls a real provider
  by definition, so the `e2e` tier's cost scales with the size of the set, and
  [`0033`](../decisions/0033-live-tiers-run-in-ci-on-demand.md) already made that
  tier something fired by hand because it costs money. Either every guide is
  executed and the set stays deliberately small, or one is representative and
  the others are checked more cheaply — which is a weaker guarantee and should
  be chosen out loud rather than by accident.
- **How a guide gets its credentials.** The harness reads `.env` in
  `tests/conftest.py`'s `live_env` fixture, but that is a *test* fixture and a
  reader running a guide does not have it. Plain `os.environ` with a one-line
  failure is the honest version and shows the reader exactly what the library
  needs; it also means the `e2e` test must put the same variables in the
  environment before running the script.
- **What this leaves [`zero-one-zero.md`](./zero-one-zero.md)'s `e2e` scope.**
  That PR was written as the one that proves the composition against a real
  provider, and one test per guide lands that proof here instead. Whatever a
  guide does not exercise — the `hear_stream` loop, if no guide watches a
  proceeding live — is what remains for it. This is settled by settling the
  first question above, and the answer is carried into that document.
- **Whether `api.md` § Shape and `loan_assessment.py` are kept in sync by
  hand.** Two copies of the flagship example that drift is worse than one that
  is slightly wrong for its context. The options are to leave the prose block as
  prose and accept hand-sync, or to make the document quote the script.
