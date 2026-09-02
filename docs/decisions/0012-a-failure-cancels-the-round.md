---
status: accepted
updated: 2026-09-02
---

# 0012. A failure cancels the round rather than draining it

## Context

[`0011`](./0011-exhaustion-is-an-outcome-failure-is-an-error.md) settled
everything about how a failed proceeding *ends*: one participant that cannot be
heard is terminal for the whole tribunal, the judge does not deliberate,
`hear()` raises `ProceedingFailed`, and there is no `Hearing`. It did not say
what becomes of the rest of the round.

That gap is real because advocates fan out concurrently. A failure in round *N*
catches siblings mid-run — some have already filed, some are seconds from
filing, some are grinding through their own retry chain — and the library has to
either stop them or wait for them. `../design/api.md` carried the question, and
`../design/outcomes.md` had to hedge in the middle of a worked example, showing
one answer and noting the other would add an entry.

Nothing about the *ending* is in play. The choice is observable in exactly three
places:

- **`ProceedingFailed.transcript`** — does round *N* hold only what landed
  before the failure, or every filing the healthy advocates would have made?
- **`ProceedingFailed.usage`** — how much of the round is counted, and how much
  is actually spent.
- **Wall clock** — how long `hear()` takes to raise.

## Decision

**The first failure cancels the round.** When an advocate or the judge raises,
the sibling runs still in flight are cancelled, and `ProceedingFailed` carries
the transcript exactly as it stood at that moment.

**`transcript` is what was filed, not what the round contained.** A filing
enters the record when its run completes and validates; a cancelled run
contributes nothing, so two runs of the same outage can leave different numbers
of entries behind. This is a property of the artifact, not a defect in it — the
record never claims a cancelled advocate had nothing to say, because it does not
represent that advocate at all.

**`participant` stays singular.** Cancelling makes "who could not be heard" the
first failure by construction, so there is never a set of simultaneous failures
to choose between or to widen the field for.

**One rule for stopping mid-fan-out.**
[`0010`](./0010-streaming-yields-the-record.md) already specified that
abandoning a stream cancels the in-flight advocate and judge runs. A failure now
stops the same way, so `enbanc` has a single account of what happens to
concurrent work when a proceeding stops early, whatever stopped it.

## Consequences

**`../design/outcomes.md` stops hedging.** The worked example in which `DENY`'s
provider is down and `REFER` never appears in the record is now the specified
behaviour rather than one of two candidates.

**Rejected: drain the fan-out, then raise.** Await every in-flight advocate,
let the healthy ones file, and raise with round *N* complete but for the
participant that failed. It produces the richest forensic record and a
deterministic transcript, and it was the option with a real case behind it.

It loses on three counts. The extra filings buy nothing that is needed: a
transcript on a failure is a diagnostic, not an audit artifact — nothing was
adjudicated — and an additional argument in a round the judge never deliberated
on does not make the diagnosis clearer. It is not resumable either, because
agent message history is created inside `hear()` and discarded when it returns
(`0002`), so there is no partial state a retry could resume from. Second, it
costs most where it hurts: failures are typically correlated, one provider
serving every advocate, so draining usually means waiting out two more retry
chains that the caller's transport has already been grinding through, after the
proceeding is known to be dead — and paying for filings that can never be ruled
on. Third, it admits several failures at once and puts pressure on
`ProceedingFailed.participant` to become a list, reopening a field `0011` had
just closed.

**Rejected: a bounded grace period.** Cancel, but give in-flight runs a short
deadline to land first. It buys part of the drained record for part of the
drained latency, at the price of a timeout constant with no defensible value —
and it leaves the transcript depending on that constant, which is
nondeterminism *and* a knob.

**Rejected: `on_peer_failure="cancel" | "drain"`.** Structurally identical to
the `on_absence` knob `0011` rejected: two behaviours with different guarantees,
both documented by the library and neither promised by it.

**Rejected: an `interrupted: list[VerdictT]` field on the exception**, naming
the advocates that were cancelled. It is derivable — the advocates addressed in
round *N*, less those with an entry in it, less the one that failed — so it is
the store-it-twice mistake that kept `position` off `Argument` and `rounds` off
`ProceedingFailed`.

**`usage` under-reports true spend, and that is accepted.** Cancellation is
client-side and does not un-bill tokens a provider has already generated, so a
cancelled proceeding may cost more than its `usage` says. `0011` already types
this honestly — usage on a failure is a floor, not a total — and spending less
while reporting a floor is better than spending more to report precisely.

**Cost: the failing round's record is timing-dependent.** A caller comparing two
failed proceedings cannot read anything into one having more entries than the
other. Accepted, because the alternative pays real latency and real money for a
record that only makes a post-mortem marginally tidier.

**This does not decide cost control.** Whether a budget can halt a proceeding
mid-round is still open in `../design/tribunal.md`. But if one ever can, how it
stops the fan-out is no longer a separate question: it cancels, like everything
else that stops a proceeding early.
