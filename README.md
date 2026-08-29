# enbanc

**Adversarial multi-agent adjudication.** Advocates argue each possible answer;
a judge cross-examines them until it can rule — with a full audit transcript.

Built on [PydanticAI](https://ai.pydantic.dev).

## Why

Most "LLM as judge" tooling asks one model to score an output. `enbanc` instead
stages an adversarial proceeding: every possible answer gets a dedicated
advocate with its own tools, and a tool-less judge interrogates them across
rounds until it can rule or the round limit is hit.

That structure is designed for decisions that need to be **defensible** —
loan underwriting, insurance appetite, eligibility screening — where you need
the reasoning and the evidence, not just the answer.

## Install

```bash
uv add enbanc
```

## Usage

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

## How it works

**Round 1** — each advocate argues freely for its assigned verdict, or concedes
that no reasonable case exists. The judge hears all arguments and evidence.

**Round 2+** — if the judge cannot rule, it issues *interrogatories*: targeted
questions to a chosen subset of advocates. Those advocates answer. Repeat.

Ends when the judge rules, or `max_rounds` is exceeded.

The judge has **no tools** — it reasons only over what advocates put into the
record. All advocate tools are **strictly read-only**.

## Vocabulary

`enbanc` borrows courtroom terms because they're precise. See
[`glossary.md`](./glossary.md) — six rows, one minute.

## Status

Early. API will change.

## License

MIT
