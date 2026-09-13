"""A failing fan-out need not raise an `ExceptionGroup`.

Pins the finding of the same name in `docs/design/execution.md`. An `anyio` task group whose
child raises propagates an `ExceptionGroup`, which would put `enbanc` in the position of
picking one failure out of a set — exactly the field
`docs/decisions/0012-a-failure-cancels-the-round.md` closed by keeping
`ProceedingFailed.participant` singular. A child that records its own failure into a single
slot and cancels the scope lets the group exit cleanly instead, so the slot is singular because
only one is ever filled rather than because `enbanc` chose.

The third test is the reason this module is worth having. Under a *child failure* the
cancelled-exception re-raise changes nothing, because the failing task fills the slot before it
cancels, with no `await` between the two statements. What it protects is an outer cancel scope
firing while every child is healthy. See `execution.md`'s "The round's task group".

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.

This one pins `anyio` rather than `pydantic-ai` itself. `anyio` arrives transitively, and the
task group is the shape `execution.md` designs the round around, so a change in its
cancellation semantics falsifies that document just as surely.
"""

from dataclasses import dataclass, field

import anyio
import pytest

#: Long enough that a healthy child is still running when the outer scope fires, short enough
#: that the module costs no wall-clock time worth measuring.
_FOREVER = 5.0
_A_MOMENT = 0.01


@dataclass
class _First:
    """`execution.md`'s single slot: the one failure `ProceedingFailed` will name."""

    participant: str | None = None
    exc: BaseException | None = None
    filed: list[str] = field(default_factory=list)


async def test_the_naive_shape_raises_an_exception_group() -> None:
    # The baseline the design refuses. Nothing here records or cancels, so anyio has a set of
    # failures to report and hands back a group.
    async def child(name: str) -> None:
        raise RuntimeError(f"{name}'s provider is down")

    with pytest.raises(BaseExceptionGroup) as caught:
        async with anyio.create_task_group() as tg:
            tg.start_soon(child, "deny")

    assert isinstance(caught.value.exceptions[0], RuntimeError)


async def test_record_and_cancel_lets_the_group_exit_cleanly() -> None:
    # `docs/design/outcomes.md#an-advocates-provider-is-down` reproduced: one named failure, the
    # peers' partial work intact, and no group for the orchestrator to pick from.
    first = _First()

    async def child(name: str, fails: bool) -> None:
        try:
            if fails:
                await anyio.sleep(_A_MOMENT)
                raise RuntimeError(f"{name}'s provider is down")
            first.filed.append(name)
            await anyio.sleep(_FOREVER)
        except anyio.get_cancelled_exc_class():
            raise
        except BaseException as e:
            if first.participant is None:
                first.participant, first.exc = name, e
            tg.cancel_scope.cancel()

    async with anyio.create_task_group() as tg:
        tg.start_soon(child, "approve", False)
        tg.start_soon(child, "deny", True)

    assert first.participant == "deny"
    assert isinstance(first.exc, RuntimeError)
    assert first.filed == ["approve"]


@pytest.mark.parametrize("reraise", [True, False])
async def test_a_child_failure_fills_the_slot_with_or_without_the_re_raise(reraise: bool) -> None:
    # `execution.md`'s own scenario, and it cannot discriminate: the failing task assigns the
    # slot *before* it calls `cancel()`, with no `await` between the two statements, so there is
    # no point at which a sibling runs in between. Written to this scenario the assertion passes
    # either way — a test that cannot fail. It is kept to show precisely that, so the next
    # reader does not mistake it for the thing the re-raise protects.
    first = await _fan_out(reraise=reraise, cancel_from_outside=False)

    assert first.participant == "deny"
    assert isinstance(first.exc, RuntimeError)


@pytest.mark.parametrize(
    ("reraise", "expected"),
    [
        (True, None),
        # Without the re-raise, the first healthy advocate to notice it was cancelled is caught
        # by the general handler and records *itself*. `ProceedingFailed` would then name a
        # participant that was merely stopped. Asserted as "some participant", not a named one:
        # which peer notices first is a scheduling detail, and the defect is that any is named.
        (False, "a participant that was merely stopped"),
    ],
)
async def test_the_re_raise_is_what_survives_an_external_cancellation(
    reraise: bool, expected: str | None
) -> None:
    # The discriminating case, and a live hazard rather than a hypothetical: a caller cancelling
    # `hear()`, or a timeout wrapped around a proceeding, reaches exactly this. Nothing failed,
    # so nothing should be named.
    first = await _fan_out(reraise=reraise, cancel_from_outside=True)

    assert (first.participant is None) == (expected is None)


async def _fan_out(*, reraise: bool, cancel_from_outside: bool) -> _First:
    """`execution.md`'s round, with the re-raise arm made optional so it can be probed."""
    first = _First()

    async def child(name: str, fails: bool) -> None:
        try:
            if fails:
                await anyio.sleep(_A_MOMENT)
                raise RuntimeError(f"{name}'s provider is down")
            await anyio.sleep(_FOREVER)
        except anyio.get_cancelled_exc_class() as e:
            if reraise:
                raise  # a peer failed; die where we stand
            if first.participant is None:
                first.participant, first.exc = name, e
            tg.cancel_scope.cancel()
        except BaseException as e:
            if first.participant is None:
                first.participant, first.exc = name, e
            tg.cancel_scope.cancel()

    with anyio.move_on_after(_A_MOMENT if cancel_from_outside else _FOREVER):
        async with anyio.create_task_group() as tg:
            tg.start_soon(child, "approve", False)
            tg.start_soon(child, "refer", False)
            tg.start_soon(child, "deny", not cancel_from_outside)

    return first
