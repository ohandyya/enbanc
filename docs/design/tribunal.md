---
status: draft
updated: 2026-09-01
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
argues freely for its assigned verdict, filing a position, a claim, and
supporting exhibits gathered through its own tools. An advocate that finds no
reasonable case for its verdict **concedes**.

**Round 2+ — interrogation.** If the judge cannot rule on the record so far, it
issues *interrogatories*: targeted questions to a chosen subset of advocates,
not a broadcast. Those advocates answer, entering new exhibits as needed.
Repeat.

**Termination.** The proceeding ends when the judge issues a ruling, or when
`max_rounds` is exceeded.

Everything said by every participant, in order, accumulates in the
**transcript** — append-only. That transcript is the audit artifact.

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

**Nothing enters an agent's context that is not also in the transcript.** Agents
accumulate message history across rounds, and that history is a
representation of the transcript — shaped for the provider and cheap to
cache — never a second channel. A framing turn, a reminder, or a summary
injected into an agent's history and nowhere else would silently break the
guarantee above: the transcript would no longer be a complete account of what
the ruling was based on. If an agent should see it, it goes in the record.

**Advocate tools are strictly read-only.** An adjudication must never mutate
the world it is reasoning about. This is enforced at the tool boundary, not by
instructing the model to behave.

**Concession is a first-class outcome, not a failure.** An advocate that
concedes has done its job well. Treating concession as an error would pressure
advocates into manufacturing arguments for indefensible positions — exactly the
failure mode the adversarial structure exists to prevent.

**Ruling and continuance are a discriminated union, not a flag.** The judge
returns either a `Ruling` (verdict + reasoning, terminal) or a `Continuance`
(interrogatories for the next round). This makes invalid states
unrepresentable: there is no decision that also carries pending questions, and
no non-decision with nothing to ask. Pydantic discriminates the union natively,
so the schema validates itself and documents itself to the model. Shape is in
[`../glossary.md`](../glossary.md#judge-output-shape).

## Open questions

Unresolved. Each should become an ADR in [`../decisions/`](../decisions/) when
it is settled.

- **Round-limit exhaustion.** What does `hear()` return when `max_rounds` is hit
  without a ruling — a forced verdict, a null result, or an exception? The
  transcript is complete either way, but the caller's contract differs sharply.
- **Advocate isolation.** In round 1, does an advocate see its peers' arguments,
  or only the case and statute? Isolation produces independent arguments;
  visibility produces genuine rebuttal. This changes the character of the output.
- **Cost control.** Rounds multiply tokens by the advocate count. Visibility is
  settled — `ruling.usage` reports what a proceeding spent — but the governor is
  not: whether `max_rounds` is the only one, or a budget can halt a proceeding
  mid-round. PydanticAI already ships `UsageLimits` and `UsageLimitExceeded`, so
  the likely answer is a pass-through rather than something to invent.
