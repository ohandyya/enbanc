---
status: draft
updated: 2026-10-10
---

# The round loop

**What a continuance starts.** Round 2 and after: ids stamped on filing,
interrogatories dispatched to the advocates they name, an advocate's own
questions answered in order, and the two ways a proceeding ends without ruling.

## Scope

The loop itself, and the state that moves per round: the `_Continuance` →
`Continuance` conversion with `r{round}-q{n}` stamped in emission order, one task
per *addressed advocate* with its interrogatories queued inside it,
`Response.answering` filled from the dispatch, the per-run advance of `since`,
the snapshot extension that makes run 7 of
[the worked proceeding](../design/execution.md#since-and-the-snapshot-run-by-run)
correct, the `max_rounds` check, and the budget check whose
`UsageLimitExceeded` is a stop signal rather than an error.

**Not in this PR.** Failure handling — [`failures.md`](./failures.md). The task
group stays the plain one, so a round-2 failure still arrives as an
`ExceptionGroup`, exactly as a round-1 failure does after
[`proceeding-core.md`](./proceeding-core.md). [`outcomes.md` § 6](../design/outcomes.md#6-the-same-endings-watched-live)
is `failures.md`'s too: a stream that ends on a `Continuance` works here for free,
because `hear()` is the stream exhausted, but that section is tested where its
failure and abandonment halves are.

## Implements

- [`execution.md` § The round loop](../design/execution.md#the-round-loop)
- [`execution.md` § The budget check](../design/execution.md#the-budget-check)
- [`execution.md` § A snapshot is constructed, not sliced](../design/execution.md#a-snapshot-is-constructed-not-sliced)
  — run 7 is the case that constrains the implementation
- [`prompting.md` § An advocate asked two questions answers them in order](../design/prompting.md#an-advocate-asked-two-questions-answers-them-in-order)
- [`api.md` § Where ids come from](../design/api.md#where-ids-come-from) — the
  stamping seam, both directions
- [`outcomes.md` § 1. The judge rules](../design/outcomes.md#1-the-judge-rules)
  and [§ 3. The envelope is spent](../design/outcomes.md#3-the-envelope-is-spent)
  — the acceptance tests, including the suppression join

## Depends on

[`proceeding-core.md`](./proceeding-core.md) — merged as
[PR #26](https://github.com/ohandyya/enbanc/pull/26).

## Files

No new module. `_proceeding.py` grows from one round to many, two docstrings
elsewhere stop saying something false, and one ADR records the choice the design
left open ([below](#who-fills-answering)).

| File | Change |
|---|---|
| `src/enbanc/_proceeding.py` | the loop in `run()`; `_answer()` beside `_argue()`; `_round()` dispatching either; `_public()` gaining two conversions; `_budget_spent()`; `_response_output()`; `_Emitted` gaining `_Response` and `_Continuance`; the `NotImplementedError` deleted |
| `src/enbanc/_filings.py` | `_Response`'s docstring — it is what the tribunal *builds*, not what the advocate *emits* ([below](#who-fills-answering)) |
| `docs/decisions/0039-a-response-is-asked-for-its-answer-alone.md` | new — the `answering` decision, and the rejected alternative |
| `docs/README.md` | indexes `0039` |
| `docs/design/execution.md`, `api.md`, `testing.md` | [below](#design-documents) |

Nothing on `__all__` moves. Every name this PR touches is private or already
exported.

### The loop

`execution.md`'s sketch, almost literally — the work is in what the two calls
inside it do:

```python
async def run(self, out):
    inbox_send, inbox_receive = anyio.create_memory_object_stream[_Filed[VerdictT]](0)
    async with anyio.create_task_group() as tg:
        tg.start_soon(self._clerk, inbox_receive, out)
        async with inbox_send:
            round, addressed = 1, None                    # None: round 1 is the full bench
            while True:
                base = await self._round(round, addressed, inbox_send)
                deliberation = await self._deliberate(round, inbox_send)
                if isinstance(deliberation, Ruling):
                    outcome = deliberation;                          break
                if round >= self.max_rounds:
                    outcome = Undecided(reason="rounds");            break
                if self._budget_spent(first=round == 1):
                    outcome = Undecided(reason="budget");            break
                round, addressed = round + 1, _addressed(deliberation)
            self.hearing = Hearing[VerdictT](outcome=outcome, ...)
    await out.aclose()
```

- **`_deliberate` returns the *public* filing**, read off the `Entry` the clerk
  acknowledged — `Ruling` or `Continuance`, never `_Continuance`. Two things
  follow. A `Ruling` outcome is the very object in `transcript[-1].filing`, so
  `hearing.outcome is hearing.transcript[-1].filing` stays true by identity
  rather than by equality. And round *N*+1 is dispatched **from the record**: the
  ids in an advocate's `## Addressed to you` are the ids in the transcript because
  they are the same objects, not because two code paths agree on a format.
- **`hearing` is still bound inside the inbox block**, after the last filing has
  been acknowledged and before `out` closes — the property
  [`proceeding-core.md`](./proceeding-core.md#hear-is-hear_stream-exhausted-and-abandoning-cancels)
  established so a consumer reads `proceeding.hearing` the moment its loop ends.
  An `Undecided` outcome is filed by nobody, so binding it needs no
  acknowledgment.
- **`_addressed(continuance)`** groups `continuance.interrogatories` by `to`, into
  a dict of lists. Insertion order is first-addressed, which decides only the
  order tasks are *started* and carries no meaning. Within each list the order is
  emission order, which is id order, which is
  [`0027`](../decisions/0027-an-advocate-answers-its-interrogatories-in-order.md)'s
  answering order — three names for one sequence, because the ids were stamped
  from it.
- **No guard for an empty `addressed`.** `_Continuance.interrogatories` carries
  `min_length=1` ([`0036`](../decisions/0036-a-continuance-carries-at-least-one-interrogatory.md)),
  so the zero-task round is unreachable. Writing a branch for it would be a test
  of something the type already rules out.
- **`>=`, not `==`, against `max_rounds`.** Found while building, not in the
  plan: `Tribunal(...)` does not validate `max_rounds` (`test_tribunal.py` pins
  that `max_rounds=0` constructs, because `ConfigurationError` has four cases and
  this is not one), and with `==` a tribunal built with `0` would run for as long
  as the judge kept asking. With `>=` it runs one round and ends
  `Undecided(reason='rounds')` — the shape a zero budget takes — and nothing
  changes for any `max_rounds` of 1 or more. `execution.md`'s sketch is corrected
  to match ([below](#design-documents)).
- **No special case for a conceded advocate.** It stays addressable
  ([`0037`](../decisions/0037-a-conceded-advocate-stays-addressable.md)), and its
  agent, ledgering toolset and history all exist from round 1. A test pins that
  nothing filters it out.

### Stamping, at the clerk

Both conversions this PR owes happen in `_public()`, the seam
[`execution.md`](../design/execution.md#the-filing-clerk) puts them at. It gains
the round as a parameter, because an id is `r{round}-q{n}` and the round is the
filer's `_Filed.round`:

| Emitted | Entered in the record |
|---|---|
| `_Continuance[V]` | `Continuance[V]`, each `_Interrogatory` gaining `id=f"r{round}-q{n}"`, `n` from 1 in emission order; `to` and `question` copied verbatim |
| `_Response[V]` | `Response[V]`, each `_Exhibit` resolved through the existing `_stamp()` |

**Nothing the judge wrote is altered** ([`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)),
and the test says so by comparing `(to, question)` pairs before and after. A
`_Response` carries `advocate` and `answering` already filled from the dispatch
([below](#who-fills-answering)), so its conversion is the field copy `_Response`'s
docstring promises, plus the one `_stamp()` call `_Argument` already makes.

### One task per addressed advocate

`_round()` keeps its task group and changes what it starts. Round 1 starts
`_argue()` for every advocate, unchanged. A later round starts `_answer()` once
per key of `addressed`, handing each the **same** base snapshot:

```python
async def _answer(self, verdict, questions, round, base, inbox) -> None:
    ledgering = self.ledgerings[verdict]
    ledgering.round = round
    entries = list(base.entries)                  # this task's own extension
    for interrogatory in questions:               # id order, one run each — 0027
        snapshot = base.model_copy(update={"entries": [*entries]})
        result = await self.advocate_agents[verdict].run(
            response_turn(snapshot, advocate=verdict, since=self.since[verdict],
                          round=round, interrogatory=interrogatory),
            output_type=self._response_output(verdict, interrogatory),
            message_history=self.history.get(verdict),
            usage=self._usage(verdict),
        )
        self.history[verdict] = result.all_messages()
        self.since[verdict] = snapshot.entries[-1].round
        entries.append(await self._file(result.output, round=round, inbox=inbox))
```

That is the whole of `0027`, and each line carries one rule:

- **The base snapshot is taken once per round, when the continuance is filed** —
  `self._snapshot()` immediately after `_deliberate` files it, returned to the
  loop and passed into `_round()`. Nothing is in flight at that moment and the
  clerk is the only writer, so *the transcript as the continuance closed round
  N−1* is the transcript at that line.
- **The extension is the task's local `entries`**, appended from the `Entry` the
  ack carries back. That is why
  [`proceeding-core.md`](./proceeding-core.md#the-filing-clerk-owns-the-transcript)
  built the ack to carry the stamped entry: reading `transcript.entries[-1]` after
  the wait would be a race a concurrent sibling wins, and the entry a sibling
  wins it with is precisely run 7's forbidden entry 5.
- **Each run gets its own copy of the list**, `[*entries]`. The rendered string
  is produced before the next append, so sharing would happen to work; copying
  makes a snapshot a value rather than a view, which is what the word
  *constructed* means.
- **`since` advances after the run returns, to the round of the snapshot's last
  entry** — *the last round whose filings this participant has been shown*, not
  the round being run. A first run of round *N* is shown the base, which ends on
  round *N*−1's continuance, so `since` becomes *N*−1; the next run's snapshot
  ends on the response just filed, renders that alone, and leaves `since` at *N*.
  That is rows 6 and 7 of `execution.md`'s table, `since` out 1 then 2. **The plan
  first had `since = round` here, and it was wrong**: the forced run-7 test caught
  it as an empty delta, and the same rule would have shown a round-3 turn none of
  round 2. `test_a_third_round_is_shown_everything_the_second_filed` pins the
  second consequence. The write sits beside the history write and before the
  filing; a run that dies writes neither
  ([`execution.md`](../design/execution.md#history-is-a-dict-written-after-each-run)).
- **`ledgering.round` is set once per task, not per run.** Every run in the task
  is the same round, and the value flows one way into the run's copy
  ([`execution.md`](../design/execution.md#a-wrapper-toolset-is-rebuilt-for-every-run)).
  The ids keep counting from the ledger, so `deny`'s round-2 find is `s2`, not
  `s1`.
- **The next run waits on the ack**, because `_file` returns only after the clerk
  has appended and delivered — so run 7 is never dispatched before entry 6 is in
  the record, which is the ordering `0027` guarantees and the only one between
  entries 5–7 that it does.

The judge's snapshot for deliberation *N* is unchanged from round 1: `_snapshot()`
when the fan-out completes, which now holds every round-*N* response.

### Who fills `answering`

**The decision the design left open, and the one this PR cannot start without.**
[`api.md`](../design/api.md#where-ids-come-from) says *no participant authors an
id in either direction* and that the tribunal *fills the link from the dispatch
rather than from the model*. [`ledgering-toolset.md`](./ledgering-toolset.md)
deferred *whether the orchestrator overwrites them from the dispatch or omits
them from the output schema* to `proceeding-core.md`, which had no round 2 and
did not decide.

As the code stands it would be neither. Handing `_Response[V]` over as the
output type puts `answering` in the schema as a **required** field, and whatever
the model writes there is what the record keeps — verified against
`pydantic-ai 2.36.0`:

```text
sole output type _Response[LD]:
  tool:     final_result
  required: ['advocate', 'answering', 'answer']
  model wrote answering='WRONG'  ->  output.answering == 'WRONG'
```

A response citing a question nobody asked would be a reachable state, which is
exactly what [`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)
exists to prevent. Two ways to close it, both verified to work:

**The plan: ask only for the answer.** The output function's parameters *are*
the schema, so give it the two fields the advocate knows and build the
`_Response` from the dispatch:

```python
def _response_output(self, verdict, interrogatory):
    response_type = _Response[self.verdicts]       # resolved from the enum, not VerdictT
    check = self.ledgerings[verdict].check_citations

    def respond(answer: str, exhibits: Sequence[_Exhibit] = ()) -> _Response[VerdictT]:
        response = response_type(advocate=verdict, answering=interrogatory.id,
                                 answer=answer, exhibits=list(exhibits))
        check(response)
        return response

    return respond
```

```text
multi-parameter output function:
  tool:     final_result
  required: ['answer']          (exhibits defaulted, as _Response's is)
  output:   advocate=deny, answering='r1-q3' — from the dispatch
```

The model is asked for nothing it cannot know, the link is the tribunal's in the
literal sense `api.md` claims, and the record cannot be wrong about it. **No
docstring on `respond`**, for the trap
[`proceeding-core.md`](./proceeding-core.md#an-output-validator-forbids-a-per-run-output-type)
found: PydanticAI would send it as the tool's description. The return annotation
is not read for the schema, so it may be written literally.

What it costs: the wire shape is now derived from a function signature rather
than from `_Response`, so a field added to `_Response` reaches the model only if
it is also added to `respond` — the same *two shapes that must move together*
[`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md) accepted for
`_Continuance`, at the same single seam. And it leans on a dependency fact not yet
pinned: that a several-parameter output function is shaped as an object of its
parameters, with `ModelRetry` inside it spending the `output` budget. That becomes
a contract-test row ([Tests](#tests)).

**Rejected: ask for both and overwrite them.** Keep `_Response[V]` as
the function's parameter and `model_copy(update={"advocate": verdict,
"answering": interrogatory.id})` before the check. The smallest diff, and the
round-2 wire stays in step with round 1's `_Argument`, which also asks for
`advocate`. It loses on what it leaves in the advocate's own history: a model
that writes `answering="r1-q1"` while answering `r1-q3` carries that wrong link
in its conversation for every later round, while the record says otherwise. That
is the fourth escape — the agent's own pre-stamp output — stretched from *a
superset of the same fact* to *a contradiction of it*, and asking a model for a
value in order to discard it is the move `0015` and `0016` were written against.

The rejected alternative is written out in `0039` with the reason, because the
choice fixes the shape of every response an advocate files and so binds future
work ([`CLAUDE.md`](../../CLAUDE.md) rule 8).

**Round 1's `advocate` is not reopened here.** `_Argument` and the public
`Concession` both ask the model for `advocate`, and a model writing a peer's
verdict would be recorded as that peer. That is real, and it is merged code
outside this PR's scope; it is recorded here so it is a known thing rather than
a rediscovered one, and it is yours to file.

### The budget check

```python
def _budget_spent(self, *, first: bool) -> bool:
    if self.budget is None:
        return False
    total = sum(self.usage_by_participant.values(), RunUsage())
    try:
        if first:
            self.budget.check_cost(total, warn_if_cost_unavailable=True)
        self.budget.check_before_request(total)
        self.budget.check_tokens(total)
        self.budget.check_before_tool_call(total)
    except UsageLimitExceeded:
        return True
    return False
```

[`0024`](../decisions/0024-a-budget-stops-the-proceeding-between-rounds.md)'s three
checkers, plus the one call that exists for its warning. Read off the installed
source rather than assumed:

- **`check_before_request` compares requests with `>=`** — *the next request
  would exceed*. At a boundary that is the right reading: a total that has
  reached `request_limit` would cross it with the first request of the next
  round. So `request_limit=0` stops after round 1, which is
  [`execution.md`](../design/execution.md#the-round-loop)'s *a ceiling of zero
  gets one round* falling out of the dependency rather than being special-cased.
  The token, cost and tool-call checks compare with `>`.
- **`check_before_request` never warns.** Only `check_cost` does, and only when
  asked — so the warning is emitted exactly where `first` says and nowhere else.
- **`first` is `round == 1`, and that is exact rather than approximate.** The
  check runs only after a continuance with rounds remaining; if one is ever
  reached, round 1's is the first. A proceeding that rules in round 1, or whose
  `max_rounds` is 1, reaches no boundary and is not warned — `cost_limit` never
  had a moment to enforce anything there. `api.md`'s *warns once per proceeding*
  is tightened to say so ([below](#design-documents)).
- **The two per-request fields are never consulted**, because none of the three
  checkers reads them. Nothing has to be written to ignore them.
- **`UsageLimitExceeded` is caught here and nowhere else.** A budget is the
  caller's declared envelope; reaching it is an ordinary end
  ([`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md)).
  The fifty-request ceiling PydanticAI enforces *inside* a run raises the same
  class from inside an advocate's task, and that one is not caught — it is a
  participant that could not be heard, and `failures.md`'s to wrap.

`total` is the same fold `Hearing.usage` computes. Two lines in two places
rather than a shared helper: `Hearing` is a public model and does not take a
dict from the orchestrator, and the orchestrator has no `Hearing` until the loop
ends.

### What leaves the module

The `NotImplementedError` and the test asserting it go first — both were
[written to be deleted here](./proceeding-core.md#what-a-continuance-does-in-this-pr).
With them go four sentences that stop being true: the module docstring's *up to a
single round and one deliberation*, `budget`'s *held and not read until the budget
check*, `_advocate_agent`'s pointer to this document, and `_Emitted`'s *join it
with the dispatch that produces them*. `advocate_agents`' annotation is
unchanged — a per-run `output_type` widens the result type of that run, not of
the agent.

### Design documents

Six edits, all `CLAUDE.md` rule 2 paid in this commit.

[`execution.md` § The proceeding, as messages](../design/execution.md#the-proceeding-as-messages)
— the correction [`proceeding-core.md`](./proceeding-core.md#an-output-validator-forbids-a-per-run-output-type)
left owed. The three round-2 advocate traces name `final_result__ResponseLoanDecision`,
and a sole output type is named `final_result`. They also show the model writing
`kind` and `advocate`; under the plan it writes `answer` and `exhibits` and
nothing else, so `approve`'s `resp 3` loses two arguments. `deny`'s `resp 4`
already reads that way.

[`execution.md` § An output validator forbids a per-run `output_type`](../design/execution.md#an-output-validator-forbids-a-per-run-output_type)
— gains the several-parameter case: such a function is shaped as an object of its
parameters, and its `ModelRetry` spends the `output` budget as the single-parameter
form's does. [`testing.md`](../design/testing.md#the-four-tiers)'s findings-table
row for that finding gains the same clause. The finding count stays at thirteen;
this extends one rather than adding one.

[`api.md` § Where ids come from](../design/api.md#where-ids-come-from) —
*fills the link from the dispatch* gains its mechanism in one sentence: an
advocate's response is asked for its answer and its exhibits, and `advocate` and
`answering` are filled from the dispatch, linking `0039`.

[`api.md` § The governors](../design/api.md#the-governors) — *warns once per
proceeding* becomes *warns once, at the first round boundary* — the precise claim
the test pins.

[`execution.md` § The round loop](../design/execution.md#the-round-loop) — the
sketch's `round_no == max_rounds` becomes `>=`, with the paragraph saying why
([above](#the-loop)).

[`outcomes.md` § 3](../design/outcomes.md#the-budget) — *the judge files a third
`Continuance`* becomes *a second*: the section's own diagram, and `rounds=2`,
show two. Found writing the mirror.

**No `PROCEDURE` bump.** No text a model reads moves: the turns are
[`rendering.md`](./rendering.md)'s, already built, and an output tool's name and
schema are PydanticAI's and outside `Transcript.procedure` by
[`execution.md`](../design/execution.md#a-filing-lands-in-history-as-a-tool-call)'s
own statement.

## Tests

Unit-tier except one row, split the way
[`proceeding-core.md`](./proceeding-core.md#tests) split it.

| Module | Tier | Pins |
|---|---|---|
| `test_round_loop.py` | unit | **new.** Ids stamped `r{round}-q{n}` in emission order, restarting at `r2-q1`, with `(to, question)` unaltered; only addressed advocates dispatched in round 2, an unaddressed one's turns and usage untouched; a conceded advocate answering (`0037`); `answering` and `advocate` equal to the dispatch, and the answer the bench wrote for that id; one advocate's two questions filed in id order, over five runs; `since` and the snapshot matching rows 5–8 of `execution.md`'s table; a round-3 turn shown everything round 2 filed; **run 7** — the forced-adversarial version [below](#run-7-forced); a round-2 response citing a round-1 id resolving; `deny`'s round-2 find ledgered `s2` with `round=2`; the invariant over a two-round proceeding |
| `test_budget.py` | unit | **new.** No check before round 1 — `request_limit=0` gets one round, then `Undecided(reason='budget')`; each checker reached through its own limit (`request_limit`, `total_tokens_limit`, `output_tokens_limit`, `tool_calls_limit`); `max_rounds` winning when both are spent; `max_rounds=0` ending after one round; `budget=None` leaving only the rounds to run out; a limit not yet reached letting the next round run, and the overshoot it costs; `UsageLimitExceeded` never escaping `hear()`; `CostNotFoundWarning` raised exactly once over a three-round unpriced proceeding, and never for one that rules in round 1 |
| `test_filing_clerk.py` | unit | gains the two conversions, driven directly: a `_Continuance` filed at round 3 entering as `r3-q1…`; a `_Response` entering as `Response` with its exhibits stamped against its own advocate's rows |
| `test_agents.py` | unit | gains the round-2 wire: the advocate offered exactly one output tool, `final_result`, whose schema properties are `answer` and `exhibits`, `answer` alone required, with PydanticAI's generic description; the instructions byte-identical to round 1's |
| `test_usage.py` | unit | gains: a participant's round-2 runs accumulate into its round-1 object; `hearing.usage` still the sum of the breakdown after three rounds |
| `test_proceeding.py` | unit | loses `test_a_continuance_is_the_round_loops_and_says_so` |
| `outcomes/test_01_judge_rules.py` | unit | **new.** [`outcomes.md` § 1](../design/outcomes.md#1-the-judge-rules) as written: seven entries, `rounds=2`, `outcome is transcript[-1].filing`; five retrieved, four filed; the suppression join returning `[(APPROVE, 's2')]` and nothing else; each advocate's ledger rows in its own order — asserted per advocate, because concurrent advocates interleave in the ledger; two failures, both `APPROVE`'s, both round 2; `REFER` with no ledger rows; four keys in the breakdown |
| `outcomes/test_03_envelope_spent.py` | unit | **new.** [§ 3](../design/outcomes.md#3-the-envelope-is-spent), both halves: `max_rounds=2` ending `Undecided(reason='rounds')` on a `Continuance` carrying `r2-q1` and `r2-q2`, with `outcome is not transcript[-1].filing`; and the `cost_limit=Decimal("0.40")` budget ending `Undecided(reason='budget')` at `rounds=2` with `usage.cost == Decimal("0.41")` — the overshoot asserted, because the record is meant to show it; and the two transcripts the same shape while the outcomes differ |
| `test_an_output_validator_forbids_a_run_output_type.py` | contract | gains the several-parameter case: a sole output function of two parameters is offered as `final_result` with an object schema of exactly those parameters, its docstring-free description is PydanticAI's generic sentence, and its `ModelRetry` spends the `output` budget |

### The bench grows three things

`tests/unit/conftest.py`'s `Bench` was built for a proceeding with one
deliberation, and three of its assumptions stop holding at round 2. Each is
found by reading what the round-2 turn actually is, not guessed:

- **It identifies a participant from the last user prompt**, and
  `Round 2. Answer r1-q3 and file your response.` names no advocate. The match
  moves to the *first* user prompt in the conversation — every advocate's history
  opens with its round-1 turn, which does name it, and the judge's opens with
  `## Round 1`. It is still read off what a model reads, which is the property
  `_ADVOCATE_TURN`'s comment protects.
- **It finds an output tool by class-name substring**, and a sole output type has
  no class name in it. `_output_tool` returns the only tool when there is one.
- **`continues: bool` becomes a script.** `continuances` is one list of
  `(to, question)` pairs per deliberation, read off the turn's *Deliberation N*,
  ruling once it runs out. A turn is keyed by what names it — an advocate's
  round-1 run by its verdict, a response by the interrogatory id it answers — and
  `calls` and `exhibits` script, per turn, the tool calls made before filing and
  the ids cited. `costs` prices every model response per participant so § 3's
  budget is a real `Decimal`, and `gates` holds a turn's filing on an
  `anyio.Event`, which is what forces run 7. A scripted `RequestUsage(cost=...)` flows into `RunUsage.cost`
  unchanged, verified, which is what makes a priced proceeding possible offline
  at all: `FunctionModel` is otherwise unpriceable and every `cost_limit` test
  would trip `CostNotFoundWarning`, which `filterwarnings = ["error"]` makes a
  failure.

### `assert_invariant_held` grows one rule

The `## Addressed to you` line is `r1-q2: Is stated income disqualifying …`, and
the reviewer render holds that question as `r1-q2 -> deny: Is stated income …`,
wrapped. Line-containment fails on a proceeding that is perfectly correct. The
helper therefore accepts a line of the form `{id}: {question}` when the
transcript holds an `Interrogatory` with exactly that id and that question — the
same register as the fourth escape: derived from the record, not a substring of
it. The *Round N. Answer {id}* scaffolding pattern is already there.

### Run 7, forced

[`testing.md`](../design/testing.md#the-transcript-invariant) names run 7 the case
that constrains everything, and the version worth having is the adversarial one:
`approve`'s entry 5 **in the transcript first**, and `deny`'s second run still not
shown it. A plain bench leaves that to the scheduler, so a passing test might
never have exercised it.

The test drives `hear_stream()` and holds `deny`'s first response on an
`anyio.Event` that the consumer sets when the stream yields `approve`'s
`Response`. Because the stream is a rendezvous, receiving entry 5 means it is in
`transcript.entries` — so by the time `deny` files entry 6 and its second run is
dispatched, entry 5 has demonstrably landed first. The assertion is on what `deny`'s
second run was handed: entry 6's stamped block present, entry 5's absent, and no
round-1 block re-rendered.

### What is deliberately not asserted

**The interleaving of entries 5 and 6**, or the order round-2 tasks start in.
`0027` guarantees 6 before 7 and nothing else, and a test of anything more would
be a test of anyio's scheduler.

**A failure in round 2.** It surfaces as an `ExceptionGroup` today and as a
singular `ProceedingFailed` after [`failures.md`](./failures.md), which owns both
the behaviour and its tests.

**That the budget stops a runaway inside a round.** It does not, by design
([`0024`](../decisions/0024-a-budget-stops-the-proceeding-between-rounds.md)) —
§ 3's overshoot is the assertion that it doesn't.

## Open questions

*None open.* The one that had to be settled before a line could be written —
[who fills `answering`](#who-fills-answering) — was decided while planning: an
advocate's response is asked for its `answer` and `exhibits` alone, and
`advocate` and `answering` are filled from the dispatch. Asking for both and
overwriting them is written out and rejected in that section, and `0039`
records the decision in the PR's commit.
