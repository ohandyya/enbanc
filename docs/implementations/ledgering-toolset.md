---
status: draft
updated: 2026-09-19
---

# The ledgering toolset

**`execution.md`'s piece 2.** One `WrapperToolset` over one `CombinedToolset`,
intercepting every tool call an advocate makes, so that every source it saw is
recorded and every citation it files can be stamped.

## Scope

`_ledgering.py`: `Ledgering` with `call_tool` overridden, `as_sources`'s
shape-sniff, the "returned *N* sources" header line composed around
`_prompting.render_source` — already built in
[`rendering.md`](./rendering.md#one-three-line-source-shape-in-three-dressings),
which is where each source's own three-line shape lives — in
[`prompting.md`](../design/prompting.md#how-ledger-ids-reach-the-model)'s
format, the per-advocate id counter that survives the whole proceeding, and the
output validator that rejects an `_Exhibit` citing an id the ledger does not
hold.

A `ModelRetry` — which is what a `Tool` timeout becomes — is recorded on
`failures` and re-raised untouched. Anything else propagates: the difference
between a degraded advocate and an unheard one is that one `except` clause.

**Not in this PR.** Wiring the toolset into an agent, and setting `round` on it
before each dispatch. Both are the orchestrator's, in
[`proceeding-core.md`](./proceeding-core.md). This PR constructs and calls the
toolset directly, which is what
[`packaging.md`](../design/packaging.md#the-modules) means by the internals being
laid out because tests import them.

## Implements

- [`execution.md` § Piece 2 — the ledgering toolset](../design/execution.md#piece-2--the-ledgering-toolset)
- [`evidence.md` § How a source becomes an exhibit](../design/evidence.md#how-a-source-becomes-an-exhibit)
- [`evidence.md` § The ledger is part of the record](../design/evidence.md#the-ledger-is-part-of-the-record)
- [`evidence.md` § A call that returned nothing is recorded too](../design/evidence.md#a-call-that-returned-nothing-is-recorded-too)
- [`evidence.md` § An unresolvable id is a validation failure](../design/evidence.md#an-unresolvable-id-is-a-validation-failure)
- [`prompting.md` § How ledger ids reach the model](../design/prompting.md#how-ledger-ids-reach-the-model)

## Depends on

[`schemas.md`](./schemas.md), [`rendering.md`](./rendering.md).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
