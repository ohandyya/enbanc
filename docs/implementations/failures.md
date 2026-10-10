---
status: draft
updated: 2026-10-10
---

# When a participant cannot be heard

**The failure half of piece 3.** A round that loses a participant cancels the
rest where they stand, names the one that failed, and raises with the record
intact.

## Scope

The task group gains its first-failure slot and its cancelled-exception
re-raise — which comes *first*, and is load-bearing: without it a cancelled
sibling can win the race and `ProceedingFailed` names an advocate that was merely
stopped. The group then exits cleanly and the orchestrator raises afterwards with
the original error as `__cause__`, so `participant` is singular by construction
rather than by picking one out of an `ExceptionGroup`.

**"Afterwards" means after the outermost group, in `proceed()`.** Found while
planning, not in the design: anyio wraps an exception raised in a task group's
*body* as well as one raised by a child
([below](#where-the-raise-can-happen)), so a `ProceedingFailed` raised anywhere
inside `run()` would reach the caller as an `ExceptionGroup` two levels deep. The
round records the failure, `run()` holds it, and `proceed()` raises it once every
group has exited.

The judge gets the same guard. It runs alone rather than in a fan-out, so its
guard is a plain `try` with the same two arms and no slot.

Also here: `ProceedingUnfinished` from `Proceeding.hearing`, and what abandoning
a stream leaves behind. That includes a consumer that *raises* out of its loop,
whose exception reaches it today as an `ExceptionGroup` for the same anyio reason.

Every round is covered, not only round 1. Since
[`round-loop.md`](./round-loop.md) the plain task group runs in every round, so a
failure in round 2 or 3 is the same code path and gets its own test.

**Not in this PR.** Any classification of provider errors. `enbanc` wraps and
does not taxonomize. Also not here: the clerk's append-before-send ordering,
which lets a consumer that `await`s in its loop see `transcript[-1]` run one
entry ahead of what it was yielded. That is a streaming defect, not a failure
one, and none of the code it touches is code this PR changes. It is
[`execution.md`'s open question](../design/execution.md#open-questions) and
[`stream-ordering.md`](./stream-ordering.md)'s PR, sequenced next.

## Implements

- [`execution.md` § The round's task group](../design/execution.md#the-rounds-task-group)
  — the failure pattern in full
- [`execution.md` § A failing fan-out need not raise an `ExceptionGroup`](../design/execution.md#a-failing-fan-out-need-not-raise-an-exceptiongroup)
- [`api.md` § When something goes wrong](../design/api.md#when-something-goes-wrong)
- [`api.md` § Watching it live](../design/api.md#watching-it-live) — a failure
  out of the `async with`, `hearing` re-raising it, and abandonment
- [`evidence.md` § What tools may do](../design/evidence.md#what-tools-may-do) —
  the timeout ladder, and where it ends
- [`outcomes.md` § 4. A participant cannot be heard](../design/outcomes.md#4-a-participant-cannot-be-heard)
  and [§ 6. The same endings, watched live](../design/outcomes.md#6-the-same-endings-watched-live)
- [`testing.md` § What must not be asserted](../design/testing.md#what-must-not-be-asserted)
  — how many entries survive a cancelled round is not a test, and exact usage
  after a failure is not either

## Depends on

[`proceeding-core.md`](./proceeding-core.md), merged as
[PR #26](https://github.com/ohandyya/enbanc/pull/26), and
[`round-loop.md`](./round-loop.md), open as
[PR #28](https://github.com/ohandyya/enbanc/pull/28). This branch starts from
#28's head. If #28 changes shape under review, the `_answer` guard below follows
it.

## Files

No new module, and nothing on `__all__` moves: `ProceedingFailed` and
`ProceedingUnfinished` have been exported since [`schemas.md`](./schemas.md), and
`ProceedingFailed`'s constructor, message and `usage` fold are already built and
tested in `test_errors.py`. This PR is the code that raises it.

| File | Change |
|---|---|
| `src/enbanc/_proceeding.py` | `_Unheard`, the one-slot dataclass; `_heard()`, the guard every advocate task runs inside; `_round()` minting usage at dispatch, starting tasks through `_heard()`, and raising after its group; the judge's guard in `_deliberate()`; `_failed()`; `run()` holding the failure; `_Orchestrator.failure`; `Proceeding.hearing` re-raising it; `proceed()` raising it, and handing a consumer's own exception back bare |
| `docs/decisions/0040-a-participant-failure-is-an-exception.md` | new, written while planning — the guard catches `Exception` ([below](#the-guard)) |
| `docs/README.md` | indexes `0040` |
| `docs/design/execution.md` | [below](#design-documents) |
| `docs/design/api.md` | [below](#design-documents) |
| `docs/design/testing.md` | [below](#design-documents) |

### Where the raise can happen

`execution.md` says the group exits cleanly and *the orchestrator raises
afterwards*. It does not say after *which* group, and there are three nested
ones: `_round()`'s fan-out inside `run()`'s clerk group inside `proceed()`'s.
Verified against **`anyio 4.14.2`**:

```text
raise in a task group's body, one healthy child   -> ExceptionGroup
raise in a task group's body, no children at all  -> ExceptionGroup
consumer raises inside a hear_stream-shaped cm    -> ExceptionGroup
cm raises after its own group has exited          -> Failed            (bare)
```

The second line is the one that matters. anyio does not distinguish a body
exception from a child's. Any `raise` lexically inside an `async with
create_task_group()` comes out grouped, even when nothing else in that group
failed. So clean exits are not enough on their own: **nothing may raise
`ProceedingFailed` inside a group at all.** That leaves one place it can be
raised from:

```python
# _round — the fan-out
first = _Unheard[VerdictT]()
async with anyio.create_task_group() as tg:
    for verdict, start in dispatch:              # _argue or _answer, with its args
        self._usage(verdict)                     # minted at dispatch — see below
        tg.start_soon(self._heard, first, tg.cancel_scope, verdict, start)
if first.participant is not None:
    raise self._failed(first.participant, round) from first.exc
```

That `raise` is *outside* `_round`'s group but still inside `run()`'s, so `run()`
catches it rather than letting it reach that group's exit:

```python
# run — the clerk's group
async with anyio.create_task_group() as tg:
    tg.start_soon(self._clerk, inbox_receive, out)
    async with inbox_send:
        try:
            outcome = await self._hear(inbox_send)       # the round loop, moved out whole
        except ProceedingFailed as failed:
            self.failure = failed
        else:
            self.hearing = Hearing[VerdictT](outcome=outcome, ...)
await out.aclose()
```

```python
# proceed — the outermost group, and the only raise
left: Exception | None = None
async with send, receive, anyio.create_task_group() as tg:
    tg.start_soon(orchestrator.run, send)
    try:
        yield proceeding
    except anyio.get_cancelled_exc_class():
        raise
    except Exception as e:           # the consumer's own, held past the group that would wrap it
        left = e
    finally:
        tg.cancel_scope.cancel()
if left is not None:
    raise left
if orchestrator.failure is not None:
    raise orchestrator.failure
```

What each piece buys:

- **`run()` stays the place the hearing is bound**, and the failure is bound at
  the same point and for the same reason: before `out` closes, so a consumer whose
  `async for` has just ended finds either one. `api.md`'s *the exception comes out
  of the `async with`, not the `async for`* then holds as written. The stream
  simply ends, and the raise happens at block exit.
- **The transcript on the exception is final when it is raised.** It is the
  orchestrator's own `Transcript`, the object `proceeding.transcript` already
  is, so `e.transcript is proceeding.transcript` and § 6's *the same entries*
  holds by identity. A cancelled sibling whose filing the clerk had already
  received still lands: the clerk drains its inbox before `run()`'s group exits,
  and `proceed()` raises only after that. Its run completed, which is when
  [`0012`](../decisions/0012-a-failure-cancels-the-round.md) says a filing enters
  the record.
- **A consumer's own exception wins over a recorded failure.** It is the one the
  consumer is handling. `proceeding.hearing` still re-raises the failure for
  anyone who asks. Cancellation is not held, because anyio does not wrap it and
  an outer scope has to see its own.
- **`hear()` does not change.** It already reads `proceeding.hearing` *after*
  the `async with`, so a failure raises out of the block exit before that line
  is reached.

### The guard

```python
async def _heard(self, first, scope, participant, start) -> None:
    try:
        await start()
    except anyio.get_cancelled_exc_class():
        raise                                    # cancellation is never a failure
    except Exception as e:                       # 0040: not BaseException
        if first.participant is None:
            first.participant, first.exc = participant, e
        scope.cancel()
```

`_argue()` and `_answer()` are not touched. A wrapper is what keeps the guard
written once rather than in two bodies. The slot is assigned before
`scope.cancel()` with no `await` between them, which is why
[the contract test's](../../tests/contract/test_a_failing_fan_out_need_not_raise_a_group.py)
child-failure case cannot discriminate.

**`except Exception`, not `BaseException`**
([`0040`](../decisions/0040-a-participant-failure-is-an-exception.md), decided
while planning). Cancellation, `KeyboardInterrupt`, `SystemExit` and
`GeneratorExit` all pass through untouched, so a Ctrl-C interrupts a proceeding
instead of being recorded as *advocate 'deny' could not be heard*. Because
anyio's cancellation is a `BaseException`, the re-raise arm no longer decides
anything. It stays first, as the explicit statement that cancellation is not a
failure, and becomes load-bearing again if the arm is ever widened.

**The judge's guard has no slot.** `_deliberate()` wraps the `judge_agent.run()`
call alone: the two arms above, with the general one raising
`self._failed(JUDGE, deliberation) from e` directly. It is not in a group, so it
raises straight into `_hear()` and on to `run()`'s `except`. A judge whose output
will not validate arrives here as `UnexpectedModelBehavior` after three attempts,
which is § 4's fourth case. Nothing about it is special.

`_failed(participant, round)` builds the exception from the orchestrator's own
state: `transcript=self.transcript` and
`usage_by_participant=self.usage_by_participant`. Both are passed as the live
objects, not copies. Nothing writes to either once the failing round's group has
exited, and identity with the handle is what § 6 shows.

### What reaches the guard, verified

`__cause__` is meant to be the original error, so what matters is what
`Agent.run()` actually raises. If PydanticAI grouped a tool's exception (it runs
tool calls concurrently), `__cause__` would be a group and § 4's
`e.__cause__ is psycopg.OperationalError(...)` would be false. Against
**`pydantic-ai 2.36.0`**, one `Agent` with `retries={'tools': 3, 'output': 2}`:

```text
tool raises                  -> builtins.ConnectionError: connection refused
tool raises beside another   -> builtins.ConnectionError: connection refused
never files (50 ceiling)     -> pydantic_ai.exceptions.UsageLimitExceeded: The next request would exceed the request_limit of 50
output never validates       -> pydantic_ai.exceptions.UnexpectedModelBehavior: Exceeded maximum output retries (2)
```

All bare, so no unwrapping is written. The fifty-request ceiling is the case
[`round-loop.md`](./round-loop.md#the-budget-check) left to this PR: it is a
`UsageLimitExceeded` from *inside* a run, caught by the general arm like
anything else. `_budget_spent()` still catches only the one raised at a boundary.

### Usage keys are minted at dispatch

`_argue()` and `_answer()` mint their participant's `RunUsage` as an argument
expression to `run()`, *inside* the task. "Every dispatched participant has a
key" then depends on each task reaching its first line before a sibling's
failure cancels it. On anyio's asyncio backend it does:

```text
two tasks started, scope cancelled before either took a step
bodies that ran: ['approve', 'refer']
```

But that is scheduler behaviour, not a guarantee. `_round()` therefore calls
`self._usage(verdict)` before `start_soon`. It is idempotent (`setdefault`), the
in-task call stays, and *dispatched* and *has a key* become the same event. A
task cancelled before its first request keeps a `RunUsage` of zeroes, which is
the row `api.md` already describes.

### What leaves the module

Four sentences that stop being true: `Proceeding.hearing`'s *that half arrives
with `failures.md`*, `_round()`'s paragraph on the plain task group, the module
docstring's silence on failure (it lists the three endings inside the envelope and
should now name the interruption), and `proceed()`'s docstring, which gains the
raise after the group and the consumer's exception.

### Design documents

**Already made while planning**, for `0040`. [`execution.md` § The round's task
group](../design/execution.md#the-rounds-task-group): the sketch's general arm
is `except Exception`, and the *load-bearing* paragraph is rewritten so that
the hierarchy is what keeps a cancel from naming a participant, with the re-raise
as its explicit statement. [§ A failing fan-out need not raise an
`ExceptionGroup`](../design/execution.md#a-failing-fan-out-need-not-raise-an-exceptiongroup)
scopes its re-raise claim to a `BaseException` handler.
[`testing.md`](../design/testing.md#the-four-tiers)'s findings-table row says the
same.

**Made with the code:**

[`execution.md` § The round's task group](../design/execution.md#the-rounds-task-group)
— *the orchestrator raises afterwards* gains where: after the outermost group, in
`proceed()`, with `run()` holding the failure. The judge's guard gets a sentence:
it runs alone, so it is a `try` with the same two arms and no slot. Minting usage
at dispatch is stated where § Usage already says *minted at its first dispatch*.

[`execution.md` § A failing fan-out need not raise an `ExceptionGroup`](../design/execution.md#a-failing-fan-out-need-not-raise-an-exceptiongroup)
— gains the second half of the finding: a raise in a group's *body* is grouped
too, even with no failing child, so a clean exit is necessary and not sufficient.
[`testing.md`](../design/testing.md#the-four-tiers)'s findings-table row for it
gains the same clause. The count stays at thirteen, because this extends a
finding rather than adding one.

[`api.md` § Watching it live](../design/api.md#watching-it-live) — one sentence:
an exception the consumer raises inside the loop comes back out of the `async
with` as itself, and `proceeding.hearing` then raises whatever the proceeding's
own state says: the failure if one was recorded, `ProceedingUnfinished` if not.

**No `PROCEDURE` bump.** No text a model reads moves.

## Tests

Unit-tier except one row.

| Module | Tier | Pins |
|---|---|---|
| `outcomes/test_04_cannot_be_heard.py` | unit | **new.** [`outcomes.md` § 4](../design/outcomes.md#4-a-participant-cannot-be-heard), all four. **An advocate's provider is down:** `DENY`'s model raises after `APPROVE`'s argument has been seen (forced, [below](#forcing-the-orderings)), and `REFER` is gated and never released. `ProceedingFailed` is raised bare, `participant is DENY`, `round == 1`, `__cause__` is the very exception the bench raised, the message is `advocate 'deny' could not be heard in round 1`; `APPROVE`'s argument is in `e.transcript`; no entry is a `Continuance`; all three advocates are keyed, `'judge'` is not; `usage.requests >= 3`. **The judge's provider is down:** `participant == 'judge'`, all four keyed, three entries and no `Continuance` (no round was cancelled, so the count is deterministic and allowed). **An advocate's tool raises:** in round 2, answering `r1-q1`, through a `psql_down` tool raising `OSError('connection refused')`. `round == 2`, the continuance is on the record, `__cause__` is that `OSError`. **The judge's output will not validate:** `continuances=[[]]`, so `__cause__` is `UnexpectedModelBehavior('Exceeded maximum output retries (2)')`, the judge captured three times under one key, and nothing it emitted is in the transcript |
| `outcomes/test_06_watched_live.py` | unit | **new.** [§ 6](../design/outcomes.md#6-the-same-endings-watched-live), all four. A ruling ends the loop after the `Ruling`; `max_rounds` and the budget end it after a `Continuance`, nothing raises, and only `reason` differs; a failure raises out of the `async with` and **not** the `async for` (a line after the loop, still inside the block, runs) with `e.transcript is proceeding.transcript`; walking away on the `Continuance` leaves four entries and `ProceedingUnfinished` |
| `test_failures.py` | unit | **new.** What § 4 does not reach. A failure in round 3, `round == 3`. Two advocates failing in the same step, released by one gate: exactly one is named and `__cause__` is *that* advocate's own exception, never a group. An **external cancel**: `hear()` under `anyio.move_on_after` with an advocate gated forever, so the scope reports it caught the cancel, nothing is raised, and no participant is named — the integration-level twin of the contract test's discriminating case. `proceeding.hearing` after a failure raises the **same object** that came out of the block (`is`), and keeps doing so. The **last rung of the timeout ladder**: `Tool(slow, timeout=0.01)` timing out four times against `tools=3` gives `__cause__` an `UnexpectedModelBehavior` naming the tool, with `DENY`'s timeouts on `e.transcript.failures`. A degraded advocate's record survives its failure. **`0040`'s line:** a tool raising a test-local `BaseException` subclass (not `KeyboardInterrupt`, which pytest itself would act on) is not wrapped — no `ProceedingFailed` anywhere in what escapes, and the subclass among its leaves, however anyio groups it |
| `test_hear_stream.py` | unit | gains: a consumer that raises `ValueError` inside the loop gets `ValueError` back, not a group, and `proceeding.hearing` then raises `ProceedingUnfinished`; an external cancel of a stream leaves `ProceedingUnfinished` too |
| `test_agents.py` | unit | `test_no_usage_limit_is_passed_into_a_run` changes from `BaseExceptionGroup` to `ProceedingFailed`: `participant` is one of the advocates (which one hits fifty first is scheduling), `__cause__` is `UsageLimitExceeded` naming `request_limit of 50`. `_leaves()` is deleted, because this was its only caller |
| `test_a_failing_fan_out_need_not_raise_a_group.py` | contract | gains the body-raise half: a raise in a group's body with no failing child is grouped, and the same raise after the group exits is bare. This module already pins anyio rather than `pydantic-ai`, and this is the fact `proceed()`'s shape rests on |

`test_filing_clerk.py`'s `BaseExceptionGroup` stays. It drives the clerk directly,
and an unresolvable id reaching the clerk is a bug in `enbanc`, not a participant
that could not be heard: an `AssertionError` from the clerk's own task is not
something the guard should launder into a `ProceedingFailed`. `test_errors.py`
needs nothing, because the exception's shape was built and tested with the
schemas.

`progress.md` said `test_hear_stream.py` and `test_proceeding.py` assert the
`ExceptionGroup` today. Neither does. The two that do are `test_agents.py` and
`test_filing_clerk.py`, and only the first changes.

### The bench grows one thing

`raises: Mapping[key, BaseException]`. A turn named there raises that exception
from the model instead of responding, *after* its gate (if any) has opened, so a
test can choose the moment as well as the participant. Raising the instance it
was given is what lets a test assert `__cause__ is` rather than `isinstance`.

The judge's turns gain a key so that `gates` and `raises` can reach them:
`("judge", n)` for deliberation *n*, read off the turn as `_deliberate` already
does. Nothing else about the bench changes. `continuances=[[]]` already scripts
§ 4's empty continuance, and a raising tool is an `Advocate(tools=[...])` in the
kwargs, not a bench feature.

The provider and the database are stand-ins: `ConnectionError("Connection
error.")` for `anthropic.APIConnectionError` and `OSError("connection refused")`
for `psycopg.OperationalError`. The offline tier imports neither SDK, and the
claim under test is *whatever was raised is `__cause__`*, which a builtin
carries as well as either.

### Forcing the orderings

§ 4's first case has `APPROVE` file before `DENY` fails. The bench leaves that to
the scheduler, so the test drives `hear_stream()` and gates `DENY` on an
`anyio.Event` that the consumer sets when it receives `APPROVE`'s `Argument`.
`DENY` then raises, and `APPROVE`'s argument is in the record because the
consumer has already seen it. That is an assertion of *which* entry is present.
It is not an assertion of how many.

`REFER` is gated on an event nothing sets, so it is demonstrably mid-run when the
failure arrives. Every test that relies on a cancel runs under
`anyio.fail_after(5)`. A missing cancel then fails the test instead of hanging
the suite, which is the trap
[`test_abandoning_the_stream…`](../../tests/unit/test_hear_stream.py) already
names.

### What is deliberately not asserted

**How many entries a failed round leaves**, beyond the entries a test forced
onto the record. [`testing.md`](../design/testing.md#what-must-not-be-asserted).
The judge-side cases are the exception, because no round was cancelled.

**Exact usage on a failure.** Keys present or absent, and `>=` against the
requests the bench is known to have served.

**Which advocate is named when two fail in one step**, or which one hits the
fifty-request ceiling first. Only that exactly one is named, and that
`__cause__` is that one's own exception.

**Anything `transcript[-1]` says while a consumer `await`s inside its loop.**
That is [`stream-ordering.md`](./stream-ordering.md)'s defect. These tests
sidestep it the way the existing streaming tests do, with loop bodies that do
not `await` before the line under test.

## Open questions

*None open.* Two were raised while planning. Which exception class the guard
catches was settled as `Exception` and recorded in
[`0040`](../decisions/0040-a-participant-failure-is-an-exception.md). The
clerk's append-before-send ordering was moved out of this PR
([Scope](#scope)).
