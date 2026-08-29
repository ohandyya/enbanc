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
tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,          # your enum: APPROVE / DENY
    statute=statute,                # the rule being judged against
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

The judge has **no tools** — it reasons only over what advocates put into the
record. All advocate tools are **strictly read-only**.

## Design

The full design lives in [`docs/design/`](./docs/design/):

- [**The tribunal**](./docs/design/tribunal.md) — how a decision is reached: the
  round structure, the judge/advocate contract, and the constraints that hold it
  together.
- [**Public API**](./docs/design/api.md) — the surface being designed toward
  `0.1.0`, and what each piece carries.
- [**Glossary**](./docs/glossary.md) — the courtroom vocabulary. Six rows, one
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
