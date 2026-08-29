---
status: current
updated: 2026-08-29
---

# Journal

Dated records of implementation work. **Not a spec.** Each entry is frozen at
write time and goes stale by design — read them as history, never as a
description of how the system currently behaves. Where a journal entry and a
design doc disagree, the design doc wins.

Naming: `YYYY-MM-DD-short-slug.md`.

## Write one only when the diff cannot explain itself

Git log, the diff, and the PR description already record *what* changed. An
entry earns its place by capturing what they can't:

- the alternatives weighed and why they lost
- the constraint that forced an unobvious shape
- a dead end worth not repeating

If an entry would just narrate the diff, skip it. Forty unread journal entries
are worse than none — they're context that costs tokens and returns nothing.

**And if the work changed how the system behaves, update `docs/design/` in the
same commit.** The journal entry is the footnote; the design doc is the truth.
