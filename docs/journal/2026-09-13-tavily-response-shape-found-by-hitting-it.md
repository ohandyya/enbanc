---
status: current
updated: 2026-09-13
---

# Hitting real Tavily found three response-shape edge cases the mapping had not

PR 3 (`web-search-tool.md`) implements `enbanc.tools.web_search` against the
field mapping `evidence.md` had already specified: `url`/`title`/`content` in,
everything else dropped. Writing the integration test in
[`tests/integration/test_web_search.py`](../../tests/integration/test_web_search.py)
against the real API — not the unit tests' canned response — surfaced three
things about Tavily's actual behavior the design had assumed rather than
observed.

## What was decided

**A result missing `url` or `content` is skipped, the rest of the response is
kept.** `Source.reference` is required, so a row with no locator cannot become
one — and it turns out Tavily can return such a row. Raising instead was the
obvious alternative and the wrong one: it would end the entire proceeding over
one malformed row, discarding every other source and every filing already made
in the round. Skipping costs the ledger that one row; the record just cannot
say the advocate saw it.

**`raw_content` and `favicon` are withheld asymmetrically, and the mapping
doesn't need to care.** Requesting neither, the response still carries
`raw_content: null` on every result, while `favicon` is absent from the payload
entirely — two different shapes of "not there." Both are dropped by the same
code that drops a key that never arrived, so the asymmetry reaches nothing in
`enbanc`. It is recorded in `evidence.md` anyway, so the next person reading the
mapping doesn't mistake the difference for a bug.

**Tavily's own `id` is scoped to the request, not the document.** Re-running
the same query renumbers it — the same URL comes back under a different id —
confirming what `evidence.md` already argued from the field's shape: it
identifies nothing a reviewer could look up later, so it was never a candidate
for `Source.reference` regardless.

## Alternatives rejected

Raising `ModelRetry` or letting a `KeyError` propagate on a malformed row —
rejected because the blast radius is the whole proceeding, not one exhibit, and
[a tool that expects to come up empty returns an empty result](../design/evidence.md#what-tools-may-do)
already sets the precedent: partial failure degrades the result, it does not
end the round.

## What to do with this

None of the three changed `_web_search.py` itself — the code was already
correct, having been written to `evidence.md`'s pre-existing mapping. What
changed is that the mapping's prose now states behavior it previously only
implied, so the next tool built to the same `reference` contract
(`docstore_search`, local file search) starts from an observed shape instead of
a guessed one.
