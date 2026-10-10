"""`docs/design/outcomes.md` § 6 — the same endings, watched live.

`hear_stream()` yields the entries as they are filed, and what differs between the endings is
only how the loop ends: after the `Ruling`; after the last `Continuance`, with nothing raised;
out of the `async with` rather than the `async for`, for a failure; or wherever the consumer
breaks, with no hearing at all.

The loop bodies here never `await` before the line under test, so `transcript[-1]` is not read
while the clerk could be ahead of the stream — that is
`docs/implementations/stream-ordering.md`'s defect, not this section's.

The doc is mirrored here, never executed. See
`docs/decisions/0032-a-design-doc-is-mirrored-by-tests.md`.
"""

from collections.abc import Callable
from typing import Any

import anyio
import pytest
from pydantic_ai.usage import UsageLimits

from enbanc import (
    Case,
    Continuance,
    Proceeding,
    ProceedingFailed,
    ProceedingUnfinished,
    Ruling,
    Tribunal,
    Undecided,
)

Kwargs = Callable[[], dict[str, Any]]

_HANG = 5


def _script(verdicts: Any) -> list[list[tuple[Any, str]]]:
    approve, deny, _ = list(verdicts)
    return [
        [
            (approve, "Which income figure does §4.2 require?"),
            (deny, "Does the Schedule C qualify as documented?"),
        ]
    ]


async def test_a_ruling_ends_the_loop_after_the_ruling(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny},
        cites={approve, deny},
        concedes={refer},
        continuances=_script(kwargs["verdicts"]),
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        kinds = [(entry.round, entry.filing.kind) async for entry in proceeding]

    assert kinds[-1] == (2, "ruling")
    assert [kind for round, kind in kinds if round == 2] == ["response", "response", "ruling"]
    assert isinstance(proceeding.hearing.outcome, Ruling)


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"max_rounds": 1}, "rounds"),
        ({"budget": UsageLimits(request_limit=0)}, "budget"),
    ],
)
async def test_an_envelope_ends_the_loop_after_a_continuance_and_nothing_raises(
    outcomes_kwargs: Kwargs,
    bench: Callable[..., Any],
    case: Case,
    overrides: dict[str, Any],
    reason: str,
) -> None:
    """The round limit and the budget look the same from the stream; only `reason` differs."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny},
        cites={approve, deny},
        concedes={refer},
        continuances=_script(kwargs["verdicts"]),
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model} | overrides))

    async with tribunal.hear_stream(case) as proceeding:
        kinds = [entry.filing.kind async for entry in proceeding]

    assert kinds[-1] == "continuance"
    outcome = proceeding.hearing.outcome
    assert isinstance(outcome, Undecided)
    assert outcome.reason == reason


async def test_a_failure_comes_out_of_the_async_with_not_the_async_for(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The stream simply ends; the raise is at block exit. The partial record is the same
    object on the exception and on the handle — the same entries, not equal ones."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve},
        cites={approve},
        concedes={refer},
        raises={deny: ConnectionError("Connection error.")},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    loop_ended = False
    # Bound before the block, because the block is the thing that raises.
    handle: Proceeding[Any] | None = None

    with pytest.raises(ProceedingFailed) as caught:
        with anyio.fail_after(_HANG):
            async with tribunal.hear_stream(case) as handle:
                async for _entry in handle:
                    pass
                loop_ended = True

    assert loop_ended
    assert handle is not None
    assert caught.value.transcript is handle.transcript
    assert len(caught.value.transcript) == len(handle.transcript)


async def test_walking_away_leaves_the_record_and_no_hearing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Break on the continuance: the in-flight round-2 runs are cancelled, the transcript holds
    everything filed before the consumer left, and there was no hearing."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny},
        cites={approve, deny},
        concedes={refer},
        continuances=_script(kwargs["verdicts"]),
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with anyio.fail_after(_HANG):
        async with tribunal.hear_stream(case) as proceeding:
            async for entry in proceeding:
                if isinstance(entry.filing, Continuance):
                    break

    assert len(proceeding.transcript) == 4
    assert isinstance(proceeding.transcript[-1].filing, Continuance)
    with pytest.raises(ProceedingUnfinished):
        _ = proceeding.hearing
