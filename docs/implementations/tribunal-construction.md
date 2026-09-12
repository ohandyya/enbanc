---
status: draft
updated: 2026-09-12
---

# Building a tribunal

**`Tribunal`, `Judge`, `Advocate` — and the four ways construction refuses.**
Everything a caller can do before spending anything, including reading the exact
instructions an agent will run under.

## Scope

`_tribunal.py`: the three public classes, the validation that runs at
`Tribunal(...)`, the assembly of a participant's instruction parts, and
`instructions_for(participant)`. A `ConfigurationError` is raised here and
nowhere else — a tribunal that cannot be built has no transcript to carry.

**Not in this PR.** `hear()` and `hear_stream()`. The class lands without its
main methods; they arrive in [`proceeding-core.md`](./proceeding-core.md), which
takes the pieces rather than the `Tribunal` and so can be built and tested
without one.

This PR brings the prompt goldens that
[`rendering.md`](./rendering.md) could not: `instructions_for()` is the seam
[`testing.md`](../design/testing.md#pinning-the-prompting-surface) pins the
instructions channel through, and it exists only now.

## Implements

- [`api.md` § What each piece carries](../design/api.md#what-each-piece-carries)
  — `Tribunal`, `Judge`, `Advocate`
- [`api.md` § The governors](../design/api.md#the-governors) — what is accepted,
  and what `request_limit` must not be
- [`execution.md` § `ConfigurationError` has four cases](../design/execution.md#configurationerror-has-four-cases)
- [`prompting.md` § How an agent is assembled](../design/prompting.md#how-an-agent-is-assembled)
  — the part order, and why the shared block comes first
- [`prompting.md` § Previewing what an agent will run under](../design/prompting.md#previewing-what-an-agent-will-run-under)
- [`outcomes.md` § 5. The tribunal is misconfigured](../design/outcomes.md#5-the-tribunal-is-misconfigured)
  — the acceptance test, messages asserted as text
- [`testing.md` § Pinning the prompting surface](../design/testing.md#pinning-the-prompting-surface)

## Depends on

[`schemas.md`](./schemas.md), [`rendering.md`](./rendering.md).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
