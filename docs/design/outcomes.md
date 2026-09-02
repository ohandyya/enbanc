---
status: draft
updated: 2026-09-02
---

# Every way a proceeding ends

Worked examples of what `hear()` actually hands back. The types are specified in
[`api.md`](./api.md) and the reasoning is in
[`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md);
this is the same surface with values in it.

> `status: draft` — none of this runs yet. The values below are what the design
> commits to, written out.

## At a glance

| Ending | `hear()` | `hearing.outcome` | The transcript ends on |
|---|---|---|---|
| The judge rules | returns a `Hearing` | `Ruling(...)` | that same `Ruling` |
| `max_rounds` is spent | returns a `Hearing` | `Undecided()` | a `Continuance` |
| A participant cannot be heard | raises `ProceedingFailed` | — | wherever it stopped |
| The tribunal is misconfigured | never runs — `Tribunal(...)` raises | — | there is none |

Two endings, one interruption, and one thing that never starts. Only the first
two produce a `Hearing`, which is the whole of the division: a `Hearing` means
the tribunal reached the end of its own process.

## The tribunal these examples use

```python
class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"
    REFER = "refer to a senior underwriter for manual review"

tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,
    statute=Statute(
        text="Approve $500k loans only where DTI < 0.43 and ...",
        name="underwriting-v3",
    ),
    model=AnthropicModel("claude-sonnet-5"),
    judge=Judge(guidance="Where the record is ambiguous, deny."),
    advocates={
        LoanDecision.APPROVE: Advocate(tools=[psql, tavily]),
        LoanDecision.DENY: Advocate(tools=[psql]),
        LoanDecision.REFER: Advocate(tools=[psql]),
    },
    max_rounds=5,
)

case = Case(applicant="A. Okonkwo", income=182000)
```

## 1. The judge rules

Three advocates argue, one concedes, the judge asks two questions and then
rules.

```text
round 1   Argument(advocate=APPROVE, exhibits=[psql, tavily])
          Argument(advocate=DENY,    exhibits=[psql])
          Concession(advocate=REFER)
          Continuance(interrogatories=[r1-q1 -> APPROVE, r1-q2 -> DENY])

round 2   Response(advocate=APPROVE, answering="r1-q1")
          Response(advocate=DENY,    answering="r1-q2", exhibits=[psql])
          Ruling(verdict=DENY)
