---
status: draft
updated: 2026-09-04
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
        LoanDecision.APPROVE: Advocate(tools=[psql, web_search(api_key=...)]),
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
round 1   Argument(advocate=APPROVE, exhibits=[psql, web_search])
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
                        Exhibit(
                            source='s1',
                            tool='psql',
                            reference='psql(sql="SELECT net_profit FROM '
                                      'schedule_c WHERE applicant = ...")',
                            content='schedule_c_2024: 182000',
                        ),
                        Exhibit(
                            source='s3',
                            tool='web_search',
                            reference='https://www.irs.gov/forms-pubs/about-schedule-c-form-1040',
                            label='About Schedule C (Form 1040)',
                            content='Net profit from Schedule C is reportable '
                                    'self-employment income.',
                        ),
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
                    exhibits=[
                        Exhibit(
                            source='s1',
                            tool='psql',
                            reference='psql(sql="SELECT wages FROM w2 '
                                      'WHERE applicant = ...")',
                            content='w2_2024: 131400',
                        ),
                    ],
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
                        Exhibit(
                            source='s2',
                            tool='psql',
                            reference='psql(sql="SELECT verification_status '
                                      'FROM income_docs WHERE ...")',
                            content='verification_status: none',
                        ),
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
        ledger=[
            # APPROVE's tools returned three sources; it filed two.
            Retrieval(
                id='s1', round=1, advocate=<LoanDecision.APPROVE: 'approve'>,
                tool='psql',
                reference='psql(sql="SELECT net_profit FROM schedule_c '
                          'WHERE applicant = ...")',
                content='schedule_c_2024: 182000',
            ),
            Retrieval(
                id='s2', round=1, advocate=<LoanDecision.APPROVE: 'approve'>,
                tool='psql',
                reference='psql(sql="SELECT verification_status FROM '
                          'income_docs WHERE ...")',
                content='verification_status: none',   # never cited by APPROVE
            ),
            Retrieval(
                id='s3', round=1, advocate=<LoanDecision.APPROVE: 'approve'>,
                tool='web_search',
                reference='https://www.irs.gov/forms-pubs/about-schedule-c-form-1040',
                label='About Schedule C (Form 1040)',
                content='Net profit from Schedule C is reportable '
                        'self-employment income.',
            ),
            # DENY's, numbered from s1 again — ids are per advocate.
            Retrieval(
                id='s1', round=1, advocate=<LoanDecision.DENY: 'deny'>,
                tool='psql',
                reference='psql(sql="SELECT wages FROM w2 WHERE applicant = ...")',
                content='w2_2024: 131400',
            ),
            Retrieval(
                id='s2', round=2, advocate=<LoanDecision.DENY: 'deny'>,
                tool='psql',
                reference='psql(sql="SELECT verification_status FROM '
                          'income_docs WHERE ...")',
                content='verification_status: none',
            ),
            # REFER conceded without calling a tool, so it has no retrievals.
        ],
        failures=[
            # Why APPROVE's round-2 response cites nothing.
            ToolFailure(
                round=2, advocate=<LoanDecision.APPROVE: 'approve'>,
                tool='web_search',
                reference='web_search(query="self-employment income '
                          'verification underwriting")',
                detail='Timed out after 15.0 seconds.',
            ),
            ToolFailure(
                round=2, advocate=<LoanDecision.APPROVE: 'approve'>,
                tool='web_search',
                reference='web_search(query="§4.2 filed income")',
                detail='Timed out after 15.0 seconds.',
            ),
        ],
    ),
    usage_by_participant={
        <LoanDecision.APPROVE: 'approve'>: RunUsage(
            requests=3, tool_calls=2,
            input_tokens=14820, output_tokens=1120, cache_read_tokens=10400,
        ),
        <LoanDecision.DENY: 'deny'>: RunUsage(
            requests=4, tool_calls=2,
            input_tokens=18960, output_tokens=1240, cache_read_tokens=13800,
        ),
        <LoanDecision.REFER: 'refer to a senior ...'>: RunUsage(
            requests=2, tool_calls=1,
            input_tokens=7310, output_tokens=380, cache_read_tokens=5100,
        ),
        'judge': RunUsage(
            requests=2, tool_calls=0,
            input_tokens=20312, output_tokens=1240, cache_read_tokens=14800,
        ),
    },
    usage=RunUsage(
        requests=11,
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
hearing.usage_by_participant["judge"].input_tokens   # 20312 — the largest line
len(hearing.transcript.ledger)                       # 5 retrieved, 4 filed
len(hearing.transcript.failures)                     # 2 — both APPROVE, round 2
```

**The ledger shows what the filings do not.** `APPROVE` retrieved five sources
across the proceeding and cited four. The one it left out —
`(APPROVE, 's2')`, the verification status — is the fact `DENY` filed in round 2
and the judge ruled on. Reading only the entries, `APPROVE` looks like an
advocate that argued from the evidence it had. Reading the ledger, it is an
advocate that queried the verification status, saw `none`, and argued around it:

```python
cited = {(e.filing.advocate, x.source)
         for e in hearing.transcript
         for x in getattr(e.filing, "exhibits", [])}
[(r.advocate, r.id) for r in hearing.transcript.ledger
 if (r.advocate, r.id) not in cited]
# [(<LoanDecision.APPROVE: 'approve'>, 's2')]
```

Nothing here calls that misconduct — an advocate is *supposed* to argue one
side, and declining to volunteer the other side's best fact is the job. What the
ledger changes is that a reviewer can see it happened and weigh the argument
accordingly, instead of reading a record in which it never occurred. Note also
that both advocates ran the same query and it is ledgered twice, once under each
— retrievals are per advocate, because what each one saw is a separate fact.

**The empty `exhibits` in APPROVE's round-2 response has an explanation, and it
is in `failures`.** Read the entries alone and that response is an advocate with
nothing to add. Read `failures` and it is an advocate whose two searches timed
out. The judge ruled against it in the next entry.

Nothing here says the ruling was wrong. `enbanc` does not mark this hearing
degraded, does not warn, and does not adjust the outcome — a populated
`failures` is not a finding. What it does is make the question askable, which is
the whole difference between a record that explains a ruling and one that merely
reports it.

**Ids restart per advocate.** `APPROVE`'s `s1` and `DENY`'s `s1` are different
retrievals, which is why an exhibit resolves on `(advocate, id)` and not on `id`
alone.

**`REFER` has no retrievals at all.** It conceded without calling a tool, and an
advocate that searched nothing is distinguishable from one that searched and
filed nothing — a distinction the record could not make before.

**The concession is not a failure.** `REFER` looked at the record, found no case
worth making, and said so. That filing is why the transcript explains a
two-horse ruling in a three-verdict tribunal.

**`rounds` counts deliberations, not filings.** Seven entries, two rounds: a
round is the advocates' filings plus the `Continuance` or `Ruling` that closes
it.

**The judge is the single most expensive participant here**, on two requests
against the advocates' nine. It reads the whole record at every deliberation
while each advocate sees only its own thread, and no aggregate would have shown
that. This is what `usage_by_participant` is for — the split is the input to
"should the judge get the stronger model, or should the advocates get the
cheaper one?"

**`usage` is the sum of those four entries**, not a number kept beside them.
Add the four and you get `requests=11`, `input_tokens=61402`: the total is
derived, so it cannot drift from its parts.

## 2. The judge rules in round 1

The cheapest proceeding there is — the record is clear enough that no
interrogatory is needed.

```text
round 1   Argument(advocate=APPROVE, exhibits=[psql])
          Argument(advocate=DENY,    exhibits=[psql, web_search])
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
    usage_by_participant={...},                          # 3 advocates + 'judge'
    usage=RunUsage(requests=6, tool_calls=3, input_tokens=21050, ...),
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
    usage_by_participant={...},                          # 3 advocates + 'judge'
    usage=RunUsage(requests=11, tool_calls=4, input_tokens=58800, ...),
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
cost, exactly as a decided one does — and `usage_by_participant` still names
every participant, because every one of them ran.

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
round 1   Argument(advocate=APPROVE, exhibits=[psql, web_search])
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
                        Exhibit(
                            source='s1',
                            tool='psql',
                            reference='psql(sql="SELECT net_profit FROM '
                                      'schedule_c WHERE applicant = ...")',
                            content='schedule_c_2024: 182000',
                        ),
                    ],
                ),
            ),
        ],
    ),
    usage_by_participant={
        <LoanDecision.APPROVE: 'approve'>: RunUsage(
            requests=2, tool_calls=1, input_tokens=7020, output_tokens=410,
        ),
    },
    usage=RunUsage(requests=2, tool_calls=1, input_tokens=7020, output_tokens=410),
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

