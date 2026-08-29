---
status: current
updated: 2026-08-29
---

# Decisions (ADRs)

One decision per file, numbered, **immutable once merged**. An ADR records
*why* a path was taken and what was rejected — the reasoning that the code
itself can never show.

Naming: `0001-short-title.md`, sequential, never renumbered.

If a decision is later reversed, write a new ADR that supersedes it and add a
line to the old one pointing forward. Never edit the original's reasoning —
the record of what you believed at the time is the entire value.

Suggested shape:

```markdown
---
status: accepted | superseded by 0007
updated: YYYY-MM-DD
---

# 0001. Title

## Context
What forced a decision.

## Decision
What was chosen.

## Consequences
What this costs, and what it rules out.
```
