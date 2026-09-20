"""What a proceeding spent, and who spent it.

One `RunUsage` per participant, minted at first dispatch and mutated in place by every run
that participant makes — `docs/decisions/0014-usage-is-broken-down-per-participant.md` and
`docs/decisions/0028-usage-accumulates-per-participant.md`. The breakdown is the stored fact
and `Hearing.usage` is its sum, so there is no second place for the two to disagree.
"""

from collections.abc import Callable
from typing import Any

from pydantic_ai.usage import RunUsage

from enbanc import Case, Tribunal

Kwargs = Callable[[], dict[str, Any]]


async def test_every_participant_appears_on_a_hearing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Round 1 fans out to every advocate, so each has an entry even if it conceded
    immediately, and the judge has one because a proceeding that produced a `Hearing`
    deliberated at least once. No key is a zero placeholder."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve}, cites={approve}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert set(hearing.usage_by_participant) == {approve, deny, refer, "judge"}
    assert all(spend.requests >= 1 for spend in hearing.usage_by_participant.values())


async def test_the_total_is_the_sum_of_the_breakdown(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`usage` is computed rather than accumulated beside the mapping — the same reason
    `position` is not on an `Argument`."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    total = RunUsage()
    for spend in hearing.usage_by_participant.values():
        total += spend
    assert hearing.usage == total
    assert hearing.usage.requests == sum(
        spend.requests for spend in hearing.usage_by_participant.values()
    )


async def test_a_participants_accumulator_carries_all_of_its_runs(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """One object per participant, passed into every run it makes — so an advocate that called
    a tool before filing reports both requests under one key, not one."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={deny}, cites={deny}, concedes={approve, refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert hearing.usage_by_participant[deny].requests == 2
    assert hearing.usage_by_participant[approve].requests == 1
    assert hearing.usage_by_participant[deny].tool_calls == 1
    assert hearing.usage_by_participant[approve].tool_calls == 0


async def test_a_key_appears_only_once_its_participant_is_dispatched(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Minted at dispatch, not up front: **absence means never dispatched**, and a
    pre-populated dict would make that unreadable the moment a proceeding failed before its
    deliberation (`docs/design/outcomes.md` § 4)."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        orchestrator = proceeding._orchestrator  # noqa: SLF001
        assert orchestrator.usage_by_participant == {}
        async for _entry in proceeding:
            # The judge has not been dispatched while advocates are still filing, so it cannot
            # have a key yet — this is the same absence a round-1 failure leaves behind.
            if len(proceeding.transcript) < 3:
                assert "judge" not in orchestrator.usage_by_participant

    assert "judge" in proceeding.hearing.usage_by_participant


async def test_an_accumulator_is_mutated_in_place_rather_than_replaced(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`enbanc` accumulates into an object it owns rather than reading a figure off each
    result, which is what leaves a partial spend behind when a run dies or is cancelled.

    Asserted on the object itself: the same `RunUsage` the proceeding minted grows as its
    participant runs. (The mapping on the `Hearing` is a validated copy of the orchestrator's,
    because Pydantic copies a dict field like it copies a list — the accumulators inside are
    what the runs were handed.)
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={deny}, cites={deny}, concedes={approve, refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    watched: list[tuple[int, int]] = []

    async with tribunal.hear_stream(case) as proceeding:
        orchestrator = proceeding._orchestrator  # noqa: SLF001
        async for _entry in proceeding:
            spend = orchestrator.usage_by_participant.get(deny)
            if spend is not None:
                watched.append((id(spend), spend.requests))

    assert len({identity for identity, _ in watched}) == 1, "one object, grown in place"
    assert proceeding.hearing.usage_by_participant[deny].requests == watched[-1][1]


async def test_two_proceedings_do_not_share_accumulators(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The usage objects are per proceeding, like everything else `hear()` builds — a tribunal
    that accumulated across calls would report the second hearing's cost as the sum of both."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    first = await tribunal.hear(case)
    second = await tribunal.hear(case)

    assert first.usage.requests == second.usage.requests
    assert first.usage_by_participant is not second.usage_by_participant
