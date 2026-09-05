---
status: draft
updated: 2026-09-05
---

# Execution

How a proceeding maps onto PydanticAI. [`tribunal.md`](./tribunal.md) says what
happens in a proceeding, [`api.md`](./api.md) says what shape the result has, and
[`prompting.md`](./prompting.md) says what text each participant reads; none of
them says how the loop is built. This does.

> `status: draft` — none of this exists yet. This is the target, not a
> reference.

Three pieces are design and the rest is ordinary implementation. What makes them
design is that each one can be got wrong *quietly*: a history that carries a
second channel, a ledger that numbers differently on every run, a stream that
shows a viewer an entry the transcript does not yet hold. None of those fail
loudly, and all three would falsify a claim the product rests on.

## What PydanticAI already does

Verified against **`pydantic-ai 2.36.0`**, the floor pinned in `pyproject.toml`,
by reading the installed source and running it. Recorded here so the findings are
not re-derived, and so they are falsifiable: these are claims about a dependency,
and they are worth re-checking when the pin moves.

None of it is a decision. It is the shape of the thing the design is built on,
and most of what looked like work turns out to be the framework's already.

### Carrying a conversation is a parameter, not a subsystem

`Agent.run()` takes `message_history: Sequence[ModelMessage] | None`, and
`result.all_messages()` hands the conversation back. Keeping each participant's
conversation across rounds is a dict:

```python
history: dict[Participant, list[ModelMessage]] = {}

async def turn(p, agent, prompt: str):
    result = await agent.run(prompt, message_history=history.get(p))
    history[p] = result.all_messages()
    return result.output
```

A participant running for the first time — every advocate in round 1, the judge
at deliberation 1 — passes `None`, which is what "the judge has no history in
round 1" means mechanically.

### Instructions are re-resolved every run and never enter history

Captured from the wire. The agent was built with two `InstructionPart`s; the
second run was given the first run's messages as `message_history`:

```text
request 1: 1 message
  ModelRequest   instructions='PROCEDURAL...\n\nSTATUTE: DTI < 0.43'
       UserPromptPart('ROUND 1: three arguments were filed ...')

request 2: 3 messages
  ModelRequest   instructions='PROCEDURAL...\n\nSTATUTE: DTI < 0.43'
       UserPromptPart('ROUND 1: three arguments were filed ...')
  ModelResponse  TextPart('ok')
  ModelRequest   instructions='PROCEDURAL...\n\nSTATUTE: DTI < 0.43'
       UserPromptPart('ROUND 2: two responses were filed ...')
```

Two consequences worth holding on to:

