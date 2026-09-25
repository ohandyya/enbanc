---
status: accepted
updated: 2026-09-25
---

# 0038. The citation check rides on the output type, not an agent-level validator

## Context

[`execution.md`](../design/execution.md#the-citation-check-resolves-ids) fixed
the shape before this decision: an advocate's `_Exhibit.source` is checked
against its own ledger, and a `ModelRetry` for an unresolvable id spends the
**`output`** retry budget rather than the `tools` one. The obvious PydanticAI
mechanism for that is `agent.output_validator(...)` — a function registered on
the agent, run against whatever it emits.

Building [`proceeding-core.md`](../implementations/proceeding-core.md) found
that mechanism does not coexist with a second thing the design already fixed:
**one agent per participant**, built once and reused across every run that
participant makes, whose output shape changes by round — `_Argument |
Concession` in round 1, `_Response` from round 2. PydanticAI's own source
(`Agent._prepare_output_schema`, `pydantic-ai 2.36.0`) refuses *any* per-run
`output_type` override once `agent.output_validator(...)` has been called,
including an override identical to the agent's own construction-time type:

```text
override raised: UserError Cannot set a custom run `output_type` when the agent has output validators
```

Both halves cannot hold at once. Either the citation check stops being an
output validator, or one agent per participant stops being true.

## Decision

**The check rides on the output type, as an output function**, not as an
agent-level validator. PydanticAI accepts a plain function of one parameter as
an output type and derives the tool name, description, and JSON schema from
that *parameter's* type rather than from the function itself:

```python
def _filing_output(filing_type, check):
    def file(filing):
        check(filing)
        return filing

    file.__annotations__ = {"filing": filing_type, "return": filing_type}
    return file
```

`ledgering-toolset.md`'s `check_citations` does not move — this is four lines
of wiring around the same method, closing over the same `Ledgering`. What
changes is only where it is attached: `output_type=[_filing_output(_Argument[V],
ledgering.check_citations), Concession[V]]` instead of
`agent.output_validator(ledgering.check_citations)`.

Verified rather than assumed, because the whole point of the move is that
nothing about the wire changes: a `ModelRetry` raised inside the function still
spends the **`output`** budget and still reaches the model as a
`RetryPromptPart`; with no agent-level validator, the per-run `output_type`
override is legal again, which is what lets one agent carry an advocate across
rounds.

**Two traps in the spelling, both load-bearing and neither guessable:**

- The parameter's annotation must be *assigned* (`file.__annotations__ = ...`),
  not written as a literal `_Argument[VerdictT]`. Pydantic returns the origin
  class for a generic parameterized with a bare `TypeVar`, evaluated at
  runtime — so a literal annotation collapses and the schema carries
  `enum: []` for the verdict field: no answer the caller declared validates,
  and every run exhausts the output budget failing. The function must be
  built with the type resolved from the tribunal's own enum.
- The inner function must carry **no docstring**. PydanticAI surfaces one as
  the output tool's *description* — text a model reads that
  `docs/design/prompting.md` would then have to own and version. Without one,
  the model reads PydanticAI's own generic sentence, exactly as it would for a
  bare model output type.

## Consequences

**One agent per participant survives untouched**, across every round that
participant argues in. The history dict stays one entry per participant, not
one per output shape, and the fan-out's *eight runs across four agents* count
in `execution.md`'s worked proceeding does not grow.

**A function used as an output type this way is invisible on the wire.** The
tool names, descriptions, and schemas a model sees are byte-identical to
handing the filing type over directly — verified against the installed
library and pinned by
[`tests/contract/test_an_output_validator_forbids_a_run_output_type.py`](../../tests/contract/test_an_output_validator_forbids_a_run_output_type.py).
This is a claim about `pydantic-ai 2.36.0`, not about `enbanc`, so
`execution.md`'s "What PydanticAI already does" carries it as a finding rather
than as a design choice, and a version bump that changes it fails the contract
tier rather than silently drifting.

**A sole output type is named `final_result`, not
`final_result__ResponseLoanDecision`.** The qualified name is what a *union*
gets; an advocate offered `_Response` alone in round 2 sees the bare name. Two
of `execution.md`'s worked traces recorded the qualified form for round 2
before this was verified, and are wrong until
[`round-loop.md`](../implementations/round-loop.md) corrects them.

**Rejected: a second agent per advocate**, one built for arguments and one for
responses, each free to keep `agent.output_validator`. Costs *one `Agent` per
participant* directly — the count `execution.md`'s worked proceeding is built
around — and splits one participant's runs across two agents that would need
to share a history entry, a `Ledgering`, and a `RunUsage` across the split:
three mutables the design otherwise keeps on one object per participant.

**Rejected: one union offered for every round** —
`_Argument | Concession | _Response` always on the table, no per-run override
needed at all. Makes a round-1 `_Response` carrying an `answering` id nobody
issued an *expressible* state, which is exactly what
[`0015`](./0015-interrogatory-ids-are-stamped-on-filing.md)'s stamping exists
to make unreachable. It would also need a second mutable "what may be filed
now" field on the orchestrator, purely to reject what the schema itself no
longer rules out.
