---
status: draft
updated: 2026-09-01
---

# Public API

The surface being designed toward `0.1.0`. Mechanics behind it are in
[`tribunal.md`](./tribunal.md); terms are defined in
[`../glossary.md`](../glossary.md).

> `status: draft` — none of this exists yet, and it will change. This is the
> target, not a reference.

## Shape

```python
from pydantic_ai.models.anthropic import AnthropicModel

from enbanc import Tribunal, Judge, Advocate, Statute, Case, Verdict

class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"

statute = Statute("Approve $500k loans only where DTI < 0.43 and ...")

tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,
    statute=statute,
    model=AnthropicModel("claude-sonnet-5"),
    judge=Judge(guidance="Where the record is ambiguous, deny."),
    advocates={
        LoanDecision.APPROVE: Advocate(tools=[psql, tavily]),
        LoanDecision.DENY: Advocate(
            tools=[psql],
            guidance="Weigh documented income over stated income.",
        ),
    },
    max_rounds=5,
)

ruling = await tribunal.hear(Case(applicant=..., income=...))

ruling.verdict      # LoanDecision.DENY
ruling.reasoning
ruling.transcript   # every argument, exhibit, and interrogatory, in order
ruling.usage        # tokens and cost, summed across judge and advocates
```

## What each piece carries

**`Verdict`** — you subclass it to enumerate the allowed answers. The set of
values determines how many advocates exist; there is exactly one advocate per
value, and no way to end up with an advocate arguing for an answer outside the
enum.

**`Statute`** — the rule being judged against, and nothing else. You author it;
it carries no model and does nothing on its own. It is a type rather than a bare
string for two reasons: it is the artifact every ruling is audited against, so
it deserves a name in the record, and it is the piece most likely to grow
structure later. See [`0001`](../decisions/0001-statute-carries-no-model.md).

**`Case`** — the facts of a single decision. Deliberately open: applicant
details, business info, whatever the statute needs to be applied. Like
`Statute`, it is a noun in the record — supplied by you, never an agent.

**`Advocate`** — assigned one verdict value, given its own read-only tools. Tools
are per-advocate on purpose: the advocate for approval may need different
evidence sources than the advocate for denial, and giving both the same toolbox
would flatten a real asymmetry. Takes an optional `model`, overriding the
tribunal's, and optional `guidance`.

**`Judge`** — exactly one, and it has no tools. It reasons only over what
advocates put into the record, which is what keeps the transcript a complete
explanation of the ruling. Its output type belongs to the library and is derived
from your `Verdict` enum — a `Ruling` or a `Continuance`, never free text — so
there is nothing to configure there. Like an advocate, it takes an optional
`model` and optional `guidance`.

**`Tribunal`** — holds the question, statute, judge, advocates, default model,
and round limit. Async, because every round fans out across advocates.

**`hear(case)`** — runs the proceeding and returns the outcome, carrying the
verdict, the reasoning, the full transcript, and the aggregate usage.

## Design commitments

**Async-first.** Rounds fan out across advocates; a sync-first API would either
serialize that or lie about it.

**The transcript rides on the result.** It is not an optional debug flag or a
callback you have to install. If the result can be returned, the record that
produced it can be inspected — that is the product.

**Verdicts are an enum, not free text.** The judge picks from a closed set, and
the type system knows the set.

**A statute is data, not an agent.** A statute carries no model. Holding a rule
fixed while swapping the models that reason about it is a workflow this library
must not obstruct — a statute that owned a model would make every such
comparison move two variables at once. Keeping it inert also keeps it readable,
diffable, and committable alongside the code that applies it. Where models *do*
live is the next commitment.

**The model is injected, not named.** `enbanc` has no provider concept and no
model-string parser; it would be reinventing one that already works. You
construct a `pydantic_ai.models.Model` and hand it over. `Tribunal(model=...)`
is required and is the default every agent inherits; `Judge` and `Advocate` may
each override it, which is what makes a strong judge over cheap advocates — or a
model comparison on a fixed statute — a one-line change. A single `Model`
instance is safe to share across every agent, and sharing one is the good path.
See [`0003`](../decisions/0003-models-and-guidance-are-injected.md).

**Guidance augments; the library owns the procedural prompt.** Each agent's
system prompt is assembled by `enbanc`: the `Ruling | Continuance` contract, the
rule that interrogatories are targeted rather than broadcast, the judge's
prohibition on gathering its own evidence, the advocate's licence to concede.
Your `guidance` is added to that, not substituted for it. A replaceable prompt
would let a caller silently break the output schema, and the failure would
present as a library bug. Guidance is per-agent and never inherited: the judge's
steer and an advocate's steer contradict each other by construction, and
anything genuinely common is already carried by `question` and `statute`.

**Agents are reusable; a proceeding's state is not.** `Judge` and `Advocate` are
descriptions — model, tools, guidance — that you construct once and may share
across tribunals. The message history each accumulates over rounds is created
inside `hear()` and discarded when it returns. That split is what makes `hear()`
safe to call twice and safe to run concurrently over several cases; state parked
on the injected object would let one case's record leak into the next.

**The set of judge implementations is closed.** `Judge` is a concrete class, not
a protocol you implement. The guarantees that make a transcript auditable — the
judge has no tools, and nothing reaches it that is not already in the record —
are enforceable only while `enbanc` owns every judge. See
[`0002`](../decisions/0002-the-judge-is-a-role.md).

## Open questions

- The schema for
  1. Verdict: StrEnum
  2. Statute: Pydantic model
  3. ruling: Pydantic model
- Whether a `Statute` is prose the judge reads, or a set of named criteria it
  must rule on one at a time. Structure would let the transcript show *which*
  criterion decided the case, and would give a drafting step something to
  compile into — see [`0001`](../decisions/0001-statute-carries-no-model.md).
- Whether `guidance` is ever machine-tuned. It is human-written in `0.1.0`.
  Keeping it per-agent, optional, and separate from the library's procedural
  prompt is what leaves the door open; nothing is built for it yet.
- Whether `ModelSettings` — temperature, `max_tokens`, retries — is exposed per
  agent, or stays something you bake into the `Model` you construct.
- Whether a bench ever sits. If it does, it joins `judge=` as a union member
  (`Judge | Bench`) rather than arriving as a second parameter. This is not an
  extension point: any bench would be `enbanc`'s own, for the reason in
  [`0002`](../decisions/0002-the-judge-is-a-role.md).
- What `hear()` returns. The judge produces a `Ruling` — verdict and reasoning,
  and nothing else it could know. The transcript and the usage are the
  tribunal's. Whether the caller gets a widened `Ruling` carrying both, or a
  distinct result type that wraps the judge's `Ruling`, is unsettled; the sample
  above writes `ruling.transcript` without committing to either.
- Whether `hear()` has a streaming counterpart for observing rounds live.
- The return type of `hear()` when the round limit is exhausted — see
  [`tribunal.md`](./tribunal.md#open-questions).
- Whether `Case` is a base class users subclass, or a generic container.
