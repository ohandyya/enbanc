"""Watching a proceeding happen, and `hear()` as that stream driven to exhaustion.

`docs/design/api.md` ("Watching it live") and
`docs/decisions/0010-streaming-yields-the-record.md`: what a consumer sees is the record being
written — the same `Entry` objects, in filing order, and nothing else. There are no lifecycle
events, no partial filings, and no token deltas, because a viewer that saw something the
transcript does not contain would be watching a second channel.
"""

from collections.abc import Callable
from typing import Any

import pytest

from enbanc import Case, Entry, Hearing, ProceedingUnfinished, Ruling, Tribunal

Kwargs = Callable[[], dict[str, Any]]


async def test_what_is_yielded_is_the_record(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Every value is an `Entry` the transcript holds, and by the end the two agree exactly."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve}, cites={approve}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    watched: list[Entry[Any]] = []

    async with tribunal.hear_stream(case) as proceeding:
        async for entry in proceeding:
            assert isinstance(entry, Entry)
            assert entry is proceeding.transcript[-1]
            watched.append(entry)

    assert watched == list(proceeding.transcript)
    assert [entry.filing.kind for entry in watched][-1] == "ruling"


async def test_the_transcript_grows_as_it_is_watched(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The handle carries the record *as it is being written*, not a copy handed over at the
    end — so its length tracks what the consumer has seen."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    lengths: list[int] = []

    async with tribunal.hear_stream(case) as proceeding:
        async for _entry in proceeding:
            lengths.append(len(proceeding.transcript))

    assert lengths == [1, 2, 3, 4]


async def test_the_hearing_is_the_one_hear_would_have_returned(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`hear()` is defined as this stream consumed, so the two cannot come apart."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        async for _entry in proceeding:
            pass
    streamed = proceeding.hearing
    heard = await tribunal.hear(case)

    assert isinstance(streamed, Hearing)
    assert streamed.rounds == heard.rounds
    assert len(streamed.transcript) == len(heard.transcript)
    assert len(streamed.transcript.ledger) == len(heard.transcript.ledger)
    assert isinstance(streamed.outcome, Ruling) and isinstance(heard.outcome, Ruling)
    assert streamed.outcome.verdict == heard.outcome.verdict


async def test_the_outcome_points_at_the_last_filing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A pointer, not a copy, so a caller does not walk the record backwards to find the
    terminal ruling."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert hearing.outcome is hearing.transcript[-1].filing


async def test_the_hearing_raises_until_the_proceeding_ends(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`proceeding.hearing` is not a nullable field a caller has to test — reading it early is
    an error, because a proceeding that has not finished has no hearing to report."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        with pytest.raises(ProceedingUnfinished):
            _ = proceeding.hearing
        async for _entry in proceeding:
            pass
        assert isinstance(proceeding.hearing, Hearing)


async def test_abandoning_the_stream_leaves_the_record_and_no_hearing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Break out of the loop and the block exits: the in-flight runs are cancelled, the
    transcript holds everything filed up to that point, and `hearing` raises.

    The block *exiting* is half the assertion. Without the cancel on the way out, the clerk
    stays blocked on a rendezvous send nobody will receive and this test hangs rather than
    fails — which is why the cancel is in a `finally` rather than after the `yield`.
    """
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        async for _entry in proceeding:
            break

    assert len(proceeding.transcript) == 1
    with pytest.raises(ProceedingUnfinished):
        _ = proceeding.hearing


async def test_an_abandoned_proceeding_still_carries_what_it_retrieved(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The ledger is written as tool calls return rather than at the end, so a proceeding that
    was walked away from still says what its advocates had seen."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny, refer}, cites={approve, deny, refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        async for _entry in proceeding:
            break

    assert len(proceeding.transcript) == 1
    assert len(proceeding.transcript.ledger) >= 1


async def test_nothing_but_entries_is_yielded(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """No lifecycle events and no round boundaries: `entry.round` names the round, and a
    `Continuance` or a `Ruling` is what closes one."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve}, cites={approve}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        kinds = [entry.filing.kind async for entry in proceeding]

    assert sorted(kinds) == ["argument", "argument", "concession", "ruling"]
    assert all(isinstance(entry, Entry) for entry in proceeding.transcript)
