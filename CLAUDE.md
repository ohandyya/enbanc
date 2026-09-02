# enbanc

Adversarial multi-agent adjudication, built on PydanticAI. Pre-`0.1.0`: the
public API described in `README.md` and `docs/design/` does not exist yet.

## Documentation map

Read this before writing code. The directories are not interchangeable — each
one carries a different guarantee about whether its contents are true.

| Path | Guarantee | When to read |
|---|---|---|
| `docs/progress.md` | **Where the work stands.** Status is current; the log is dated. | First, at the start of a session |
| `docs/design/` | **Current truth.** How the system is meant to work. | Always, before implementing |
| `docs/decisions/` | Immutable ADRs. Why a path was chosen. | When a decision seems arbitrary |
| `docs/glossary.md` | The domain vocabulary. | Always |
| `docs/guides/` | User-facing how-to. | When changing public behavior |
| `docs/journal/` | **Historical. May be stale.** Records of past work. | Only when explicitly asked |
| `notes/`, `local/` | Human-only. | Never — reads are denied |

## Rules

1. **`docs/design/` is the spec.** It describes the system as it is now, not as
   it once was. Edit it in place; never append "update:" sections.
2. **A change to behavior updates the design doc in the same commit.** If you
   implement something that contradicts `docs/design/`, the design doc is wrong
   and fixing it is part of the change — not a follow-up.
3. **Never treat `docs/journal/` as a spec.** Entries are dated snapshots,
   frozen at write time, and go stale by design. If a journal entry and a design
   doc disagree, the design doc wins.
4. **Superseded designs move to `docs/design/_superseded/`** rather than being
   deleted, and get a `status: superseded` line saying what replaced them.
5. **Write a journal entry only when the diff cannot explain itself.** Git log,
   the diff, and the PR description already cover *what* changed. A journal entry
   earns its place by recording how an episode of work went — a constraint found
   only by building, a shape the implementation was forced into, a dead end worth
   not repeating. Otherwise skip it. A choice that *binds* future work is an ADR
   in `docs/decisions/`, not a journal entry.
6. **`docs/progress.md` is the session checkpoint, not a spec.** The `wrap-up`
   skill maintains it: `Current state` is rewritten in place, `Log` entries are
   prepended and never edited. Reasoning belongs in `docs/journal/`, linked from
   the log entry — not inlined.
7. **Resolving an open question is three moves in one commit.** The answer goes
   into the design doc's prose, where it becomes spec; an ADR in
   `docs/decisions/` records why and what was rejected, indexed in
   `docs/README.md`; only then is the bullet deleted from `## Open questions`.
   Deleting without the first two drops the question without answering it, and
   leaving a struck-through bullet behind is the "update:" section rule 1
   forbids — the ADR is the record, and the index is how it is found. Two cases
   are not resolutions: a question that is merely *sharpened* stays, rewritten
   in place with no ADR, and one that goes *moot* is deleted by whichever ADR
   made it moot, which says so.

## Conventions

Every doc in `docs/` opens with frontmatter:

```yaml
---
status: current | superseded | draft
updated: YYYY-MM-DD
---
```

- `docs/design/` — named by subject, no numbers: `tribunal.md`, `transcript.md`
- `docs/decisions/` — numbered and immutable: `0001-short-title.md`
- `docs/journal/` — dated: `YYYY-MM-DD-short-slug.md`

## Development

`make help` lists the available targets. Tooling is uv + ruff + pyright +
pytest, with pre-commit hooks enforced in CI.
