---
status: current
updated: 2026-09-04
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

**Phase:** Design complete; **no `enbanc` code exists yet** —
`src/enbanc/__init__.py` is a placeholder and `tests/` holds one placeholder
test. The published `0.0.4` on PyPI reserves the name and nothing more. Settled
and binding, across
[`0001`](./decisions/0001-statute-carries-no-model.md)–[`0024`](./decisions/0024-a-budget-stops-the-proceeding-between-rounds.md):
every public type, every way a proceeding can *end*, and now its *behaviour*.
[`0023`](./decisions/0023-advocates-argue-blind-and-rebut-informed.md) settled
what an advocate sees (blind in round 1, the record from round 2);
[`0024`](./decisions/0024-a-budget-stops-the-proceeding-between-rounds.md)
settled what a proceeding may spend: an optional `budget` checked between
rounds, landing as `Undecided(reason='budget')`, plus a `max_concurrency` that
bounds the fan-out. **`docs/design/` now describes a complete system with no
open questions in it.**

**Next up:** Implementation. There is no design work queued — the next commit
that matters puts code in `src/enbanc/`, and the schemas in `design/api.md` are
the thing to build first, since every other piece is keyed on them.

**Open questions:**

- None. [`design/tribunal.md`](./design/tribunal.md#open-questions) and
  [`design/api.md`](./design/api.md#open-questions) both carry none, and
  `0001`–`0024` record why each was closed.
- Nothing else outstanding at the project level.

## Log

### 2026-09-02 — four ADRs, and `api.md` runs out of questions

**Did:** Closed the last four unsettled pieces of the `0.1.0` surface, one ADR
each: the first failure cancels the round rather than draining it
([`0012`](./decisions/0012-a-failure-cancels-the-round.md)), `Case` is a
subclassable base rather than a second type parameter on every generic
([`0013`](./decisions/0013-a-case-is-a-subclassable-base.md)), a `Hearing`
carries `usage_by_participant` as the stored fact with `usage` as its sum
([`0014`](./decisions/0014-usage-is-broken-down-per-participant.md)), and the
tribunal stamps `r{round}-q{n}` onto an interrogatory when it files the
continuance instead of asking the judge to invent it
([`0015`](./decisions/0015-interrogatory-ids-are-stamped-on-filing.md)).
`design/api.md` now lists no open questions; both survivors are in
`design/tribunal.md` and both are about behaviour, not shape.

**Stopped at:** Clean. `README.md` and the glossary were swept here — the README
still claimed `api.md` carried open questions and its sample predated
`usage_by_participant`; the glossary described a `Hearing`'s usage as merely
aggregate and had no row for *participant*, which `0012` and `0014` both lean
on.

**Why this way:**
[`decisions/0012`](./decisions/0012-a-failure-cancels-the-round.md)–[`0015`](./decisions/0015-interrogatory-ids-are-stamped-on-filing.md);
no journal entry — every choice this session binds future work, so all of it is
ADR material and none of it is session narrative.

**Commits:** `26c2c16`, `329b897`, `db7ac7d`, `d4bd74f`, `f8c711c`

### 2026-09-02 — streaming, and what happens when there is no verdict

**Did:** Added `hear_stream()` as a live view of the transcript
([`0010`](./decisions/0010-streaming-yields-the-record.md)), then settled how a
proceeding reports *not* ruling. Exhaustion is now a recorded `Undecided`
outcome on `Hearing.outcome`; provider, tool, and validation failures raise
`ProceedingFailed` carrying the partial transcript. `Hearing.ruling` is gone,
and with it the last open question that was blocking a type. Added
[`design/outcomes.md`](./design/outcomes.md) — every ending written out as
concrete values — which is what caught two defects in the schemas above it.

**Stopped at:** Clean. `docs/design/` and the README match the new surface.

**Why this way:**
[`decisions/0010`](./decisions/0010-streaming-yields-the-record.md),
[`decisions/0011`](./decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md),
and
[`journal/2026-09-02-values-before-schemas.md`](./journal/2026-09-02-values-before-schemas.md)
for why the examples doc found what schema review did not.

**Commits:** `231358c`, `eee4dca`, `3ccdad7`

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
