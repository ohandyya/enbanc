---
status: accepted
updated: 2026-09-11
---

# 0036. A continuance carries at least one interrogatory

## Context

`../design/tribunal.md` already states the rule. Under *Ruling and continuance are
a discriminated union*: "there is no decision that also carries pending questions,
and **no non-decision with nothing to ask**." The first half is unrepresentable —
a `Ruling` has no interrogatory field. The second half was prose only:
`interrogatories: list[Interrogatory[VerdictT]]` admits `[]`.

`../design/degenerate-deliberations.md` parked that as a hole, on the grounds that
answering it changes no type and can wait for the implementation to reach it. The
first is wrong and the second made it urgent. `../design/api.md`'s schemas are the
next thing to be written, so this is a decision now and a change to a shipped
schema later.

What an empty continuance actually does is worse than the placeholder suggests.
`../design/execution.md`'s round loop sets `addressed =
advocates_addressed_by(deliberation)`, so the next round dispatches **zero tasks**
and the judge deliberates again on an empty delta — with no new information, so it
can only repeat itself. The proceeding burns to `Undecided(reason="rounds")` and
the audit artifact ends up holding N identical empty continuances. For a library
whose whole product is a record a reviewer can read, that is the expensive failure,
not the cheap one.

Whether the schema could carry the constraint was not obvious.
[`0030`](./0030-the-retry-budgets.md) established two independent retry budgets and
named an unresolvable `_Exhibit.source` — an **output validator** — as what spends
`output`. A Pydantic constraint on the output *type* is a different path, and
`pydantic-ai 2.36.0` was probed rather than read:

```text
retries={'tools': 5, 'output': 1}  -> 2 attempts, Exceeded maximum output retries (1)
retries={'tools': 1, 'output': 4}  -> 5 attempts, Exceeded maximum output retries (4)
```

Attempts track `output` alone; `tools` is never consulted. `min_length=1` reaches
the model as `minItems: 1` in the output tool's JSON schema, and the retry prompt
carries the Pydantic message verbatim — *List should have at least 1 item after
validation, not 0*. So the model is told the rule before it is corrected for
breaking it.

## Decision

**`interrogatories` carries `min_length=1`, on the judge's emit-shape and on the
public type.**

```python
class _Continuance(BaseModel, Generic[VerdictT]):   # what the judge emits
    kind: Literal["continuance"] = "continuance"
    interrogatories: list[_Interrogatory[VerdictT]] = Field(min_length=1)

class Continuance(BaseModel, Generic[VerdictT]):    # what the record holds
    kind: Literal["continuance"] = "continuance"
    interrogatories: list[Interrogatory[VerdictT]] = Field(min_length=1)
```

**Both, because they are validated at different moments.** The private one is what
the judge's output is checked against during a run. The public one is what a
persisted transcript is checked against when it is read back
([`0006`](./0006-the-transcript-schema.md) makes round-tripping the point of the
`kind` tags), and an invariant that holds only while the proceeding is in memory is
not one the artifact carries.

**An empty emission is a correction, then a failure.** It spends the `output`
budget of 2, and exhausting it is a participant whose output will not validate —
`ProceedingFailed`, which is exactly
[`0011`](./0011-exhaustion-is-an-outcome-failure-is-an-error.md)'s rule and needs
no new case.

**The judge's procedural prompt says so too.** `../design/prompting.md`'s `p1` gains
a sentence: a continuance carries at least one question. The schema is what enforces
it; the prompt is what keeps a well-behaved judge from ever meeting the enforcement.
`p1` is authored but unshipped, so it is edited in place with no changelog row —
the bump discipline at `prompting.md`'s *Procedure versions* protects transcripts
that claim a version, and none exist.

## Consequences

**`../design/api.md` and `../design/tribunal.md` are corrected in the same commit**,
under rule 2. `tribunal.md`'s "no non-decision with nothing to ask" stops being an
aspiration. `api.md`'s note that the questions a judge still wanted answered "are
the interrogatories on the last `Continuance`" is strengthened by it: that list can
no longer be empty, so an `Undecided` always points at something.

**`../design/execution.md`'s zero-task round is unreachable rather than tolerated.**
`advocates_addressed_by()` cannot return an empty set, so the round loop needs no
guard and no branch. This is the cheaper half of the decision: the alternative
required code, and this one deletes the case.

**A ninth claim about `pydantic-ai`, pinned.** The probe above is
`tests/contract/test_output_validation_spends_the_output_budget.py`, alongside the
eight findings `execution.md` already makes. A version bump that moved the budget
attribution would otherwise falsify this ADR's mechanism silently.

**Rejected: tolerate the no-op round.** No schema change, and the degenerate case
self-limits — `max_rounds` is a bound the caller already set, so a judge stuck in a
loop stops eventually with a legitimate `Undecided(reason="rounds")`. It is
rejected on the artifact. A transcript holding four identical empty continuances
does not record a hard case; it records a broken one, and nothing in it
distinguishes the two. The library exists to make that distinction.

**Rejected: read an empty continuance as a stop signal.** Treat it as the judge
saying the record cannot decide the question, and end immediately with an
`Undecided`. It has a real appeal — it is the charitable reading of what a model
emitting `[]` might mean. Rejected twice over: it needs a third `reason` value,
which is a public surface change this decision otherwise avoids entirely, and it
hands the judge a way to end a proceeding that no procedural prompt mentions. A
judge that wants to stop without ruling has no such lever today, deliberately —
`../design/tribunal.md` gives it two moves, rule or continue, and inventing a third
by inference from an empty list is the opposite of the explicit contract the
`Ruling | Continuance` union exists to be.

**Rejected: an output validator instead of a schema constraint.** Equivalent in
effect and it spends the same budget, but it puts the rule in code rather than in
the type, so a persisted transcript read back through the public `Continuance`
would not be checked at all. The constraint is a property of the shape.

**Cost: a judge that insists on an empty continuance ends the proceeding with an
error rather than an outcome.** Three attempts, then `ProceedingFailed`. That is
the right side of `0011`'s line — the tribunal did not finish its own process — but
it is a real ending that a tolerated no-op would have turned into a `Hearing`. It
is also the ending every other malformed output already gets, and a judge that
cannot produce a valid continuance twice in a row is not one whose ruling anybody
should want.

**`../design/degenerate-deliberations.md` is deleted by this ADR and
[`0037`](./0037-a-conceded-advocate-stays-addressable.md) together.** The file held
three holes. This one answers the first, `0037` answers the second, and the third —
two interrogatories to the same advocate in one round — was already answered on the
day the placeholder was written, by
[`0027`](./0027-an-advocate-answers-its-interrogatories-in-order.md), which settled
the dispatch shape, the snapshot, and `since`. `0027` is immutable and cannot record
that it made the bullet moot, so this is where that is recorded.
