---
status: accepted
updated: 2026-09-04
---

# 0025. The record includes what steered it

## Context

[`0002`](./0002-the-judge-is-a-role.md) states the invariant the audit claim
rests on: *nothing enters an agent's context that is not also in the
transcript.* [`0019`](./0019-the-ledger-is-part-of-the-record.md) restored its
absolute wording by recording tool results, and
[`0021`](./0021-retry-prompts-are-outside-the-invariant.md) then admitted one
exception — `enbanc`'s own retry prompts — on the ground that an invariant known
to be false is worse than a narrower one that is true. `0021` closes by
requiring that no second exception be added.

Writing `../design/prompting.md` found that two were already there, and had been
since before `0021`.

**`guidance` enters an agent's context and no transcript holds it.**
`Judge(guidance="Where the record is ambiguous, deny.")` is a sentence the caller
writes that can decide the proceeding, and a reviewer holding the transcript
cannot see it. The artifact says the judge denied; it does not say the judge was
told to deny when in doubt. That is the exact failure the audit claim exists to
prevent, sitting in the one input `../design/api.md` advertises as a lever.

**The procedural prompt is the same problem at a different scale.** It is
`enbanc`'s own text rather than the caller's, so it does not vary between two
proceedings of the same version — but two proceedings of *different* versions are
not comparable and nothing in either record says so.

Two further facts reach a context with no field behind them.
`../design/prompting.md` tells an advocate the whole verdict set, so it argues
against the bench it actually faces rather than one it invented; the set is a
type parameter and a serialized transcript names only the verdicts that were
used. And the judge is told which deliberation this is and how many the
proceeding allows, which `max_rounds` is and the transcript does not carry.

Whether to tell the judge the round count is a decision in its own right, and it
is what forces the fourth field, so it is settled here rather than separately.

## Decision

**Four standing fields join `Transcript`.**

```python
class Transcript(BaseModel, Generic[VerdictT]):
    question: str
    statute: Statute
    case: SerializeAsAny[Case]
    verdicts: list[VerdictT]                                # new
    max_rounds: int                                         # new
    guidance: dict[VerdictT | Literal["judge"], str] = {}   # new
    procedure: str                                          # new
    entries: list[Entry[VerdictT]] = []
    ledger: list[Retrieval[VerdictT]] = []
    failures: list[ToolFailure[VerdictT]] = []
```

**`guidance` is stored in full**, keyed by participant, holding only those that
were given one. Absence means none was given — unambiguous here, unlike
`usage_by_participant`, where a missing key on a failure means "did not report".

**`procedure` is a prompt-set version, not the prompt text.** It names the whole
prompting surface — both procedural prompts, the turn templates, the tool-result
format, the render format — and `enbanc` bumps it when any of that text changes
and not otherwise. It is deliberately not the package version: two hearings on
`0.1.0` and `0.1.1` stay comparable if no prompt moved. `../design/prompting.md`
owns the version table.

**`verdicts` records the bench.** An advocate is told the whole set and which
value is its own, so the field is what makes that context legal. It also gives a
serialized transcript the verdicts nobody argued to, which the entries alone
never show.

**`max_rounds` records the envelope, and the judge is told where it stands in
it.** Each deliberation turn carries *Deliberation N of M*. The judge is **never**
told anything about the budget.

**With those four, the invariant returns to `0021`'s form**: retry prompts are
the only exception, and `../design/prompting.md` carries the table that traces
every element of every context to the field holding it.

## Consequences

**`0021` stands and is no longer the only qualifier that ought to have been
there.** Its reasoning is what this applies: name the gap or close it, never
leave the invariant true-ish. Of the two options it offers, closing was available
here and was not available for retry prompts, which cannot be recorded without
recording intra-agent churn.

