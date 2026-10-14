---
status: accepted
updated: 2026-10-14
---

# 0043. Filings carry a confidence

## Context

An advocate's argument says what it claims and cites what supports it. It does
not say how strong the advocate thinks that claim is, so the judge cannot tell a
strong claim from one that was only made. A `Ruling` says what was decided and
why. It does not say how sure the judge is, so a caller has nothing to act on
when deciding whether to rely on the ruling or send the case to a person.

Both gaps have the same fix, a number from the filing's author. But a seat in an
adversarial proceeding pulls that number one way: an advocate is told to argue
its verdict as well as it can be argued, and asking the same advocate how
strong its case is invites the answer *very*.

## Decision

**`Argument`, `Response` and `Ruling` gain a required
`confidence: float = Field(ge=0, le=1)`**, the last field on each, so a model
writes its case before it scores it.

- **An advocate's confidence is how strongly the record supports the verdict it
  was assigned**, not how sure it is of the filing. The two readings differ on a
  response that concedes again, which scores low under this one. So the number
  means one thing on every advocate filing, and that thing is what the judge
  needs.
- **The judge's is its estimate that its verdict is correct on this record.**
- **`Concession` and `Continuance` carry none.** A concession already says no
  reasonable case exists, so a number could only repeat that or contradict it. A
  continuance decides nothing.

**The meaning lives in the procedural prompts, and the schema carries only the
bounds.** A `Field(description=…)` would be prompt text that
[`prompting.md`](../design/prompting.md) does not own and `Transcript.procedure`
does not version, the same reason the output functions carry no docstring. A
value outside `[0, 1]` is a retry against the `output` budget.

**Both prompts address the incentive directly.** The advocate's says a
proceeding exists for the best ruling the record can support, not for any
advocate's win. It says the confidence is a candid estimate kept apart from the
advocacy, and that an overstated one misleads the judge exactly as a
manufactured case does. The judge's says an advocate's confidence is a party's
own estimate, to be tested against the exhibits rather than adopted, and that
its own confidence is read by whoever acts on the ruling.

**It renders in the filing's header line**: `argued (confidence 0.7):`. Every
view renders the same header, so the judge reads an advocate's confidence
through the existing projection and the invariant needs no new row.

**`p1` is amended rather than bumped**, for
[`0042`](./0042-a-retrieval-names-its-call.md)'s reason: `0.1.0` has not
shipped, so no transcript outside development claims `p1`.

## Consequences

- The judge can weigh how strongly each advocate holds its case, and a caller
  can route a low-confidence ruling to a human.
- **The number is a model's self-report, not a calibrated probability**, and
  [`api.md`](../design/api.md#the-judges-output) says so. `enbanc` does not
  measure it against outcomes and sets no threshold. A caller that treats `0.8`
  as an 80% chance of being right is reading more into it than anything
  guarantees.
- The prompts can lower an advocate's pull toward a high number, but they can't
  remove it. The judge is told why it should not take the number at face value.
  The record keeps every advocate's confidence beside its exhibits, so a
  reviewer can see when one was inflated.
- The field is required, with no default. A transcript serialized before this
  change no longer validates. None exists outside development, and a default
  would make a filing with no stated confidence look like one with a stated
  value.
- An advocate's response is built from `respond()`'s signature rather than from
  `_Response` ([`0039`](./0039-a-response-is-asked-for-its-answer-alone.md)), so
  the bounds are declared twice: on the model and on that parameter.

## Alternatives considered

- **Confidence in the filing itself.** Ambiguous on a response that concedes
  again, where high confidence would mean the opposite of high confidence on an
  argument.
- **A confidence on `Concession` too, for uniformity.** It is either near 0,
  which repeats the concession, or not near 0, which contradicts it.
- **Describing the field in the schema.** It would reach the model as unversioned
  prompt text, outside `Transcript.procedure`.
- **A categorical scale (`low` / `medium` / `high`).** Easier for a model to
  produce consistently, but the request was a number a caller can threshold, and
  a three-step scale gives up the resolution that thresholding depends on.
- **Judge-only confidence.** It covers the caller and leaves the judge unable to
  tell a strong claim from one that was only made, which was half the reason
  for the change.
