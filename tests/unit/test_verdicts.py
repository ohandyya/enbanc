"""`Verdict` is an empty, subclassable `StrEnum`, and `Participant` is it plus the judge.

Pins `docs/design/api.md` ("Verdicts") and
`docs/decisions/0004-verdicts-are-a-strenum.md`. The interpolation test is the whole of that
ADR's argument: the value is what the model reads and what the transcript records, so a
member that rendered as a Python identifier would leak into both.
"""

from enum import StrEnum
from typing import Literal, get_args

import pytest
from pydantic import BaseModel, ValidationError

from enbanc import Verdict
from enbanc._verdicts import JUDGE, Participant


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"
    REFER = "refer to a senior underwriter for manual review"


def test_the_base_declares_no_members() -> None:
    """Which is exactly what makes it subclassable — Python extends an Enum only while empty."""
    assert list(Verdict) == []


def test_a_subclass_enumerates_the_allowed_answers() -> None:
    assert [v.value for v in LoanDecision] == [
        "approve",
        "deny",
        "refer to a senior underwriter for manual review",
    ]


def test_a_verdict_is_a_str_enum() -> None:
    assert issubclass(Verdict, StrEnum)
    assert LoanDecision.APPROVE == "approve"


def test_a_member_interpolates_as_its_value_not_as_its_identifier() -> None:
    """ADR 0004's reason for `StrEnum` over `(str, Enum)`, in one assertion.

    Under `(str, Enum)` this would be `'LoanDecision.APPROVE'` — a Python identifier reaching
    the model as noise and the audit artifact as a lie about what was applied.
    """
    assert f"{LoanDecision.APPROVE}" == "approve"
    assert str(LoanDecision.REFER) == "refer to a senior underwriter for manual review"


def test_the_judge_key_is_the_reserved_string() -> None:
    assert JUDGE == "judge"
    assert get_args(Literal["judge"]) == ("judge",)


def test_participant_admits_a_verdict_and_the_judge_and_nothing_else() -> None:
    """The alias is what every participant-keyed mapping in the record is spelled with."""

    class Keyed(BaseModel):
        who: Participant[LoanDecision]

    assert Keyed(who=LoanDecision.DENY).who is LoanDecision.DENY
    assert Keyed(who="judge").who == "judge"

    with pytest.raises(ValidationError):
        Keyed(who="bailiff")  # type: ignore[arg-type]
