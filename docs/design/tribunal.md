---
status: draft
updated: 2026-09-02
---

# The tribunal

How a decision is actually reached. Vocabulary is defined in
[`../glossary.md`](../glossary.md); the public surface is in [`api.md`](./api.md).

> `status: draft` — nothing here is implemented. This describes the system being
> built toward `0.1.0`, and it is the document to argue with before writing code.

## The premise

Most "LLM as judge" tooling asks one model to score an output. A single model
holding every possible answer at once has no incentive to make the strongest
case for any of them, and no record of what it considered and rejected.

`enbanc` splits the roles instead. Every possible answer gets a dedicated
advocate whose only job is to argue for it. A separate judge — with no tools of
its own — interrogates them across rounds until it can rule.

The point is **defensibility**. For loan underwriting, insurance appetite, or
eligibility screening, the answer alone is not the deliverable; you need the
reasoning and the evidence that produced it, in a form a reviewer can audit.

## The proceeding

**Round 1 — argument.** One advocate is instantiated per verdict value. Each
argues freely for its assigned verdict, filing an *argument*: a claim and the
exhibits supporting it, gathered through its own tools. An advocate that finds
no reasonable case for its verdict **concedes**.

**Deliberation.** The judge reads the record and either rules or issues a
*continuance* carrying **interrogatories**: targeted questions to a chosen
subset of advocates, not a broadcast.

**Round 2+ — interrogation.** Each addressed advocate files a *response*
answering one interrogatory by id, entering new exhibits as needed. Then the
judge deliberates again. Repeat.

A round is the advocates' filings **plus the deliberation that closes it**. So
round 1 is the arguments and the continuance that follows them, and
`max_rounds` counts judge deliberations — the thing that actually drives cost.

**Termination.** A proceeding ends in one of three ways. The judge issues a
**ruling**. Or `max_rounds` deliberations pass without one, and the hearing's
outcome is **undecided** — a real finding about the case, recorded and
serializable, not an error. Or a participant **cannot be heard** — its model is
unreachable, its tool raises, its output will not validate — and the proceeding
stops without an outcome at all. Only the third raises; see
[`api.md`](./api.md#when-something-goes-wrong),
[`outcomes.md`](./outcomes.md) for each written out, and
[`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md).

Everything filed by every participant, in order, accumulates in the
**transcript** — append-only. That transcript is the audit artifact. Its schema
is in [`api.md`](./api.md#the-record).

Each agent carries its own conversation across rounds rather than being rebuilt
from scratch each time: the judge deliberates repeatedly, and an advocate that
filed in round 1 answers interrogatories in round 3 with its own argument still
in view. The transcript remains the authority on what those conversations may
contain — see the invariant below.

## Constraints that define the design

These are load-bearing. Relaxing any of them changes what the system is.

**The judge has no tools.** It reasons only over what advocates put into the
record. This is what makes the transcript complete: if the judge could go
gather its own evidence, the record would no longer explain the ruling.

**Nothing reaches an agent from outside itself that is not also in the
transcript.** Agents accumulate message history across rounds, and that history
is a representation of the transcript — shaped for the provider and cheap to
cache — never a second channel. A framing turn, a reminder, or a summary
injected into an agent's history and nowhere else would silently break the
guarantee above: the transcript would no longer be a complete account of what
the ruling was based on. If one participant should see what another said, it
goes in the record.

The qualifier *from outside itself* is doing real work, and it is narrower than
this invariant was originally stated. An advocate's own tool results reach its
context and stop there unless it files them as exhibits. That is deliberate:
the judge only ever sees filings, so filings remain a complete account of what
the ruling rests on. **The record is complete as to the ruling, not as to the
search** — an advocate that pulled damaging evidence and quietly declined to
file it leaves no trace. See
[`0006`](../decisions/0006-the-transcript-schema.md), which refines the form of
the invariant stated in [`0002`](../decisions/0002-the-judge-is-a-role.md).

**Advocate tools are strictly read-only.** An adjudication must never mutate
the world it is reasoning about. This is enforced at the tool boundary, not by
instructing the model to behave.

**Concession is a first-class outcome, not a failure.** An advocate that
concedes has done its job well. Treating concession as an error would pressure
advocates into manufacturing arguments for indefensible positions — exactly the
failure mode the adversarial structure exists to prevent.

**A tribunal that loses a participant does not rule.** One advocate's model
failing ends the proceeding, even when the judge and the remaining advocates are
healthy. Deliberating on what is left would produce a decision reached because
the opposing advocate was knocked offline rather than answered — and nothing in
that ruling would distinguish it from one reached on a full bench. This is the
counterpart to concession being first-class: an advocate that declines to argue
has done its job, and an advocate that could not argue has not been heard at
all. The two must never be recorded as the same thing.

**Ruling and continuance are a discriminated union, not a flag.** The judge
returns either a `Ruling` (verdict + reasoning, terminal) or a `Continuance`
(interrogatories for the next round), both parameterized by the verdict enum
and both tagged with a defaulted `kind` literal. This makes invalid states
unrepresentable: there is no decision that also carries pending questions, and
no non-decision with nothing to ask. Pydantic discriminates on the tag, so the
schema validates itself, documents itself to the model, and survives being
persisted and read back. Shape is in
[`../glossary.md`](../glossary.md#judge-output-shape).

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. A question that is only *sharpened* — its options narrowed, nothing
decided — stays, rewritten in place. See rule 7 in
[`../../CLAUDE.md`](../../CLAUDE.md).

- **Advocate isolation.** In round 1, does an advocate see its peers' arguments,
  or only the case and statute? Isolation produces independent arguments;
  visibility produces genuine rebuttal. This changes the character of the output.
- **Cost control.** Rounds multiply tokens by the advocate count. Visibility is
  settled — `hearing.usage` reports what a proceeding spent — but the governor
  is not: whether `max_rounds` is the only one, or a budget can halt a
  proceeding mid-round. PydanticAI already ships `UsageLimits` and
  `UsageLimitExceeded`, so the likely answer is a pass-through rather than
  something to invent. What
  [`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md)
  adds is where the answer lands: a budget stop is either a finding about the
  case, in which case it joins `Undecided` as an outcome, or a fact about the
  caller's wallet, in which case it is a `ProceedingFailed`. That is the same
  line `0011` draws, applied to a governor that does not exist yet.
