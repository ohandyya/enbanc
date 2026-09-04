---
status: accepted
updated: 2026-09-04
---

# 0023. Advocates argue blind and rebut informed

## Context

[`../design/tribunal.md`](../design/tribunal.md) carried this as its first open
question: in round 1, does an advocate see its peers' arguments, or only the
case and statute? It was the last unsettled thing that changes what the system
*produces* rather than the shape of a type, and
[`../progress.md`](../progress.md) named it next.

Nothing already decided forces an answer. The invariant from
[`0002`](./0002-the-judge-is-a-role.md) — nothing enters an agent's context that
is not also in the transcript — is the first rule one reaches for and it decides
nothing here: a peer's argument *is* in the transcript, so showing it is
permitted, and showing nothing is trivially permitted. The schemas are
indifferent too. `Argument` names its advocate, `Response` cites an
interrogatory id, and neither changes under either answer. That is why the
question outlasted the twenty-two decisions around it.

Round 1 has a structural wrinkle the question as filed did not name. Advocates
fan out concurrently — [`0012`](./0012-a-failure-cancels-the-round.md) is built
on it throughout — so at the moment a round-1 advocate runs, no peer argument
exists. Visibility in round 1 is therefore not a context-assembly choice; it
forces either sequencing the advocates or splitting the round into two phases.

The question was also narrower than the decision it forces. What a proceeding
produces depends on the rule for every round, not just the first.

## Decision

**An advocate argues blind and rebuts informed.**

**In round 1 an advocate sees no peer filing.** Its context is the question, the
statute, the case, its assigned verdict, its guidance, and its own tool traffic.
Round 1 stays a concurrent fan-out, unchanged from what `0012` assumes.

**From round 2 an advocate sees the record as it stood when the continuance was
filed**, alongside the interrogatory addressed to it. It answers with the
opposing exhibits in front of it rather than with the judge's paraphrase of
them.

**Filings only, in both directions.** An advocate never reads another's
retrievals. The ledger remains what [`0019`](./0019-the-ledger-is-part-of-the-record.md)
made it — written for the reviewer, not for the proceeding — and the judge's
own sight is unchanged.

**Concession stays a round-1 filing.** An advocate persuaded by the record it
reads in a later round says so in its response, which is what the interrogatory
asked for. Nothing in the filing set or the response contract moves.

**This is a rule, not a knob.** There is no `visibility=` on `Tribunal` or
`Advocate`, for the reason [`0011`](./0011-exhaustion-is-an-outcome-failure-is-an-error.md)
rejected `on_absence` and `0012` rejected `on_peer_failure`: two behaviours with
different guarantees, both documented by the library and neither promised by it.

## Consequences

**Contamination runs one way, and that is the load-bearing reason.** An isolated
round 1 can have rebuttal added to it later; a contaminated one can never be
recovered. Where nothing forces the answer, the option that keeps the other one
reachable wins.

**The transcript keeps a readable round 1.** A reviewer can read it as *the
strongest independent case for each verdict*, and what follows as what survived
contact. That reading is the defensibility claim `../design/tribunal.md` opens
with, stated at the level of a single round.

**Concession stays a finding about the facts.** Peer text in a round-1 context
would anchor a model onto its opponent's framing, and an advocate that folded
after reading a strong argument would file a `Concession` the record could not
distinguish from one meaning no reasonable case exists. `../design/tribunal.md`
makes concession first-class specifically to avoid manufactured arguments; it
should not acquire a second, contaminated sense.

**The judge does not become an evidence-summarizer.** It is tool-less by
[`0002`](./0002-the-judge-is-a-role.md) and cannot re-fetch anything, so under
strict isolation the only route from one advocate's exhibit to another's context
is the judge restating it in the interrogatory text — paraphrase drift into the
one artifact meant to be verbatim. Letting the record carry the content keeps
the judge choosing *who is asked and what*, which is all
[`0015`](./0015-interrogatory-ids-are-stamped-on-filing.md) ever meant by
targeted.

**Cost: later rounds carry more context than earlier ones.** An advocate's
round-*N* context grows with what its peers filed, so spend per advocate rises
across a proceeding rather than staying flat. `hearing.usage_by_participant`
([`0014`](./0014-usage-is-broken-down-per-participant.md)) is where that shows
up. It does not change the open cost-control question in
`../design/tribunal.md`: `max_rounds` still counts deliberations, and fan-out
width is still the same unsettled lever.

**Cost: an advocate given the record may volley at a peer instead of answering.**
Bounded, not eliminated, by `Response` citing exactly one interrogatory id and
by the procedural prompt `enbanc` owns. Round 1 is unaffected, so the fallback
position — the isolated independent case — is in the record regardless.

**Rejected: strict isolation in every round.** The cheapest context, the fullest
parallelism, and the most literal reading of interrogatories being targeted
rather than broadcast. Rejected on what it does to rebuttal: an advocate asked
whether documented income supports a DTI claim, with no sight of what the
opposing advocate actually filed, is answering a question stripped of its
context, and the only fix routes every exhibit through the judge's prose. That
trades a real capability for a saving the design does not need — round 1, where
isolation earns its keep, is identical either way.

**Rejected: visibility in round 1 by sequencing the advocates.** Real rebuttal
immediately, with no extra round. But whoever runs last gets the last word, so
the declaration order of the verdict enum becomes semantically load-bearing —
a Python detail no reviewer of the transcript can see. It also turns round 1
from a fan-out into a chain, which costs O(*n*) latency and forces `0012` to be
restated: "a failure catches its siblings mid-run" becomes "the chain stops
here", and two transcripts of the same case under different orderings stop being
comparable.

**Rejected: a two-phase round 1 — argue in parallel, then rebut in parallel.**
Symmetric, concurrent, no ordering artifact, and genuine confrontation before
the first deliberation. It was the strongest of the rejected options. It loses
on what it costs the rest of the design: a sixth filing type against a set
[`0006`](./0006-the-transcript-schema.md) closed at five, roughly double the
spend in round 1, and a rebuttal phase that `max_rounds` does not count — since
that limit counts deliberations — which quietly widens the one governor the
proceeding has while cost control is still open. It also duplicates the
interrogatory mechanism: the judge's continuance already produces exactly the
round where confrontation belongs, chosen rather than automatic.

**Rejected: showing an advocate its peers' ledger entries.** It would let one
advocate surface what another buried, which is the gap `0019` describes where
tools are per-advocate. But `0019` settled that the ledger answers the
*reviewer's* question, and routing it into a participant's context would make
unfiled tool output bear on the ruling — reversing `0006`'s line about what the
judge decides on, from the side it was never argued from.

**Consequence: the last behavioural question is closed.** What remains open in
`../design/tribunal.md` is cost control, which is about what a proceeding may
spend rather than what it produces.
