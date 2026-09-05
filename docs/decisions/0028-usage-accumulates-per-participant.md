---
status: accepted
updated: 2026-09-05
---

# 0028. Usage accumulates into one object per participant

## Context

[`0014`](./0014-usage-is-broken-down-per-participant.md) settled the *shape*:
`usage_by_participant` is the stored fact and `Hearing.usage` is its sum. It also
settled what happens when a proceeding fails — "a run that was cancelled or died
before reporting contributes nothing, so absence means *did not report*, never
*spent nothing*" — and `../design/api.md` and `../design/outcomes.md` both wrote
that down as a guarantee a caller must live with.

That caveat was inherited from
[`0012`](./0012-a-failure-cancels-the-round.md)'s floor-not-a-total reasoning,
and it was settled on the surface, because nothing was implemented. It assumed a
mechanism: that usage is read *off a result*, so a run with no result reports
nothing.

Writing `../design/execution.md` established that the assumption is false in
`pydantic-ai 2.36.0`. `Agent.run(usage=u)` accumulates into the caller's object
in place, `result.usage` **is** that object, and a run that dies mid-flight
leaves its partial spend behind:

```text
after run 1, shared u: requests=2 input=300   | result.usage: 2 300
after run 2, shared u: requests=4 input=600   | result.usage: 4 600
same object: True

raised: RuntimeError('tool exploded')
usage after failure: requests=1 input=100 output=10
```

[`0024`](./0024-a-budget-stops-the-proceeding-between-rounds.md) recorded this
same mechanic, and drew the opposite conclusion from it — correctly, because it
was considering **one** accumulator shared across every participant. That would
make `AgentRunResult.usage` report the whole proceeding's spend under every key
and erase `0014`'s breakdown entirely. One object *per participant* is not a
weaker version of that idea; it is the other one.

## Decision

**`enbanc` mints one `RunUsage` per participant at the start of a proceeding and
passes it to every run that participant makes.** The dict of those objects *is*
`usage_by_participant`. `Hearing.usage` is computed from it, as `0014` requires.

**The guarantee on a failure is strengthened.** On a `ProceedingFailed`, every
participant that was **dispatched** has a key, holding whatever it spent before
the proceeding stopped — including a run that was cancelled mid-flight and a run
that died in a provider call. **Absence now means *never dispatched*.**

```python
# round 1, DENY's provider is down, REFER cancelled where it stood
usage_by_participant={
    <LoanDecision.APPROVE: 'approve'>: RunUsage(requests=2, ...),   # filed
    <LoanDecision.DENY: 'deny'>:       RunUsage(requests=1, ...),   # died mid-run
    <LoanDecision.REFER: 'refer ...'>: RunUsage(requests=1, ...),   # cancelled
}   # no 'judge' key — the deliberation was never dispatched
```

**`usage` on a failure is still a floor, and for a different reason.**
Cancellation is client-side and does not un-bill tokens a provider has already
generated, so the true cost of a cancelled proceeding can exceed what any
accumulator saw. `0012`'s caveat survives; what does not survive is the claim
that a participant's spend is *unattributable*.

## Consequences

**`api.md` and `outcomes.md` are edited in the same commit**, under rule 2. Both
said a participant that did not report has no key; both now say absence means the
participant never ran. `outcomes.md` §4's three worked failures gain the keys
they were missing.

**The breakdown becomes the more useful half of a failure, not the emptier
one.** "Which advocate had spent what when the provider went down" is a question
a caller debugging a flaky proceeding actually asks, and under the old wording
the answer was systematically absent for exactly the participant that failed —
the one being investigated.

**Absence becomes informative.** Under the old rule a missing key was ambiguous
between *cancelled*, *died*, and *never started*, so it carried nothing. It now
carries one fact, and `outcomes.md`'s judge-is-down example reads it: no `'judge'`
key means the deliberation was never attempted, which is the same thing the
absent `Continuance` in the transcript says. Two independent parts of the
artifact now agree, where before one was silent.

**The invariant `0014` names is unchanged and is now enforced in one place.**
Both `Hearing` and `ProceedingFailed` are constructed from the same dict, and the
aggregate is a sum over it. `0014` called that "a bug the moment they are not";
minting the objects up front is what makes there be nothing else to keep in
sync.

**Rejected: keep the weaker promise and implement the accumulator anyway.** The
library would deliver more than it documents, leaving room to change mechanism
later without breaking a stated guarantee. Rejected because an audit artifact
that under-describes itself is the same defect as one that over-describes itself,
pointed the other way: a reviewer who reads "did not report" will not look at a
key that is sitting right there, and the caution buys freedom to make the
artifact *worse* later, which is not freedom worth reserving.

**Rejected: a shared accumulator across participants.** `0024` rejected it and
this does not reopen it. It is the only shape that would let a budget stop a
proceeding the instant it was crossed, and it costs `0014`'s breakdown outright.

**Rejected: reading usage off `AgentRunResult` and summing at the end.** The
mechanism the old caveat assumed. It works for every proceeding that succeeds and
degrades exactly where the information is most wanted, which is the shape of a
design that was never tested against its own failure path.

**Cost: the accumulators are mutable state held across a proceeding.** They are
minted in `hear()` and discarded with it, alongside the history dict and the
ledgering toolsets (`../design/execution.md`, *Also in scope*), so they do not
weaken the reusable-agents split. But they are the third such structure, and each
one is a thing that must not leak between two concurrent `hear()` calls.

**Cost: a participant can hold a `RunUsage` reporting zero.** A participant
dispatched into a round that was cancelled before its first request has a key
with nothing in it, which reads like "spent nothing" and means "got nowhere".
`0014`'s "no key is a zero placeholder" holds on a `Hearing`, where every
participant ran to completion; on a failure it does not, and `api.md` says so.
