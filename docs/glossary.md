---
status: current
updated: 2026-09-01
---

# Glossary

`enbanc` uses courtroom vocabulary. It's precise once you know it, and this
table is the whole tax.

| Term | What it is |
|---|---|
| **Tribunal** | The orchestrator. Holds the question, the statute, the advocates, and the round limit. |
| **Statute** | The rule judged against — underwriting guidelines, selection criteria. Authored by you. Inert data: it carries no model. |
| **Verdict** | The enum of allowed answers. You subclass it. One advocate is created per value. |
| **Case** | The facts of a single decision: applicant details, business info, whatever context you supply. |
| **Advocate** | An agent assigned one verdict value, with its own read-only tools. Its job is to convince the judge the answer is *X* — or to concede. |
| **Argument** | An advocate's round-1 filing: a position, a claim, and supporting exhibits. |
| **Concession** | An advocate stating no reasonable case exists for its assigned verdict. A first-class outcome, not a failure. |
| **Exhibit** | A piece of evidence entered into the record by an advocate. |
| **Interrogatory** | A targeted question from the judge to a specific advocate, issued when it cannot yet rule. |
| **Ruling** | The judge's decision: a verdict plus reasoning. Terminal. |
| **Continuance** | The judge's "not yet" — carries the interrogatories for the next round. |
| **Transcript** | Append-only shared record of everything every agent said, in order. Passed to each agent as history. This is your audit artifact. |

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

## Where the metaphor stops

Tools, model providers, retries, and configuration look like ordinary
PydanticAI. No `@discovery` decorator, no `jurisdictions` for providers.
Someone arriving from PydanticAI should recognize the tool API immediately.
