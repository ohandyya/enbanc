---
name: wrap-up
description: End-of-session checkpoint. Update docs/progress.md so the next session can pick up cold, write a docs/journal/ entry when the reasoning cannot be reconstructed from the diff, and sweep README.md for anything that stopped being true. Use when the user says wrap up, wrap-up, checkpoint this session, document progress, or is ending a working session.
---

# Wrap up a session

The next session may be days away and remembers nothing. This skill leaves
behind the one thing git cannot: where the work stands and why it took the
shape it did.

Three files, three different jobs — do not blur them:

| File | Job | How it's written |
|---|---|---|
| [`docs/progress.md`](../../../docs/progress.md) | Where the work stands, and a terse trail of how it got here | `## Current state` rewritten in place; `## Log` prepended, never edited |
| [`docs/journal/`](../../../docs/journal/) | How one session's work went, where the diff can't show it | New dated file, only when earned |
| [`README.md`](../../../README.md) | The project's public claim about itself | Rewritten in place |

Never commit. Write the files, report them, and stop — the user stages their
own work.

## Step 1 — Gather

```bash
sed -n '1,40p' docs/progress.md          # current state + date of newest log entry
git log --format='%h %ad %s' --date=short -15
git status --porcelain
git diff --stat
git rev-parse --abbrev-ref HEAD
```

Scope is **everything since the newest log entry's date**, including
uncommitted work. A half-finished refactor sitting in the working tree is
exactly what the next session needs warned about.

Then re-read this conversation for what git cannot show: what was decided, what
was tried and abandoned, what was deliberately left unfinished, and what
question is still open.

**If nothing meaningful changed since the last entry, say so and stop.** Do not
write a filler entry. A log of "tidied imports" entries is worse than a gap.

## Step 2 — Prepend a log entry

New entry at the top of `## Log` (newest first). **Never edit an existing
entry** — each is true as of its date, and rewriting history is the one thing
that makes this file untrustworthy.

```markdown
### YYYY-MM-DD — short title

**Did:** what changed, in a sentence or two. Not a file listing.

**Stopped at:** where work was interrupted mid-stream — a half-done refactor, a
failing test, a decision that must be made before the next step. Omit if the
session ended clean.

**Why this way:** [`docs/journal/YYYY-MM-DD-slug.md`](./journal/YYYY-MM-DD-slug.md).
Omit unless a journal entry was written.

**Commits:** short hashes. Omit if nothing was committed.
```

Only `**Did:**` is required. Drop lines that would be empty — an entry with
three "N/A" lines is noise.

**The test for every line: could this be reconstructed from the diff or
`git log`?** If yes, cut it. No file inventories, no restating what a function
does, no counts recorded elsewhere. The value here is entirely in what is not
derivable: where things stopped, and the pointer to why.

Reasoning does **not** go in the log. The log says *what* and *where it
stopped*; the journal says *why*. Keep the log line short enough that scanning
ten of them is fast.

## Step 3 — Rewrite `## Current state`

Overwrite it in place — this block has no history, and stale text here is worse
than none. Update the `updated:` frontmatter date to match.

- **Phase** — where the project is, plus an honest one-line read on how solid
  it is. `enbanc` is pre-`0.1.0`: nothing in the public API exists yet, and this
  line is where that stays visible.
- **Next up** — the single next actionable thing, with enough context to start
  without re-deriving it. Point at the design doc section it comes from.
- **Open questions** — anything unresolved that will block work later. Drop
  items once resolved; the log keeps the history. Design docs carry their own
  open questions — link, don't copy.

## Step 4 — Write a journal entry, but only if it's earned

`CLAUDE.md` rule 5 and [`docs/journal/README.md`](../../../docs/journal/README.md)
both say the same thing: **an entry earns its place only when the diff cannot
explain itself.** Write one when the session produced at least one of:

- a constraint discovered only by building — a library behaving unlike its docs
- a shape the implementation was forced into, and what forced it
- a dead end worth not repeating