```

```python
hearing = await tribunal.hear(case)
```

`hearing` is bound to:

```python
Hearing(
    outcome=Ruling(
        kind='ruling',
        verdict=<LoanDecision.DENY: 'deny'>,
        reasoning='Documented income governs. The W-2 record puts DTI at 0.51, '
                  'above the 0.43 ceiling; the stated figure is unverified.',
    ),
    transcript=Transcript(
        question='Shall the bank loan this applicant $500k?',
        statute=Statute(
            text='Approve $500k loans only where DTI < 0.43 and ...',
            name='underwriting-v3',
        ),
        case=Case(applicant='A. Okonkwo', income=182000),
        entries=[
            Entry(
                round=1,
                filed_at=datetime(2026, 9, 2, 14, 3, 11, tzinfo=UTC),
                filing=Argument(
                    kind='argument',
                    advocate=<LoanDecision.APPROVE: 'approve'>,
                    claim='DTI is 0.38 on documented income.',
                    exhibits=[
                        Exhibit(source='psql', content='schedule_c_2024: 182000'),
                        Exhibit(source='tavily', content='...'),
                    ],
                ),
            ),
            Entry(
                round=1,
                filed_at=datetime(2026, 9, 2, 14, 3, 14, tzinfo=UTC),
                filing=Argument(
                    kind='argument',
                    advocate=<LoanDecision.DENY: 'deny'>,
                    claim='Stated income unverified; DTI is 0.51 on W-2s.',
                    exhibits=[Exhibit(source='psql', content='w2_2024: 131400')],
                ),
            ),
            Entry(
                round=1,
                filed_at=datetime(2026, 9, 2, 14, 3, 15, tzinfo=UTC),
                filing=Concession(
                    kind='concession',
                    advocate=<LoanDecision.REFER: 'refer to a senior ...'>,
                    reason='The record is not ambiguous enough to warrant '
                           'manual review; both figures are documented.',
                ),
            ),
            Entry(
                round=1,
                filed_at=datetime(2026, 9, 2, 14, 3, 22, tzinfo=UTC),
                filing=Continuance(
                    kind='continuance',
                    interrogatories=[
                        Interrogatory(
                            id='r1-q1',
                            to=<LoanDecision.APPROVE: 'approve'>,
                            question='Which income figure does §4.2 require?',
                        ),
                        Interrogatory(
                            id='r1-q2',
                            to=<LoanDecision.DENY: 'deny'>,
                            question='Does the Schedule C qualify as documented?',
                        ),
                    ],
                ),
            ),
            Entry(
                round=2,
                filed_at=datetime(2026, 9, 2, 14, 3, 31, tzinfo=UTC),
                filing=Response(
                    kind='response',
                    advocate=<LoanDecision.APPROVE: 'approve'>,
                    answering='r1-q1',
                    answer='§4.2 permits self-employment income where filed.',
                    exhibits=[],
                ),
            ),
            Entry(
                round=2,
                filed_at=datetime(2026, 9, 2, 14, 3, 35, tzinfo=UTC),
                filing=Response(
                    kind='response',
                    advocate=<LoanDecision.DENY: 'deny'>,
                    answering='r1-q2',
                    answer='Filed but unaudited; §4.2 requires verification.',
                    exhibits=[
                        Exhibit(source='psql', content='verification_status: none'),
                    ],
                ),
            ),
            Entry(
                round=2,
                filed_at=datetime(2026, 9, 2, 14, 3, 44, tzinfo=UTC),
                filing=Ruling(
                    kind='ruling',
                    verdict=<LoanDecision.DENY: 'deny'>,
                    reasoning='Documented income governs. ...',
                ),
            ),
        ],
    ),
    usage=RunUsage(
        requests=8,
        tool_calls=5,
        input_tokens=61402,
        output_tokens=3980,
        cache_read_tokens=44100,
        details={},
    ),
    rounds=2,
)
```

Things worth reading off it:

```python
hearing.outcome.verdict                              # <LoanDecision.DENY: 'deny'>
hearing.rounds                                       # 2 — not 5, the budget
len(hearing.transcript)                              # 7
hearing.outcome is hearing.transcript[-1].filing     # True — a pointer, not a copy
```

**The concession is not a failure.** `REFER` looked at the record, found no case
worth making, and said so. That filing is why the transcript explains a
two-horse ruling in a three-verdict tribunal.

**`rounds` counts deliberations, not filings.** Seven entries, two rounds: a
round is the advocates' filings plus the `Continuance` or `Ruling` that closes
it.

## 2. The judge rules in round 1

The cheapest proceeding there is — the record is clear enough that no
interrogatory is needed.

```text
round 1   Argument(advocate=APPROVE, exhibits=[psql])
          Argument(advocate=DENY,    exhibits=[psql, tavily])
          Concession(advocate=REFER)
          Ruling(verdict=APPROVE)
```

```python
Hearing(
    outcome=Ruling(
        kind='ruling',
        verdict=<LoanDecision.APPROVE: 'approve'>,
        reasoning='DTI is 0.31 on audited returns; no clause is in tension.',
    ),
    transcript=Transcript(..., entries=[...]),           # 4 entries
    usage=RunUsage(requests=4, tool_calls=3, input_tokens=21050, ...),
    rounds=1,
)
```

A `Continuance` never appears. `max_rounds=5` is a ceiling, not a target.

## 3. The round limit is spent

Same tribunal, but built with `max_rounds=2`. The judge asks, gets answers,
and still cannot rule.

```text
round 1   Argument(APPROVE), Argument(DENY), Concession(REFER)
          Continuance(interrogatories=[r1-q1 -> APPROVE, r1-q2 -> DENY])

round 2   Response(APPROVE), Response(DENY)
          Continuance(interrogatories=[r2-q1 -> APPROVE, r2-q2 -> DENY])
          ^ the second deliberation is max_rounds. No round 3 follows.
