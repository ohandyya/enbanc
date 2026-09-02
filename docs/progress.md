---
status: current
updated: 2026-09-02
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

**Phase:** Scaffolding complete; the `0.1.0` surface is mostly designed but
**no `enbanc` code exists yet** — `src/enbanc/__init__.py` is a placeholder and
`tests/` holds one placeholder test. The published `0.0.4` on PyPI reserves the
name and nothing more. What is now settled and binding is the *shape* of the
public types: verdicts, statute, the five filings, the transcript envelope, the
judge's discriminated union, and what `hear()` returns
([`0001`](./decisions/0001-statute-carries-no-model.md) through
[`0009`](./decisions/0009-model-settings-live-on-the-model.md)). What is not
settled is the *behaviour* of the proceeding.

**Next up:** Settle **round-limit exhaustion** in
[`design/tribunal.md`](./design/tribunal.md#open-questions) — what `hear()` does
when `max_rounds` is hit with no ruling. It is the next one to take because it
is the only open question with a committed downstream consequence: `api.md`
types `Hearing.ruling` as `Ruling | None` *solely* because this is unresolved,
so resolving it toward an exception deletes the optionality, the `if` in the
README sample, and a bullet from
[`design/api.md`](./design/api.md#open-questions). The choice is between leaving
`ruling` `None` (every caller writes a check for a case most never hit) and
raising an exception carrying the `Hearing` (exhaustion impossible to ignore);
a forced verdict is the third option and the weakest. Per rule 7, that is three
moves in one commit: prose into `tribunal.md`, an ADR, then the bullet goes.

**Open questions:**

- The design docs carry their own, and own them:
  [`tribunal.md`](./design/tribunal.md#open-questions) (round-limit exhaustion,
  advocate isolation, cost control) and
  [`api.md`](./design/api.md#open-questions) (`Hearing.ruling`'s optionality,
  `Case` as base vs. generic, per-agent usage, interrogatory id assignment).
- Nothing else outstanding at the project level.

## Log

### 2026-09-02 — the schemas, and six ADRs

**Did:** Took `design/api.md` from a sketch to a full schema spec — verdicts as
a `StrEnum` base, the five filings and their `Entry` envelope, a self-contained
`Transcript`, and `hear()` returning a `Hearing` that wraps the judge's
`Ruling` — and settled six binding pieces as ADRs
[`0004`](./decisions/0004-verdicts-are-a-strenum.md)–[`0009`](./decisions/0009-model-settings-live-on-the-model.md).
Propagated the vocabulary through `design/tribunal.md` and the glossary
(*round*, *filing*, *response*, *entry*, *hearing*), narrowed the
"nothing enters an agent's context" invariant to *nothing from outside itself*
so an advocate's unfiled tool results are legal, and added rule 7 to
`CLAUDE.md` fixing what it takes to resolve an open question.

**Why this way:**
[`decisions/0004`](./decisions/0004-verdicts-are-a-strenum.md)–[`0009`](./decisions/0009-model-settings-live-on-the-model.md);
no journal entry — the only build-time constraint found (Pydantic collapsing a
generic alias parameterized by a bare `TypeVar`) is recorded as spec in
[`design/api.md`](./design/api.md#a-note-on-generic-aliases).

**Commits:** `b8eb899`, `87f6595`, `c363992`, `d4aa820`, `420abc3`, `6934205`,
`96f9615`, `9625fc4`

### 2026-09-01 — the statute is inert; first ADR

**Did:** Settled the first binding piece of the `0.1.0` surface — a `Statute`
carries no model and `Statute.draft()` is cut — and propagated it through
`design/api.md`, the glossary, and the `docs/README.md` index. Sharpened the
journal-vs-ADR split in `CLAUDE.md`, `docs/journal/README.md`, and the `wrap-up`
skill: the journal records how a session went, `decisions/` records what the
project is committed to. Documented in `pyproject.toml` that `uv_build` ships an
allowlist, not everything git tracks — `notes/` and `docs/` stay out of the
sdist only because that section stays bare. Released the `0.0.4` placeholder.

**Stopped at:** Two open questions were dropped into
[`design/api.md`](./design/api.md#open-questions) as raw first-person notes
rather than design prose — the missing `Judge` role, and how `instructions` and
a PydanticAI `Model` are injected into each agent. They need writing up before
they can be settled.

**Why this way:**
[`docs/decisions/0001-statute-carries-no-model.md`](./decisions/0001-statute-carries-no-model.md)

**Commits:** `183fe8a`, `be2b72b`, `045af5a`, `131c94a`, `333b338`, `9b0e08d`,
`e2fa55b`

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
