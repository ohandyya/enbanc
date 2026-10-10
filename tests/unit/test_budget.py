"""The budget check: a proceeding-wide envelope, tested between rounds and never inside one.

`docs/design/execution.md` ("The budget check") and
`docs/decisions/0024-a-budget-stops-the-proceeding-between-rounds.md`. A budget that is reached
is an *outcome* — `Undecided(reason='budget')` on a `Hearing` — so every test here ends with a
hearing in hand, and none of them expects `UsageLimitExceeded` to reach the caller.

The bench's runs are cheap and countable: an advocate that neither searches nor concedes makes
one request, and so does the judge. So round 1 of the three-advocate bench is four requests,
and every limit below is chosen against that count.
"""

import warnings
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.exceptions import CostNotFoundWarning
from pydantic_ai.usage import UsageLimits

from enbanc import Case, Continuance, Ruling, Tribunal, Undecided

Kwargs = Callable[[], dict[str, Any]]


def _asks_every_round(verdicts: Any, rounds: int = 5) -> list[list[tuple[Any, str]]]:
    """A judge that never rules within the script: one question to `DENY`, every round."""
    _, deny, _ = list(verdicts)
    return [[(deny, f"Question {n}?")] for n in range(1, rounds + 1)]


async def _hear(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case, **overrides: Any
) -> Any:
    kwargs = outcomes_kwargs()
    scripted_kwargs = overrides.pop("scripted", {})
    scripted = bench(continuances=_asks_every_round(kwargs["verdicts"]), **scripted_kwargs)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model} | overrides))
    return await tribunal.hear(case)


async def test_there_is_no_check_before_round_one(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A ceiling of zero gets one round. Nothing has been spent before round 1, and a
    proceeding always runs at least one — so the coarse governor's cost, at its smallest."""
    hearing = await _hear(outcomes_kwargs, bench, case, budget=UsageLimits(request_limit=0))

    assert hearing.outcome == Undecided(reason="budget")
    assert hearing.rounds == 1
    assert isinstance(hearing.transcript[-1].filing, Continuance)


@pytest.mark.parametrize(
    "budget",
    [
        # `check_before_request` compares with `>=`: four requests reached a limit of four.
        UsageLimits(request_limit=4),
        UsageLimits(request_limit=None, total_tokens_limit=1),
        UsageLimits(request_limit=None, output_tokens_limit=1),
    ],
    ids=["request_limit", "total_tokens_limit", "output_tokens_limit"],
)
async def test_each_cumulative_limit_stops_the_proceeding(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case, budget: UsageLimits
) -> None:
    hearing = await _hear(outcomes_kwargs, bench, case, budget=budget)

    assert hearing.outcome == Undecided(reason="budget")
    assert hearing.rounds == 1


async def test_the_tool_call_limit_stops_the_proceeding(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`check_before_tool_call` is the fourth checker, and the one only a search can reach."""
    kwargs = outcomes_kwargs()
    approve, _, _ = list(kwargs["verdicts"])
    hearing = await _hear(
        outcomes_kwargs,
        bench,
        case,
        budget=UsageLimits(request_limit=None, tool_calls_limit=0),
        scripted={"searches": {approve}},
    )

    assert hearing.outcome == Undecided(reason="budget")
    assert hearing.rounds == 1


async def test_a_limit_not_yet_reached_lets_the_next_round_run(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Five requests is not reached by round 1's four, so round 2 runs — its two requests
    bring the total to six, and the proceeding stops at the boundary after it. It overshoots
    by design: nothing halts a run mid-round."""
    hearing = await _hear(outcomes_kwargs, bench, case, budget=UsageLimits(request_limit=5))

    assert hearing.outcome == Undecided(reason="budget")
    assert hearing.rounds == 2
    assert hearing.usage.requests == 6


async def test_max_rounds_is_tested_before_the_budget(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Both spent at once is recorded as rounds — the limit every tribunal has."""
    hearing = await _hear(
        outcomes_kwargs, bench, case, max_rounds=1, budget=UsageLimits(request_limit=0)
    )

    assert hearing.outcome == Undecided(reason="rounds")
    assert hearing.rounds == 1


async def test_a_max_rounds_below_one_still_terminates_after_one_round(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`max_rounds` is not validated (`ConfigurationError` has four cases and this is not one),
    and it is what makes a proceeding terminate at all — so zero gets one round, like a zero
    budget does, rather than a judge that keeps asking running forever."""
    hearing = await _hear(outcomes_kwargs, bench, case, max_rounds=0)

    assert hearing.outcome == Undecided(reason="rounds")
    assert hearing.rounds == 1


async def test_with_no_budget_only_the_rounds_can_run_out(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    hearing = await _hear(outcomes_kwargs, bench, case, max_rounds=3)

    assert hearing.outcome == Undecided(reason="rounds")
    assert hearing.rounds == 3


async def test_a_budget_that_is_never_reached_changes_nothing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The judge rules after the script runs out — three continuances, then a ruling."""
    kwargs = outcomes_kwargs()
    scripted = bench(continuances=_asks_every_round(kwargs["verdicts"], rounds=2))
    tribunal = Tribunal(
        **(kwargs | {"model": scripted.model, "budget": UsageLimits(request_limit=1000)})
    )

    hearing = await tribunal.hear(case)

    assert isinstance(hearing.outcome, Ruling)
    assert hearing.rounds == 3


async def test_an_unpriceable_cost_limit_is_warned_about_once(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`FunctionModel` cannot be priced, so `cost_limit` enforces nothing here — and the caller
    hears that once, at the first boundary, not at each of the four this proceeding reaches."""
    with pytest.warns(CostNotFoundWarning) as caught:
        hearing = await _hear(
            outcomes_kwargs,
            bench,
            case,
            budget=UsageLimits(cost_limit=Decimal("2.00"), request_limit=None),
        )

    assert hearing.outcome == Undecided(reason="rounds")
    assert hearing.rounds == 5
    assert len([w for w in caught if issubclass(w.category, CostNotFoundWarning)]) == 1


async def test_a_proceeding_that_reaches_no_boundary_is_not_warned(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A ruling in round 1 never reaches a boundary, so `cost_limit` never had a moment to
    enforce anything and there is nothing to warn about."""
    kwargs = outcomes_kwargs()
    scripted = bench()
    budget = UsageLimits(cost_limit=Decimal("2.00"), request_limit=None)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model, "budget": budget}))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        hearing = await tribunal.hear(case)

    assert isinstance(hearing.outcome, Ruling)
    assert not [w for w in caught if issubclass(w.category, CostNotFoundWarning)]


async def test_a_priced_proceeding_is_stopped_by_its_cost(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """With a cost on every response, `cost_limit` is a real governor and no warning fires.

    Ten cents a request: round 1's four requests are $0.40, which is not *over* a $0.40
    ceiling (the cost check is `>`), so round 2 runs — `DENY`'s response and the judge — and
    its two bring the total to $0.60.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    priced = dict.fromkeys([approve, deny, refer, "judge"], Decimal("0.10"))
    hearing = await _hear(
        outcomes_kwargs,
        bench,
        case,
        budget=UsageLimits(cost_limit=Decimal("0.40"), request_limit=None),
        scripted={"costs": priced},
    )

    assert hearing.outcome == Undecided(reason="budget")
    assert hearing.rounds == 2
    assert hearing.usage.cost == Decimal("0.60")
