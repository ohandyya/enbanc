"""Watching a proceeding happen, and `hear()` as that stream driven to exhaustion.

`docs/design/api.md` ("Watching it live") and
`docs/decisions/0010-streaming-yields-the-record.md`: what a consumer sees is the record being
written — the same `Entry` objects, in filing order, and nothing else. There are no lifecycle
events, no partial filings, and no token deltas, because a viewer that saw something the
transcript does not contain would be watching a second channel.
"""

from collections.abc import Callable
from typing import Any

import anyio
import pytest

from enbanc import Case, Entry, Hearing, Proceeding, ProceedingUnfinished, Ruling, Tribunal

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


async def test_a_consumers_own_exception_comes_back_as_itself(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Raising out of the loop is walking away, and the caller gets its own exception back —
    not an `ExceptionGroup`, which is what anyio makes of anything raised in a task group's
    body. `proceeding.hearing` then reports the proceeding's own state: nothing failed, so
    there was no hearing."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    mine = ValueError("the consumer's own")
    handle: Proceeding[Any] | None = None

    with pytest.raises(ValueError) as caught:
        async with tribunal.hear_stream(case) as handle:
            async for _entry in handle:
                raise mine

    assert caught.value is mine
    assert handle is not None
    with pytest.raises(ProceedingUnfinished):
        _ = handle.hearing


async def test_an_external_cancel_leaves_no_hearing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A caller's timeout around the stream is not a failure: the scope sees its own cancel,
    and `hearing` raises `ProceedingUnfinished` rather than naming a participant that was
    merely stopped."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={approve, refer}, gates={deny: anyio.Event()})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    handle: Proceeding[Any] | None = None

    with anyio.fail_after(5):
        with anyio.move_on_after(0.1) as scope:
            async with tribunal.hear_stream(case) as handle:
                async for _entry in handle:
                    pass

    assert scope.cancelled_caught
    assert handle is not None
    with pytest.raises(ProceedingUnfinished):
        _ = handle.hearing


async def test_a_consumer_that_awaits_still_holds_the_last_entry(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The consumer the stream exists for does real work in its loop body. However long it
    spends, the entry in hand stays `transcript[-1]`: the record moves at the consumer's pace
    (`docs/decisions/0041-the-clerk-files-when-the-consumer-asks.md`).

    `wait_all_tasks_blocked()` stands in for a database write. It runs every other task until
    it blocks, which is the furthest a clerk could ever get ahead — deterministically.
    """
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    seen: list[tuple[int, bool]] = []

    async with tribunal.hear_stream(case) as proceeding:
        async for entry in proceeding:
            await anyio.wait_all_tasks_blocked()
            seen.append((len(proceeding.transcript), entry is proceeding.transcript[-1]))

    assert seen == [(1, True), (2, True), (3, True), (4, True)]


async def test_walking_away_after_awaiting_leaves_only_what_was_received(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Every advocate has filed by the time the consumer leaves, and the record still holds
    only the one entry it was given."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        async for _entry in proceeding:
            await anyio.wait_all_tasks_blocked()
            break

    assert len(proceeding.transcript) == 1
    with pytest.raises(ProceedingUnfinished):
        _ = proceeding.hearing


async def test_a_stream_never_iterated_files_nothing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Nobody asked for an entry, so nothing entered the record — though every advocate ran."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with anyio.fail_after(5):
        async with tribunal.hear_stream(case) as proceeding:
            await anyio.wait_all_tasks_blocked()

    assert len(proceeding.transcript) == 0
    with pytest.raises(ProceedingUnfinished):
        _ = proceeding.hearing


async def test_an_external_cancel_leaves_at_most_the_entry_in_hand(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A timeout around the stream can land between the consumer's ask and its receive, and
    then the record holds one entry the consumer never got — the one accepted gap. Never
    more: the clerk cannot append a second entry without a second ask.

    The cancel here reaches the consumer while it waits for a third entry that a gated
    advocate will never file, so this asserts the bound. `test_filing_clerk.py` lands it
    between the ask and the receive and pins the extra entry.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={approve, refer}, gates={deny: anyio.Event()})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    received = 0
    waiting = anyio.Event()
    handle: Proceeding[Any] | None = None

    async def time_out(scope: anyio.CancelScope) -> None:
        await waiting.wait()
        await anyio.wait_all_tasks_blocked()
        scope.cancel()

    scope = anyio.CancelScope()
    with anyio.fail_after(5):
        async with anyio.create_task_group() as tg:
            with scope:
                tg.start_soon(time_out, scope)
                async with tribunal.hear_stream(case) as handle:
                    async for _entry in handle:
                        await anyio.wait_all_tasks_blocked()
                        received += 1
                        if received == 2:
                            waiting.set()

    assert scope.cancelled_caught
    assert received == 2
    assert handle is not None
    assert len(handle.transcript) in (received, received + 1)