- **Instructions are not frozen at the first run.** They are re-resolved from the
  agent each time, so changing an agent's instructions between runs would apply
  retroactively to the whole conversation. `enbanc` cannot reach that state —
  agents are built inside `hear()` and discarded
  ([`api.md`](./api.md#design-commitments)) — but it is another reason that split
  has to hold, and it would be a real hazard for any future agent reuse.
- **For Anthropic the parts hoist once to the top-level `system` parameter**
  rather than being re-emitted per historical request (`models/anthropic.py`,
  `_map_message`: "only the opening `SystemPromptPart`s in the first request …
  hoist to the top-level `system` parameter"). That is what makes
  [`prompting.md`](./prompting.md#how-an-agent-is-assembled)'s shared-cache-prefix
  claim true rather than aspirational.

### Three channels reach a model, and `enbanc` writes one of them

| What the agent needs | Channel | Supplied by |
|---|---|---|
| Role, process, question, statute, assignment, guidance | `instructions` | `enbanc`, re-sent automatically every run |
| Its **own** past turns, tool calls, and tool results | `message_history` | PydanticAI, for free |
| **Other participants'** filings, the interrogatory, the case | `user_prompt` | `enbanc` — the rendered delta |

This is the answer to "how does the judge see what the advocates filed?", and it
is two different answers. A participant's own prior output — the judge's last
`Continuance`, an advocate's round-1 argument — is already in its history and
needs no rendering. Another participant's output is not, and nothing in
PydanticAI moves it. That gap is exactly what
[`prompting.md`](./prompting.md#the-turns) fills, and it is why a turn renders a
*delta* rather than the whole record: the rest is already there.

### A filing lands in history as a tool call, not as text

An agent whose `output_type` is a union gets **one output tool per member**, named
from the member's class:

```text
output_tools: ['final_result_ArgumentLoanDecision', 'final_result_ConcessionLoanDecision']

ModelResponse  ToolCallPart    {'kind': 'argument', 'advocate': 'approve',
                                'claim': 'DTI is 0.38 on documented income.',
                                'exhibits': [{'source': 's1', 'content': 'net profit: 182,000'}]}
ModelRequest   ToolReturnPart  'Final result processed.'
```

So a participant's own filing is a `ToolCallPart` carrying the model's arguments,
followed by a `ToolReturnPart('Final result processed.')`. There is no `TextPart`
on the path an `enbanc` participant takes, ever.

**The tool names are PydanticAI's, derived from the class names.** They are not
`enbanc`'s prompting surface and are not covered by `Transcript.procedure`
([`prompting.md`](./prompting.md#procedure-versions)) — the same way the JSON
schema of a filing is not. The observation is recorded because renaming a filing
class silently changes a string the model reads, which is worth knowing before
someone does it.

### What lands in history that no rendered turn contains

The reason the invariant needs the qualifications it has, visible in the data
structure:

- **Tool calls and their results**, as `ToolCallPart` and `ToolReturnPart`. An
  advocate's round-1 retrievals are in its round-3 context whether or not it
  filed them — which is precisely why
  [`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md) had to put the
  ledger in the transcript.
- **Retry prompts**, as `RetryPromptPart`. They cannot be filtered out without
  giving up retries, which is
  [`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md)'s
  exception showing up as a message part.
- **The agent's own pre-stamp output.** An advocate emits a private `_Exhibit` —
  a bare ledger id and an excerpt — while the transcript holds the stamped public
  `Exhibit` ([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)). The
  transcript row is a superset, so the invariant holds, but the two are not
  byte-identical and an advocate therefore sees its own round-1 filing twice in
  round 2: once as it wrote it, once as it entered the record.
- **`ToolReturnPart('Final result processed.')`**, the receipt for the output
  tool above. It is `0021`-shaped rather than a new exception — it carries no
  fact about the case, the statute, or another participant, and is not even about
  the agent's own last action in the way a retry prompt is. It is listed because
  a list of what escapes the invariant is worth nothing if it is incomplete.

### Intercepting a tool call is one method

`WrapperToolset.call_tool` receives the tool name, the validated arguments, the
`RunContext`, and the resolved tool, and its return value becomes the
`ToolReturnPart` content **verbatim**. That is the whole interception point
[`evidence.md`](./evidence.md#how-a-source-becomes-an-exhibit) needs.

Two things make it sufficient rather than merely available:

- **A `Tool`'s timeout raises inside the toolset it wraps.**
  `FunctionToolset.call_tool` applies `anyio.fail_after(timeout)` and converts a
  `TimeoutError` into `ModelRetry(f'Timed out after {timeout} seconds.')`
  (`toolsets/function.py:702-709`). A wrapper therefore *sees* the timeout, can
  record it, and re-raises it unchanged for PydanticAI to turn into a
  `RetryPromptPart`. `Transcript.ledger` and `Transcript.failures` are written at
  one seam, and `0022`'s `detail` is PydanticAI's own string rather than one
  `enbanc` composes.
- **`FunctionToolset(tools=…)` accepts plain functions and `Tool` instances
  alike**, so the `Tool(fn, timeout=…)` form
  [`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md) prescribes needs
  no separate path.

### Usage accumulates into an object the caller owns

`Agent.run(usage=u)` mutates `u` in place, and `result.usage` **is** `u`:

```text
after run 1, shared u: requests=2 input=300   | result.usage: 2 300
after run 2, shared u: requests=4 input=600   | result.usage: 4 600
same object: True

raised: RuntimeError('tool exploded')
usage after failure: requests=1 input=100 output=10
```

The second half is the load-bearing one: **a run that dies mid-flight leaves its
partial spend in the object**, because the object was never the run's to begin
with. That is what lets `usage_by_participant` name every participant that was
dispatched even on a failure, and it is why
[`api.md`](./api.md#when-something-goes-wrong) can say what it now says.

[`0024`](../decisions/0024-a-budget-stops-the-proceeding-between-rounds.md) used
this same mechanic to reject *one* accumulator shared across participants, and
that rejection is untouched: a shared object would report the whole proceeding's
spend under every key and erase
[`0014`](../decisions/0014-usage-is-broken-down-per-participant.md)'s breakdown.
One object **per participant** is the opposite — it is `0014`'s stored fact,
directly.

### Two retry budgets, not one

`Agent(retries=…)` takes `int | AgentRetries`, where `AgentRetries` is
`{'tools': int, 'output': int}` and a bare `int` sets both. **Both default to
`1`.** They are independent:

```text
same tool timing out N times:
  timeouts=1  retries=None          -> OK
  timeouts=2  retries=None          -> UnexpectedModelBehavior: Tool 'slow' exceeded
                                       max retries count of 1
  timeouts=2  retries={'tools': 3}  -> OK

tools=1 fully spent by a timeout, then two output-validation retries still available
  -> OK
```

Three facts follow, and all three matter:

- **A tool timeout and an unresolvable `_Exhibit.source` spend different
  budgets.** The first is `tools`, the second is `output`. A flaky tool cannot
  exhaust the budget that guards citation integrity, and vice versa.
- **Tool retries are counted per tool name** (`tool_manager.py:262`, keyed on
  `name`), not per run. `find_filings` failing twice is a separate budget from
  `web_search` failing twice — which is what makes `0020`'s "reach for another
  tool" a real move rather than a figure of speech.
- **`max_retries` resolves `tool → toolset → ctx`** (`agent/__init__.py:699`), so
  `Tool(fn, max_retries=…)` overrides the agent-level default for one tool.

### `max_concurrency` is set at construction

It is an `Agent.__init__` parameter and not a `run()` argument, normalized once
by `normalize_to_limiter` (`agent/__init__.py:719`). `0024` already records what
that forces — normalize the caller's value once per proceeding and hand the same
limiter object to every advocate agent — and this is where the constraint comes
from.

### A failing fan-out need not raise an `ExceptionGroup`

An anyio task group whose child raises propagates an `ExceptionGroup`, which
would put `enbanc` in the position of choosing one failure out of a set — exactly
the field
[`0012`](../decisions/0012-a-failure-cancels-the-round.md) closed by keeping
`participant` singular. It does not have to. A child that records its own failure
and cancels the scope lets the group exit cleanly:

```text
  refer: CANCELLED where it stood
first failure: deny -> RuntimeError("deny's provider is down")
filed: ['approve']          transcript: ['filing from approve']
```

That is [`outcomes.md`](./outcomes.md#an-advocates-provider-is-down) reproduced
exactly. **Re-raising the cancelled-exception class before the general handler is
load-bearing**: without it, `REFER`'s cancellation is caught and recorded as the
failure, and the exception would name the wrong participant.

## The proceeding, as messages

Three advocates, two rounds, `DENY` twice-questioned — eight runs across four
agents. Written out because every rule in the three pieces below is a rule about
this sequence, and because the last two times a rendering was written out it
found holes that reviewing the rule had not
([`journal/2026-09-04-writing-the-prompt-found-the-holes.md`](../journal/2026-09-04-writing-the-prompt-found-the-holes.md)).

Content matches [`prompting.md`](./prompting.md#the-turns)'s worked examples, so
the two documents cannot drift.

**The tribunal.** `verdicts = approve | deny | refer`, `max_rounds=5`,
`Judge(guidance="Where the record is ambiguous, deny.")`, and the `deny` advocate
alone steered with `"Weigh documented income over stated income."`

### The transcript this produces

| # | round | filing |
|---|---|---|
| 1 | 1 | `Argument(approve)` — cites `approve/s1` |
| 2 | 1 | `Argument(deny)` — cites `deny/s1` |
| 3 | 1 | `Concession(refer)` |
| 4 | 1 | `Continuance(r1-q1 → approve, r1-q2 → deny, r1-q3 → deny)` |
| 5 | 2 | `Response(approve, answering="r1-q1")` |
| 6 | 2 | `Response(deny, answering="r1-q2")` — cites `deny/s2` |
| 7 | 2 | `Response(deny, answering="r1-q3")` |
| 8 | 2 | `Ruling(deny)` |

Entries 1–3 arrive in a nondeterministic order, and 5 interleaves with 6
arbitrarily. **6 before 7 is the one ordering the design guarantees**
([`0027`](../decisions/0027-an-advocate-answers-its-interrogatories-in-order.md)).

### `since` and the snapshot, run by run

| Run | Participant | `since` in | Snapshot | Delta rendered | `since` out |
|---|---|---|---|---|---|
| 1 | approve | — | — | the case only; round 1 is blind | 0 |
| 2 | deny | — | — | the case only | 0 |
| 3 | refer | — | — | the case only | 0 |
| 4 | judge, deliberation 1 | 0 | entries 1–3 | 1, 2, 3 | 1 |
| 5 | approve, `r1-q1` | 0 | entries 1–4 | 1, 2, 3, 4 | 1 |
| 6 | deny, `r1-q2` | 0 | entries 1–4 | 1, 2, 3, 4 | 1 |
| 7 | deny, `r1-q3` | 1 | entries 1–4 **+ 6** | 6 alone | 2 |
| 8 | judge, deliberation 2 | 1 | entries 1–7 | 5, 6, 7 | 2 |

Runs 1–3 do not advance `since`: an advocate that argued blind was *shown*
nothing, and filing and being shown are different events.

Run 7 is the row that constrains the implementation. Its snapshot holds entry 6
and must not hold entry 5 **even when entry 5 landed first**, so a snapshot is
neither "the transcript now" nor "the transcript at the round boundary".

### `APPROVE`'s history — two runs, eight messages

Instruction parts, re-resolved every run and never in history: `procedural`,
`question`, `statute`, `assignment`. No `guidance` part — `approve` was given
none.

```text
RUN 1 — round 1, message_history=None

req 1   instructions=<4 parts>
        UserPromptPart:
          ## The case

          {
            "applicant": "A. Okonkwo",
            "income": 182000
          }

          Round 1. File your argument for "approve", or concede.

resp 1  ToolCallPart    find_filings(applicant="A. Okonkwo")

req 2   ToolReturnPart:
          find_filings(applicant="A. Okonkwo") returned 2 sources.

          [s1] Schedule C, 2024
            s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
            net profit: 182,000

          [s2] W-2, 2024
            s3://underwriting-docs/okonkwo/w2-2024.pdf
            wages: 131,400

resp 2  ToolCallPart    final_result_ArgumentLoanDecision(
                          kind="argument", advocate="approve",
                          claim="DTI is 0.38 on documented income.",
                          exhibits=[{source: "s1",
                                     content: "net profit: 182,000"}])

req 3   ToolReturnPart  'Final result processed.'
```

Ledger after run 1: `approve/s1` and `approve/s2`, both round 1. **`s2` is never
cited by anything.** Entry 1 is stamped, appended, and yielded; `history[approve]`
becomes these five messages.

```text
RUN 2 — round 2, r1-q1, message_history=<the five above>

req 4   instructions=<4 parts, re-resolved, byte-identical>
        UserPromptPart:
          ## Filed since you last filed

          [round 1] approve argued:
            DTI is 0.38 on documented income.
            Exhibits:
              [approve/s1] Schedule C, 2024
                s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
                net profit: 182,000

          [round 1] deny argued:
            Documented wages put DTI at 0.51.
            Exhibits:
              [deny/s1] W-2, 2024
                s3://underwriting-docs/okonkwo/w2-2024.pdf
                wages: 131,400

          [round 1] refer conceded:
            The ratios are unambiguous; nothing here calls for manual review.

          [round 1] the judge issued a continuance:
            r1-q1 -> approve: Does the W-2 reconcile with the Schedule C figure?
            r1-q2 -> deny: Is stated income disqualifying when documented income
              is on file?
            r1-q3 -> deny: Would a verified 2024 return change your answer?

          ## Addressed to you

          r1-q1: Does the W-2 reconcile with the Schedule C figure?

          Round 2. Answer r1-q1 and file your response.

resp 3  ToolCallPart    final_result_ResponseLoanDecision(
                          kind="response", advocate="approve",
                          answer="The Schedule C figure is gross; the W-2 is the "
                                 "reconciled number.",
                          exhibits=[])

req 5   ToolReturnPart  'Final result processed.'
```

Two things are visible here and nowhere else.

**`approve` reads its own round-1 argument twice, and the two differ.** In
`resp 2` it is the bare `_Exhibit(source="s1", content=…)` it wrote; in `req 4` it
is the public `Exhibit` with the tool, reference and label the tribunal stamped
beside them. That is the third bullet of
[What lands in history](#what-lands-in-history-that-no-rendered-turn-contains),
in the one place it is concrete.

**`approve/s2` appears in no rendered turn, ever.** It is in `req 2`'s tool
result — where `approve` read it, saw the wages figure that undercuts its own
claim, and declined to file it — and in `Transcript.ledger`, where a reviewer
finds it. Nothing else in the proceeding carries it. That is `0019`'s entire
argument, in two messages.

### `DENY`'s history — three runs, thirteen messages

Instruction parts: `procedural`, `question`, `statute`, `assignment`, `guidance`
— five, because `deny` was steered.

```text
RUN 1 — round 1
        As approve's run 1: the case turn, find_filings returning one source
        (deny/s1, the W-2), then final_result_ArgumentLoanDecision citing s1.
        Five messages.

RUN 2 — round 2, r1-q2, message_history=<the five above>

req 4   UserPromptPart:
          the same "## Filed since you last filed" block approve saw in its
          req 4 — identical snapshot, identical since=0, identical delta — then:

          ## Addressed to you

          r1-q2: Is stated income disqualifying when documented income is on file?

          Round 2. Answer r1-q2 and file your response.

resp 3  ToolCallPart    find_filings(applicant="A. Okonkwo", year=2024)

req 5   ToolReturnPart:
          find_filings(applicant="A. Okonkwo", year=2024) returned 1 source.

          [s2] W-2, 2024
            s3://underwriting-docs/okonkwo/w2-2024.pdf
            wages: 131,400

resp 4  ToolCallPart    final_result_ResponseLoanDecision(
                          answer="Yes — the statute's ceiling is on documented "
                                 "income.",
                          exhibits=[{source: "s2", content: "wages: 131,400"}])

req 6   ToolReturnPart  'Final result processed.'
```

Ledger gains `deny/s2`, round 2 — **`s2`, not `s3`**, because ids are numbered
within an advocate and `deny` has issued one before. Entry 6 is stamped,
appended and yielded, and `history[deny]` reaches ten messages, **before run 3 is
dispatched**.

```text
RUN 3 — round 2, r1-q3, message_history=<the ten above>

req 7   UserPromptPart:
          ## Filed since you last filed

          [round 2] deny responded to r1-q2:
            Yes — the statute's ceiling is on documented income.
            Exhibits:
              [deny/s2] W-2, 2024
                s3://underwriting-docs/okonkwo/w2-2024.pdf
                wages: 131,400

          ## Addressed to you

          r1-q3: Would a verified 2024 return change your answer?

          Round 2. Answer r1-q3 and file your response.

resp 5  ToolCallPart    final_result_ResponseLoanDecision(...)

req 8   ToolReturnPart  'Final result processed.'
```

Run 3's turn is the smallest in the proceeding. Its `since` is 1, so only round-2
filings in its snapshot render, and its own just-stamped response is the only one
there. `approve`'s entry 5 is excluded by the snapshot rather than by `since` —
the two mechanisms do different jobs, which is
[the second rule](#a-snapshot-is-constructed-not-sliced) below.

### `REFER`'s history — one run, three messages

```text
req 1   UserPromptPart:  the case turn, as approve's req 1 but for "refer"
resp 1  ToolCallPart     final_result_ConcessionLoanDecision(
                           kind="concession", advocate="refer",
                           reason="The ratios are unambiguous; nothing here "
                                  "calls for manual review.")
req 2   ToolReturnPart   'Final result processed.'
```

No tool calls, so no ledger rows and no failures. `refer` is never addressed
again and never runs again — which is what makes "an advocate that searched
nothing is distinguishable from one that searched and filed nothing"
([`outcomes.md`](./outcomes.md#1-the-judge-rules)) a fact about the record rather
than a hope.

### The judge's history — two runs, six messages

Instruction parts: `procedural`, `question`, `statute`, `guidance`. No
`assignment` — the judge is seated for no verdict.

```text
RUN 1 — deliberation 1, message_history=None

req 1   UserPromptPart:
          ## Round 1

          [round 1] approve argued:
            DTI is 0.38 on documented income.
            Exhibits:
              [approve/s1] Schedule C, 2024
                s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
                net profit: 182,000

          [round 1] deny argued:
            ...

          [round 1] refer conceded:
            ...

          Deliberation 1 of 5. Rule, or issue a continuance.

resp 1  ToolCallPart    final_result__ContinuanceLoanDecision(
                          interrogatories=[
                            {to: "approve", question: "Does the W-2 reconcile …"},
                            {to: "deny",    question: "Is stated income …"},
                            {to: "deny",    question: "Would a verified 2024 …"}])

req 2   ToolReturnPart  'Final result processed.'
```

The tribunal stamps `r1-q1`, `r1-q2`, `r1-q3` in emission order, converts to the
public `Continuance`, and files it as entry 4.

```text
RUN 2 — deliberation 2, message_history=<the three above>

req 3   UserPromptPart:
          ## Filed since you last deliberated

          [round 2] approve responded to r1-q1:
            The Schedule C figure is gross; the W-2 is the reconciled number.

          [round 2] deny responded to r1-q2:
            Yes — the statute's ceiling is on documented income.
            Exhibits:
              [deny/s2] W-2, 2024
                s3://underwriting-docs/okonkwo/w2-2024.pdf
                wages: 131,400

          [round 2] deny responded to r1-q3:
            ...

          Deliberation 2 of 5. Rule, or issue a continuance.

resp 2  ToolCallPart    final_result_RulingLoanDecision(
                          kind="ruling", verdict="deny", reasoning="…")

req 4   ToolReturnPart  'Final result processed.'
```

**The judge never sees the ids it caused.** It emitted three id-less
`_Interrogatory`s, and `r1-q1` exists only in the advocates' turns and in the
transcript. At deliberation 2 it reads `responded to r1-q2` and has to resolve
that against `resp 1`'s second interrogatory — **order is the only join it has.**

That is deliberate and it stays. Stamping is the tribunal's job precisely so that
no model authors a link ([`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)),
and re-rendering the judge's own continuance every deliberation to show it the
ids would pay per-round tokens for a fact that does not change, and would need a
per-participant carve-in that
[`prompting.md`](./prompting.md#one-renderer-three-viewpoints) says the projection
does not have. What was genuinely missing is smaller: the advocate's procedural
prompt explains its id scheme and the judge's explained none, so the judge met
`r1-q2` as a format nothing had described. One sentence in the judge's procedural
prompt now describes it, paid once in the cached instruction prefix.

## Piece 1 — message history and the transcript

[`tribunal.md`](./tribunal.md#constraints-that-define-the-design) states that each
agent carries its own conversation across rounds and that the history "is a
representation of the transcript — never a second channel". Three rules make that
mechanical.

### History is a dict, written after each run

`history: dict[Participant, list[ModelMessage]]`, assigned from
`result.all_messages()` when a run returns. A first run passes `None`.

**A cancelled or failed run writes nothing, and nothing needs it to.** There is
no partial `result` to read `all_messages()` off, so the participant's entry stays
as its previous round left it. That is harmless because nothing resumes: the first
failure ends the proceeding
([`0012`](../decisions/0012-a-failure-cancels-the-round.md)), the history dict is
local to `hear()`, and it is discarded with everything else when `hear()` returns
([`api.md`](./api.md#design-commitments)). A design in which a proceeding could
resume would have to answer this; this one deletes the question rather than
answering it.

### A snapshot is constructed, not sliced

**The snapshot for every run of round *N* is the transcript as the continuance
closed round *N*−1, plus — for a second or later run of the same advocate — that
advocate's own filings already made in round *N*.** Nothing else from round *N* is
ever in it.

The word *constructed* is the whole point. Run 7's snapshot holds entries 1–4 and
entry 6, and it must exclude entry 5 **even though entry 5 may already be in the
transcript** — `approve` and `deny` run concurrently and either may file first. So
a snapshot cannot be a prefix of the live transcript, and it cannot be a slice of
it either.

Mechanically: the orchestrator takes one base snapshot per round, at the moment
the continuance is filed, and hands the *same* list to every task in that round.
An advocate's task keeps a local extension of it and appends its own stamped
filings as they are acknowledged. Nothing reads shared mutable state, which is
also why a concurrent round is safe to render at all — a peer filing at the same
moment is not in anyone's snapshot, so no ordering artifact can reach a context
and [`0023`](../decisions/0023-advocates-argue-blind-and-rebut-informed.md) holds
unchanged.

### `since` advances once per run, not once per round

`since: dict[Participant, int]` is the last round whose filings this participant
has been shown. A view renders every filing in the snapshot from a round *after*
it, in transcript order.

`since` and the snapshot are two pieces of state advanced at different moments,
and run 7 is where that separation earns its place: `since=1` selects round-2
filings, and the snapshot decides *which* round-2 filings exist to select from.
Either alone would be wrong — `since` alone would admit `approve`'s entry 5, and
the snapshot alone would re-render the four round-1 entries the advocate's own
history already carries.

Round 1 does not advance `since`, because an advocate that argued blind was shown
nothing. **An advocate's own filing is in its delta** and is not carved out, for
the reason [`prompting.md`](./prompting.md#one-renderer-three-viewpoints) gives:
the projection stays a plain filter, and what the advocate emitted is not what
entered the record.

## Piece 2 — the ledgering toolset

[`evidence.md`](./evidence.md#how-a-source-becomes-an-exhibit) specifies the
behaviour: a toolset `enbanc` owns wraps everything the advocate was given,
intercepts every call, assigns ids, writes
[`Transcript.ledger`](./api.md#the-record) and `Transcript.failures`, and rewrites
what the model sees so the ids are citable. Given
[the interception finding](#intercepting-a-tool-call-is-one-method), the shape is
small.

### One wrapper over one combined toolset

```python
Ledgering(
    wrapped=CombinedToolset([
        FunctionToolset(tools=advocate.tools),   # plain functions and Tool(...) alike
        *advocate.toolsets,                      # MCP servers, FunctionToolset, anything
    ])
)
```

That object is the agent's **only** `toolsets=` argument, and no `tools=` is
passed. Routing everything through one wrapper is what makes "intercepts every
call" true of an MCP server as well as of a function — `enbanc` never sees the
difference, because `CombinedToolset` has already erased it.

**One `Ledgering` instance per advocate, living the whole proceeding.** It is
what holds the id counter, and holding it across rounds is what lets a round-3
response cite a round-1 find ([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)).
It is per advocate because an advocate's tool calls are sequential — which
`0027`'s dispatch rule now protects from the inside — so its ids are deterministic
run to run, where one counter shared across concurrent advocates would not be.

### What `call_tool` does

```python
async def call_tool(self, name, tool_args, ctx, tool) -> Any:
    call = render_call(name, tool_args)         # 'find_filings(applicant="A. Okonkwo")'
    try:
        result = await super().call_tool(name, tool_args, ctx, tool)
    except ModelRetry as e:
        self.failures.append(ToolFailure(round=self.round, advocate=self.advocate,
                                         tool=name, reference=call, detail=str(e)))
        raise                                   # PydanticAI makes it a RetryPromptPart
    sources = as_sources(result, fallback_reference=call)
    rows = [Retrieval(id=self.next_id(), round=self.round, advocate=self.advocate,
                      tool=name, reference=s.reference, content=s.content,
                      label=s.label)
            for s in sources]
    self.ledger.extend(rows)
    return render_results(call, rows)           # prompting.md's format, verbatim
```

**The `except` catches `ModelRetry` specifically**, which is what a timeout
becomes, and re-raises it untouched so the advocate is told exactly what
PydanticAI would have told it. A tool that *raises* anything else is not caught
here: it propagates, ends the round, and surfaces as `ProceedingFailed`
([`evidence.md`](./evidence.md#what-tools-may-do)). The difference between a
degraded advocate and an unheard one is one `except` clause, and it is this one.

**`round` is set on the instance by the orchestrator before each dispatch.** The
toolset outlives every round, because the id counter has to; `Retrieval.round` and
`ToolFailure.round` do not. A mutable attribute is the seam between the two
lifetimes, and it is safe to mutate because an advocate's runs are sequential.

**`as_sources` is the `Source`-shape test.** A `Source`, or a sequence of them,
is taken as written. Anything else — a string, a dict, a model, an MCP payload —
becomes one anonymous `Source` whose `reference` is the rendered call and whose
`content` is the value stringified. `enbanc` sniffs the shape rather than
requiring a declaration, which is what keeps every existing PydanticAI tool
usable with no adaptation
([`evidence.md`](./evidence.md#a-reference-is-what-makes-an-exhibit-auditable)).

### The output validator resolves ids

An advocate's `_Exhibit.source` is checked against the same instance's ledger by
an output validator, which raises `ModelRetry` for an id the advocate was never
issued. That spends the **`output`** budget, not the `tools` one — so an advocate
whose search tool is flapping still has its full citation budget, and an advocate
inventing citations cannot be masked by a healthy tool. This is
[`evidence.md`](./evidence.md#an-unresolvable-id-is-a-validation-failure) with the
budget named.

## Piece 3 — round orchestration

### The filing clerk

**One coroutine owns the transcript.** Tasks send it completed filings; it stamps
`filed_at`, converts private types to public, appends to `transcript.entries`,
sends to the stream, and acknowledges the sender.

```python
async def clerk(inbox, transcript, out):
    async for filing, round_no, done in inbox:
        entry = Entry(round=round_no, filed_at=datetime.now(UTC), filing=filing)
        transcript.entries.append(entry)
        await out.send(entry)
        done.set()
```

This exists to make one sentence true by construction.
[`0010`](../decisions/0010-streaming-yields-the-record.md) promises that *the
entry just received is the last entry of `proceeding.transcript`*. If each task
appended and then sent, a sibling could append between the two operations and a
consumer would receive entry 5 while `transcript[-1]` was entry 6 — the live view
and the record disagreeing about a proceeding whose whole product is that they do
not. With a single owner there is no interleaving to reason about.

The acknowledgment is not overhead bought for this guarantee; `0027` needs it
independently. `DENY`'s run 3 must not be dispatched until entry 6 is in the
record, because entry 6 is in run 3's snapshot.

**Both private-to-public conversions happen here**, at the filing seam:
`_Continuance` → `Continuance` with `r{round}-q{n}` stamped in emission order
([`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)), and
`_Exhibit` → `Exhibit` resolved against the advocate's ledger
([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)). That is the same
seam and the same principle as the `Entry` envelope one level up: every field
whose correctness the record depends on is filled by the tribunal, at the moment a
filing enters the record, from something the tribunal observed.

### The round's task group

One task per **addressed advocate**, with that advocate's interrogatories queued
sequentially inside it — `0027`'s shape, not one task per interrogatory. Round 1
addresses every advocate; later rounds address whoever the continuance named.

Each task holds:

```python
try:
    ...run, file, await the ack, run again for the next interrogatory...
except anyio.get_cancelled_exc_class():
    raise                                     # a peer failed; die where we stand
except BaseException as e:
    if first.participant is None:
        first.participant, first.exc = participant, e
    tg.cancel_scope.cancel()
```

**The cancelled-exception re-raise comes first and is load-bearing.** Without it a
cancelled sibling is caught by the general handler and may win the race to fill
`first`, and `ProceedingFailed` would name an advocate that was merely stopped
rather than the one that failed.

**The group exits cleanly and the orchestrator raises afterwards**, with
`first.exc` as `__cause__`. So `ProceedingFailed.participant` is singular because
only one slot is ever filled — not because `enbanc` picked one out of an
`ExceptionGroup`. That is `0012`'s guarantee held structurally.

**The concurrency limiter is normalized once and shared.**
`normalize_to_limiter(max_concurrency)` at the start of the proceeding, and the
same object into every advocate's `Agent(max_concurrency=…)`. The judge's agent
gets none: it runs alone, and the fan-out is the only place concurrency exists
([`0024`](../decisions/0024-a-budget-stops-the-proceeding-between-rounds.md)).

### Usage

**One `RunUsage` per participant, minted at the start of the proceeding**, passed
as `run(usage=…)` to every run that participant makes. The dict of them *is*
`usage_by_participant`; `Hearing.usage` is its sum, computed rather than
accumulated beside it, so the two cannot disagree
([`0014`](../decisions/0014-usage-is-broken-down-per-participant.md)).

Because the objects are the orchestrator's and are mutated in place, **a run that
was cancelled or that died mid-flight still leaves what it spent**. Every
participant that was dispatched therefore has a key, on a `ProceedingFailed` as
well as on a `Hearing`, and absence means *never dispatched*. See
[`0028`](../decisions/0028-usage-accumulates-per-participant.md).

### The round loop

```python
round_no, addressed = 1, every_advocate         # round 1 is the full bench
while True:
    await dispatch_advocates(round_no, addressed)
    deliberation = await deliberate(round_no)
    if isinstance(deliberation, Ruling):
        outcome = deliberation;                              break
    if round_no == max_rounds:
        outcome = Undecided(reason="rounds");                break
    if budget_exceeded(usage_by_participant):
        outcome = Undecided(reason="budget");                break
    round_no += 1
    addressed = advocates_addressed_by(deliberation)
```

**`max_rounds` is tested before the budget.** A proceeding that hit both is
recorded as having run out of rounds — the limit every tribunal has, and the one
that needs no measurement to establish.

**There is no budget check before round 1.** Nothing has been spent, and a
proceeding always runs at least one round; a caller who set a ceiling of zero gets
one round and then `Undecided(reason='budget')`, which is the coarse-governor cost
`0024` accepted stated at its smallest.

### The budget check

Against the sum of the per-participant accumulators, with `0024`'s three checkers
unchanged:

```python
if first_boundary:
    budget.check_cost(total, warn_if_cost_unavailable=True)   # CostNotFoundWarning
budget.check_before_request(total)     # request_limit, cost, input and total tokens
budget.check_tokens(total)             # and output_tokens_limit
budget.check_before_tool_call(total)   # tool_calls_limit
```

`UsageLimitExceeded` is the **stop signal**, caught and turned into
`Undecided(reason="budget")` — not an error to propagate. A budget is an envelope
the caller declared, so reaching it is an ordinary end
([`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md)).

**The cost warning fires once per proceeding, not once per round.**
`check_cost(warn_if_cost_unavailable=True)` emits `CostNotFoundWarning` when a
`cost_limit` is set and the model could not be priced — a standing condition that
does not change between rounds, so repeating it every round would be noise about
the same fact. Once is what a caller needs, and needs badly: an unpriceable model
makes `cost_limit` enforce nothing at all, and the token and request limits are
the only governors left.

**`budget.request_limit` must have been chosen**, which `Tribunal(...)` enforces
at construction — see [below](#configurationerror-has-four-cases) and
[`0029`](../decisions/0029-a-budgets-request-limit-must-be-chosen.md).

## Also in scope

**One `Agent` per participant, constructed inside `hear()` and discarded when it
returns.** With it goes the history dict, the `since` dict, the ledgering
toolsets, and the usage accumulators — every piece of per-proceeding state named
above. That is the split [`api.md`](./api.md#design-commitments) commits to under
"Agents are reusable; a proceeding's state is not", and it is what makes `hear()`
safe to call twice and safe to run concurrently over several cases.

**`retries={'tools': 3, 'output': 2}` on every agent `enbanc` builds.** Three
failures of the *same* tool before an advocate is treated as unheard — enough for
[`outcomes.md`](./outcomes.md#1-the-judge-rules)'s two timed-out searches to be a
degraded advocate rather than a dead proceeding, and per-tool-name counting means
reaching for a different tool costs nothing. Two output retries: one correction
usually fixes a miscited id, and two covers a stubborn model without paying
indefinitely for a broken one.

Neither number is configurable through `enbanc`
([`0009`](../decisions/0009-model-settings-live-on-the-model.md)), but the `tools`
half is overridable per tool where it belongs — `Tool(fn, timeout=…,
max_retries=…)`, the same object `0020` put the timeout on, resolving
`tool → toolset → ctx`. A warehouse query and a third-party search API do not want
the same tolerance any more than they want the same timeout. The `output` budget
stays unreachable, because it guards the `Ruling | Continuance` contract the
library owns. See
[`0030`](../decisions/0030-the-retry-budgets.md).

**`enbanc` passes no `usage_limits` into any run**, so PydanticAI's inherited
default stands: fifty model requests per participant per round. A run that
exhausts it is a participant that could not be heard. That fifty and a `budget`'s
`request_limit` are different numbers at different scopes, which is why the latter
may not be inherited.

**`hear()` is `hear_stream()` driven to exhaustion.** Literally — it opens the
context manager, consumes the iterator, discards the entries, and returns
`proceeding.hearing`. There is one implementation of a proceeding, and the two
entry points cannot come apart
([`0010`](../decisions/0010-streaming-yields-the-record.md)).

### `ConfigurationError` has four cases

All raised from `Tribunal(...)`, never from `hear()`, because a tribunal that
cannot be built has nothing to record and no transcript to carry:

- `advocates` is missing a verdict;
- `advocates` names a key that is not a verdict;
- a verdict's value is the reserved string `"judge"`
  ([`0014`](../decisions/0014-usage-is-broken-down-per-participant.md));
- `budget` was passed with `request_limit` still at `UsageLimits`' own default of
  `50` ([`0029`](../decisions/0029-a-budgets-request-limit-must-be-chosen.md)).

The last two are the same move. A `StrEnum` member valued `"judge"` and an
inherited `request_limit` both look like an ordinary configuration and both
silently mean something the caller did not write — one collapsing two
participants into one usage entry, the other capping a proceeding at fifty
requests in the name of a cost limit. Converting each into a loud construction
error is cheaper than any amount of documentation.

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. See rule 7 in [`../../CLAUDE.md`](../../CLAUDE.md).

*None open.* This was the last document required before `0.1.0`, and
[`docs/design/`](./) now describes a complete system.
