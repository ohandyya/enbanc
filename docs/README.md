---
status: current
updated: 2026-09-01
---

# Documentation

Everything under `docs/` is readable by AI agents. Human-only material lives in
`notes/` (versioned) or `local/` (gitignored), both of which are blocked in
`.claude/settings.json`.

The split that matters is **current truth vs. dated record**:

- `design/` and `decisions/` describe the system as it is meant to work now.
- `journal/` records what happened on a given day and is never updated after.
- `progress.md` straddles the two on purpose: its `Current state` block is
  rewritten every session, its `Log` is never edited.

If the two disagree, `design/` wins. See [`../CLAUDE.md`](../CLAUDE.md) for the
full ruleset.

## Index

| Doc | What it covers |
|---|---|
| [`progress.md`](./progress.md) | Where the work stands right now, and a dated trail of how it got here. Start here |
| [`glossary.md`](./glossary.md) | Courtroom vocabulary — tribunal, statute, advocate, ruling |

### Design — how the system should work

| Doc | What it covers |
|---|---|
| [`design/tribunal.md`](./design/tribunal.md) | The proceeding: rounds, interrogatories, concession, and the constraints that make the transcript complete |
| [`design/api.md`](./design/api.md) | The public surface being designed toward `0.1.0` |

### Decisions — ADRs

| Doc | What it covers |
|---|---|
| [`decisions/0001-statute-carries-no-model.md`](./decisions/0001-statute-carries-no-model.md) | Why a `Statute` is inert rule text with no model attached, why `Statute.draft()` is cut from `0.1.0`, and why it stays a type rather than a `str` |
| [`decisions/0002-the-judge-is-a-role.md`](./decisions/0002-the-judge-is-a-role.md) | Why `Judge` is a concrete `enbanc`-owned class rather than a protocol, why per-proceeding state lives in a sitting instead of on the injected agent, and the invariant that keeps message history inside the transcript |
| [`decisions/0003-models-and-guidance-are-injected.md`](./decisions/0003-models-and-guidance-are-injected.md) | Why the caller constructs and injects a PydanticAI `Model`, how `Tribunal`'s default and per-agent overrides interact, and why the per-agent steer is `guidance` that augments rather than `instructions` that replaces |

### Guides — user-facing how-to

*(none yet)*

### Journal — implementation records

*(none yet)*

## Adding a doc

1. Put it in the directory whose guarantee matches it (table in `CLAUDE.md`).
2. Give it the standard frontmatter: `status` and `updated`.
3. Add a row to the index above. An unindexed doc is one nobody finds.
