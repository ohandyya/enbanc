---
status: draft
updated: 2026-08-29
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

statute = Statute.draft(
    "Approve $500k loans only where DTI < 0.43 and ...",
    model="anthropic:claude-sonnet-4-6",
)

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

**`Statute`** — the rule being judged against. Authored directly, or drafted
from prose with `Statute.draft()`. Drafting takes a model because turning loose
policy language into a testable rule is itself a model call, and one worth doing
once up front rather than implicitly on every hearing.

**`Case`** — the facts of a single decision. Deliberately open: applicant
details, business info, whatever the statute needs to be applied.

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

## Open questions

- Whether `Advocate` needs a model parameter, or inherits one from `Tribunal`.
- Whether `hear()` has a streaming counterpart for observing rounds live.
- The return type of `hear()` when the round limit is exhausted — see
  [`tribunal.md`](./tribunal.md#open-questions).
- Whether `Case` is a base class users subclass, or a generic container.
