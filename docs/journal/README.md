---
status: current
updated: 2026-09-01
---

# Journal

Dated records of implementation work. **Not a spec.** Each entry is frozen at
write time and goes stale by design — read them as history, never as a
description of how the system currently behaves. Where a journal entry and a
design doc disagree, the design doc wins.

Naming: `YYYY-MM-DD-short-slug.md`.

## Write one only when the diff cannot explain itself

Git log, the diff, and the PR description already record *what* changed. An
entry earns its place by capturing how an episode of work actually went:

- a constraint discovered only by building — a library behaving unlike its
  docs, an interaction the design could not have anticipated
- a shape the implementation was forced into, and what forced it
- a dead end worth not repeating

If an entry would just narrate the diff, skip it. Forty unread journal entries
are worse than none — they're context that costs tokens and returns nothing.

## A decision that binds future work is not a journal entry

If the outcome is something a later change must formally *overturn* rather than
quietly ignore, it is an ADR: write it in [`../decisions/`](../decisions/)
instead. The journal records how one session went; `decisions/` records what
the project is now committed to. One session can earn both — they are two
files, not one.

**And if the work changed how the system behaves, update `docs/design/` in the
same commit.** The journal entry is the footnote; the design doc is the truth.
