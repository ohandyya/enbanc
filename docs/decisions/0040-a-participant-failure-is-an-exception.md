---
status: accepted
updated: 2026-10-10
---

# 0040. A participant failure is an `Exception`, not a `BaseException`

## Context

[`0012`](./0012-a-failure-cancels-the-round.md) made the first failure in a
round cancel the advocates still in flight, and
[`execution.md`](../design/execution.md#the-rounds-task-group) gave the shape
that makes it work: each advocate task records its own failure into a single
slot and cancels the group's scope, so the group exits cleanly and
`ProceedingFailed.participant` is singular because only one slot is ever filled.

The sketch's general arm caught **`BaseException`**, with an
`except anyio.get_cancelled_exc_class(): raise` arm ahead of it. That arm was
written up as load-bearing, and under `BaseException` it is.
`tests/contract/test_a_failing_fan_out_need_not_raise_a_group.py` shows that
without it, an outer cancel scope firing while every child is healthy gets the
first cancelled advocate recorded as the failure.

Planning [`failures.md`](../implementations/failures.md) raised a question the
sketch had not asked: what else does `BaseException` catch? `KeyboardInterrupt`,
`SystemExit` and `GeneratorExit`, none of which is anything a participant did.
Caught there, each would be wrapped as `ProceedingFailed`, which is an
`Exception`. So a stop signal would be turned into an ordinary error. A caller
looping over cases with `except ProceedingFailed: log and continue` would log a
Ctrl-C as *advocate 'deny' could not be heard in round 2* and go on to the next
case.

## Decision

**The guard around a participant's run catches `Exception`.** Anything that is
not an `Exception` passes through untouched and is never recorded as a failure.
That covers cancellation, `KeyboardInterrupt`, `SystemExit` and
`GeneratorExit`. The same holds for the judge's guard, which has no slot but the
same two arms.

```python
try:
    ...run, file, await the ack...
except anyio.get_cancelled_exc_class():
    raise                                     # cancellation is never a failure
except Exception as e:
    if first.participant is None:
        first.participant, first.exc = participant, e
    tg.cancel_scope.cancel()
```

**The re-raise arm stays, first, though it now decides nothing.** anyio's
cancellation is `asyncio.CancelledError` or `trio.Cancelled`, and both are
`BaseException`, so neither can reach an `except Exception` arm. The guarantee
that an external cancel names no participant now rests on the exception
hierarchy rather than on the order of two `except` clauses, which is harder to
break by rearranging code. The arm is kept as the explicit statement that
cancellation is deliberately not a failure. It becomes load-bearing again the
moment anyone widens the general arm.

Every failure the design names is still caught, because every one is an
`Exception`. That covers a provider error, a tool's own exception, a timed-out
tool's spent `tools` budget (`UnexpectedModelBehavior`), output that will not
validate (`UnexpectedModelBehavior`), PydanticAI's fifty-request ceiling
(`UsageLimitExceeded`), and an `ExceptionGroup` a tool raises from a task group
of its own.

## Consequences

**`ProceedingFailed` means what it says.** It is raised only when a participant
could not be heard, never when the process or the caller is stopping. Interrupting
a proceeding interrupts it.

**A `BaseException` subclass raised for a participant-level reason is not
wrapped.** A tool or SDK that raised one to report an ordinary failure would
surface bare instead of as `ProceedingFailed`, breaking
[`api.md`](../design/api.md#when-something-goes-wrong)'s *no provider exception
reaches you bare* for that case. Doing that is a defect in the raising code,
and nothing `enbanc` depends on does it today. If one ever does, the fix is to
catch that class by name, not to widen the arm back.

**The contract test is unchanged.** It pins how anyio behaves under a
`BaseException` handler, which is still the fact that explains why the re-raise
arm exists, and it says nothing about which arm `enbanc` writes.

## Alternatives considered

**Keep `BaseException`, exactly as the sketch had it.** No design edit, and the
re-raise stays load-bearing in the literal sense. Rejected because it turns a
process-level stop into a recorded participant failure, and the cost of the
alternative is one word. On asyncio a Ctrl-C is usually delivered to the event
loop rather than raised inside a tool coroutine, so the mislabelling is rarer
than it sounds. It is more reachable under anyio's trio backend and through a
tool that calls `sys.exit()`. When it does happen it produces a wrong record
and a loop that is hard to stop.

**`BaseException`, re-raising `KeyboardInterrupt` and `SystemExit` by name.**
Rejected because it lists the exceptions to let through rather than the ones to
catch. It is `except Exception` written longer, and it misses whatever the next
`BaseException` subclass turns out to be.
