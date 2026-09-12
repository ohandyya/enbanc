---
status: draft
updated: 2026-09-12
---

# Prompting and rendering

**One renderer, three viewpoints, and every word `enbanc` puts in front of a
model.** `_prompting.py`: procedure `p1`, both procedural prompts, the four turn
templates, the projections, and the body behind `Transcript.render()`.

## Scope

The whole of [`prompting.md`](../design/prompting.md) that does not need a live
proceeding: the two procedural prompts verbatim, the turn templates, the
`ReviewerView` / `JudgeView` / `AdvocateView` projections and their `since`
filter, the `p1` constant, and `Transcript.render()` — which is where the one
forced import cycle is broken, `_prompting` importing `_transcript` under
`TYPE_CHECKING` only.

**Not in this PR.** `instructions_for()` and the goldens that run through it.
Assembling instruction parts needs a `Tribunal`, so both land in
[`tribunal-construction.md`](./tribunal-construction.md) — the prompt *text* is
here, the assembly of it is there. The tool-result format is specified here and
implemented in [`ledgering-toolset.md`](./ledgering-toolset.md), where
`render_call` and `render_results` live.

## Implements

- [`prompting.md` § One renderer, three viewpoints](../design/prompting.md#one-renderer-three-viewpoints)
- [`prompting.md` § The advocate's procedural prompt](../design/prompting.md#the-advocates-procedural-prompt)
  and [§ The judge's](../design/prompting.md#the-judges-procedural-prompt)
- [`prompting.md` § The turns](../design/prompting.md#the-turns) — all four
- [`prompting.md` § `Transcript.render()`](../design/prompting.md#transcriptrender)
- [`prompting.md` § Procedure versions](../design/prompting.md#procedure-versions)
  — `p1`, and the bump discipline this PR is the first to owe
- [`execution.md` § `since` advances once per run](../design/execution.md#since-advances-once-per-run-not-once-per-round)
  — the filter half; the state that feeds it is
  [`proceeding-core.md`](./proceeding-core.md)
- [`packaging.md` § What imports what](../design/packaging.md#what-imports-what)
  — the cycle break

## Depends on

[`schemas.md`](./schemas.md).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