```

```python
hearing = await tribunal.hear(case)      # returns normally — nothing raises
```

```python
Hearing(
    outcome=Undecided(kind='undecided'),
    transcript=Transcript(
        question='Shall the bank loan this applicant $500k?',
        statute=Statute(text='...', name='underwriting-v3'),
        case=Case(applicant='A. Okonkwo', income=182000),
        entries=[
            # ... rounds 1 and 2 as above; the last entry is:
            Entry(
                round=2,
                filed_at=datetime(2026, 9, 2, 14, 4, 2, tzinfo=UTC),
                filing=Continuance(
                    kind='continuance',
                    interrogatories=[
                        Interrogatory(
                            id='r2-q1',
                            to=<LoanDecision.APPROVE: 'approve'>,
                            question='Can you produce an audited 2024 return?',
                        ),
                        Interrogatory(
                            id='r2-q2',
                            to=<LoanDecision.DENY: 'deny'>,
                            question='Would verification alone resolve this?',
                        ),
                    ],
                ),
            ),
        ],
    ),
    usage=RunUsage(requests=7, tool_calls=4, input_tokens=58800, ...),
    rounds=2,
)
```

```python
hearing.rounds                                       # 2 == max_rounds
hearing.outcome is hearing.transcript[-1].filing     # False — nobody filed it
[i.question for i in hearing.transcript[-1].filing.interrogatories]
# ['Can you produce an audited 2024 return?',
#  'Would verification alone resolve this?']
```

**`Undecided()` has one field, the `kind` tag, and that is deliberate.** What
the judge still wanted is already in the record — the interrogatories on the
final `Continuance` — and how much budget was spent is `hearing.rounds`.
Copying either onto the outcome would create two places that can disagree.

**You still pay for it.** `hearing.usage` reports what an undecided proceeding
cost, exactly as a decided one does.

**This is not an error.** It serializes, it carries a complete record of why it
stopped, and a reviewer can pick it up. Handing a hard case back undecided is a
finding about the case.

## 4. A participant cannot be heard

Any of three things — an unreachable provider, a tool that raises, output that
will not validate after retries — ends the proceeding and raises
`ProceedingFailed`. `hearing` is never bound.

### An advocate's provider is down

Advocates fan out concurrently, so `APPROVE` files before `DENY`'s model call
gives up.

```text
round 1   Argument(advocate=APPROVE, exhibits=[psql, tavily])
          <DENY's provider unreachable; the caller's retry transport gave up>
```

```python
try:
    hearing = await tribunal.hear(case)
except ProceedingFailed as e:
    ...
```

`e` is:

```python
ProceedingFailed(
    participant=<LoanDecision.DENY: 'deny'>,
    round=1,
    transcript=Transcript(
        question='Shall the bank loan this applicant $500k?',
        statute=Statute(text='...', name='underwriting-v3'),
        case=Case(applicant='A. Okonkwo', income=182000),
        entries=[
            Entry(
                round=1,
                filed_at=datetime(2026, 9, 2, 14, 3, 11, tzinfo=UTC),
                filing=Argument(
                    kind='argument',
                    advocate=<LoanDecision.APPROVE: 'approve'>,
                    claim='DTI is 0.38 on documented income.',
                    exhibits=[
                        Exhibit(source='psql', content='schedule_c_2024: 182000'),
                    ],
                ),
            ),
        ],
    ),
    usage=RunUsage(requests=1, tool_calls=1, input_tokens=7020, output_tokens=410),
)
```

and the traceback names the real cause:

```text
anthropic.APIConnectionError: Connection error.

The above exception was the direct cause of the following exception:

enbanc.ProceedingFailed: advocate 'deny' could not be heard in round 1
```

**The judge never deliberated**, so nothing was decided and there is no
`Hearing` to mistake for one. `APPROVE`'s argument survives on
`e.transcript` because it had already filed.

**`REFER` is absent from the record**, because it had not filed yet. Whether an
advocate still in flight when a sibling fails is cancelled outright, or allowed
to land its filing first, is [an open question](./api.md#open-questions). The
transcript above shows the cancelling answer; under the other it would carry one
more entry.

### The judge's provider is down

Same failure, one participant later — all three advocates filed, and the
deliberation that would have closed round 1 never happened.

```python
ProceedingFailed(
    participant='judge',
    round=1,
    transcript=Transcript(..., entries=[...]),      # 3 entries, no Continuance
    usage=RunUsage(requests=3, tool_calls=3, input_tokens=19400, ...),
)
```

`participant` is `'judge'`, the one non-verdict value it can take.

### An advocate's tool raises

Nothing to do with the model — `psql` is down, and the tool function raises in
round 2 while answering an interrogatory.

```python
ProceedingFailed(
    participant=<LoanDecision.DENY: 'deny'>,
    round=2,
    transcript=Transcript(..., entries=[...]),      # 5 entries: round 1 complete,
                                                    # plus APPROVE's response
    usage=RunUsage(requests=6, tool_calls=4, ...),
)
# e.__cause__ is psycopg.OperationalError('connection refused')
```

Same type, same shape. From the caller's side an agent could not file, and why
is `__cause__`'s business.

**`round` is where it stopped, not how far it got.** Round 1 completed; the
failure is in round 2. There is no `rounds` field here — a round completes when
its deliberation is filed, so failing in round *N* always leaves *N-1* behind,
and carrying both would store one fact twice.

**Nothing was retried by `enbanc`.** By the time you see this, the retry policy
on the httpx client inside your own `Model` has already given up. See
[`0009`](../decisions/0009-model-settings-live-on-the-model.md).

## 5. The tribunal is misconfigured

No proceeding runs at all — this raises from the constructor.

```python
tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,          # APPROVE, DENY, REFER
    statute=statute,
    model=model,
    judge=Judge(),
    advocates={
        LoanDecision.APPROVE: Advocate(tools=[psql]),
        LoanDecision.DENY: Advocate(tools=[psql]),
        # REFER is missing
    },
)
```

```text
enbanc.ConfigurationError: advocates is missing a verdict: 'refer to a senior
underwriter for manual review'
```

An unknown key raises the same way. `ConfigurationError` carries no transcript
because nothing ran, which is why it sits beside `ProceedingFailed` rather than
under it.

This is what makes adding an enum member a loud failure instead of a silent
one: a new verdict with no advocate would otherwise be an answer nobody was
assigned to argue for.

## 6. The same endings, watched live

`hear_stream()` yields the entries as they are filed. What differs between the
cases is only how the loop ends.

**A ruling** — the loop ends after the `Ruling`:

```python
async with tribunal.hear_stream(case) as proceeding:
    async for entry in proceeding:
        print(f"round {entry.round}: {entry.filing.kind}")
        # round 1: argument, argument, concession, continuance
        # round 2: response, response, ruling

