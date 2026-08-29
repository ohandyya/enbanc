---
status: current
updated: 2026-08-29
---

# Design

**These documents are the spec.** They describe how `enbanc` is meant to work
right now — not how it was once planned, and not what was built last Tuesday.

Edit them in place. When behavior changes, the design doc changes in the same
commit; a design doc that has drifted from the code is a bug.

- One file per subject, named for the subject: `tribunal.md`, `transcript.md`.
- No numbers — these are living documents, not a sequence.
- A design that is abandoned or replaced moves to `_superseded/` with a
  `status: superseded` line naming what replaced it. Don't delete it; a future
  reader asking "why not X?" deserves to find the answer.
