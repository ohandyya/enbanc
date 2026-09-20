---
status: draft
updated: 2026-09-20
---

# A proceeding that runs once

**The first half of `execution.md`'s piece 3: everything needed to run round 1
and one deliberation, end to end, offline.** After this PR a tribunal whose judge
rules immediately produces a real `Hearing`.

## Scope

`_proceeding.py`, up to a single-round proceeding: one `Agent` per participant
built inside the proceeding and discarded with it, the ledgering toolset wired in
per advocate, the shared concurrency limiter, one `RunUsage` per participant, the
history dict, the `since` dict, the base snapshot, the filing clerk that owns the
transcript, and the `Proceeding` handle behind `hear_stream()` — with `hear()`
defined as that stream driven to exhaustion, literally.

**`__all__` completes here.** `Tribunal`, `Judge`, `Advocate` and `Proceeding`
are all exported by the end of this PR, so
`tests/unit/test_export_surface.py` ([`packaging.md`](../design/packaging.md#the-export-surface))
lands with it and pins the twenty-nine-name list for the first time.

**Not in this PR.** The round loop and everything a continuance starts — that is
[`round-loop.md`](./round-loop.md). Failure handling and cancellation are
[`failures.md`](./failures.md); the task group here is the plain one, and gains
its first-failure slot there.

Concretely, a judge that issues a `_Continuance` in this PR raises
`NotImplementedError` naming `round-loop.md`, and the `_Continuance` →
`Continuance` stamping stays with the dispatch it exists for
([below](#what-a-continuance-does-in-this-pr)).

## Implements

- [`execution.md` § Piece 1 — message history and the transcript](../design/execution.md#piece-1--message-history-and-the-transcript)
  — all three rules
- [`execution.md` § The filing clerk](../design/execution.md#the-filing-clerk)
- [`execution.md` § The round's task group](../design/execution.md#the-rounds-task-group)
  — the fan-out and the shared limiter
- [`execution.md` § Usage](../design/execution.md#usage) and
  [§ Also in scope](../design/execution.md#also-in-scope) — the retry budgets,
  and what is deliberately not passed into a run
- [`api.md` § Watching it live](../design/api.md#watching-it-live)
- [`outcomes.md` § 2. The judge rules in round 1](../design/outcomes.md#2-the-judge-rules-in-round-1)
  — the acceptance test
- [`testing.md` § The transcript invariant](../design/testing.md#the-transcript-invariant)
  — `assert_invariant_held` lands here, and every later proceeding test calls it

## Depends on

[`tribunal-construction.md`](./tribunal-construction.md),
[`ledgering-toolset.md`](./ledgering-toolset.md).

## Files

One new module, two existing ones extended, and one dependency declared. The
module map ([`packaging.md`](../design/packaging.md#the-modules)) puts
`_proceeding.py` last, below `_tribunal.py` — but the orchestrator takes the
pieces rather than the `Tribunal`, so the runtime import runs `_tribunal` →
`_proceeding` and never back ([below](#_proceedingpy-takes-the-pieces)).

| Module | Holds | Imports from the package |
|---|---|---|
| `_proceeding.py` | `Proceeding`, `_Orchestrator`, `_Filed`, `proceed()`, the clerk | `_verdicts`, `_inputs`, `_evidence`, `_filings`, `_prompting`, `_transcript`, `_hearing`, `_errors`, `_ledgering`; `_tribunal` under `TYPE_CHECKING` |
| `_tribunal.py` | gains `hear()` and `hear_stream()` | gains `_proceeding` |
| `__init__.py` | exports `Proceeding` — the twenty-ninth name | gains `_proceeding` |
| `pyproject.toml` | declares `anyio` | — |

**One new public name.** `Proceeding` is the last of
[`packaging.md`](../design/packaging.md#the-export-surface)'s twenty-nine.
Everything else in the module is internal the way `Ledgering` is — the module is
underscore-prefixed, so nothing inside it is reachable — and `_Orchestrator` and
`_Filed` carry a leading underscore on top of that for the reason `_Exhibit`
does: each sits close enough to a public name to be mistaken for one.

### An output validator forbids a per-run output type

The load-bearing fact about this module, and it is not guessable from the design.
It was found by running `pydantic-ai 2.36.0`:

```text
override raised: UserError Cannot set a custom run `output_type` when the agent has output validators
```

`Agent._prepare_output_schema` (`agent/__init__.py:3203`) refuses **any** run-level
`output_type` once `agent.output_validator(...)` has been called — including an
override identical to the agent's own. That collides head-on with two things the
design already fixed:

- an advocate's output shape varies by round — `_Argument | Concession` in round
  1, `_Response` from round 2
  ([`api.md`](../design/api.md#where-ids-come-from),
  [`prompting.md`](../design/prompting.md#the-turns));
- there is **one agent per participant**, built inside the proceeding and
  discarded with it — *eight runs across four agents* in
  [the worked proceeding](../design/execution.md#the-proceeding-as-messages).

Both cannot hold while the citation check is registered as an output validator.

**The resolution: the check rides on the output type, as an output function.** A
plain function whose single parameter is the filing model is accepted as an
output type, and PydanticAI derives the output tool from the *parameter's* type
rather than from the function:

```text
output tools: ['final_result__ArgumentLoanDecision', 'final_result_ConcessionLoanDecision']
desc:         '_Argument[LoanDecision]: The final response which ends this conversation'
schema:       the model's own, unchanged
```

So nothing the model sees moves — the same tool names
[`execution.md`](../design/execution.md#approves-history--two-runs-eight-messages)'s
traces show, the same schemas, and PydanticAI's own generic description rather
than the class docstring. What changes is only where the check is attached:

```python
def _filing_output(filing_type, check):
    def file(filing):
        check(filing)
        return filing

    file.__annotations__ = {"filing": filing_type, "return": filing_type}
    return file


agent = Agent(
    advocate.model or model,
    output_type=[
        _filing_output(_Argument[self.verdicts], ledgering.check_citations),
        Concession[self.verdicts],
    ],
    ...
)
```

**Two traps, both found by building and neither guessable from the design.** The
obvious spelling of that function — `def file_argument(argument:
_Argument[VerdictT])`, with a docstring saying what it does — is wrong twice over:

- **A bare `TypeVar` collapses, and the collapse reaches the model.** Pydantic
  returns the origin class for a generic parameterized with a bare `TypeVar`, and
  PydanticAI evaluates the parameter's annotation at runtime — so
  `_Argument[VerdictT]` is `_Argument`, whose `advocate` field is typed by the
  *unsubclassed* `Verdict`. That enum declares no members, so the schema carries
  `enum: []`:

  ```text
  bare TypeVar:       'verdict': {'enum': [], 'description': '<the Verdict docstring>'}
  runtime enum class: 'verdict': {'$ref': '#/$defs/LoanDecision'}  → ['approve', 'deny', …]
  ```

  No verdict the caller declared is a valid answer, every attempt fails
  validation, and the run dies having spent the output budget explaining it. The
  fix is the annotation being *assigned* from a type resolved against the
  tribunal's own enum — which is why `_Orchestrator.verdicts` is the enum class
  rather than the list of members `instruction_parts` wants.
- **A docstring on it becomes the output tool's description.** Verified: the
  model reads it. So the functions `enbanc` builds carry a comment instead, and
  PydanticAI's own generic sentence is what reaches the wire.

Both are now findings in `execution.md` and rows in the contract test, because
both are claims about the dependency rather than about `enbanc`.

Three properties were verified rather than assumed, because the whole point of
the move is that it changes nothing:

- **`ModelRetry` raised inside the output function spends the `output` budget**,
  exactly as an output validator does — `Exceeded maximum output retries (1)`
  with `retries={'tools': 5, 'output': 1}`, and `(3)` with
  `{'tools': 1, 'output': 3}`. That is what
  [`evidence.md`](../design/evidence.md#an-unresolvable-id-is-a-validation-failure)
  and [`0030`](../decisions/0030-the-retry-budgets.md) require of the citation
  check, and it is unchanged.
- **It reaches the model as a `RetryPromptPart`**, carrying
  `check_citations`'s own message. Driven end to end — round 1 citing `s1`, round
  2 citing a `s9` no tool returned, retried, then filed — the parts are
  `ToolCallPart`, `RetryPromptPart`, `ToolCallPart`, `ToolReturnPart`.
- **With no agent-level validator the per-run override is legal again**, so one
  agent carries the advocate across rounds and the history dict has one entry
  per participant, not one per shape.

**`check_citations` does not move.** It stays the method
[`ledgering-toolset.md`](./ledgering-toolset.md#the-validator-and-the-two-filings-it-validates)
built, still closing over the orchestrator's `Ledgering` and still seeing the
rows the run just wrote. The output function is four lines of wiring around it,
and it is wiring that PR deliberately left to this one.

**Rejected: a second agent per advocate**, one for arguments and one for
responses, keeping `agent.output_validator`. It costs *one `Agent` per
participant* and the *four agents* count, and it splits one participant's runs
across two agents that share a history entry, a `Ledgering`, and a `RunUsage` —
three shared mutables where the design has one object.

**Rejected: one union for every round** — `_Argument | Concession | _Response`
always offered, no override needed. It makes a round-1 `_Response` carrying an
`answering` id nobody issued an expressible state, which is precisely what
[`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)'s stamping
exists to make unreachable, and it would need a second mutable *what may be filed
now* field on the orchestrator to reject it.

**One consequence owed to [`round-loop.md`](./round-loop.md), not paid here.** A
sole output type is named `final_result`, not `final_result__ResponseLoanDecision`
— verified, and true of a bare `_Response[V]` as much as of an output function
over one. [`execution.md`'s round-2 traces](../design/execution.md#denys-history--three-runs-thirteen-messages)
show the qualified name, so they are wrong about round 2 whichever way this was
spelled. The correction lands with the PR that dispatches a round 2.

### One agent per participant, built here and discarded

```python
RETRIES: Final[AgentRetries] = {"tools": 3, "output": 2}

limiter = normalize_to_limiter(max_concurrency)        # once, per proceeding

agent = Agent(
    advocate.model or model,
    output_type=[
        _filing_output(_Argument[self.verdicts], ledgering.check_citations),
        Concession[self.verdicts],
    ],
    instructions=instruction_parts(
        question=question, statute=statute, verdicts=list(verdicts),
        advocate=verdict, guidance=advocate.guidance,
    ),
    toolsets=[ledgering],
    deps_type=type(None),
    retries=RETRIES,
    max_concurrency=limiter,
)
```

- **`instructions=` takes the parts `instruction_parts()` already builds**, and
  PydanticAI joins them with the same `"\n\n"` `instructions_for()` spells. That
  is what makes *the string a caller previews is the string the agent runs under*
  a fact rather than a parallel implementation — the assertion
  [`tribunal-construction.md`](./tribunal-construction.md#what-is-deliberately-not-asserted)
  deferred to this PR, because only here is there a wire to read it off.
- **`deps_type=type(None)` on every agent**, including the judge's. For an
  advocate it is forced: `Agent.__init__` declares `deps_type: type[AgentDepsT] =
  object` while also solving `AgentDepsT` from `toolsets`, so a toolset typed
  `AbstractToolset[None]` against the `object` default is a pyright error about a
  value neither call site wrote
  ([`execution.md`](../design/execution.md#a-wrapper-toolset-is-rebuilt-for-every-run),
  and `ledgering-toolset.md` recorded it so this PR would not rediscover it). The
  judge has no toolsets and needs none, and carries it so the two agents are
  spelled the same way.
- **`retries={'tools': 3, 'output': 2}` on both**, from one module constant, as
  [`0030`](../decisions/0030-the-retry-budgets.md) fixes. Nothing is configurable
  through `enbanc`; the `tools` half stays overridable per tool where `0020` put
  it.
- **The limiter is normalized once and shared.** `normalize_to_limiter` is an
  `Agent.__init__` parameter's helper and not a `run()` argument
  ([`execution.md`](../design/execution.md#max_concurrency-is-set-at-construction)),
  so one object is built per proceeding and handed to every advocate. It returns
  `None` for `None`, which is what an unbounded tribunal passes. **The judge gets
  none** — it runs alone, and the fan-out is the only place concurrency exists
  ([`0024`](../decisions/0024-a-budget-stops-the-proceeding-between-rounds.md)).
- **No `usage_limits=` is passed into any run**, so PydanticAI's inherited
  fifty-request default stands per participant per round. That number is not
  `enbanc`'s and is at a different scope from a `budget`'s `request_limit`, which
  is why the latter may not be inherited
  ([`0029`](../decisions/0029-a-budgets-request-limit-must-be-chosen.md)).

The judge's agent is the same shape with `output_type=[Ruling[verdicts],
_Continuance[verdicts]]`, no `toolsets`, no limiter, and `advocate=None` into
`instruction_parts` — which is how that function already spells *the judge is
seated for no verdict*. It needs no output function, because a judge cites
nothing; it is parameterized from the enum for the same reason an advocate's is,
and that is what `tribunal-construction.md` meant by *the judge learns the verdict
set from the output schema*.

### The toolset, and the callable form of one

[`execution.md`](../design/execution.md#one-wrapper-over-one-combined-toolset)
writes the construction as `*advocate.toolsets`, and that does not type-check:

```text
error: Argument of type "list[AgentToolset[None] | FunctionToolset[None]]" cannot be
assigned to parameter "toolsets" of type "Sequence[AbstractToolset[AgentDepsT]]"
  "FunctionType" is not assignable to "AbstractToolset[None]"
```

`AgentToolset = AbstractToolset[AgentDepsT] | ToolsetFunc[AgentDepsT]`, so
`Advocate.toolsets` already admits the **callable** form — a function resolved
per run that returns a toolset — while `CombinedToolset` takes resolved toolsets
only. Handing a callable straight to the agent instead would put its tool calls
outside the wrapper, and *intercepts every call* would quietly stop being true.

The fix is the one `Agent.__init__` makes for itself at `agent/__init__.py:710`:

```python
CombinedToolset[None](
    [
        FunctionToolset[None](tools=advocate.tools),
        *(
            toolset
            if isinstance(toolset, AbstractToolset)
            else DynamicToolset[None](toolset_func=toolset)
            for toolset in advocate.toolsets
        ),
    ]
)
```

`DynamicToolset` is public (`pydantic_ai.toolsets.__all__`), so this is the
dependency's own adapter rather than one `enbanc` invents, and a dynamic toolset
ends up inside the ledger exactly like a static one. Verified to type-check
clean. **`Advocate` is not narrowed** — tightening the annotation to
`AbstractToolset` would have been the cheap fix and would have dropped a form
[`evidence.md`](../design/evidence.md#a-reference-is-what-makes-an-exhibit-auditable)
promises works.

That object is the agent's only `toolsets=` argument and no `tools=` is passed,
which is what erases the difference between a function, a `FunctionToolset`, an
MCP server and a callable before `enbanc` ever sees it.

### The transcript is built before the toolsets are

Pydantic **copies a list field at construction**, verified:

```text
ledger list is the one passed in: False
rows saw it: 0 1
```

So a `Ledgering` handed a list that was later passed to `Transcript(ledger=...)`
writes into an orphan, and `Transcript.ledger` comes back empty from a proceeding
that retrieved plenty — with nothing raising. The order is therefore fixed and is
not a style choice:

```python
transcript = Transcript[VerdictT](..., entries=[], ledger=[], failures=[])
ledgering = Ledgering[VerdictT](
    wrapped=...,
    advocate=verdict,
    ledger=transcript.ledger,          # the validated list, after construction
    failures=transcript.failures,
)
```

This is [`0016`](../decisions/0016-exhibits-are-stamped-citations.md)'s ownership
constraint — *the ledger is owned by the proceeding* — with the one spelling that
actually satisfies it.

`Transcript.guidance` is keyed on `guidance is not None`, the same predicate
`instruction_parts` uses to emit the guidance part, so the record and the prompt
agree about who was steered — the note
[`tribunal-construction.md`](./tribunal-construction.md) left for this PR.
`procedure` is `_prompting.PROCEDURE`, and `verdicts` is `list(tribunal.verdicts)`
in declaration order.

### The filing clerk owns the transcript

Two rendezvous streams and one coroutine, which is
[`execution.md`](../design/execution.md#the-filing-clerk)'s sketch with the ack
carrying something back:

```python
@dataclass(slots=True)
class _Filed(Generic[VerdictT]):
    filing: _Emitted[VerdictT]        # the union of what a participant may emit
    round: int
    done: anyio.Event
    entry: Entry[VerdictT] | None = None   # written by the clerk before done.set()


async def _clerk(inbox, transcript, out) -> None:
    async for filed in inbox:
        entry = Entry[VerdictT](
            round=filed.round,
            filed_at=datetime.now(UTC),
            filing=_public(filed.filing, transcript.ledger),
        )
        transcript.entries.append(entry)
        await out.send(entry)
        filed.entry = entry
        filed.done.set()
```

`_Emitted` is a private alias in this module — `_Argument | Concession | Ruling`
today, gaining `_Response` and `_Continuance` with the dispatch that produces
them. It is the emit side of [`_filings.py`](../design/packaging.md#the-modules)'s
pairing, and it is local because nothing outside the orchestrator holds a filing
before the clerk has converted it.

- **Both streams are built with a buffer of `0`.** A rendezvous send returns only
  once the value has been received, which is what makes
  [`0010`](../decisions/0010-streaming-yields-the-record.md)'s promise — *the
  entry just received is the last entry of `proceeding.transcript`* — hold with no
  reasoning about interleaving. Verified on the skeleton: for every entry,
  `yielded is transcript[-1]`.
- **The ack carries the stamped `Entry`**, not just permission to continue. The
  task that filed needs the public entry for its own snapshot extension in round
  2, and reading `transcript.entries[-1]` after the wait would be a race a
  concurrent sibling wins. `0027` needs the ack independently, and this PR builds
  it with what that PR will read.
- **Appending, sending and acking are one uninterrupted sequence in one task.**
  There is no second writer to `entries`, so the invariant is structural rather
  than asserted.

### What the clerk stamps in this PR

Both private-to-public conversions happen at this seam
([`execution.md`](../design/execution.md#the-filing-clerk)), and round 1 needs
exactly one of them:

| Emitted | Entered in the record |
|---|---|
| `_Argument[V]` | `Argument[V]`, each `_Exhibit` resolved against the ledger |
| `Concession[V]` | itself — it carries nothing stamped |
| `Ruling[V]` | itself — the judge's verdict and reasoning are its own |

Resolution is a lookup on `(filing.advocate, exhibit.source)` in
`transcript.ledger`, filling `tool`, `reference` and `label` from the
`Retrieval` and keeping `content` as the advocate wrote it — the two are
different facts about one source, and
[`api.md`](../design/api.md#what-participants-file) keeps both. **The advocate
qualifying the id comes from the enclosing filing**, never from the exhibit,
which is the same rule `_exhibits()` already follows in the renderer.

**A miss is an `AssertionError`, not a `ModelRetry`.** By the time a filing
reaches the clerk the output function has already rejected every id this advocate
was not issued, so an unresolvable id here is a bug in `enbanc` rather than a
model behaving badly. It is spelled the way this package already spells an
unreachable arm.

`_Response` and `_Continuance` are the other two rows of that table and they
arrive with the dispatch that produces them
([`round-loop.md`](./round-loop.md)).

### The snapshot, and `since` in round 1

Rows 1–4 of
[`execution.md`'s eight-row table](../design/execution.md#since-and-the-snapshot-run-by-run)
are what this PR has to be right about, and they are the cheap end of it:

| Run | Participant | `since` in | Snapshot | `since` out |
|---|---|---|---|---|
| 1–3 | each advocate | — | — | 0 |
| 4 | judge, deliberation 1 | 0 | entries 1–3 | 1 |

- **Round 1 has no snapshot at all.** An advocate arguing blind gets
  `argument_turn(case, verdict)` and no record, which is
  [`0023`](../decisions/0023-advocates-argue-blind-and-rebut-informed.md) as a
  missing argument rather than as a filter.
- **Round 1 does not advance `since`.** An advocate that was *shown* nothing has
  been shown nothing; filing and being shown are different events, and the dict
  stays at `0` for all three.
- **The judge's snapshot is taken when the fan-out completes**, as a
  `Transcript.model_copy(update={"entries": [...]})` — the shape
  [`rendering.md`](./rendering.md#the-turns) already fixed, so the renderer needs
  no second signature. A shallow copy is right: the agent views read `entries`
  alone.
- **`history` and `since` are plain dicts keyed on `Participant`**, local to the
  proceeding and discarded with it. A first run passes `message_history=None`,
  and `history[p] = result.all_messages()` after each one.

The construction that matters — the base snapshot handed to every task of a
round, extended locally per advocate — is only exercised from round 2, so this PR
builds the base and [`round-loop.md`](./round-loop.md) builds the extension.

### Usage is minted at dispatch

[`execution.md` § Usage](../design/execution.md#usage) says *one `RunUsage` per
participant, minted at the start of the proceeding*, and
[`api.md`](../design/api.md#when-something-goes-wrong) says **absence means never
dispatched** — with
[`outcomes.md` § 4](../design/outcomes.md#4-a-participant-cannot-be-heard)
showing a round-1 failure whose breakdown has *no `'judge'` key*. Pre-populating
the dict would put a judge row of zeroes on exactly that exception and make the
absence unreadable.

So the dict gains a key at the moment a participant is dispatched, and the object
is the orchestrator's from then on:

```python
usage = self.usage_by_participant.setdefault(participant, RunUsage())
result = await agent.run(turn, message_history=history.get(participant), usage=usage)
```

Which satisfies both sentences: the objects are minted by the proceeding and
mutated in place across every run a participant makes, so a run that dies or is
cancelled still leaves what it spent
([`0028`](../decisions/0028-usage-accumulates-per-participant.md)), and a
participant that never ran has no row. `execution.md` gains the four words that
say *at first dispatch* ([below](#design-documents)).

`Hearing.usage` is already the computed sum of the mapping, so nothing here
accumulates a total beside it.

### What a continuance does in this PR

`NotImplementedError`, raised from the orchestrator, naming
[`round-loop.md`](./round-loop.md) — and asserted by a test, so it is a stated
boundary rather than an accident.

The alternatives are worse in the way that matters. Filing the continuance and
returning `Undecided(reason='rounds')` is *correct* for `max_rounds=1` and a
false record for every other tribunal — a transcript stating the rounds ran out
when four remained. Pulling the loop forward is
[`round-loop.md`](./round-loop.md)'s whole scope, and the deferral is what keeps
this PR reviewable.

The placeholder is three lines and its deletion is the first thing the next PR
does. `outcomes.md` § 2 — *the judge rules in round 1* — is the acceptance test
precisely because it is the one ending reachable without a loop.

### `hear()` is `hear_stream()` exhausted, and abandoning cancels

```python
@asynccontextmanager
async def proceed(...) -> AsyncIterator[Proceeding[VerdictT]]:
    ...
    async with anyio.create_task_group() as tg:
        tg.start_soon(orchestrator.run)
        try:
            yield proceeding
        finally:
            tg.cancel_scope.cancel()
```

```python
# on Tribunal
def hear_stream(self, case: Case) -> AbstractAsyncContextManager[Proceeding[VerdictT]]:
    return proceed(question=self.question, statute=self.statute, case=case, ...)

async def hear(self, case: Case) -> Hearing[VerdictT]:
    async with self.hear_stream(case) as proceeding:
        async for _ in proceeding:
            pass
    return proceeding.hearing
```

`hear()` is the stream driven to exhaustion **literally** — it opens the context
manager, consumes the iterator, discards the entries and returns the hearing.
There is one implementation of a proceeding, so the two entry points cannot come
apart ([`0010`](../decisions/0010-streaming-yields-the-record.md)).

**The `finally` is load-bearing and was found by running the skeleton.** Without
it, a consumer that breaks out of the loop leaves the clerk blocked forever on a
rendezvous send nobody will receive, and the `async with` never returns — a
library that hangs on a documented action. Cancelling the scope on the way out
makes [`api.md`](../design/api.md#watching-it-live)'s *abandoning is allowed* true:
in-flight runs are cancelled, `proceeding.transcript` holds what was filed up to
that point, and `proceeding.hearing` raises. Both paths verified:

```text
  yielded: entry:ruling | transcript[-1]: entry:ruling | same: True
hearing over 4 entries
  abandoning after entry:adv0
after break, entries: ['entry:adv0']
hearing after abandon: unfinished
```

On the finished path the cancel is a no-op — every task has already returned, and
the hearing is bound *before* the ruling is acknowledged, because `_file` waits on
an acknowledgment the clerk sets only after the consumer has taken the entry. So a
caller reading `proceeding.hearing` the moment its `async for` ends finds one.

**Both stream ends are closed on the way out, on every path.** A memory object
stream collected without being closed warns from `__del__`, and a library that
leaves a `ResourceWarning` in a caller's test suite has a leak the caller's
process reports. `async with send, receive:` around the task group is the whole
fix, and `filterwarnings = ["error"]` in `pyproject.toml` is what turned it from
invisible into a failing test.

**A raise from inside the proceeding arrives as an `ExceptionGroup`** until
[`failures.md`](./failures.md) adds the first-failure slot — the task group here
is the plain one, which is what this PR's scope says it is. The tests that assert
a failure assert the group, so making it singular later shows up as a diff on
them rather than as a silent widening.

`Proceeding` itself is the handle [`api.md`](../design/api.md#watching-it-live)
specifies and nothing more: `transcript`, `hearing`, and an `__aiter__` that
returns the receive stream. It is not a `BaseModel` — it holds no fact of its own,
is never serialized, and never appears on a result — and `hearing` raises
`ProceedingUnfinished` until the proceeding ends well. Re-raising a
`ProceedingFailed` from that property instead is
[`failures.md`](./failures.md)'s.

### `_proceeding.py` takes the pieces

[`packaging.md`](../design/packaging.md#what-imports-what) fixes the direction:
`_tribunal` imports `_proceeding` and never the reverse, so the round loop is
constructible from a test without building a `Tribunal` first. `proceed()`
therefore takes the question, the statute, the case, the verdict **enum**, the
judge, the advocates, the model and the three limits as keyword arguments — the
enum class rather than a list of members, because the output types are
parameterized with it ([above](#an-output-validator-forbids-a-per-run-output-type))
and `list(verdicts)` is what the two callers that want members write.

Two of those are `Judge` and `Advocate`, which live in `_tribunal.py` — so
`_proceeding.py` imports them **under `TYPE_CHECKING` only**, which is a second
annotation-only break in what is otherwise a one-directional import graph. It is
safe for the same property that makes the renderer's break safe: nothing here
constructs a `Judge` or an `Advocate` and nothing dispatches on either type. The
orchestrator reads `.model`, `.guidance`, `.tools` and `.toolsets`, and that is
all.

**Rejected: moving `Judge` and `Advocate` into a module below `_proceeding.py`.**
It would keep the graph acyclic even in annotations, and it would split *the
three things a caller builds* across two files to serve an import ordering, move
two public names between modules a PR ago, and make `_tribunal.py` a file holding
one class. **Rejected: passing primitives** — a model, a guidance string, a tools
sequence and a toolsets sequence per advocate — which avoids the import by
spreading one object across four parameters.

`packaging.md`'s *one exception* sentence becomes two, with the second one
described ([below](#design-documents)).

### `anyio` becomes a declared dependency

`_proceeding.py` is the first module to import it: task groups, memory object
streams, `anyio.Event`, and — in [`failures.md`](./failures.md) —
`anyio.get_cancelled_exc_class()`. It arrives transitively through `pydantic-ai`
and is pinned at `4.14.2` in the lock, but a package declares what it imports
rather than relying on a transitive it does not control. That is the same
argument `pyproject.toml` already makes for `typing-extensions`, in a comment
that says so, and this line gets one too.

### `__all__` completes at twenty-nine

`Proceeding` is the last name, so `tests/unit/test_export_surface.py` loses its
placeholder and gains the literal list
[`packaging.md`](../design/packaging.md#the-export-surface) fixes.
`test_the_one_name_that_does_not_exist_yet_is_not_claimed` — which holds both the
count of twenty-eight and the assertion that `Proceeding` is absent — goes with
it, replaced by one `==` against twenty-nine sorted strings, and the module
docstring's *partial, deliberately* paragraph goes too.

`__init__.py`'s module docstring loses its *this is a partial surface* paragraph,
and `Tribunal`'s docstring loses *`hear()` and `hear_stream()` do not exist yet*.
Both were written to be deleted here.

### Design documents

Six edits, all of them `CLAUDE.md` rule 2 paid in this commit.

[`execution.md` § What PydanticAI already does](../design/execution.md#what-pydanticai-already-does)
gains a thirteenth finding, **An output validator forbids a per-run
`output_type`**, with the `UserError`, the output-function shape that resolves
it, the three properties verified of it — the tool name and schema derived from
the parameter's type, the `output` budget, and the `RetryPromptPart` — and the two
traps the build found: a bare `TypeVar` reaching the schema as `enum: []`, and a
docstring reaching the model as the tool's description. It also records that a
sole output type is named `final_result`.
[`testing.md`](../design/testing.md#the-four-tiers) carries the count in two
sentences — *records twelve findings* and *two of the twelve findings are
derivations* — and both move to thirteen, with its findings table gaining the
matching row.

[`execution.md` § The output validator resolves ids](../design/execution.md#the-citation-check-resolves-ids)
— retitled *The citation check resolves ids*, because the check becomes an output
function over the same `check_citations` for the reason the finding above gives.
The budget it spends, and the sentence about what that buys, do not move.
[`evidence.md` § An unresolvable id is a validation failure](../design/evidence.md#an-unresolvable-id-is-a-validation-failure)
keeps its prose — *rejected by an output validator* becomes *rejected when the
filing is validated* — because what that section is about is the budget and the
`ProceedingFailed` at the end of it, neither of which changed.

[`execution.md` § One wrapper over one combined toolset](../design/execution.md#one-wrapper-over-one-combined-toolset)
— `*advocate.toolsets` becomes the `DynamicToolset` comprehension, with one
sentence saying why: a toolset may be the callable form, and a callable handed
straight to the agent would make its calls invisible to the ledger.

[`execution.md` § Usage](../design/execution.md#usage) — *minted at the start of
the proceeding* becomes *minted at first dispatch and owned by the proceeding*,
so it stops contradicting
[`api.md`](../design/api.md#when-something-goes-wrong)'s *absence means never
dispatched* and `outcomes.md` § 4's missing `'judge'` key.

[`packaging.md` § What imports what](../design/packaging.md#what-imports-what) —
*one exception* becomes *two annotation-only imports*, with the second one
(`_proceeding` → `_tribunal`) spelled out and the property that keeps it safe.
`tests/unit/test_cycle_break.py` grows the matching assertion, so the claim is
checked rather than stated. The module map's `_proceeding.py` line gains the
orchestrator.

**No `PROCEDURE` bump.** Every word a model reads in this PR is text
[`prompting.md`](../design/prompting.md) already fixed and
[`rendering.md`](./rendering.md) already built; this PR chooses which turn is
rendered when, and writes none of its own.

Every design document keeps `status: draft` and its *none of this exists yet*
banner; making the documentation stop lying is
[`zero-one-zero.md`](./zero-one-zero.md)'s scope.

## Tests

All in `tests/unit/` except one, which is the split the tiers exist for: the
claim about `enbanc` goes to `unit`, and the claim about `pydantic-ai` goes to
`contract` so that a version bump reports as a moved dependency rather than as a
broken library.

| Module | Tier | Pins |
|---|---|---|
| `test_proceeding.py` | unit | round 1 end to end against a `FunctionModel` bench: three advocates dispatched concurrently, one conceding; every filing in `entries` with `round=1` and a stamped `filed_at`; an `_Argument`'s exhibits resolved from the ledger with `tool`, `reference` and `label` filled and `content` left as written; the judge's first run passing `message_history=None` and reading all three round-1 filings; round 1 blind and no peer filing in an advocate's turn; the ledger being the transcript's own list; the invariant; a continuance raising; one tribunal heard twice and twice at once; and the record it produced validating back |
| `test_agents.py` | unit | what the agents are built with, read off the wire: the instruction parts matching `tribunal.instructions_for(participant)` byte for byte; `retries={'tools': 3, 'output': 2}`; the output tools offered per participant, by name; the verdict values reaching the model in the output schema; no `enbanc`-authored tool description; one limiter object shared by every advocate agent and none on the judge's; the inherited fifty-request ceiling standing, asserted where it bites; a per-advocate and per-judge `model` override; a callable toolset reaching the ledger through `DynamicToolset` |
| `test_filing_clerk.py` | unit | the clerk alone, driven directly: the entry sent is the entry appended; `transcript[-1]` is that same object at the moment it is yielded; the ack carrying the stamped `Entry` back; a `Concession` and a `Ruling` passing through unconverted; an exhibit resolving against its own advocate's rows; an unresolvable id reaching the clerk raising `AssertionError`; the toolsets writing into the transcript's own lists; a snapshot that stops growing; the orchestrator built with no `Tribunal` at all |
| `test_hear_stream.py` | unit | `hear()` returning what the exhausted stream returns, over one scripted bench; `proceeding.hearing` raising `ProceedingUnfinished` before the end; breaking out of the loop leaving the transcript intact and the block exiting rather than hanging; `hearing.outcome is hearing.transcript[-1].filing` |
| `test_usage.py` | unit | one `RunUsage` per participant, mutated in place across runs; `hearing.usage` equal to the sum of the breakdown; a key appearing only once its participant is dispatched |
| `test_export_surface.py` | unit | the twenty-nine-name literal, replacing the placeholder |
| `outcomes/test_02_rules_in_round_1.py` | unit | [`outcomes.md` § 2](../design/outcomes.md#2-the-judge-rules-in-round-1) as written: four entries, `rounds=1`, `Ruling` as both the outcome and the last filing, three advocates plus `'judge'` in the breakdown, no `Continuance` anywhere |
| `test_an_output_validator_forbids_a_run_output_type.py` | contract | the finding: `run(output_type=...)` raising `UserError` on an agent with a validator, including when the override equals the agent's own type; an output function over a single model parameter producing the same tool name, description and schema as that model alone; its `ModelRetry` spending the `output` budget and reaching the model as a `RetryPromptPart` |

### The capturing model, and `assert_invariant_held`

[`testing.md` § The transcript invariant](../design/testing.md#the-transcript-invariant)
specifies a helper taking what a capturing `FunctionModel` recorded and the
transcript that resulted, and
[`rendering.md`](./rendering.md#what-is-deliberately-not-asserted) deliberately
left it out — *a helper with no caller is a guess about its own signature*. This
is the PR with a caller.

Both land in `tests/unit/conftest.py` as fixtures, beside the worked-proceeding
transcript, because a `conftest.py` is not a module a test may import from:

- **the capturing model** — a `FunctionModel` that records every `ModelMessage`
  it is handed, keyed by participant, and then behaves as the script says;
- **`assert_invariant_held(captured, transcript, instructions_for)`** — which
  requires every message part to be derivable from `render(transcript, view)` or
  from the participant's instructions, or to be one of the four escapes
  [`execution.md`](../design/execution.md#what-lands-in-history-that-no-rendered-turn-contains)
  enumerates: a `RetryPromptPart`, tool-call traffic, `ToolReturnPart('Final
  result processed.')`, and the agent's own pre-stamp output.

The fourth escape is why this cannot be a substring test, and this PR is where
that stops being theory: the advocate emits `_Exhibit(source='s1',
content=...)` and the transcript holds the `Exhibit` with the tool and the
reference stamped beside it, so a byte-for-byte containment check fails on a
proceeding that is perfectly correct. The helper compares the stamped fields it
can and accounts for the rest.

**It is an assertion, not a test.** `test_proceeding.py` and
`outcomes/test_02_rules_in_round_1.py` both call it, and every proceeding test
written after this PR gets the invariant checked for free — which is the point of
writing it as a helper rather than as one dedicated test.

### The bench is the fixture that already exists

`tests/unit/conftest.py` holds `outcomes_kwargs`, the tribunal
[`outcomes.md`](../design/outcomes.md#the-tribunal-these-examples-use) works every
ending through, with `psql` and `web_search` faked and `TestModel` as the model.
This PR varies one key — the model — and hands it a scripted `FunctionModel`
bench instead. `psql` is called for the first time here, which is what makes the
ledger, the exhibits and the suppression join real data rather than hand-built
rows.

The eight-entry `proceeding` transcript stays what it is: a hand-built record for
the renderer's tests. It is a *two-round* proceeding, so nothing in this PR can
produce it, and `test_proceeding.py` asserts against the four-entry record its
own bench actually files.

### What is deliberately not asserted

**Anything about round 2.** No response is dispatched, no interrogatory is
stamped, and no `since` advances past the judge's first deliberation. The
`NotImplementedError` a continuance raises is asserted — as a boundary, with the
message naming the next PR — and nothing beyond it is.

**How many entries survive a cancelled round**, and **exact usage after a
failure**. [`testing.md`](../design/testing.md#what-must-not-be-asserted) rules
both out, and in any case nothing fails in this PR: the task group has no
first-failure slot until [`failures.md`](./failures.md).

**That the fan-out is actually concurrent.** `max_concurrency` is handed to the
agents and the tasks are started in one group; asserting overlap in wall-clock
time would be a test of anyio's scheduler. What is asserted is the object
identity — one limiter, shared — which is the claim `enbanc` makes.

**That a provider caches the instruction prefix.** The parts are static and the
first three are byte-identical across advocates, which
[`tribunal-construction.md`](./tribunal-construction.md) already pins. Whether a
provider then caches them is the provider's.

## Open questions

*None open.* The one that had to be settled before a line could be written is in
the prose above: an output validator forbids a per-run `output_type`, so the
citation check rides on [the output type](#an-output-validator-forbids-a-per-run-output-type)
instead — with a second agent per advocate and a three-shape union both written
out and rejected there. Building it added two traps to that section rather than
reopening it: a filing parameterized with a bare `TypeVar` reaches the model as
`enum: []`, and a docstring on an output function reaches it as the tool's
description. Four smaller ones were settled the same way and each
answer carries its reasoning: the transcript is
[built before](#the-transcript-is-built-before-the-toolsets-are) the toolsets that
write into it, usage is [minted at dispatch](#usage-is-minted-at-dispatch), a
callable toolset is [wrapped rather than excluded](#the-toolset-and-the-callable-form-of-one),
and a continuance [raises](#what-a-continuance-does-in-this-pr) rather than being
half-handled. Three of those are edits to `execution.md` in this commit rather
than facts that live only here.