If the session was "implemented the thing the design doc already described,"
write no entry. Forty unread journal entries cost tokens and return nothing.

If the session *settled* something that binds future work, that belongs in
[`docs/decisions/`](../../../docs/decisions/) as an ADR — not here. A session
can earn both; they are two files.

When it is earned, create `docs/journal/YYYY-MM-DD-short-slug.md`:

```markdown
---
status: current
updated: YYYY-MM-DD
---

# Short title

One paragraph of context: what was being done and what forced a choice.

## What was decided

The choice, stated plainly.

## Alternatives rejected

Each one, and the reason it lost. This is the part the diff cannot show.

## Dead ends

What was tried that did not work. Omit if none.
```

Then link it from the log entry's `**Why this way:**` line, and add a row to the
Journal section of [`docs/README.md`](../../../docs/README.md) — an unindexed
doc is one nobody finds.

## Step 5 — Sweep `README.md`

**Only if the session changed what an outside reader would conclude** — a
capability landed or was withdrawn, a command changed, a phase completed, the
planned API in the code sample moved. A refactor, a test addition, or a docs
tidy-up leaves the project's outside shape identical: skip silently, and do not
write a "no changes needed" line.

`README.md` is the only doc here written for someone who has never seen the
repo, and it is public — it ships to PyPI. `progress.md` and the README carry
the same facts for different readers: `progress.md` keeps the reasoning for the
next session; the README keeps only the conclusion. Never copy log prose into
it.

**Rewrite in place; it has no history section to grow.** A change that makes a
sentence wrong deletes that sentence rather than qualifying it.

What goes stale, roughly in the order it burns:

- **The WIP callout and the Status section.** These are load-bearing while the
  package on PyPI is a placeholder. An overclaim here is the worst failure this
  file can have.
- **The "A taste" code sample.** It is labelled *planned API*. When
  `docs/design/api.md` changes, this sample is wrong until it matches.
- **Links into `docs/design/`.** A renamed or superseded design doc leaves a
  dead link on the public page.
- **Install and command lines** — anything a reader would paste.

**The rule that outranks the rest: never overstate.** Where there is a choice of
phrasing, take the one that makes the gap between what exists and what is
planned impossible to miss.

## Step 6 — Flag drift you should not fix here

Wrap-up does not silently edit the spec. `CLAUDE.md` rule 2 puts a design
update in the *same commit* as the behavior change — so drift found at
checkpoint time is a signal something was missed, and burying the fix in a docs
sweep hides it.

Check and **report, then ask**:

- **`docs/design/`** — did anything built this session contradict the spec? If
  so the design doc is wrong (rule 1), and fixing it is part of the change, not
  a follow-up. Name the file and the contradiction; ask whether to fix it now.
- **`docs/glossary.md`** — did the session introduce courtroom or domain
  vocabulary the glossary doesn't carry? Ask before adding.
- **`CLAUDE.md`** — did the session establish a new convention it should own?
  Say so; do not fold that content into `progress.md`. Each doc owns its own
  material.
- **`CHANGELOG.md`** — user-visible changes belong there at release time, not
  here. Mention it only if something shipped that a release would need to name.
- **A superseded design** — if a design was abandoned this session, it moves to
  `docs/design/_superseded/` with a `status: superseded` line naming its
  replacement. Never deleted.

## Step 7 — Report

Two or three lines. Name each file written, quote the new `Next up`, and list
the drift from Step 6 as explicit questions. Do not commit unless asked.

## Rules

- Never edit an existing `## Log` entry, and never reorder them.
- Never write a log entry when nothing meaningful changed.
- Never write a journal entry that only narrates the diff.
- Never put reasoning in the log or status in the journal.
- Never treat `docs/journal/` as a source of current truth while gathering — if
  a journal entry and a design doc disagree, the design doc wins.
- Never read `notes/` or `local/`. Those reads are denied in
  `.claude/settings.json` and are human-only.
- Never run `git commit`, `git push`, or `gh` from this skill.
