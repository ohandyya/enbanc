"""Building one, and the edges of the four ways building one refuses.

`outcomes/test_05_misconfigured.py` is the acceptance test: the three messages
`docs/design/outcomes.md` § 5 writes out, asserted as text over the bench that document uses.
What is here is everything around them that a worked example does not reach — the plural
forms, the order two cases resolve in, and the copies that make *raised only from
`Tribunal(...)`* true rather than merely intended.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import UsageLimits

from enbanc import Advocate, ConfigurationError, Judge, Statute, Tribunal, Verdict

Kwargs = Callable[[], dict[str, Any]]


class Escalation(Verdict):
    HANDLE = "handle"
    ESCALATE = "escalate"


class Reserved(Verdict):
    HANDLE = "handle"
    JUDGE = "judge"


def tribunal_for(verdicts: type[Verdict], **overrides: Any) -> Tribunal[Verdict]:
    """The smallest thing that builds: every verdict seated, nothing else configured."""
    kwargs: dict[str, Any] = {
        "question": "Shall this be escalated?",
        "verdicts": verdicts,
        "statute": Statute(text="Escalate only where ..."),
        "model": TestModel(),
        "judge": Judge(),
        "advocates": {member: Advocate() for member in verdicts},
        "max_rounds": 3,
    }
    kwargs.update(overrides)
    return Tribunal(**kwargs)


# --- what the three descriptions hold ------------------------------------------------------


def test_a_judge_defaults_to_nothing() -> None:
    """Both fields optional: the tribunal's model, and no steer."""
    assert Judge() == Judge(model=None, guidance=None)


def test_an_advocate_copies_its_tools_into_tuples() -> None:
    """A caller's list stays theirs. Appending to it after construction would otherwise put a
    tool in front of a model that the tribunal was never validated with."""

    async def psql(query: str) -> list[str]:
        """Query."""
        return []

    mine = [psql]
    advocate = Advocate(tools=mine)
    mine.append(psql)

    assert advocate.tools == (psql,)
    assert advocate.toolsets == ()


@pytest.mark.parametrize("cls", [Judge, Advocate, Tribunal])
def test_the_three_are_frozen(cls: type) -> None:
    """Frozen is what keeps `ConfigurationError` a construction-time error. A tribunal whose
    bench could be swapped afterwards would raise from `hear()`, or not at all."""
    built = cls() if cls is not Tribunal else tribunal_for(Escalation)
    with pytest.raises(Exception, match="frozen|immutable|cannot assign"):
        built.guidance = "after the fact"  # type: ignore[misc]


def test_the_bench_is_read_only_after_construction() -> None:
    """The half a frozen dataclass does not cover: the caller still holds the dict they passed,
    and `MappingProxyType` is what stops both it and the tribunal's own copy."""
    mine = {member: Advocate() for member in Escalation}
    tribunal = tribunal_for(Escalation, advocates=mine)

    del mine[Escalation.HANDLE]
    assert set(tribunal.advocates) == set(Escalation)

    with pytest.raises(TypeError):
        tribunal.advocates[Escalation.HANDLE] = Advocate()  # type: ignore[index]


def test_the_limits_are_held_and_not_read() -> None:
    """Nothing consults them until there is a round loop. A tribunal that accepts them is all
    this PR claims."""
    budget = UsageLimits(cost_limit=Decimal("2.00"), request_limit=None)
    tribunal = tribunal_for(Escalation, budget=budget, max_concurrency=4)

    assert tribunal.budget is budget
    assert tribunal.max_concurrency == 4
    assert tribunal.max_rounds == 3


def test_max_rounds_is_not_validated() -> None:
    """`docs/design/execution.md` says `ConfigurationError` has four cases and names them.
    `max_rounds=0` is not one, and adding a fifth here would be a design change made in code."""
    assert tribunal_for(Escalation, max_rounds=0).max_rounds == 0


# --- the four refusals ---------------------------------------------------------------------


def test_a_verdict_valued_judge() -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        tribunal_for(Reserved)
    assert str(excinfo.value) == (
        "'judge' is a reserved verdict value: it would collide with the judge's key in "
        "usage_by_participant"
    )


def test_the_reserved_value_is_reported_before_the_bench() -> None:
    """It is a fact about the enum, not about the mapping. Reported second, an advocate keyed
    on a `judge`-valued member would read as a missing or unknown key — the symptom, with the
    cause hidden."""
    with pytest.raises(ConfigurationError, match="reserved verdict value"):
        tribunal_for(Reserved, advocates={Reserved.HANDLE: Advocate()})