**`REFER` and `DENY` are absent from `usage_by_participant` too**, and that is
the one place the mapping is allowed to be incomplete. `DENY`'s run died before
it could report what it had spent; `REFER`'s was cancelled where it stood. A
missing key here means "did not report", never "spent nothing" — which is why
this usage is a floor and the aggregate above understates the real bill. On a
`Hearing` there is no such gap: every participant has an entry.

**`REFER` is absent from the record**, because it had not filed yet. The first
failure cancels the round: `REFER`'s run is stopped where it stood, and nothing
waits for it to land a filing that no judge will read. So this transcript is
what *had been* filed, not what round 1 would have held — had `REFER` been a
second quicker, the same outage would leave two entries behind instead of one.
See [`0012`](../decisions/0012-a-failure-cancels-the-round.md).

### The judge's provider is down

Same failure, one participant later — all three advocates filed, and the
deliberation that would have closed round 1 never happened.

```python
ProceedingFailed(
    participant='judge',
    round=1,
    transcript=Transcript(..., entries=[...]),      # 3 entries, no Continuance
    usage_by_participant={...},                     # 3 advocates; no 'judge' key
    usage=RunUsage(requests=6, tool_calls=3, input_tokens=19400, ...),
)
```

`participant` is `'judge'`, the one non-verdict value it can take — and the key
it would have held in `usage_by_participant` is missing, because the run that
failed never reported. All three advocates are there: they filed before the
deliberation was attempted.

