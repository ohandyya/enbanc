---
status: current
updated: 2026-09-04
---

# Glossary

`enbanc` uses courtroom vocabulary. It's precise once you know it, and this
table is the whole tax.

| Term | What it is |
|---|---|
| **Tribunal** | The orchestrator. Holds the question, the statute, the judge, the advocates, the default model, and the limits a proceeding runs inside — the round limit, an optional budget, an optional concurrency bound. |
| **Statute** | The rule judged against — underwriting guidelines, selection criteria. Authored by you, in whatever form the rule wants. Inert data: it carries no model, `enbanc` makes no assumption about its text, and it is frozen. |
| **Verdict** | The enum of allowed answers. You subclass it. One advocate is created per value, and the enum is the type parameter every other shape here is keyed on. |
| **Case** | The facts of a single decision: applicant details, business info, whatever context you supply. A base class you subclass to give those facts a schema, open enough to construct as it is, and frozen once made. |
| **Advocate** | An agent assigned one verdict value, with its own read-only tools. Its job is to convince the judge the answer is *X* — or to concede. |
| **Judge** | The single agent that rules. It has no tools and reasons only over the record the advocates build. Concrete and `enbanc`-owned, not an interface you implement. |
| **Participant** | Any agent that runs in a proceeding: each advocate, plus the judge. It is the unit filings are made by and spend is attributed to, keyed by the advocate's verdict value or the literal `"judge"` — which is reserved, so a verdict may not use it. |
| **Guidance** | Optional per-agent steer — "ambiguity favors denial" — added to the procedural prompt `enbanc` writes for that role, as its last part. Human-authored, never a replacement for it, and recorded on the transcript so a steered ruling does not read as an unsteered one. |
| **Round** | One exchange: the advocates' filings, plus the judge's deliberation that closes it. `max_rounds` counts deliberations. |
| **Filing** | Anything a participant enters into the record: an argument, a concession, a response, a continuance, or a ruling. |
| **Argument** | An advocate's round-1 filing: a claim and its supporting exhibits, made blind — no peer's filing is in view. |
| **Concession** | An advocate stating no reasonable case exists for its assigned verdict. A first-class outcome, not a failure, and a round-1 filing. |
| **Tool** | A plain async function an advocate may call to gather evidence. Read-only, per-advocate, and PydanticAI's own — `enbanc` defines no tool base class and no tool decorator. |
| **Source** | One piece of evidence a tool found, together with the reference that locates it. What tools *return*; most never become exhibits. |
| **Reference** | The string that says where a piece of evidence lives — a URL, a document key, a file path, the query that produced a row. Each tool defines what a locator means for it; `enbanc` never parses one. |
| **Exhibit** | A piece of evidence entered into the record by an advocate: its excerpt, plus the tool and reference the tribunal stamps from what that tool actually returned. What it *files* — a subset of what its tools returned, and the ledger holds the rest. |
| **Retrieval** | One source a tool returned, recorded verbatim with the round and advocate that produced it. Filed or not — that is what makes suppression visible. |
| **Ledger** | Every retrieval in a proceeding, on `Transcript.ledger`. Where `entries` say what the ruling rests on, the ledger says what was available to rest on. |
| **Tool failure** | A tool call that returned nothing — it timed out. Recorded on `Transcript.failures` so an advocate blocked from a source is distinguishable from one that never looked. It carries no id, because nothing came back to cite. |
| **Interrogatory** | A targeted question from the judge to a specific advocate, issued when it cannot yet rule. Carries an id naming the round it was issued in, stamped by the tribunal when the continuance is filed. |
| **Response** | An advocate's answer to one interrogatory, entering new exhibits as needed and written with the record to date in view. It cites that interrogatory's id, which the tribunal stamps from the dispatch — no participant writes an id. |
| **Ruling** | The judge's decision: a verdict plus reasoning. Terminal. |
| **Continuance** | The judge's "not yet" — carries the interrogatories for the next round. |
| **Entry** | One filing plus the tribunal's record of it: which round it belongs to and when it was filed. |
| **Transcript** | Append-only record of every filing, in order, plus the ledger of everything the advocates' tools returned and the calls that returned nothing, together with the standing record it was decided under — the question, the statute, the case, the bench, the round limit, the guidance each participant was given, and the procedure that ran. This is your audit artifact. |
| **Hearing** | What `hear()` returns: the outcome, the transcript, the round count, and what the proceeding spent — broken down per participant, with the aggregate as that breakdown's sum. It exists only when the tribunal ran to the end of its own process. |
| **Outcome** | How a proceeding ended: a `Ruling`, or `Undecided`. A discriminated union, so a caller cannot read a verdict without first acknowledging there might not be one. |
| **Undecided** | The proceeding ran out of the envelope it was given — `max_rounds` deliberations, or the budget — and reached no verdict. Recorded and serializable, not a failure, and it names which of the two ran out. |
| **Budget** | An optional ceiling on what a whole proceeding may spend, given as PydanticAI's `UsageLimits`. Checked between rounds against the running total, never inside a round. |
| **Procedure** | The prompting surface a proceeding ran under, named by version on `Transcript.procedure` — both procedural prompts, the turn templates, and the render format. `enbanc` bumps it when that text changes and not when the package does. |
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
    id: str            # stamped on filing; names the issuing round, e.g. "r1-q2"
    to: VerdictT       # the advocate addressed — targeted, never broadcast
    question: str

Deliberation = Ruling[VerdictT] | Continuance[VerdictT]
```

This makes invalid states unrepresentable — you can't have a decision that also
carries pending questions, or a non-decision with nothing to ask. The `kind`
tags are defaulted, so the model never has to produce them, and they are what
lets a persisted transcript be read back without Pydantic guessing a union
member from field shape.

`Interrogatory.id` is the one field here the judge does not fill either, and it
is handled differently: a defaulted id has no correct value the way `kind` does,
so the judge emits a private id-less twin and the tribunal stamps the id when it
files the continuance. See [`design/api.md`](./design/api.md#where-ids-come-from)
and
[`decisions/0015-interrogatory-ids-are-stamped-on-filing.md`](./decisions/0015-interrogatory-ids-are-stamped-on-filing.md).

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

Tools and models look like ordinary PydanticAI: you pass PydanticAI tools and
toolsets, and you construct a PydanticAI `Model` and inject it. Usage comes back
as PydanticAI's `RunUsage`. No `@discovery` decorator, no `jurisdictions` for
providers. Someone arriving from PydanticAI should recognize all three
immediately.

A tool is a plain async function and stays one. `Source` is the only `enbanc`
type that appears anywhere near it, it is a *return* type rather than a base
class or a registration, and it is optional: a tool that returns a string is
still citable, just with the call as its reference. See
[`design/evidence.md`](./design/evidence.md).

The metaphor governs `enbanc`'s vocabulary, not its surface area. Anything
`enbanc` does not expose you configure on the PydanticAI object it belongs to,
in ordinary PydanticAI terms: temperature, retries, and per-request settings on
the `Model` you build; a tool's execution timeout on the `Tool` you wrap it in.
There is no `settings=` and no `tool_timeout=` anywhere on `enbanc`'s own
types.

It also stops at the exceptions, deliberately. `EnbancError`,
`ConfigurationError`, `ProceedingFailed`, and `ProceedingUnfinished` say what
went wrong in plain terms rather than courtroom ones, because they are read in
stack traces by people who have not opened this table. `Mistrial` is the right
legal word for a proceeding terminated without a verdict, and it is not the
right word to meet at 3am. See
[`0011`](./decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md).
