"""A participant that cannot be heard, beyond the four cases `outcomes.md` § 4 works through.

`docs/design/execution.md` ("The round's task group"): every advocate task runs inside a guard
that records the first failure into one slot and cancels the round, so the group exits cleanly
and `ProceedingFailed` is raised *after* every task group has exited — bare, naming one
participant, with the original error as `__cause__`.

What is deliberately not asserted is `docs/design/testing.md`'s list: how many entries a
cancelled round leaves, exact usage, and which of two simultaneous failures is the one named.
"""

from collections.abc import Callable
from typing import Any

import anyio
import pytest
from pydantic_ai import Tool
from pydantic_ai.exceptions import UnexpectedModelBehavior

from enbanc import Advocate, Case, Continuance, Proceeding, ProceedingFailed, Tribunal

Kwargs = Callable[[], dict[str, Any]]

_HANG = 5


class _Halt(BaseException):
    """Stands in for `KeyboardInterrupt` or `SystemExit`, which pytest would itself act on."""


def _leaves(error: BaseException) -> list[BaseException]:
    """Every non-group exception inside a possibly nested `BaseExceptionGroup`."""
    if isinstance(error, BaseExceptionGroup):
        return [leaf for exc in error.exceptions for leaf in _leaves(exc)]
    return [error]


async def test_a_failure_in_round_three_names_round_three(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The guard runs in every round, not only the first."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    down = ConnectionError("Connection error.")
    scripted = bench(
        concedes={approve, refer},
        continuances=[
            [(deny, "Does the Schedule C qualify as documented?")],
            [(deny, "Would verification alone resolve this?")],
        ],
        raises={"r2-q1": down},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(ProceedingFailed) as caught:
        await tribunal.hear(case)

    assert caught.value.participant is deny
    assert caught.value.round == 3
    assert caught.value.__cause__ is down
    continuances = [e.round for e in caught.value.transcript if isinstance(e.filing, Continuance)]
    assert continuances == [1, 2]


async def test_two_failures_in_one_round_name_exactly_one(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The slot is filled once, so `participant` is singular by construction — and its cause
    is that participant's own error, never a group of both. Which one is named is
    scheduling."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    errors: dict[Any, Exception] = {
        approve: ConnectionError("approve's provider is down"),
        deny: ConnectionError("deny's provider is down"),
    }
    scripted = bench(concedes={refer}, raises=errors)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(ProceedingFailed) as caught:
        await tribunal.hear(case)

    assert caught.value.participant in errors
    assert caught.value.__cause__ is errors[caught.value.participant]


async def test_an_external_cancel_names_nobody(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A caller's timeout around `hear()` cancels a healthy round. Nothing failed, so nothing
    is raised and no participant is named — the integration-level twin of the contract test's
    discriminating case, and what `docs/decisions/0040-a-participant-failure-is-an-exception.md`
    keeps true by catching `Exception`."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={approve, refer}, gates={deny: anyio.Event()})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with anyio.fail_after(_HANG):
        with anyio.move_on_after(0.1) as scope:
            await tribunal.hear(case)

    assert scope.cancelled_caught


async def test_hearing_re_raises_the_same_failure(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Not a blander `ProceedingUnfinished`, and not a new exception: the very object that came
    out of the block, as often as it is asked for."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={approve, refer}, raises={deny: ConnectionError("down")})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    handle: Proceeding[Any] | None = None

    with pytest.raises(ProceedingFailed) as caught:
        async with tribunal.hear_stream(case) as handle:
            async for _entry in handle:
                pass

    assert handle is not None
    for _ in range(2):
        with pytest.raises(ProceedingFailed) as again:
            _ = handle.hearing
        assert again.value is caught.value


async def test_the_last_rung_of_the_timeout_ladder_ends_the_proceeding(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Timeout → the advocate adapts → retries spent → the proceeding fails
    (`docs/design/evidence.md`, "What tools may do"). Four timeouts of one tool against the
    `tools` budget of 3 is the last rung, and the degraded advocate's record survives it."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])

    async def slow(query: str) -> str:
        """Query a source that never answers in time."""
        await anyio.sleep(_HANG)
        return "never"

    kwargs["advocates"][deny] = Advocate(tools=[Tool(slow, timeout=0.01)])
    scripted = bench(concedes={approve, refer}, calls={deny: [("slow", {"query": "w2"})] * 4})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(ProceedingFailed) as caught:
        with anyio.fail_after(_HANG):
            await tribunal.hear(case)

    assert caught.value.participant is deny
    assert isinstance(caught.value.__cause__, UnexpectedModelBehavior)
    assert "slow" in str(caught.value.__cause__)
    failures = caught.value.transcript.failures
    assert len(failures) >= 3
    assert {(f.advocate, f.tool) for f in failures} == {(deny, "slow")}


async def test_a_base_exception_is_not_a_participant_that_could_not_be_heard(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`docs/decisions/0040-a-participant-failure-is-an-exception.md`'s line. A Ctrl-C or a
    `sys.exit()` inside a run is the process stopping, not a participant failing, so it is
    never wrapped — however anyio groups it on the way out."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])

    async def halt(query: str) -> str:
        """Query a source that stops the process."""
        raise _Halt

    kwargs["advocates"][deny] = Advocate(tools=[halt])
    scripted = bench(concedes={approve, refer}, calls={deny: [("halt", {"query": "w2"})]})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(BaseException) as caught:  # noqa: PT011 — whatever escapes is the subject
        with anyio.fail_after(_HANG):
            await tribunal.hear(case)

    leaves = _leaves(caught.value)
    assert any(isinstance(leaf, _Halt) for leaf in leaves)
    assert not any(isinstance(leaf, ProceedingFailed) for leaf in leaves)
