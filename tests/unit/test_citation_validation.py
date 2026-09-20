"""An id the ledger does not hold is a validation failure, not a filed exhibit.

Pins `docs/design/evidence.md` ("An unresolvable id is a validation failure") and
`docs/decisions/0016-exhibits-are-stamped-citations.md`. An advocate that cites an id it was
never issued has invented a citation, which is the failure the whole mechanism exists to
prevent: the filing is rejected, PydanticAI retries against the **`output`** budget, and an
exhausted budget is a participant whose output will not validate.

The method is called directly here. Registering it on an agent is the orchestrator's, and
`tests/contract/test_output_validation_spends_the_output_budget.py` already pins which budget
an output validator spends — neither claim is re-made here.
"""

import pytest
from pydantic_ai import ModelRetry
from pydantic_ai.toolsets import CombinedToolset, FunctionToolset

from enbanc import Retrieval, Verdict
from enbanc._evidence import _Exhibit
from enbanc._filings import _Argument, _Response
from enbanc._ledgering import Ledgering

W2 = "s3://underwriting-docs/okonkwo/w2-2024.pdf"


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


def retrieval(id: str, advocate: LoanDecision) -> Retrieval[LoanDecision]:
    return Retrieval[LoanDecision](
        id=id,
        round=1,
        advocate=advocate,
        tool="find_filings",
        reference=W2,
        content="wages: 131,400",
        label="W-2, 2024",
    )


def toolset(
    advocate: LoanDecision, ledger: list[Retrieval[LoanDecision]]
) -> Ledgering[LoanDecision]:
    return Ledgering[LoanDecision](
        wrapped=CombinedToolset([FunctionToolset(tools=[])]),
        advocate=advocate,
        ledger=ledger,
        failures=[],
    )


def argued(*sources: str) -> _Argument[LoanDecision]:
    return _Argument[LoanDecision](
        advocate=LoanDecision.DENY,
        claim="Documented wages put DTI at 0.51.",
        exhibits=[_Exhibit(source=source, content="wages: 131,400") for source in sources],
    )


def test_an_issued_id_resolves() -> None:
    ledgering = toolset(LoanDecision.DENY, [retrieval("s1", LoanDecision.DENY)])

    ledgering.check_citations(argued("s1"))


def test_an_id_the_ledger_does_not_hold_is_a_retry() -> None:
    ledgering = toolset(
        LoanDecision.DENY,
        [retrieval("s1", LoanDecision.DENY), retrieval("s2", LoanDecision.DENY)],
    )

    with pytest.raises(ModelRetry) as excinfo:
        ledgering.check_citations(argued("s7"))

    assert str(excinfo.value) == "[s7] was not issued to you. The ids you may cite are: s1, s2."


def test_another_advocates_id_is_not_citable_although_the_row_is_right_there() -> None:
    """Ids are numbered within an advocate, so `APPROVE`'s `s2` and `DENY`'s `s2` are
    different retrievals. One ledger, two sequences, and only one of them is this advocate's
    to cite."""
    ledger = [retrieval("s1", LoanDecision.DENY), retrieval("s2", LoanDecision.APPROVE)]
    ledgering = toolset(LoanDecision.DENY, ledger)

    with pytest.raises(ModelRetry) as excinfo:
        ledgering.check_citations(argued("s2"))

    assert str(excinfo.value) == "[s2] was not issued to you. The ids you may cite are: s1."


def test_a_qualified_id_is_told_what_it_actually_did() -> None:
    """The rendered record writes another advocate's ids with that advocate's name in front,
    so `deny/s2` is an id copied out of a filing rather than out of a tool result. The
    procedural prompt already warns that those are not the advocate's to cite; the message
    says which half went wrong rather than listing ids that all look unlike what it wrote."""
    ledgering = toolset(LoanDecision.APPROVE, [retrieval("s1", LoanDecision.APPROVE)])

    with pytest.raises(ModelRetry) as excinfo:
        ledgering.check_citations(argued("deny/s2"))

    assert str(excinfo.value) == (
        "[deny/s2] belongs to another advocate and is not yours to cite. "
        "The ids you may cite are: s1."
    )


def test_an_empty_ledger_says_so_rather_than_offering_an_empty_list() -> None:
    """A model told to pick from an empty list picks again; told there are none, it files
    without exhibits."""
    ledgering = toolset(LoanDecision.DENY, [])

    with pytest.raises(ModelRetry) as excinfo:
        ledgering.check_citations(argued("s1"))

    assert str(excinfo.value) == (
        "[s1] was not issued to you. The ids you may cite are: "
        "(none) — your tools have returned no sources."
    )


def test_the_first_unresolvable_id_is_the_one_reported() -> None:
    ledgering = toolset(LoanDecision.DENY, [retrieval("s1", LoanDecision.DENY)])

    with pytest.raises(ModelRetry, match=r"\[s4\]"):
        ledgering.check_citations(argued("s1", "s4", "s9"))


def test_a_response_is_validated_the_same_way() -> None:
    ledgering = toolset(LoanDecision.DENY, [retrieval("s1", LoanDecision.DENY)])
    responded = _Response[LoanDecision](
        advocate=LoanDecision.DENY,
        answering="r1-q2",
        answer="Yes — the statute's ceiling is on documented income.",
        exhibits=[_Exhibit(source="s1", content="wages: 131,400")],
    )

    ledgering.check_citations(responded)


def test_a_filing_with_no_exhibits_passes() -> None:
    """An advocate that filed nothing to check has nothing to invent. A `Concession` never
    reaches this method at all, because it carries no exhibits to carry an id."""
    ledgering = toolset(LoanDecision.DENY, [])

    ledgering.check_citations(argued())


def test_issued_lists_this_advocates_ids_in_order() -> None:
    ledger = [
        retrieval("s1", LoanDecision.DENY),
        retrieval("s1", LoanDecision.APPROVE),
        retrieval("s2", LoanDecision.DENY),
    ]

    assert toolset(LoanDecision.DENY, ledger).issued() == ["s1", "s2"]
