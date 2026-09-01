---
status: current
updated: 2026-09-01
---

# Glossary

`enbanc` uses courtroom vocabulary. It's precise once you know it, and this
table is the whole tax.

| Term | What it is |
|---|---|
| **Tribunal** | The orchestrator. Holds the question, the statute, the judge, the advocates, the default model, and the round limit. |
| **Statute** | The rule judged against — underwriting guidelines, selection criteria. Authored by you. Inert data: it carries no model. |
| **Verdict** | The enum of allowed answers. You subclass it. One advocate is created per value. |
| **Case** | The facts of a single decision: applicant details, business info, whatever context you supply. |
| **Advocate** | An agent assigned one verdict value, with its own read-only tools. Its job is to convince the judge the answer is *X* — or to concede. |
| **Judge** | The single agent that rules. It has no tools and reasons only over the record the advocates build. Concrete and `enbanc`-owned, not an interface you implement. |
| **Guidance** | Optional per-agent steer — "ambiguity favors denial" — added to the procedural prompt `enbanc` writes for that role. Human-authored, and never a replacement for it. |
| **Argument** | An advocate's round-1 filing: a position, a claim, and supporting exhibits. |
| **Concession** | An advocate stating no reasonable case exists for its assigned verdict. A first-class outcome, not a failure. |
| **Exhibit** | A piece of evidence entered into the record by an advocate. |
| **Interrogatory** | A targeted question from the judge to a specific advocate, issued when it cannot yet rule. |
| **Ruling** | The judge's decision: a verdict plus reasoning. Terminal. |
| **Continuance** | The judge's "not yet" — carries the interrogatories for the next round. |
| **Transcript** | Append-only shared record of everything every agent said, in order. This is your audit artifact. |

## Judge output shape

`Ruling` and `Continuance` are a discriminated union, not a boolean flag:

```python
class Ruling(BaseModel):
    verdict: VerdictT
    reasoning: str

class Continuance(BaseModel):
    interrogatories: list[Interrogatory]

Deliberation = Ruling | Continuance
```

This makes invalid states unrepresentable — you can't have a decision that also
carries pending questions, or a non-decision with nothing to ask. Pydantic
discriminates the union natively, so the judge's output schema validates itself
and documents itself to the LLM.

This is what the *judge* returns each round. What `hear()` hands back to the
caller also carries the transcript and the proceeding's usage, neither of which
the judge produces; whether that is a widened `Ruling` or a separate type
wrapping one is an open question in
[`design/api.md`](./design/api.md#open-questions).

## Where the metaphor stops

Tools and models look like ordinary PydanticAI: you pass PydanticAI tools, and
you construct a PydanticAI `Model` and inject it. No `@discovery` decorator, no
`jurisdictions` for providers. Someone arriving from PydanticAI should recognize
both immediately.

The metaphor governs `enbanc`'s vocabulary, not its surface area. Anything
`enbanc` does not expose — temperature, retries, per-request settings — you
configure on the `Model` you build, in ordinary PydanticAI terms.
