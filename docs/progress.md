---
status: current
updated: 2026-08-29
---

# Progress

**Where the work stands, and how it got here.** Written at the end of a working
session by the [`wrap-up`](../.claude/skills/wrap-up/SKILL.md) skill, and read
at the start of the next one.

Two halves, two different guarantees:

- `## Current state` is **current truth**, rewritten in place every session.
  Anything stale here is a bug.
- `## Log` is **history**, prepended newest-first and never edited. Entries are
  true as of their date and go stale by design.

The log says *what* changed and *where it stopped*. It does not say *why* —
that lives in [`journal/`](./journal/), linked from the entry. Neither half is a
spec: [`design/`](./design/) is.

## Current state

**Phase:** Scaffolding, complete. Tooling, CI, release pipeline, and the
documentation structure are in place and working. **No `enbanc` code exists
yet** — `src/enbanc/__init__.py` is a placeholder and `tests/` holds one
placeholder test. The published `0.0.3` on PyPI reserves the name and nothing
more.

**Next up:** Settle the open questions in
[`design/api.md`](./design/api.md#open-questions) — whether `Advocate` carries
its own model or inherits one from `Tribunal`, and what `hear()` returns when
the round limit is exhausted. Both block the first real implementation, because
they change the shape of the public surface that `0.1.0` promises. Settled ones
become ADRs in [`decisions/`](./decisions/).

**Open questions:**

- The design docs carry their own, and own them:
  [`tribunal.md`](./design/tribunal.md#open-questions) and
  [`api.md`](./design/api.md#open-questions). Do not copy them here.
- Nothing else outstanding at the project level.

## Log

### 2026-08-29 — documentation structure and the wrap-up skill

**Did:** Established the `docs/` layout and the rules that govern it
(`CLAUDE.md`): `design/` as spec, `decisions/` as immutable ADRs, `journal/` as
dated and stale-by-design, `notes/`/`local/` denied to agents. Added this file
and the `wrap-up` skill that maintains it. Earlier in the day: uv + ruff +
pyright + pytest tooling, pre-commit hooks enforced in CI, the release workflow
with its tag-vs-version check, and the `0.0.3` placeholder release.

**Stopped at:** Clean. `docs/decisions/` and `docs/guides/` are still empty, by
design — nothing has been decided or shipped that needs them.

**Commits:** `f795ae0`, `71ebadc`, `9eb7d33`, `0ea8a40`, `f387674`, `cd05dec`
