---
status: accepted
updated: 2026-09-02
---

# 0014. Usage is broken down per participant

## Context

[`0002`](./0002-the-judge-is-a-role.md) settled that `hear()` reports usage at
all, and settled it as an aggregate: one `pydantic_ai.usage.RunUsage` summed
across the judge and every advocate. The reason it is on the result rather than
in the record is stated there — usage is "the one thing a proceeding produces
that the transcript does not contain."

`api.md` carried the follow-on question ever since: whether that aggregate is
ever split by who spent it. Two things kept it open.

The pull is that the model is configured **per agent**.
[`0003`](./0003-models-and-guidance-are-injected.md) makes `Judge(model=...)`
and `Advocate(model=...)` overrides of the tribunal's default, and `api.md`
advertises a strong judge over cheap advocates as a one-line change. The
aggregate cannot say whether that trade paid. The judge re-reads the whole
record at every deliberation while each advocate sees less of it, and there are
*n* advocates; which side dominates is not knowable a priori. Comparing
aggregates across two proceedings does not settle it either, because the case
and the round count move at the same time.

The push-back is this design's standing rule that a fact lives in one place —
the rule that kept `position` off `Argument` and `rounds` off
`ProceedingFailed`. A total and a breakdown are the same fact twice.

There is also a shape hazard. `VerdictT | Literal["judge"]` was rejected for
filings and accepted for `ProceedingFailed.participant`
([`0011`](./0011-exhaustion-is-an-outcome-failure-is-an-error.md)), the line
being whether the thing is part of the record. Usage is not. But as a **dict
key** that union has a failure the exception field does not: verdicts are a
`StrEnum` ([`0004`](./0004-verdicts-are-a-strenum.md)), so a member
`JUDGE = "judge"` compares equal to and hashes with the judge's key, and two
participants collapse into one entry without a word.

Nothing is implemented, so this is settled on the surface rather than found by
building.

## Decision

**`Hearing` carries a per-participant breakdown, and `ProceedingFailed` carries
the same field.** `usage_by_participant: dict[VerdictT | Literal["judge"], RunUsage]`
— one entry per advocate, one for the judge under `"judge"`.

**The mapping is the stored fact; `usage` is its sum.** `RunUsage` supports
addition, so the aggregate is computed from the breakdown rather than
accumulated alongside it. This is what answers the store-it-twice objection:
there is one place the numbers come from, and no second place to disagree with
it. `usage` stays as a field because "what did this cost?" is the common
question and should not require a fold.

**A value is a participant's whole proceeding.** Every run that participant made,
across every round, summed. Not per round.

**On a `Hearing`, every participant has an entry.** Round 1 fans out to every
advocate, so each one ran even if it conceded; a `Hearing` exists only if the
judge deliberated at least once. There are no zero-valued entries and no missing
keys.

**On a `ProceedingFailed`, keys may be missing.** A run that was cancelled or
died before reporting contributes nothing, so absence means "did not report",
never "spent nothing". This is `0012`'s floor-not-a-total caveat applied to the
breakdown, and it is why the completeness guarantee above is stated of a
`Hearing` only.

**`"judge"` is a reserved verdict value.** `Tribunal(...)` raises
`ConfigurationError` at construction if any member of the verdict enum has the
value `"judge"`, alongside the existing checks for a missing or unknown key in
`advocates`.

## Consequences

**The advertised per-agent model override becomes measurable from the return
value.** `hearing.usage_by_participant["judge"].cost` against the advocates' is
the number that decides whether a stronger judge is worth it, and it takes one
proceeding rather than a controlled comparison of two.

**An unpriced participant stops hiding.** Adding `RunUsage`s treats a `None`
cost as zero, so an aggregate mixing priced and unpriceable runs reports the sum
of the priced ones and looks complete. `api.md` already warns that `cost is
None` means unpriceable rather than free; the breakdown is the first place that
warning can actually be acted on, because it names which participant had no
price.

**A verdict may not be called `judge`.** A real, if narrow, restriction on the
caller's enum — `JUDGE = "judge"` as a verdict value is now a construction-time
error. Rejecting it loudly is the point: the alternative is a mapping that
silently attributes an advocate's spend to the judge. The check also removes the
same ambiguity from `ProceedingFailed.participant`, which had it already and had
been living with it.

**Rejected: no breakdown, and the question closed.** The argument was that
attribution is observability — PydanticAI's instrumentation already attributes
spend per run, so `enbanc` surfacing a field reinvents what the ecosystem has,
in the same spirit as "no usage type of its own" and "no model-string parser".
It loses because the parts must already exist to compute the sum: the library
does the attribution either way and was discarding the result. Making the caller
stand up OTel to recover a number the return value was holding is not
minimalism, and `0002`'s own reason for surfacing usage — it is the fact the
transcript cannot carry — does not stop at the total.

**Rejected: a `UsageBreakdown` type with `judge`, `advocates`, and a computed
`total`.** Structurally immune to the key collision, since the judge is a field
rather than a key, and it mirrors the real asymmetry of one judge and one
advocate per verdict. It loses to a two-line construction check that buys the
same safety: the type is a third public name for one fact, it changes the shape
of `hearing.usage` that `README.md` and `outcomes.md` already show, and it
splits "who spent what" across two access paths.

**Rejected: per participant per round.** The finest grain, and the one that
would show cost growing as the record lengthens. That is a cost-*control*
question, and the governor — whether `max_rounds` is the only one, or a
`UsageLimits` pass-through can halt a proceeding mid-round — is still open in
`tribunal.md`. Settling attribution should not pre-empt it, and a nested mapping
is the largest surface of the four options.

**Cost: a second usage field on two public types**, and an invariant the
implementation has to hold — the aggregate must be the sum of the mapping, in
both the `Hearing` path and the failure path. That is enforceable in one place
if both are constructed from the mapping, and it is a bug the moment they are
not.
