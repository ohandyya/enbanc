---
status: current
updated: 2026-09-02
---

# Glossary

`enbanc` uses courtroom vocabulary. It's precise once you know it, and this
table is the whole tax.

| Term | What it is |
|---|---|
| **Tribunal** | The orchestrator. Holds the question, the statute, the judge, the advocates, the default model, and the round limit. |
| **Statute** | The rule judged against — underwriting guidelines, selection criteria. Authored by you, in whatever form the rule wants. Inert data: it carries no model, `enbanc` makes no assumption about its text, and it is frozen. |
| **Verdict** | The enum of allowed answers. You subclass it. One advocate is created per value, and the enum is the type parameter every other shape here is keyed on. |
| **Case** | The facts of a single decision: applicant details, business info, whatever context you supply. |
| **Advocate** | An agent assigned one verdict value, with its own read-only tools. Its job is to convince the judge the answer is *X* — or to concede. |
| **Judge** | The single agent that rules. It has no tools and reasons only over the record the advocates build. Concrete and `enbanc`-owned, not an interface you implement. |
| **Guidance** | Optional per-agent steer — "ambiguity favors denial" — added to the procedural prompt `enbanc` writes for that role. Human-authored, and never a replacement for it. |
| **Round** | One exchange: the advocates' filings, plus the judge's deliberation that closes it. `max_rounds` counts deliberations. |
| **Filing** | Anything a participant enters into the record: an argument, a concession, a response, a continuance, or a ruling. |
| **Argument** | An advocate's round-1 filing: a claim and its supporting exhibits. |
| **Concession** | An advocate stating no reasonable case exists for its assigned verdict. A first-class outcome, not a failure. |
| **Exhibit** | A piece of evidence entered into the record by an advocate. What it *files* — not everything its tools returned. |
| **Interrogatory** | A targeted question from the judge to a specific advocate, issued when it cannot yet rule. Carries an id naming the round it was issued in. |
| **Response** | An advocate's answer to one interrogatory, citing that interrogatory's id and entering new exhibits as needed. |
| **Ruling** | The judge's decision: a verdict plus reasoning. Terminal. |
| **Continuance** | The judge's "not yet" — carries the interrogatories for the next round. |
| **Entry** | One filing plus the tribunal's record of it: which round it belongs to and when it was filed. |
| **Transcript** | Append-only record of every filing, in order, together with the question, statute, and case it was decided under. This is your audit artifact. |
| **Hearing** | What `hear()` returns: the ruling, the transcript, the aggregate usage, and the round count. |
| **Proceeding** | A hearing while it is still going: the live handle `hear_stream()` hands back. Iterate it to receive each entry as it is filed; when it ends it carries the same `Hearing` `hear()` would have returned. |

## Judge output shape

`Ruling` and `Continuance` are a discriminated union, not a boolean flag, and
both are parameterized by your verdict enum:

```python
class Ruling(BaseModel, Generic[VerdictT]):
    kind: Literal["ruling"] = "ruling"
    verdict: VerdictT
    reasoning: str

class Continuance(BaseModel, Generic[VerdictT]):
    kind: Literal["continuance"] = "continuance"
    interrogatories: list[Interrogatory[VerdictT]]

class Interrogatory(BaseModel, Generic[VerdictT]):
    id: str            # assigned by enbanc; names the issuing round, e.g. "r1-q2"
    to: VerdictT       # the advocate addressed — targeted, never broadcast
    question: str

Deliberation = Ruling[VerdictT] | Continuance[VerdictT]
```

This makes invalid states unrepresentable — you can't have a decision that also
carries pending questions, or a non-decision with nothing to ask. The `kind`
tags are defaulted, so the model never has to produce them, and they are what
lets a persisted transcript be read back without Pydantic guessing a union
member from field shape.

A ruling carries a verdict and reasoning and nothing else, because there is
nothing else the judge could know. Which round it was issued in, what the
proceeding cost, and what came before it are the tribunal's facts: they live on
`Entry` and on `Hearing`.

That is why `hear()` hands back a `Hearing` rather than a widened `Ruling` —
see [`design/api.md`](./design/api.md#the-result) and
[`decisions/0005-hear-returns-a-hearing.md`](./decisions/0005-hear-returns-a-hearing.md).
The exact spelling of the `Deliberation` alias is a little fussier than shown
here, for a Pydantic reason recorded in
[`design/api.md`](./design/api.md#a-note-on-generic-aliases).

## Where the metaphor stops

Tools and models look like ordinary PydanticAI: you pass PydanticAI tools, and
you construct a PydanticAI `Model` and inject it. Usage comes back as
PydanticAI's `RunUsage`. No `@discovery` decorator, no `jurisdictions` for
providers. Someone arriving from PydanticAI should recognize all three
immediately.

The metaphor governs `enbanc`'s vocabulary, not its surface area. Anything
`enbanc` does not expose — temperature, retries, per-request settings — you
configure on the `Model` you build, in ordinary PydanticAI terms.
