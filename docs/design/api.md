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
from enbanc import Tribunal, Advocate, Statute, Case, Verdict

class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"

statute = Statute("Approve $500k loans only where DTI < 0.43 and ...")

tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,
    statute=statute,
    advocates={
        LoanDecision.APPROVE: Advocate(tools=[psql, tavily]),
        LoanDecision.DENY: Advocate(tools=[psql]),
    },
    max_rounds=5,
)

ruling = await tribunal.hear(Case(applicant=..., income=...))

ruling.verdict      # LoanDecision.DENY
ruling.reasoning
ruling.transcript   # every argument, exhibit, and interrogatory, in order
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
would flatten a real asymmetry.

**`Tribunal`** — holds the question, statute, advocates, and round limit. Async,
because every round fans out across advocates.

**`hear(case)`** — runs the proceeding and returns the outcome, carrying the
verdict, the reasoning, and the full transcript.

## Design commitments

**Async-first.** Rounds fan out across advocates; a sync-first API would either
serialize that or lie about it.

**The transcript rides on the result.** It is not an optional debug flag or a
callback you have to install. If the result can be returned, the record that
produced it can be inspected — that is the product.

**Verdicts are an enum, not free text.** The judge picks from a closed set, and
the type system knows the set.

**A statute is data, not an agent.** Model assignment has exactly one home, and
it is `Tribunal`. Holding a rule fixed while swapping the models that reason
about it is a workflow this library must not obstruct — a statute that owned a
model would make every such comparison move two variables at once. Keeping it
inert also keeps it readable, diffable, and committable alongside the code that
applies it.

## Open questions

- Whether a `Statute` is prose the judge reads, or a set of named criteria it
  must rule on one at a time. Structure would let the transcript show *which*
  criterion decided the case, and would give a drafting step something to
  compile into — see [`0001`](../decisions/0001-statute-carries-no-model.md).
- Whether `Advocate` needs a model parameter, or inherits one from `Tribunal`.
- Whether `hear()` has a streaming counterpart for observing rounds live.
- The return type of `hear()` when the round limit is exhausted — see
  [`tribunal.md`](./tribunal.md#open-questions).
- Whether `Case` is a base class users subclass, or a generic container.
