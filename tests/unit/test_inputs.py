"""`Statute` and `Case`: what the caller supplies, and what the record says was applied.

Pins `docs/design/api.md` ("The inputs"),
`docs/decisions/0007-a-statute-is-opaque-text.md`, and
`docs/decisions/0013-a-case-is-a-subclassable-base.md`.
"""

import pytest
from pydantic import ValidationError

from enbanc import Case, Statute


class LoanApplication(Case):
    applicant: str
    income: int
    dti: float
    documents: list[str] = []


def test_a_statute_is_text_and_an_optional_name() -> None:
    assert Statute(text="DTI < 0.43").name is None
    assert Statute(text="DTI < 0.43", name="underwriting-v3").name == "underwriting-v3"


def test_a_statute_is_frozen() -> None:
    """A rule that could be edited mid-hearing makes the record's account unfalsifiable."""
    statute = Statute(text="DTI < 0.43")
    with pytest.raises(ValidationError) as caught:
        statute.text = "DTI < 0.99"  # type: ignore[misc]
    assert caught.value.errors()[0]["type"] == "frozen_instance"


def test_statute_text_is_opaque_and_passed_through_whole() -> None:
    """`enbanc` does not parse, split, normalize or validate the shape of a rule."""
    policy = "## §4.2\n\n  1. Documented income governs.\n\n  2. Stated income does not.\n"
    assert Statute(text=policy).text == policy


def test_a_bare_case_is_open() -> None:
    """The shortest thing that works while a tribunal is still being sketched.

    Note the suppression, which is a real property of this path rather than test noise:
    `extra="allow"` is a runtime setting, and Pydantic synthesizes `__init__` from the
    *declared* fields — of which the base has none. So a type checker rejects the very call
    `api.md` advertises, even though it validates and dumps exactly as documented. Subclassing
    (below) is the typed path, and it is the one anything that runs twice should take.
    """
    case = Case(applicant="A. Okonkwo", income=182000)  # type: ignore[call-arg]
    assert case.model_dump() == {"applicant": "A. Okonkwo", "income": 182000}


def test_a_case_subclass_validates_its_fields() -> None:
    with pytest.raises(ValidationError):
        LoanApplication(applicant="A. Okonkwo", income="a lot", dti=0.51)  # type: ignore[arg-type]


def test_a_case_is_frozen() -> None:
    case = LoanApplication(applicant="A. Okonkwo", income=182000, dti=0.51)
    with pytest.raises(ValidationError) as caught:
        case.income = 500000  # type: ignore[misc]
    assert caught.value.errors()[0]["type"] == "frozen_instance"


def test_a_subclass_survives_a_round_trip_onto_the_open_base() -> None:
    """`extra="allow"` is what keeps a persisted transcript legible.

    The static type does not survive — the value comes back a bare `Case` — but every field
    does, and naming the concrete class once recovers the shape.
    """
    original = LoanApplication(
        applicant="A. Okonkwo", income=182000, dti=0.51, documents=["w2-2024"]
    )
    as_base = Case.model_validate(original.model_dump())

    assert type(as_base) is Case
    assert as_base.model_dump() == original.model_dump()
    assert LoanApplication.model_validate(as_base.model_dump()) == original
