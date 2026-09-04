---
status: draft
updated: 2026-09-04
---

# The tribunal

How a decision is actually reached. Vocabulary is defined in
[`../glossary.md`](../glossary.md); the public surface is in
[`api.md`](./api.md), and how advocates gather what they file is in
[`evidence.md`](./evidence.md).

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
exhibits supporting it, gathered through its own tools. It argues **blind** —
the round is a concurrent fan-out and no peer's filing is in view. An advocate
that finds no reasonable case for its verdict **concedes**.

**Deliberation.** The judge reads the record and either rules or issues a
*continuance* carrying **interrogatories**: targeted questions to a chosen
subset of advocates, not a broadcast.

**Round 2+ — interrogation.** Each addressed advocate files a *response*
answering one interrogatory by id, entering new exhibits as needed — now with
the record as it stood when the continuance was filed in view, so it rebuts what
its peers actually filed. Then the judge deliberates again. Repeat.

Interrogatory ids are the tribunal's, not a participant's. The judge emits the
question; the tribunal stamps `r{round}-q{n}` on it when the continuance is
filed, and dispatches one advocate run per interrogatory — so an advocate asked
two questions files two responses, and the link each carries comes from the
dispatch rather than from the model. See
[`api.md`](./api.md#where-ids-come-from) and
[`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md).

A round is the advocates' filings **plus the deliberation that closes it**. So
round 1 is the arguments and the continuance that follows them, and
`max_rounds` counts judge deliberations. It bounds how many times the judge
thinks, not what a round costs — that is the `budget`, below.

**Termination.** A proceeding ends in one of three ways. The judge issues a
**ruling**. Or the envelope the caller set runs out — `max_rounds` deliberations
without a ruling, or a `budget` spent — and the outcome is **undecided**, saying
which of the two it was: recorded and serializable, not an error. Or a
participant **cannot be heard** — its model is
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

**Nothing enters an agent's context that is not also in the transcript**, except
`enbanc`'s own retry prompts — which carry no fact about the case, the statute,
or another participant. Agents accumulate message history across rounds, and
that history is a representation of the transcript — shaped for the provider and
cheap to cache — never a second channel. A framing turn, a reminder, or a summary injected into an agent's
history and nowhere else would silently break the guarantee above: the
transcript would no longer be a complete account of what the ruling was based
on. If one participant should see what another said, it goes in the record.

This is the absolute form [`0002`](../decisions/0002-the-judge-is-a-role.md)
originally stated. [`0006`](../decisions/0006-the-transcript-schema.md) had to
narrow it to *nothing from outside itself*, because an advocate's tool results
reached its context and stopped there unless filed as exhibits — leaving the
record complete as to the ruling but not as to the search.
[`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md) removes that
exception: what a tool returns is recorded verbatim on `Transcript.ledger`.

Two further exceptions went unnamed until
[`prompting.md`](./prompting.md#the-invariant-accounted-for) was written. Your
`guidance` and `enbanc`'s own procedural prompt both reach an agent's context and
neither was in any transcript — and guidance is the one of the two that can decide
a proceeding. Both are closed rather than named:
[`0025`](../decisions/0025-the-record-includes-what-steered-it.md) puts the steer
on `Transcript.guidance` in full and the prompting surface on
`Transcript.procedure` by version, alongside `verdicts` and `max_rounds` for the
two other facts a participant is told. That document's table traces every element
of every context to the field that holds it.

The one exception left is procedural. When a tool times out or an advocate cites
a ledger id that does not resolve, the library puts a retry prompt into that
agent's history — `Timed out after 15.0 seconds.` — and no transcript holds it.
It is named rather than hidden because an invariant listed here that is known to
be false is worse than a narrower one that is true. A retry prompt reports a
mechanical failure of the agent's own last action; it carries no evidence and
nothing another participant said, so it cannot bear on the ruling, and whatever
the agent files in response is in the record. See
[`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md).

**Advocates argue blind and rebut informed.** In round 1 an advocate sees the
question, the statute, the case, its assigned verdict and its guidance — and no
peer filing, because none exists yet: the round fans out concurrently. From
round 2 it sees the record as it stood when the continuance was filed, alongside
the interrogatory addressed to it. Filings only, in both directions — no
advocate reads another's retrievals, and the ledger stays the reviewer's.

An advocate is told **which verdicts the tribunal is deciding among**, from round
1. That is the bench it faces, not a peer's argument; without it an advocate
argues against an opposite it invented, and `Transcript.verdicts` is what keeps
the fact in the record. And from round 2 it reads the **whole** continuance,
including the questions put to its peers. *Targeted* is a duty about who must
answer — the procedural prompt says so in those terms — not a rule about who may
read, and seeing what the judge is asking elsewhere is what lets a rebuttal meet
the case rather than a paraphrase of it. Both are rendered by
[`prompting.md`](./prompting.md#the-turns).

Each half is for something different. Round 1 is where the transcript records
the strongest *independent* case for every verdict; peer text in context would
anchor a model onto its opponent's framing and turn a concession into a reaction
to rhetoric rather than a finding about the facts. Rounds 2+ are where
confrontation belongs, and the judge already controls it — it chooses who is
asked and what. Letting the record supply what was *said* is what keeps a
tool-less judge from becoming an evidence-summarizer, restating exhibits it
cannot re-fetch.

The ordering is this way round because contamination only runs one way: an
isolated round 1 can have rebuttal added to it later, and a contaminated one can
never be recovered. See
[`0023`](../decisions/0023-advocates-argue-blind-and-rebut-informed.md).

**The record is complete as to the search as well as the ruling.** `entries` say
what the ruling rests on; the ledger says what was available to rest on. An
advocate that pulls damaging evidence and declines to file it leaves a trace —
the retrieval is recorded and no exhibit cites it — which is the cost `0006`
accepted and `0019` reverses. The judge still sees only filings: the ledger is
written for the reviewer, not for the proceeding.

**Advocate tools are read-only.** An adjudication must never mutate the world it
is reasoning about: a proceeding that changed the facts it was weighing would
produce a record that no longer describes the thing decided. `enbanc` enforces
this where it can — it ships no tool that writes, the judge has no tools at all,
and the library itself has no mutation path — but a tool you pass is your code,
and a function cannot be inspected for side effects. **Read-only is a contract
you keep, not one `enbanc` checks**, and saying otherwise would be a guarantee
the library cannot honor. See
[`0017`](../decisions/0017-read-only-is-a-contract.md).

**A filed exhibit carries a reference the tribunal stamped.** An advocate cites
a source its tools actually returned and writes the excerpt it relies on; the
tribunal fills in where that evidence came from. So a reviewer reading the
record can follow any exhibit back to the document, row, or page behind it, and
an advocate cannot cite something no tool produced. This is what makes the
transcript checkable rather than merely complete — the audit claim above is
otherwise only as good as the models' honesty about their own sources. See
[`evidence.md`](./evidence.md) and
[`0016`](../decisions/0016-exhibits-are-stamped-citations.md).

The three parts answer different questions, and an audit needs all of them. A
stamped reference answers *is this exhibit real?*; the ledger answers *what was
left out?*; `Transcript.failures` answers *what did an advocate try to get and
not get?* No one of them is enough — a proceeding can cite honestly, argue from
a third of what it found, and file thinly because its best source was down, and
the first two would show only the middle failing.

**Concession is a first-class outcome, not a failure.** An advocate that
concedes has done its job well. Treating concession as an error would pressure
advocates into manufacturing arguments for indefensible positions — exactly the
failure mode the adversarial structure exists to prevent. It is a round-1
filing: an advocate persuaded by the record it reads in a later round says so in
its response, which is what the interrogatory asked for.

**An advocate can be degraded without being lost, and the record says so.** A
tool that raises ends the proceeding under the rule below; a tool that times out
does not — the advocate is told, adapts, and files what it can
([`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md)). That is a third
state between *heard* and *not heard*, and without a trace it would make a
blocked advocate read as a lazy one. Each failed call is recorded on
`Transcript.failures`
([`0022`](../decisions/0022-tool-failures-are-recorded.md)). `enbanc` does not
act on it: whether a gap should have changed the ruling is the reviewer's
judgment, not the library's.

**A tribunal that loses a participant does not rule.** One advocate's model
failing ends the proceeding, even when the judge and the remaining advocates are
healthy, and the peers still in flight are cancelled where they stand rather
than drained ([`0012`](../decisions/0012-a-failure-cancels-the-round.md)).
Deliberating on what is left would produce a decision reached because the
opposing advocate was knocked offline rather than answered — and nothing in that
ruling would distinguish it from one reached on a full bench. This is the
counterpart to concession being first-class: an advocate that declines to argue
has done its job, and an advocate that could not argue has not been heard at
all. The two must never be recorded as the same thing.

**A proceeding stops inside the envelope it was given, and the record says which
half ran out.** `max_rounds` bounds deliberations. The optional `budget` —
PydanticAI's `UsageLimits`, carrying a cost, token, or request ceiling — bounds
what the whole proceeding spends, checked between rounds against the running
total `enbanc` already keeps per participant. Both are limits the caller
declared, so reaching either is an ordinary end rather than a failure: the
outcome is `Undecided`, and its `reason` says whether the rounds or the money
ran out. A reviewer must never have to guess whether a hard case was hard or
merely expensive.

**The judge is told which deliberation this is and how many the proceeding
allows, and is told nothing about the budget.** Both halves are deliberate. The
round count is two facts the record already holds — the round from `entries`, the
limit from `Transcript.max_rounds` — so disclosing it opens no hole in the
invariant, and a judge blind to it spends its last deliberation asking a question
nobody will answer. Spend is not a standing fact: it is measured between rounds,
no transcript carries it, and a judge that knew money was short would rule for a
reason the record could never show. The cost of disclosing the first half — a
final deliberation that is systematically different from the others, with nothing
marking which one it was — is stated in
[`0025`](../decisions/0025-the-record-includes-what-steered-it.md).

Checking between rounds rather than mid-run is what makes that true. A budget
enforced inside an advocate's run would stop with a round half-filed and nothing
adjudicated — the tribunal would not have finished its own process, which is the
exception side of `0011`'s line. Stopping at a round boundary lands on the same
seam `max_rounds` lands on, with whole rounds behind it. The price is a coarse
governor: a proceeding stops within one round of its budget, not before crossing
it.

`max_concurrency` is a second lever rather than the same one in different units.
It bounds how many advocates run at once — a provider's rate limit, not the
caller's wallet — and a twelve-verdict tribunal meets that limit in round 1
however much it is allowed to spend. `enbanc` passes no usage limit into an
individual run, so PydanticAI's own default is the only per-run bound, and a run
that exhausts it is a participant that could not be heard. See
[`0024`](../decisions/0024-a-budget-stops-the-proceeding-between-rounds.md).

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

*None open.* Settling one was three moves in a single commit: the answer into
the prose above, an ADR in [`../decisions/`](../decisions/), and then the bullet
left this list. See rule 7 in [`../../CLAUDE.md`](../../CLAUDE.md).