def test_one_missing_verdict() -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        tribunal_for(Escalation, advocates={Escalation.HANDLE: Advocate()})
    assert str(excinfo.value) == "advocates is missing a verdict: 'escalate'"


def test_several_missing_verdicts() -> None:
    """The plural form, in `verdicts` declaration order — the same determinism `## The bench`
    holds itself to when it renders guidance."""
    with pytest.raises(ConfigurationError) as excinfo:
        tribunal_for(Escalation, advocates={})
    assert str(excinfo.value) == "advocates is missing verdicts: 'handle', 'escalate'"


def test_one_unknown_key() -> None:
    advocates = {member: Advocate() for member in Escalation}
    advocates["maybe"] = Advocate()  # type: ignore[index]
    with pytest.raises(ConfigurationError) as excinfo:
        tribunal_for(Escalation, advocates=advocates)
    assert str(excinfo.value) == (
        "advocates names a key that is not a verdict of Escalation: 'maybe'"
    )


def test_several_unknown_keys() -> None:
    """Insertion order, there being no enum order to appeal to for a key outside the enum."""
    advocates: dict[Any, Advocate] = {member: Advocate() for member in Escalation}
    advocates["maybe"] = Advocate()
    advocates["perhaps"] = Advocate()
    with pytest.raises(ConfigurationError) as excinfo:
        tribunal_for(Escalation, advocates=advocates)
    assert str(excinfo.value) == (
        "advocates names keys that are not verdicts of Escalation: 'maybe', 'perhaps'"
    )


def test_a_missing_verdict_is_reported_before_an_unknown_key() -> None:
    """One mistyped key produces both, and the verdict the caller *meant* to seat is the more
    useful half of that pair."""
    with pytest.raises(ConfigurationError, match="missing a verdict"):
        tribunal_for(
            Escalation,
            advocates={Escalation.HANDLE: Advocate(), "escalat": Advocate()},
        )


def test_a_key_from_another_verdict_enum_is_unknown() -> None:
    """`StrEnum` members compare by value, so a member of another enum with the same value
    would be accepted — which is correct, and is why this uses one that differs.

    It also names the member by its **value**, not its `repr`. A `StrEnum`'s `repr` is
    `<Reserved.JUDGE: 'judge'>`, and leaking a Python identifier into a message is the defect
    ADR 0004 rejects — the same split `ProceedingFailed` already makes.
    """
    with pytest.raises(ConfigurationError) as excinfo:
        tribunal_for(
            Escalation,
            advocates={
                Escalation.HANDLE: Advocate(),
                Escalation.ESCALATE: Advocate(),
                Reserved.JUDGE: Advocate(),
            },
        )
    assert str(excinfo.value) == (
        "advocates names a key that is not a verdict of Escalation: 'judge'"
    )


def test_a_budget_with_an_inherited_request_limit() -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        tribunal_for(Escalation, budget=UsageLimits(cost_limit=Decimal("2.00")))
    assert str(excinfo.value) == (
        "budget.request_limit is 50, which is UsageLimits' own per-run default rather than a "
        "proceeding-wide figure you chose. Pass request_limit=None for no cap, or an explicit "
        "number."
    )


@pytest.mark.parametrize("request_limit", [None, 400, 1])
def test_a_chosen_request_limit_is_accepted(request_limit: int | None) -> None:
    """Either spelling: no cap, or a real ceiling."""
    budget = UsageLimits(cost_limit=Decimal("2.00"), request_limit=request_limit)
    assert tribunal_for(Escalation, budget=budget).budget is budget


def test_no_budget_reaches_no_check() -> None:
    """`0029` scopes the check to a budget that was given. A tribunal without one touches no
    `UsageLimits` object at all."""
    assert tribunal_for(Escalation, budget=None).budget is None


def test_the_budget_is_checked_after_the_bench() -> None:
    """A tribunal with a broken bench has the worse problem, and the budget is about a
    different argument entirely."""
    with pytest.raises(ConfigurationError, match="missing a verdict"):
        tribunal_for(
            Escalation,
            advocates={Escalation.HANDLE: Advocate()},
            budget=UsageLimits(cost_limit=Decimal("2.00")),
        )
