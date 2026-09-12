"""The five filings, their discriminators, and the ids nobody is asked to author.

Pins `docs/design/api.md` ("What participants file", "The judge's output", "Where ids come
from") and `docs/decisions/0015-interrogatory-ids-are-stamped-on-filing.md`.
"""

import pytest
from pydantic import BaseModel, ValidationError

from enbanc import (
    Argument,
    Concession,
    Continuance,
    Deliberation,
    Exhibit,
    Filing,
    Interrogatory,
    Response,
    Ruling,
    Verdict,
)
from enbanc._filings import _Continuance, _Interrogatory


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


class Record(BaseModel):
    filing: Filing[LoanDecision]


class Deliberated(BaseModel):
    deliberation: Deliberation[LoanDecision]


def test_every_kind_defaults_so_no_model_has_to_produce_it() -> None:
    assert Argument[LoanDecision](advocate=LoanDecision.APPROVE, claim="DTI is 0.38").kind == (
        "argument"
    )
    assert Concession[LoanDecision](advocate=LoanDecision.DENY, reason="conceded").kind == (
        "concession"
    )
    assert (
        Response[LoanDecision](
            advocate=LoanDecision.APPROVE, answering="r1-q1", answer="§4.2 permits it"
        ).kind
        == "response"
    )
    assert Ruling[LoanDecision](verdict=LoanDecision.DENY, reasoning="...").kind == "ruling"
    assert (
        Continuance[LoanDecision](
            interrogatories=[
                Interrogatory[LoanDecision](id="r1-q1", to=LoanDecision.DENY, question="?")
            ]
        ).kind
        == "continuance"
    )


def test_a_filing_defaults_to_no_exhibits() -> None:
    assert Argument[LoanDecision](advocate=LoanDecision.APPROVE, claim="...").exhibits == []
    assert (
        Response[LoanDecision](
            advocate=LoanDecision.APPROVE, answering="r1-q1", answer="..."
        ).exhibits
        == []
    )


def test_nothing_carries_a_position_or_an_author() -> None:
    """Both were rejected: one would store a fact twice, the other would make a ruling
    issued by an advocate expressible."""
    assert "position" not in Argument.model_fields
    for filing in (Argument, Concession, Response, Continuance, Ruling):
        assert "author" not in filing.model_fields


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"kind": "argument", "advocate": "approve", "claim": "c"}, Argument),
        ({"kind": "concession", "advocate": "deny", "reason": "r"}, Concession),
        (
            {"kind": "response", "advocate": "approve", "answering": "r1-q1", "answer": "a"},
            Response,
        ),
        (
            {
                "kind": "continuance",
                "interrogatories": [{"id": "r1-q1", "to": "deny", "question": "q"}],
            },
            Continuance,
        ),
        ({"kind": "ruling", "verdict": "deny", "reasoning": "r"}, Ruling),
    ],
)
def test_the_discriminator_reads_each_filing_back_as_the_right_class(
    payload: dict[str, object], expected: type[BaseModel]
) -> None:
    """Pydantic discriminates on `kind` rather than guessing a union member from field shape.

    That matters more here than for most unions: the whole point of the artifact is that
    someone reads it later.
    """
    filing = Record.model_validate({"filing": payload}).filing
    assert isinstance(filing, expected)


def test_a_deliberation_is_a_ruling_or_a_continuance() -> None:
    ruled = Deliberated.model_validate(
        {"deliberation": {"kind": "ruling", "verdict": "deny", "reasoning": "r"}}
    )
    continued = Deliberated.model_validate(
        {
            "deliberation": {
                "kind": "continuance",
                "interrogatories": [{"id": "r1-q1", "to": "deny", "question": "q"}],
            }
        }
    )
    assert isinstance(ruled.deliberation, Ruling)
    assert isinstance(continued.deliberation, Continuance)


def test_narrowing_works_by_isinstance_not_by_identity() -> None:
    """`Ruling[LoanDecision]` is a genuine subclass Pydantic built, not `Ruling` itself."""
    ruling = Ruling[LoanDecision](verdict=LoanDecision.DENY, reasoning="...")
    assert type(ruling) is not Ruling
    assert isinstance(ruling, Ruling)


def test_an_interrogatory_id_is_required_and_has_no_default() -> None:
    """A transcript whose `Response.answering` link does not resolve is not an audit artifact,
    so the field cannot be defaulted — a defaulted id is one a malformed transcript
    reconstructs silently."""
    assert Interrogatory.model_fields["id"].is_required()

    with pytest.raises(ValidationError):
        Interrogatory[LoanDecision](to=LoanDecision.DENY, question="?")  # type: ignore[call-arg]


def test_the_judge_is_never_asked_for_an_id() -> None:
    """The emit-shape has no `id` field at all, which is what buys the public one its
    required-no-default. The judge does not know its own round number, and nothing would stop
    it issuing the same id in two rounds."""
    assert set(_Interrogatory.model_fields) == {"to", "question"}
    assert set(Interrogatory.model_fields) - set(_Interrogatory.model_fields) == {"id"}


def test_an_exhibit_rides_on_the_filings_that_can_carry_one() -> None:
    exhibit = Exhibit(source="s1", tool="psql", reference="psql(...)", content="182000")
    argued = Argument[LoanDecision](
        advocate=LoanDecision.APPROVE, claim="DTI is 0.38", exhibits=[exhibit]
    )
    assert argued.exhibits[0].reference == "psql(...)"
    assert "exhibits" not in Concession.model_fields
    assert "exhibits" not in Ruling.model_fields


def test_the_emitted_continuance_nests_the_emitted_interrogatory() -> None:
    emitted = _Continuance[LoanDecision](
        interrogatories=[_Interrogatory[LoanDecision](to=LoanDecision.APPROVE, question="?")]
    )
    assert emitted.kind == "continuance"
    assert isinstance(emitted.interrogatories[0], _Interrogatory)
