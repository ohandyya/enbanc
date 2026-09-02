# enbanc

**Adversarial multi-agent adjudication.** Advocates argue each possible answer;
a judge cross-examines them until it can rule — with a full audit transcript.

Built on [PydanticAI](https://ai.pydantic.dev).

> [!WARNING]
> **Work in progress — not usable yet.**
> Nothing described below is implemented. The published packages are
> placeholders; installing `enbanc` today gets you nothing that runs.
> **The first usable version will be `0.1.0`.**

## Why

Most "LLM as judge" tooling asks one model to score an output. `enbanc` instead
stages an adversarial proceeding: every possible answer gets a dedicated
advocate with its own tools, and a tool-less judge interrogates them across
rounds until it can rule or the round limit is hit.

That structure is designed for decisions that need to be **defensible** —
loan underwriting, insurance appetite, eligibility screening — where you need
the reasoning and the evidence, not just the answer.

## Install

Not yet. Wait for `0.1.0`.

Once it ships:

```bash
uv add enbanc
```

## A taste

*Planned API. None of this works today.*

```python
from pydantic_ai.models.anthropic import AnthropicModel

from enbanc import Advocate, Case, Judge, Statute, Tribunal, Verdict

class LoanDecision(Verdict):        # the allowed answers, one advocate each
    APPROVE = "approve"
    DENY = "deny"

tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,
    statute=Statute(                # the rule being judged against
        text="Approve $500k loans only where DTI < 0.43 and ...",
        name="underwriting-v3",
    ),
    model=AnthropicModel("claude-sonnet-5"),
    judge=Judge(guidance="Where the record is ambiguous, deny."),
    advocates={
        LoanDecision.APPROVE: Advocate(tools=[psql, tavily]),
        LoanDecision.DENY: Advocate(tools=[psql]),
    },
    max_rounds=5,
)

hearing = await tribunal.hear(Case(applicant=..., income=...))

if hearing.ruling is not None:      # None only when the round limit was hit
    hearing.ruling.verdict          # LoanDecision.DENY
    hearing.ruling.reasoning

hearing.transcript                  # every filing, in order
hearing.usage                       # tokens and cost, judge plus advocates
```

The judge has **no tools** — it reasons only over what advocates put into the
record. All advocate tools are **strictly read-only**.

A proceeding takes minutes, so you can watch the record being written instead of
waiting for it:

```python
async with tribunal.hear_stream(case) as proceeding:
    async for entry in proceeding:  # each filing, at the moment it is filed
        print(f"round {entry.round}: {entry.filing.kind}")

hearing = proceeding.hearing        # the Hearing hear() would have returned
```

What you watch is the transcript itself — the same entries, in the same order —
and `hear()` is this stream consumed to the end.

## Design

The full design lives in [`docs/design/`](./docs/design/):

- [**The tribunal**](./docs/design/tribunal.md) — how a decision is reached: the
  round structure, the judge/advocate contract, and the constraints that hold it
  together.
- [**Public API**](./docs/design/api.md) — the surface being designed toward
  `0.1.0`, and what each piece carries.
- [**Glossary**](./docs/glossary.md) — the courtroom vocabulary. One table, one
  minute.

Both design documents carry open questions that aren't settled yet. If you have
opinions, that's the place to aim them.

## Status

Pre-alpha, work in progress. Not usable. Current releases are placeholders that
exist only to reserve the name and exercise the release pipeline.

**`0.1.0` is the first version intended to actually run.** The API will keep
changing until then, and likely after.

## License

MIT