proceeding.hearing.outcome        # Ruling(verdict=<LoanDecision.DENY: 'deny'>, ...)
```

**The round limit** — the loop ends after the final `Continuance`, and nothing
raises:

```python
        # round 1: argument, argument, concession, continuance
        # round 2: response, response, continuance
        #                              ^ last entry; max_rounds spent

proceeding.hearing.outcome        # Undecided(kind='undecided')
```

**A failure** — the exception comes out of the `async with`, not the `async
for`, and the partial record is still readable:

```python
try:
    async with tribunal.hear_stream(case) as proceeding:
        async for entry in proceeding:
            ...                   # round 1: argument
except ProceedingFailed as e:
    len(e.transcript)             # 1
    len(proceeding.transcript)    # 1 — the same entries
```

**Walking away** — break out, and there was no hearing:

```python
async with tribunal.hear_stream(case) as proceeding:
    async for entry in proceeding:
        if entry.filing.kind == "continuance":
            break                 # in-flight runs are cancelled here

len(proceeding.transcript)        # 4 — everything filed before you left
proceeding.hearing                # raises ProceedingUnfinished
```

`ProceedingUnfinished` is for a proceeding still running or one you abandoned.
A proceeding that *failed* re-raises its `ProceedingFailed` from
`proceeding.hearing` instead, so the reason is never downgraded to "unfinished".

## 7. Persisting a hearing and reading it back

Both endings are Pydantic models all the way down, which is what makes the
audit artifact an artifact:

```python
blob = hearing.model_dump_json()
restored = Hearing[LoanDecision].model_validate_json(blob)

restored.outcome.verdict          # <LoanDecision.DENY: 'deny'> — a real enum member
restored.transcript[3].filing     # Continuance(...), not a dict
```

The `kind` tags are what make this work: Pydantic discriminates on them rather
than guessing a union member from field shape, so a `Ruling` comes back a
`Ruling` and an `Undecided` comes back an `Undecided`.

One thing does *not* survive the round trip:

```python
restored.outcome is restored.transcript[-1].filing    # False
hearing.outcome is hearing.transcript[-1].filing      # True
```

In memory the outcome is a pointer to the terminal filing. Through JSON it is
written twice and read back as two equal objects. They compare equal; they are
not the same object.

`Transcript` is self-contained on its own, so persisting only the record is
also legitimate — it carries the question, statute, and case, and needs no
`Hearing` to be legible.

## What is not here

**A forced verdict.** No ending in this document converts "we could not decide"
into a decision. `Undecided` is the answer to a spent round limit, and it stays
an answer.

**A ruling on a partial bench.** There is no example of the judge ruling after
an advocate dropped out, because the design has none: a participant that cannot
be heard ends the proceeding. An advocate that *concedes* is a different thing
entirely, and case 1 shows it.

**Partial filings.** Nothing yields half an argument, in the stream or in the
record. See [`0010`](../decisions/0010-streaming-yields-the-record.md).
