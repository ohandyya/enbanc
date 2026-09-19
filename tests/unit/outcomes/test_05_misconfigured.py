"""`docs/design/outcomes.md` § 5 — the tribunal is misconfigured.

The first module of the spine `docs/design/testing.md` ("`outcomes.md` is the spine") lays
out: one module per section of that document, each varying only what its section varies. § 5
comes first in code rather than first in order because it is the only section that needs no
proceeding — all three of its subsections raise from the constructor.

**The messages are asserted as text, not just as a raised type.** `testing.md` names this as
one of two things worth a test in its own right: each message exists because the mistake it
catches looks ordinary, so the message is the whole remedy.

The doc is mirrored here, never executed. What keeps the two in step is `CLAUDE.md` rule 2 — a
change to behaviour updates the design doc in the same commit, and a change to behaviour is
exactly what breaks this module. See
`docs/decisions/0032-a-design-doc-is-mirrored-by-tests.md`.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.usage import UsageLimits

from enbanc import Advocate, ConfigurationError, Judge, Tribunal, Verdict

Kwargs = Callable[[], dict[str, Any]]


def test_the_bench_that_outcomes_md_uses_builds(outcomes_kwargs: Kwargs) -> None:
    """The control. Every assertion below varies one key of this, so a failure here would make
    the three of them meaningless."""
    tribunal = Tribunal(**outcomes_kwargs())

    assert len(tribunal.advocates) == 3
    assert tribunal.max_rounds == 5
    assert tribunal.budget is None
    assert tribunal.judge.guidance == "Where the record is ambiguous, deny."


def test_an_advocate_is_missing(outcomes_kwargs: Kwargs) -> None:
    """`REFER` unseated. This is what makes adding an enum member a loud failure instead of a
    silent one: a new verdict with no advocate would otherwise be an answer nobody was
    assigned to argue for."""
    kwargs = outcomes_kwargs()
    refer = next(
        verdict
        for verdict in kwargs["advocates"]
        if verdict.value == "refer to a senior underwriter for manual review"
    )
    del kwargs["advocates"][refer]

    with pytest.raises(ConfigurationError) as excinfo:
        Tribunal(**kwargs)
    assert str(excinfo.value) == (
        "advocates is missing a verdict: 'refer to a senior underwriter for manual review'"
    )


def test_an_unknown_key_raises_the_same_way(outcomes_kwargs: Kwargs) -> None:
    """The one-line aside § 5 makes and does not work through: an unknown key raises the
    same way a missing verdict does."""
    kwargs = outcomes_kwargs()
    kwargs["advocates"]["approve!"] = Advocate()

    with pytest.raises(ConfigurationError) as excinfo:
        Tribunal(**kwargs)
    assert str(excinfo.value) == (
        "advocates names a key that is not a verdict of LoanDecision: 'approve!'"
    )


def test_a_verdict_named_judge(outcomes_kwargs: Kwargs) -> None:
    """Left alone, that advocate's spend and the judge's would land in one entry of
    `hearing.usage_by_participant` with no sign that two participants had merged — in the
    artifact whose whole job is attributing spend. See
    `docs/decisions/0014-usage-is-broken-down-per-participant.md`."""

    class Escalation(Verdict):
        HANDLE = "handle"
        JUDGE = "judge"  # reserved

    kwargs = outcomes_kwargs()
    kwargs["verdicts"] = Escalation
    kwargs["advocates"] = {member: Advocate() for member in Escalation}

    with pytest.raises(ConfigurationError) as excinfo:
        Tribunal(**kwargs)
    assert str(excinfo.value) == (
        "'judge' is a reserved verdict value: it would collide with the judge's key in "
        "usage_by_participant"
    )


def test_a_budget_with_an_inherited_request_limit(outcomes_kwargs: Kwargs) -> None:
    """`UsageLimits` defaults `request_limit` to 50, so that object carries a fifty-request
    ceiling nobody typed. Applied to a whole proceeding it would stop this tribunal after about
    five rounds and record `Undecided(reason='budget')` for a hearing that had spent thirty
    cents of its two dollars — the audit artifact stating that the money ran out when it had
    not."""
    kwargs = outcomes_kwargs()
    kwargs["budget"] = UsageLimits(cost_limit=Decimal("2.00"))

    with pytest.raises(ConfigurationError) as excinfo:
        Tribunal(**kwargs)
    assert str(excinfo.value) == (
        "budget.request_limit is 50, which is UsageLimits' own per-run default rather than a "
        "proceeding-wide figure you chose. Pass request_limit=None for no cap, or an explicit "
        "number."
    )


@pytest.mark.parametrize("request_limit", [None, 400])
def test_either_spelling_is_accepted(outcomes_kwargs: Kwargs, request_limit: int | None) -> None:
    """No cap, or a real ceiling — the two forms § 5 writes out."""
    kwargs = outcomes_kwargs()
    kwargs["budget"] = UsageLimits(cost_limit=Decimal("2.00"), request_limit=request_limit)

    assert Tribunal(**kwargs).budget is kwargs["budget"]


def test_a_configuration_error_carries_no_transcript(outcomes_kwargs: Kwargs) -> None:
    """§ 5: it carries no transcript because nothing ran, which is why it sits beside
    `ProceedingFailed` rather than under it. That one has `.transcript`; this has no such
    attribute to read."""
    kwargs = outcomes_kwargs()
    kwargs["judge"] = Judge()
    kwargs["advocates"] = {}

    with pytest.raises(ConfigurationError) as excinfo:
        Tribunal(**kwargs)
    assert not hasattr(excinfo.value, "transcript")
