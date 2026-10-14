# enbanc

**Adversarial multi-agent adjudication.** Advocates argue each possible answer;
a judge cross-examines them until it can rule — with a full audit transcript.

Built on [PydanticAI](https://ai.pydantic.dev).

> [!WARNING]
> **Work in progress — not released yet.**
> The code in this repository runs, but nothing usable is on PyPI: the
> published packages are placeholders, and installing `enbanc` today gets you
> nothing that runs. **The first usable release will be `0.1.0`.**

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

*This runs today from a source checkout, with `OPENAI_API_KEY` and
`TAVILY_API_KEY` set. The published package is still a placeholder until
`0.1.0`.*

```python
import asyncio
import os

from pydantic_ai.models import infer_model

from enbanc import (
    Advocate, Case, Judge, Ruling, Source, Statute, Tribunal, Undecided, Verdict,
)
from enbanc.tools import web_search

class LoanDecision(Verdict):        # the allowed answers, one advocate each
    APPROVE = "approve"
    DENY = "deny"

class LoanApplication(Case):        # the facts of one decision, given a schema
    applicant: str
    income: int

async def credit_file(applicant: str) -> list[Source]:
    """Look up the applicant's credit file."""  # a tool is any async function
    return [Source(reference=f"bureau://{applicant}", content="Debt-to-income: 0.51")]

tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,
    statute=Statute(                # the rule being judged against
        text="Approve $500k loans only where DTI < 0.43 and ...",
        name="underwriting-v3",
    ),
    model=infer_model("openai:gpt-6-luna"),  # any pydantic-ai model
    judge=Judge(guidance="Where the record is ambiguous, deny."),
    advocates={
        LoanDecision.APPROVE: Advocate(
            tools=[credit_file, web_search(api_key=os.environ["TAVILY_API_KEY"])]
        ),
        LoanDecision.DENY: Advocate(tools=[credit_file]),
    },
    max_rounds=5,
)

async def main() -> None:
    hearing = await tribunal.hear(LoanApplication(applicant="A. Okonkwo", income=182000))

    match hearing.outcome:          # a ruling, or no verdict at all
        case Ruling(verdict=verdict, reasoning=reasoning, confidence=confidence):
            print(verdict)          # deny
            print(reasoning)        # why, in the judge's words, resting on the record
            print(confidence)       # 0.8: the judge's own estimate, not a probability
        case Undecided(reason=reason):  # rounds or budget spent, no verdict
            print(f"no verdict: the {reason} ran out")

    hearing.transcript              # every filing, in order
    hearing.usage                   # tokens and cost, judge plus advocates
    hearing.usage_by_participant    # the same spend, split by who incurred it

asyncio.run(main())
```

The judge has **no tools** — it reasons only over what advocates put into the
record. Advocate tools are **read-only**, and that is a contract you keep:
`enbanc` ships nothing that writes and has no mutation path of its own, but it
cannot inspect a function you pass for side effects.

Every exhibit in the record carries a **reference** the tribunal stamped — a
URL, a document key, the query that produced a row — taken from what the tool
actually returned rather than from what the model said it returned. So a
reviewer can follow any piece of evidence back to its source, and an advocate
cannot cite something no tool produced.

The transcript also holds everything the advocates' tools returned and they
*didn't* file, verbatim. An advocate that queries a damaging fact and argues
around it leaves a trace: the retrieval is in the record and no exhibit cites
it. That is the question no LLM-as-judge transcript usually answers — not
*what did it decide on?* but *what did it leave out?*

It also holds what *steered* the decision: the guidance you gave each
participant, the verdicts the bench was deciding among, and the version of the
procedural prompt `enbanc` ran. A ruling reached under "where the record is
ambiguous, deny" does not read in the artifact as one reached without it.

A tool is a plain async function; there is nothing to register or decorate, and
`enbanc.tools.web_search` is built the same way yours is.

A tribunal that runs out of the envelope it was given — `max_rounds`
deliberations, or an optional token or cost `budget` — without reaching a
verdict returns `Undecided`, naming which of the two ran out. That is a finding,
and it comes back on the hearing with the full transcript. A tribunal that loses a participant — the provider is down, a tool
raises — is a different thing, and raises `ProceedingFailed` with the record so
far attached. No ruling is ever issued on a bench that lost an advocate.

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
- [**Evidence**](./docs/design/evidence.md) — what a tool is, how you add your
  own, and how what one returns becomes an exhibit a reviewer can check.
- [**Outcomes**](./docs/design/outcomes.md) — every way a proceeding can end,
  worked through with concrete values: a ruling, a spent round limit, a spent
  budget, a downed provider, a misconfigured tribunal.
- [**Prompting and rendering**](./docs/design/prompting.md) — what every
  participant actually reads: both procedural prompts in full, how a statute,
  case, and record become text, and what a rendered transcript looks like.
- [**Execution**](./docs/design/execution.md) — how a proceeding maps onto
  PydanticAI: the whole thing written out as literal messages, then the message
  history behind the transcript, the toolset that ledgers what an advocate's
  tools return, and the round loop itself.
- [**Testing**](./docs/design/testing.md) — how a library whose behaviour is
  LLM-driven is asserted on deterministically: the tiers, why the offline ones
  are enforced rather than trusted, and how the guarantee the transcript makes
  is checked by a test rather than by review.
- [**Packaging**](./docs/design/packaging.md) — how the library is laid out as
  a package: the two namespaces you may import from, what `__all__` promises,
  and what `import enbanc` is allowed to do.
- [**Glossary**](./docs/glossary.md) — the courtroom vocabulary. One table, one
  minute.

**The design is complete and carries no open questions.** It is settled down to
the schemas and the behaviour both: what an advocate sees, how a proceeding
stops, what every ending looks like, the exact text each agent is sent, and how
the loop is built. Every question those documents once carried is closed with an
ADR in [`docs/decisions/`](./docs/decisions/) saying what was rejected and why.
If you have opinions, that's the place to aim them.

What is *not* done is the release. The code runs from a source checkout, and
the API may still change before `0.1.0`.

How that design gets built is broken into pull requests in
[`docs/implementations/`](./docs/implementations/) — one document per PR: its
scope, the design sections it implements, and the tests it brings. Fifteen
are planned; thirteen have merged, and the fourteenth is open.

## Status

Pre-alpha, work in progress. Not usable from PyPI. Current releases are
placeholders that exist only to reserve the name and exercise the release
pipeline.

**`0.1.0` is the first release intended to be used.** The API will keep
changing until then, and likely after.

## License

MIT
