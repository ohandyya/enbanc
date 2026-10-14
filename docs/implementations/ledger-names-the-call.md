---
status: current
updated: 2026-10-14
---

# A ledger row names its call

**The record says what each advocate asked for, not only what came back.** Found
while writing [`guides.md`](./guides.md)'s first guide: listing an advocate's tool
calls from the transcript could fill who, which tool and the output, but not the
input — the call was rendered, shown to the advocate, and dropped.

## Scope

`Retrieval` gains a required `call: str`, filled by the ledgering wrapper from
the `render_call` string it already builds for the tool result's header. Every
row one call produced carries the same string. `## The ledger` renders it on a
`via {call} in round {n}` line between the reference and the content, dropped
for an anonymous source whose reference already is the call.

`p1` is amended in place rather than bumped to `p2`: nothing has shipped, so no
transcript claims `p1` yet. [`0042`](../decisions/0042-a-retrieval-names-its-call.md)
records that, and the rest of the decision.

**Not in this PR.** The guide's use of the field — listing tool calls after the
ruling — lands in [`guides.md`](./guides.md), once this merges and that branch is
rebased onto it. The tool result the advocate reads is unchanged.

## Implements

- [`evidence.md` § The ledger is part of the record](../design/evidence.md#the-ledger-is-part-of-the-record)
  — the new field and why it exists.
- [`prompting.md` § `Transcript.render()`](../design/prompting.md#transcriptrender)
  — the `via` line and when it is dropped.
- [`api.md` § The record](../design/api.md#the-record) — `Retrieval`'s schema.

## Depends on

[`ledgering-toolset.md`](./ledgering-toolset.md) (#25), merged — the wrapper and
the `Retrieval` rows this extends.

## Files

| File | Change |
|---|---|
| `src/enbanc/_transcript.py` | `Retrieval.call: str`, required, with a docstring paragraph on why. |
| `src/enbanc/_ledgering.py` | `_ledger_rows` takes the rendered call and stamps it on every row. |
| `src/enbanc/_prompting.py` | `render_source` gains `via`; `## The ledger` passes `"{call} in round {n}"`, or nothing when the reference is the call. |
| `docs/decisions/0042-a-retrieval-names-its-call.md` | **New.** The ADR. Indexed in `docs/README.md`. |
| `docs/design/api.md`, `evidence.md`, `prompting.md`, `execution.md`, `docs/glossary.md` | The schema, the paragraph, the worked example and rule, the ledgering sketch, and the glossary row. |

## Tests

All `unit`. No live tier changes: the field is filled offline, and the live run
that motivated it is the guide's.

- `test_ledgering.py::test_every_row_names_the_call_that_produced_it` — two
  calls, three rows: each row's `call` is its call, both rows of the two-source
  call share it, and it is the exact header the advocate read.
- `test_transcript_render.py::test_the_whole_artifact` — the snapshot gains the
  `via` lines, and its anonymous `dti_for` row shows the line dropped.
- Every fixture that builds a `Retrieval` passes `call`, because the field has no
  default.

## Open questions

None.
