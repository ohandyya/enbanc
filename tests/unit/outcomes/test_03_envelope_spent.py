"""`docs/design/outcomes.md` § 3 — the envelope is spent.

Two ways to run out, one outcome type, and `Undecided.reason` saying which:

    round 1   Argument(APPROVE), Argument(DENY), Concession(REFER)
              Continuance(interrogatories=[r1-q1 -> APPROVE, r1-q2 -> DENY])

    round 2   Response(APPROVE), Response(DENY)
              Continuance(interrogatories=[r2-q1 -> APPROVE, r2-q2 -> DENY])

Both halves produce that same transcript — the round limit at `max_rounds=2`, the budget at
`max_rounds=5` with a `cost_limit` the second round crosses. That is the section's point: a
reviewer reading the record alone cannot tell a hard case from an expensive one, which is
exactly why `reason` exists.

The doc is mirrored here, never executed. See
`docs/decisions/0032-a-design-doc-is-mirrored-by-tests.md`.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from pydantic_ai.usage import UsageLimits

from enbanc import Case, Continuance, Hearing, Response, Tribunal, Undecided

Kwargs = Callable[[], dict[str, Any]]


def _script(verdicts: Any) -> list[list[tuple[Any, str]]]:
    approve, deny, _ = list(verdicts)
    return [
        [
            (approve, "Which income figure does §4.2 require?"),
            (deny, "Does the Schedule C qualify as documented?"),
        ],
        [
            (approve, "Can you produce an audited 2024 return?"),
            (deny, "Would verification alone resolve this?"),
        ],
        [(approve, "A third question nobody is asked.")],
    ]


async def _hear(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case, **overrides: Any
) -> tuple[Hearing[Any], Any, Tribunal[Any]]:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        concedes={refer},
        continuances=_script(kwargs["verdicts"]),
        costs=overrides.pop("costs", {}),
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model} | overrides))
    return await tribunal.hear(case), scripted, tribunal


def _assert_the_shape_both_halves_share(hearing: Hearing[Any]) -> None:
    approve, deny, refer = hearing.transcript.verdicts
    assert hearing.rounds == 2
    # The responses land in either order; the continuance is last because the judge cannot
    # deliberate on a round that has not closed.
    assert [entry.filing.kind for entry in hearing.transcript if entry.round == 2] == [
        "response",
        "response",
        "continuance",
    ]
    last = hearing.transcript[-1].filing
    assert isinstance(last, Continuance)
    assert [(i.id, i.to) for i in last.interrogatories] == [("r2-q1", approve), ("r2-q2", deny)]
    responses = {e.filing.answering for e in hearing.transcript if isinstance(e.filing, Response)}
    assert responses == {"r1-q1", "r1-q2"}
    # Every one of them ran, so every one of them is in the breakdown.
    assert set(hearing.usage_by_participant) == {approve, deny, refer, "judge"}


async def test_the_round_limit(
    outcomes_kwargs: Kwargs,
    bench: Callable[..., Any],
    case: Case,
    assert_invariant_held: Callable[..., None],
) -> None:
    """The snippets § 3 prints for the round limit, directly usable as written:

    hearing.rounds                                       # 2 == max_rounds
    hearing.outcome is hearing.transcript[-1].filing     # False — nobody filed it
    [i.question for i in hearing.transcript[-1].filing.interrogatories]
    # ['Can you produce an audited 2024 return?',
    #  'Would verification alone resolve this?']
    """
    hearing, scripted, tribunal = await _hear(outcomes_kwargs, bench, case, max_rounds=2)

    assert hearing.outcome == Undecided(reason="rounds")
    assert hearing.rounds == hearing.transcript.max_rounds == 2
    assert hearing.outcome is not hearing.transcript[-1].filing
    last = hearing.transcript[-1].filing
    assert isinstance(last, Continuance)
    assert [i.question for i in last.interrogatories] == [
        "Can you produce an audited 2024 return?",
        "Would verification alone resolve this?",
    ]
    _assert_the_shape_both_halves_share(hearing)
    assert_invariant_held(scripted.captured, hearing.transcript, tribunal.instructions_for)


async def test_the_budget(outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case) -> None:
    """The snippets § 3 prints for the budget:

    hearing.rounds                 # 2 — and max_rounds was 5
    hearing.usage.cost             # Decimal('0.41') — the ceiling was 0.40

    Priced so the arithmetic is § 3's: five cents an advocate request, eight a deliberation.
    Round 1 is three advocates and the judge — $0.23, under the ceiling, so round 2 runs. Round
    2 is two responses and the judge — $0.18, for $0.41 in all, past it. The overshoot is the
    assertion: nothing halts a run mid-round, and the record says by how much.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    costs = dict.fromkeys([approve, deny, refer], Decimal("0.05")) | {"judge": Decimal("0.08")}

    hearing, _, _ = await _hear(
        outcomes_kwargs,
        bench,
        case,
        budget=UsageLimits(cost_limit=Decimal("0.40"), request_limit=None),
        costs=costs,
    )

    assert hearing.outcome == Undecided(reason="budget")
    assert hearing.rounds == 2
    assert hearing.transcript.max_rounds == 5
    assert hearing.usage.cost == Decimal("0.41")
    _assert_the_shape_both_halves_share(hearing)


async def test_the_two_transcripts_are_indistinguishable_and_the_outcomes_are_not(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    costs = dict.fromkeys([approve, deny, refer], Decimal("0.05")) | {"judge": Decimal("0.08")}

    rounds, _, _ = await _hear(outcomes_kwargs, bench, case, max_rounds=2)
    budget, _, _ = await _hear(
        outcomes_kwargs,
        bench,
        case,
        budget=UsageLimits(cost_limit=Decimal("0.40"), request_limit=None),
        costs=costs,
    )

    def shape(hearing: Hearing[Any]) -> list[tuple[int, str]]:
        return sorted((entry.round, entry.filing.kind) for entry in hearing.transcript)

    assert shape(rounds) == shape(budget)
    assert rounds.outcome != budget.outcome