### An advocate's tool raises

Nothing to do with the model — `psql` is down, and the tool function raises in
round 2 while answering an interrogatory.

```python
ProceedingFailed(
    participant=<LoanDecision.DENY: 'deny'>,
    round=2,
    transcript=Transcript(..., entries=[...]),      # 5 entries: round 1 complete,
                                                    # plus APPROVE's response
    usage_by_participant={...},                     # DENY's covers round 1 only
    usage=RunUsage(requests=9, tool_calls=4, ...),
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

No proceeding runs at all — these raise from the constructor.

### An advocate is missing

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

### A verdict named `judge`

The other construction-time check. `Verdict` is a `StrEnum`, so this value is
equal to — and hashes with — the judge's own key:

```python
class Escalation(Verdict):
    HANDLE = "handle"
    JUDGE = "judge"                 # reserved

tribunal = Tribunal(verdicts=Escalation, ...)   # this is what raises
```

```text
enbanc.ConfigurationError: 'judge' is a reserved verdict value: it would collide
with the judge's key in usage_by_participant
```

Left alone, that advocate's spend and the judge's would land in one entry of
`hearing.usage_by_participant` with no sign that two participants had merged —
in the artifact whose whole job is attributing spend. Renaming the member is the
fix. See [`0014`](../decisions/0014-usage-is-broken-down-per-participant.md).

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
restored.usage_by_participant     # keys are enum members again, plus 'judge'
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
