---
status: current
pr: 34
updated: 2026-10-14
---

# Confidence on what is argued and what is ruled

**Every argument, response and ruling says how strongly its author holds it.**
Today, nothing in an advocate's filing tells the judge whether a claim is strong
or merely made. Nothing in a ruling tells the caller whether to act on it or
send it to a human. A `confidence` in `[0, 1]` on the three filings that take a
position addresses both.

## Scope

**Three filings gain a required `confidence: float`, constrained to `0 ≤ c ≤ 1`.**

- **`Argument` and `Response`:** the advocate's estimate of how strongly the
  record supports *the verdict it was assigned*. This is not its confidence in
  the filing. The two readings differ on a response that concedes again:
  "the record still does not support my verdict" scores low, the same as a
  weak argument. That gives the number one meaning on every advocate filing, and
  it is the meaning the judge needs.
- **`Ruling`:** the judge's estimate that its verdict is correct on this record.
- **`Concession` and `Continuance` carry none.** A concession already says no
  reasonable case exists, so a number on it would either repeat that or
  contradict it. A continuance decides nothing, so there is nothing to be
  confident about.

The field sits last on each shape, after the claim, answer or reasoning, so the
model writes its case before it scores it. It is required with no default, as
`Retrieval.call` was in
[`0042`](../decisions/0042-a-retrieval-names-its-call.md). A transcript
serialized before this change no longer validates, and none exists outside
development.

**The number is self-reported, and both prompts say so.** The advocate's prompt
says the goal of a proceeding is the best ruling possible, not a win for any
advocate. It says the confidence is a candid estimate kept apart from the
advocacy, and that overstating it damages the record the same way manufacturing
a case does. The judge's prompt adds confidence to the paragraph that already
weighs a stamped reference against a selective excerpt: an advocate's confidence
is its own claim, made by a party to the case. `api.md` and both guides say
plainly that a ruling's confidence is a model's self-report, not a calibrated
probability.

**The meaning lives in the procedural prompts, not in the schema.** No
`Field(description=…)`, for the same reason the output functions carry no
docstring: a description is prompt text that `prompting.md` does not own and
`Transcript.procedure` would not version. The schema carries only the bounds,
as `minimum` and `maximum`. A value outside them is a retry against the
**`output`** budget.

**It renders in the filing's header line:** `[round 1] approve argued
(confidence 0.85):`, `… responded to r1-q1 (confidence 0.4):`, and `the judge
ruled — deny (confidence 0.7):`. Every view shows the same bytes, so the judge
reads an advocate's confidence through the existing projection, with no new
channel.

**`p1` is amended rather than bumped**, under the same reasoning as `0042`:
`0.1.0` has not shipped, so no transcript outside development claims `p1`.
[`0043`](../decisions/0043-filings-carry-a-confidence.md) records the decision.

**Not in this PR.** There's no confidence accessor on `Hearing`: a caller reads
`ruling.confidence`, the same way it reads `reasoning`. There's no threshold or
policy on the number, because what to do with a low-confidence ruling is the
caller's decision. Calibration is not measured either. The stale
`docs/guides/content_moderation.json` snapshot is left alone; dropping it
belongs to [`content-moderation-guide.md`](./content-moderation-guide.md)'s
follow-up.

## Implements

- [`api.md` § What participants file](../design/api.md#what-participants-file)
  and [§ The judge's output](../design/api.md#the-judges-output): the field on
  `Argument`, `Response` and `Ruling`, what it means on each, and why
  `Concession` and `Continuance` have none.
- [`prompting.md` § The advocate's procedural prompt](../design/prompting.md#the-advocates-procedural-prompt)
  and [§ The judge's procedural prompt](../design/prompting.md#the-judges-procedural-prompt):
  the new text.
- [`prompting.md` § `Transcript.render()`](../design/prompting.md#transcriptrender):
  the header-line format.
- [`execution.md` § A function of several parameters](../design/execution.md):
  a keyword-only parameter is offered in signature order, and its bounds are
  checked before the function runs.
- [`docs/glossary.md`](../glossary.md): a **Confidence** row, plus the
  `Argument`, `Response` and `Ruling` rows and the judge output sketch.

## Depends on

Nothing open. It extends work that has merged:
[`schemas.md`](./schemas.md) (#19) for the filing shapes,
[`rendering.md`](./rendering.md) (#23) for the entry blocks,
[`proceeding-core.md`](./proceeding-core.md) (#26) for the clerk's conversion,
[`round-loop.md`](./round-loop.md) (#28) for the response output function, and
[`guides.md`](./guides.md) (#31) and
[`content-moderation-guide.md`](./content-moderation-guide.md) (#33) for the
guides that print it.

## Files

| File | Change |
|---|---|
| `src/enbanc/_filings.py` | `confidence: float = Field(ge=0, le=1)` on `Argument`, `_Argument`, `Response`, `_Response` and `Ruling`, with a docstring paragraph on what it means for each author. |
| `src/enbanc/_proceeding.py` | `_public` copies `confidence` across. `_response_output`'s `respond` gains a `confidence` parameter with the same bounds, because the wire shape is that signature rather than `_Response`. |
| `src/enbanc/_prompting.py` | New text in both procedural prompts. `_entry_block` renders `(confidence {c})` in the argument, response and ruling header lines. |
| `docs/decisions/0043-filings-carry-a-confidence.md` | **New.** The ADR, indexed in `docs/README.md`. |
| `docs/design/api.md`, `prompting.md`, `execution.md`, `outcomes.md`, `docs/glossary.md` | Schemas, prompt text, render examples, the keyword-only finding, the glossary rows, and every worked filing that spells out its fields. |
| `docs/guides/loan_assessment.py`, `content_moderation.py`, `docs/guides/README.md` | Print each filing's confidence and the ruling's. Say in prose that the number is uncalibrated. |
| `README.md` | The `match` on `Ruling` shows `confidence`. |

## Tests

All `unit` and `contract`. Nothing new in the live tiers: the `e2e` tier
already runs both guides, so a guide that prints `confidence` is exercised
there as written.

- `test_filings.py`: each of the three shapes rejects a confidence below 0,
  above 1, or missing, and accepts both endpoints. `Concession` and
  `Continuance` have no such field.
- `test_procedural_prompts.py`: the goldens follow `prompting.md`'s new text.
  Those tests are what hold the prompt and the doc to the same bytes.
- `test_entry_blocks.py`, `test_transcript_render.py`, `test_turns.py`,
  `test_projections.py`: the header lines carry `(confidence …)`.
- `test_filing_clerk.py`: the clerk copies `confidence` from `_Argument` and
  `_Response` onto the public filing unchanged.
- `test_agents.py`: a response run's output schema is `answer`, `exhibits`,
  `confidence`, in that order, with `minimum: 0` and `maximum: 1` on the last.
  An out-of-range value is retried rather than filed.
- `contract/test_an_output_validator_forbids_a_run_output_type.py`: the
  PydanticAI behaviour that relies on. A keyword-only parameter is offered in
  signature order, and its `Annotated` bounds are checked before the function
  body runs.
- Every fixture and `FunctionModel` script that builds an `Argument`,
  `Response` or `Ruling` passes `confidence`, because the field has no default.
  That includes `tests/unit/conftest.py` and the `outcomes/` mirror. The
  contract tier's stand-in classes are its own and are not touched.

## Open questions

None.
