---
status: accepted
updated: 2026-09-04
---

# 0022. A tool call that returned nothing is recorded

## Context

[`0019`](./0019-the-ledger-is-part-of-the-record.md) records every source an
advocate's tools returned, and claims the record is complete as to the search.
[`0020`](./0020-tool-timeouts-ride-on-the-tool.md) established that a tool
timeout is not fatal: PydanticAI cancels the call, tells the model
`Timed out after 15.0 seconds.`, and the advocate carries on.

Together those leave a hole. A tool call that fails produces no source, so it
produces no ledger row, so it appears nowhere. Observed against PydanticAI 2.36,
an advocate whose document store hangs:

```text
tool-call     find_filings(applicant='A. Okonkwo')  -> ''
retry-prompt  find_filings                          -> 'Timed out after 0.2 seconds.'
tool-call     find_filings(applicant='A. Okonkwo')  -> ''
retry-prompt  find_filings                          -> 'Timed out after 0.2 seconds.'
tool-call     web_search(query='self-employment income')
tool-return   web_search                            -> 'generic guidance …'

outcome: "Argument: income appears adequate."
usage.tool_calls (successful only): 1
```

The transcript would hold one retrieval and one thin argument. The document
store — the only authoritative source — appears in no entry, no ledger row, and
not in `usage`. The record says *this advocate searched the web once*. The truth
is *this advocate was blocked from the source that mattered and fell back*.

**This is a third state the design has no vocabulary for.**
[`0011`](./0011-exhaustion-is-an-outcome-failure-is-an-error.md) and
[`0012`](./0012-a-failure-cancels-the-round.md) turn on one distinction: an
advocate that *declined* to argue has done its job, and one that *could not* be
heard has not — and a tribunal that loses a participant must not rule. `0020`
legitimized *partially silenced*: alive, degraded, still filing, and the
proceeding rules.

Which state a proceeding lands in depends on how the tool broke, not on how much
evidence was lost. A store that returns 500 fast raises, propagates, and becomes
`ProceedingFailed` — no ruling. A store that hangs times out, degrades, and the
tribunal rules. From an audit standpoint that is arbitrary.

It also undercuts `0019` directly. `0019` tells a reviewer to read the ledger
for suppression. A thin ledger has two readings — *did not look*, or *looked and
got nothing* — and `0019` supplies no way to separate them.

## Decision

**A tool call that returned nothing is recorded, in a list of its own.**

```python
class ToolFailure(BaseModel, Generic[VerdictT]):
    round: int
    advocate: VerdictT
    tool: str
    reference: str    # the call: 'find_filings(applicant="A. Okonkwo")'
    detail: str       # what the advocate was told: 'Timed out after 15.0 seconds.'

class Transcript(BaseModel, Generic[VerdictT]):
    ...
    failures: list[ToolFailure[VerdictT]] = []
```

**`ToolFailure` has no id, deliberately.** A `Retrieval` carries an id so an
`Exhibit.source` can name it; that is the whole reason the type exists. A failed
call produced nothing and can never be cited. The absent id is the type saying
so.

**Every attempt is a row.** A tool that timed out three times is a different
fact from one that timed out once.

**`Retrieval` and `Transcript.ledger` are unchanged**, and so is `0019`'s
`(advocate, id)` join.

## Consequences

**Rejected: an `outcome` field on `Retrieval`.** One list, one join, one field —
the smaller change. It fails on what the ledger's rows *mean*. A successful call
yields one row per source; a failed call yields none. Folding failures in forces
a synthetic one-row-per-call into a list whose unit is a source, so rows would
silently mean two different things, and `content` would become conditionally
meaningless. It would also put a permanently uncitable row in the list whose
entire purpose is citation.

**Rejected: refusing to rule when an advocate's tools degraded.** It would
extend `0011`'s "a tribunal that loses a participant does not rule" to cover
this. The bar there is losing a *participant*, not a call — one timeout out of
twenty that succeeded on retry is not a silenced advocate, and killing
proceedings over it would make flaky infrastructure fatal. The record's job here
is to make the question askable, not to answer it.

**Rejected: surfacing it on `Hearing` rather than `Transcript`.** It would match
the `usage` precedent — nobody *filed* a failure. But `0019` settled that the
transcript is the artifact that travels and gets handed to a reviewer, and a
degradation signal that vanishes when the transcript is persisted is one that
will not be there when it is needed.

**This is cheap, unlike `0019`.** A failure row has no `content` — on the order
of 150 bytes — and the count is bounded by `Agent(retries=...)` rather than by
what a caller's tools happen to return. `0006`'s bulk objection, which drove
every earlier decision in this area, barely applies.

**It narrows `0021`'s exception.** Storing `detail` puts the retry-prompt text
into the transcript, so
[`0021`](./0021-retry-prompts-are-outside-the-invariant.md)'s carve-out shrinks
from *all* retry prompts to output-validation retry prompts only. It does not
close: an advocate that cited an unresolvable ledger id still sees a prompt no
transcript holds.

**Cost: this records that a tool failed, not whether the ruling turned on it.**
A reviewer reading that `APPROVE`'s searches timed out twice still has to judge
whether the judge should have weighed it. `enbanc` does not mark a hearing
degraded, does not warn, and does not adjust the outcome. Recording is not
adjudicating, and a reader should not take a populated `failures` list as a
finding.

**Cost: a flaky tool puts rows in every transcript.** Bounded, but real, and a
caller whose infrastructure is unreliable will see the noise.

**Consequence: the seam that observes retry prompts is now load-bearing twice.**
`enbanc` already reads the agent's message stream to build the ledger; it now
also reads it to build `failures`. A PydanticAI change to how tool failures are
represented in message history breaks both.