**Cost: the final deliberation is systematically different from the others, and
the record does not flag which one it was.** A judge told *Deliberation 5 of 5*
knows continuing produces nothing, and will rule on a record it might otherwise
have questioned. `Hearing.rounds` and `Transcript.max_rounds` together let a
reviewer see that a ruling landed on the last available deliberation, but nothing
distinguishes a ruling made because the record decided it from one made because
the clock did. This is the sharp edge of the decision.

It is accepted because the alternative is worse in the same direction.
`../design/tribunal.md` makes `Undecided` a real outcome precisely so a hard case
is not disguised as a decided one; a judge blind to the envelope spends its last
deliberation asking a question nobody will answer, and the proceeding reports
`Undecided(reason='rounds')` having thrown away the one round in which it could
have ruled. Both readings are visible to a reviewer only if `max_rounds` is in
the record, which is the field this adds.

**Cost: the budget half stays undisclosed, so the two governors are not
symmetric.** A proceeding can stop on `Undecided(reason='budget')` with a judge
that never knew money was short. That asymmetry is deliberate: spend is measured
between rounds and is not a standing fact, so telling the judge would put a
number in its context that no transcript holds — reopening the hole this ADR
closes — and `0024` already accepts that a budget stops a proceeding coarsely.

**Cost: `guidance` travels.** A transcript now reproduces the caller's steer to
every participant, and `0019` already warned that a transcript is as sensitive as
the most sensitive thing an advocate's tools can reach. Guidance is a second such
thing, and it is one a caller may have thought of as configuration rather than as
content. It is recorded anyway, because a steer invisible in the artifact is
worse than a steer visible in it.

**`guidance`'s participant-keyed union is not the `author` field
`../design/api.md` rejects.** That rejection is about *filings*: a filing
carrying `VerdictT | Literal["judge"]` would make a ruling issued by an advocate
expressible. This is the tribunal's own accounting of who was steered, the same
shape and the same reason as `usage_by_participant` and
`ProceedingFailed.participant`, and it enters no filing.

**Rejected: narrowing the invariant instead.** Restate it as being about *facts*
— the case, the statute, another participant's filing — and call the procedure
and the guidance constitutive, the way a court's rules of procedure are not
evidence. It is a real argument for the procedural prompt and a bad one for
guidance: "where the record is ambiguous, deny" is not a rule of procedure, it is
a thumb on the scale, and a record that cannot show it does not explain its own
ruling. Taking the narrowing for one and not the other is what this decision
does, and the seam it draws is *who wrote it* — the caller's steer is stored, the
library's published text is cited.

**Rejected: storing both procedural prompts verbatim on every transcript.** It
would make an artifact reproducible against a future release with no lookup at
all. Rejected on what it costs the artifact: roughly two pages of identical
library boilerplate in every transcript, repeated per role, in a document whose
whole value is that someone reads it end to end. The version plus a published
changelog answers the same question, and `../design/prompting.md` is where it
resolves.

**Rejected: telling the judge nothing about the envelope.** The cleanest
invariant story and no new field. Rejected because the judge would then be the
only participant unable to see a constraint that decides how its proceeding ends,
and because the failure mode it produces — burning the last deliberation on a
question — degrades exactly the outcome `0011` and `0024` worked to keep
honest.

**Rejected: `procedure` as the package version.** Nothing new to maintain, and it
points at a git tag whose `prompting.md` is authoritative. Rejected because it
changes on every release whether or not a prompt did, so it cannot answer *were
these two hearings judged under the same procedure?* — which is the only question
the field exists for.

**Rejected: `procedure` as a content hash.** Self-verifying, and it would catch a
caller who patched the library. Rejected as opaque: a reviewer holding
`sha256:9f3c…` needs a lookup table `enbanc` does not ship, and the version plus
the changelog is legible without one.

**Consequence: `../design/outcomes.md` and `../design/api.md` both move.** The
schema gains four fields and every worked example that constructs a `Transcript`
gains them too. `../design/prompting.md` is where the fields are spent.
