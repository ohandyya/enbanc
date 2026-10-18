---
status: draft
updated: 2026-10-18
---

# An excerpt check a reviewer runs over a finished transcript

**A helper that compares each exhibit's excerpt with the ledger row it cites,
and reports.** An advocate writes its own excerpt, so it can misquote.
[`evidence.md`](../design/evidence.md#why-content-is-the-advocates-excerpt)
accepts that because the citation resolves and a reviewer can *find* the
misquote. Nothing does the finding, though: the row and the excerpt sit side by
side in the transcript, and no check compares them.

## Scope

**Settle [`evidence.md`'s open question](../design/evidence.md#open-questions)**
by taking its third option: a helper the reviewer runs over a finished
`Hearing` or `Transcript`. The other two options are rejected, and the ADR says
why:

- **A substring test at filing** rejects a fair paraphrase and costs the
  advocate retries.
- **A flag on `Exhibit`** changes the record's schema to hold a judgment the
  record otherwise does not make.

**It reports and never rejects.** It runs after the proceeding, so it changes
no prompt, no output schema and no procedure version. Because it only reports,
it can grade a paraphrase with a similarity measure instead of failing it.
Exactly what it returns, and whether "similar" is a threshold or a score, is
settled when the PR starts.

**It is a new public name**, so it joins `__all__` and
[`api.md`](../design/api.md), and ships in a minor release. That is `0.2.0`
unless it is released earlier on its own.

**It comes before the benchmark.** [`benchmark.md`](./benchmark.md) measures
citation faithfulness, and this helper is that measurement. Building it first
means the benchmark reuses it rather than writing a second copy.

## Implements

- [`evidence.md` § Open questions](../design/evidence.md#open-questions): the
  excerpt bullet, settled under `CLAUDE.md` rule 7 (prose, ADR, bullet
  removed).
- [`evidence.md` § Why `content` is the advocate's excerpt](../design/evidence.md#why-content-is-the-advocates-excerpt):
  the prose that says a misquote can be *found* gains the tool that finds it.
- [`api.md`](../design/api.md): the new export.

## Depends on

Nothing open. It reads `Exhibit` and `Retrieval`, which have merged:
[`schemas.md`](./schemas.md) (#19) and
[`ledger-names-the-call.md`](./ledger-names-the-call.md) (#32).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
