---
status: accepted
updated: 2026-09-11
---

# 0037. A conceded advocate stays addressable, and a concession is revisable

## Context

`../design/tribunal.md` says concession is a first-class outcome and that "an
advocate persuaded by the record it reads in a later round says so in its
response". That is the *forward* direction — argue in round 1, concede in round 3.
The reverse was never ruled on: an advocate that concedes in round 1, and an
interrogatory addressed to it in round 2.

`../design/degenerate-deliberations.md` parked it as two questions in one. Is a
conceded advocate still addressable, and is a concession revisable? Nothing in
`../design/api.md` forbids either — `Interrogatory.to` is a `VerdictT`, and every
verdict has a seated advocate — so the schemas permit it and no document rules on
it.

Both halves matter for the same reason. An advocate concedes on the record it
built alone: round 1 is blind
([`0023`](./0023-advocates-argue-blind-and-rebut-informed.md)), so a round-1
concession is a finding about the facts that advocate could reach by itself. By
round 3 a peer may have filed an exhibit that bears directly on it. If the judge
cannot ask, or if the advocate cannot answer that the case is now arguable, the
proceeding rules against a finding the record has already undermined — and the
transcript will not show why, because the question was never put.

The judge's own procedural prompt already leans the other way: a concession "is
evidence about the verdict it was seated for". Evidence is a thing a judge is
entitled to probe.

## Decision

**An advocate that conceded stays seated and stays addressable.** The judge may
put an interrogatory to it like any other advocate. Nothing validates `to` against
what that advocate filed.

**A concession is revisable.** The response to such an interrogatory may maintain
the concession, or argue the assigned verdict afresh on evidence that has entered
the record since. Both are ordinary `Response` filings.

**Nothing in the record is marked superseded.** There is no `withdrawn` flag, no
retraction filing, and no sixth `kind`. The transcript is append-only and ordered:
a `Concession` in round 1 followed by a `Response` with exhibits in round 3 is a
complete account of an advocate that changed its mind and why, and a reviewer
reads the two in order. A flag would be a second place that can disagree with the
entries — the same store-it-twice mistake that keeps `position` off `Argument` and
the round count off `Ruling`.

**Both procedural prompts say so.** The advocate's gains the case it did not
cover — you conceded, and a question is now addressed to you. The judge's gains
the fact that a conceded advocate is still seated. `p1` is edited in place with no
changelog row, for the reason [`0036`](./0036-a-continuance-carries-at-least-one-interrogatory.md)
gives: it is authored but unshipped, and no transcript claims it yet.

## Consequences

**No type changes, and no code.** This is the rare answer that is entirely prose:
a sentence in `../design/tribunal.md`, a qualification in `../glossary.md`, and two
prompt sentences. The dispatch already works — a conceded advocate has an agent, a
message history, and a `Ledgering` toolset that lived the whole proceeding
([`../design/execution.md`](../design/execution.md)'s piece 2), so a round-3 response
from it can even cite a round-1 find. Nothing had to be built to make this legal;
it only had to be decided.

**`0023` is extended, not disturbed.** Its concern was a concession that reacts to
rhetoric rather than to facts, which is exactly why round 1 is blind — and it puts
confrontation in rounds 2 and after, where the judge controls who is asked and
what. A revival in round 3 is the judge's own doing, on a record it chose to
develop. `0023`'s "concession stays a round-1 filing" is untouched: `Concession` is
still the only filing type an advocate may open with, and a later change of
position is a `Response`, not a second `Concession`.

**`../glossary.md`'s *Concession* row is corrected in the same commit**, under
rule 2. "A first-class outcome, not a failure, and a round-1 filing" is true of the
filing and misleading about the advocate, which is now not finished when it files
one.

**An advocate can contradict itself across rounds, visibly.** That is the accepted
cost, and it is smaller than it looks. The contradiction is in the record with both
halves dated and the intervening evidence between them, which is the form in which
a change of position is *informative*. The failure this design fears is the
invisible one — a concession that quietly stops mattering, or a verdict reached
because nobody asked.

**Rejected: addressable, but the concession is final.** The judge may probe why an
advocate conceded; the advocate may not resume arguing. It keeps a concession
meaning one thing and removes any flip-flopping from the record. Rejected because
it is unenforceable and incoherent together: nothing in the schema distinguishes a
`Response` that explains a concession from one that argues the verdict, so the rule
could only live in the prompt — and a model told both "give the strongest honest
case for your verdict" and "you may not, you conceded" is being asked to suppress a
finding the record now supports. `../design/tribunal.md` already refuses the
symmetric version of this: manufacturing a case for an indefensible position
damages the record, and so does withholding one for a defensible one.

**Rejected: a conceded advocate is not addressable.** A concession ends that
advocate's participation, enforced by an output validator checking
`Interrogatory.to` against the transcript. Rejected on three counts. It spends the
`output` budget — the one guarding citation integrity and the
`Ruling | Continuance` contract ([`0030`](./0030-the-retry-budgets.md)) — to
correct a judge that did something reasonable. It is the first stateful constraint
on the judge's output, where every other check is a property of the shape alone.
And it removes a legitimate judicial act to prevent an untidy record, which is the
wrong trade for a library whose product is the record.

**Rejected: a `withdrawal` filing type.** A sixth `kind` making the revision
explicit and machine-readable. It is the tempting one, because "this advocate is no
longer conceding" becomes a fact a tool can query rather than something a reader
infers. Rejected because it adds a public type, a `Filing` union member, a
transcript `kind`, and a rendering rule — to encode something two existing entries
already say in order. `../design/api.md` has exactly five filings because there are
exactly five things a participant does, and changing your mind is not a sixth: it
is the thing you file next.
