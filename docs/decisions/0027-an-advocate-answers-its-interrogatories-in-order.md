---
status: accepted
updated: 2026-09-04
---

# 0027. An advocate answers its interrogatories in order

## Context

The judge's procedural prompt permits it explicitly — *"You may put more than one
question to the same advocate"* — and
[`0015`](./0015-interrogatory-ids-are-stamped-on-filing.md) settled that the
tribunal dispatches **one advocate run per interrogatory**, which is what lets it
stamp `Response.answering` from the dispatch rather than asking the model to
write a link.

So an advocate asked two questions runs twice in the same round.
`../design/prompting.md` opened this as its only open question, framed as a
rendering problem: both runs would get the same delta, differing only in
`## Addressed to you`, so the second could not see the first's answer and might
contradict it inside one round.

That framing understated it. Running the two concurrently breaks two things other
documents already rest on.

**A participant's message history forks.** Two concurrent runs of one agent both
read that participant's history and both write it back; one clobbers the other,
and round 3 carries one of the two round-2 answers with the other silently gone.
A conversation is linear, and `../design/execution.md` records that carrying one
across rounds is `message_history` plus a dict — a shape that has no meaning for
two simultaneous runs of the same participant.

**Ledger ids stop being deterministic.**
[`0016`](./0016-exhibits-are-stamped-citations.md) numbers sources per advocate,
and `../design/evidence.md` justifies that with an explicit premise: *"an
advocate's tool calls are sequential, while one counter shared across advocates
running concurrently would number the same proceeding differently on every run."*
Two concurrent runs of the same advocate falsify the premise and reintroduce
exactly the nondeterminism per-advocate numbering exists to remove.

## Decision

**An advocate's interrogatories are answered sequentially, in interrogatory-id
order, one run each.**

**The fan-out is across addressed advocates.** Round *N* dispatches one concurrent
task per advocate the continuance addressed. An advocate's own questions are a
queue inside its task, so cross-advocate concurrency — which
[`0012`](./0012-a-failure-cancels-the-round.md) and `max_concurrency` are both
built on — is untouched.

**Each run files before the next is dispatched.**

**The second run's snapshot is the continuance snapshot plus that advocate's own
responses already filed in this round**, and nothing else from the round. A peer's
concurrently filed response stays out.

**Its delta is that response alone.** `since` advances once per run rather than
once per round, so the second run does not re-read the record its own history
already carries — but it does see its just-filed response in **stamped** form,
because what it emitted was a bare ledger id and an excerpt and what entered the
record has the tool and the reference beside it.

`0015` is unchanged: one run per interrogatory, one response per run, the link
stamped from the dispatch.

## Consequences

**Nothing in the record moves.** No schema, no filing type, no output type, and no
new field. This is a dispatch-ordering rule and a `since` rule; it is the only one
of the options considered that costs no public surface at all.

**Two answers from one advocate in one round can no longer contradict each
other**, because the second is written with the first in front of it. That was the
question as filed, and it is the smallest of the three things fixed.

**`../design/evidence.md`'s determinism premise stays true as written.** An
advocate's tool calls remain sequential across its whole proceeding, so its ledger
ids are reproducible run to run. The premise is now load-bearing for a dispatch
decision as well as a numbering one, and `evidence.md` says so.

**Cost: a round takes as long as its most-questioned advocate.** Round latency
becomes `max(questions addressed to one advocate) × run time` rather than one run
time. A round in which every advocate gets one question — the common case — is
exactly as fast as before. The cost is proportionate: the judge asked for more
work from that advocate, and gets it serially.

**`0023`'s objection to sequencing does not reach this.** It rejected giving round
1 peer visibility by sequencing the advocates, because *"the declaration order of
the verdict enum becomes semantically load-bearing — a Python detail no reviewer
of the transcript can see."* That is an objection to an **invisible** ordering.
Here the order is the judge's own interrogatory order, stamped `r1-q1`, `r1-q2`
and sitting in the record, so a reviewer can see precisely why one was answered
first. `0023` also protected round 1's concurrent fan-out, and this changes
nothing about round 1 or about concurrency between advocates.

**Rejected: keep both runs concurrent with isolated histories.** Branch each run
from the advocate's round-1 history. It does not work: two forks cannot be merged
back into one linear conversation, so round 3 either drops a branch or abandons
history for that advocate entirely — and the ledger ids stay nondeterministic
regardless. It solves the stated problem and neither real one.

**Rejected: one run per advocate per round answering every question.** The
cheapest option in tokens — one run, one cached prefix, and answers made
consistent in a single act of reasoning. Rejected on blast radius: it overturns
`0015`'s dispatch rule, changes the advocate's output type to an ordered list, and
introduces a "the list must have exactly *N* entries" validation failure that did
not exist. Matching answers to questions by position also makes the link a
property of ordering rather than of dispatch, which is weaker than what `0015`
bought.

**Rejected: forbid more than one interrogatory per advocate per round.** The
simplest rule, and it removes a capability `0015` and the judge's own prompt both
grant. Enforcing it needs a retry loop when the judge does it anyway, spending the
`Agent(retries=...)` budget on a well-formed continuance; and the alternative —
merging two questions into one — is closed by `0015`'s "nothing the judge wrote is
altered".

**Consequence: `../design/execution.md`'s piece 3 gains a constraint.** The
task-group shape is now fixed at one task per addressed advocate with a sequential
queue inside it, rather than one task per interrogatory. That document is still
unwritten; this is a boundary it must respect.
