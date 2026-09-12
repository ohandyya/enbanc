"""A continuance carries at least one interrogatory — on both shapes, for two reasons.

Named by `docs/design/api.md` ("The judge's output") and required by
`docs/decisions/0036-a-continuance-carries-at-least-one-interrogatory.md`.

An empty continuance is not a harmless no-op: the round that followed it would dispatch
nobody and the judge would deliberate again on an empty delta, so it could only repeat itself
until `max_rounds` ran out — leaving a transcript of identical empty continuances that
records a broken proceeding as though it were a hard one.

The constraint sits on both shapes because they are checked at different moments. On
`_Continuance` it validates the judge's output during a run, where an empty emission spends
the `output` retry budget — `tests/contract/test_output_validation_spends_the_output_budget.py`
pins that half against `pydantic-ai`. On `Continuance` it validates a persisted transcript
read back, which is what makes the invariant a property of the artifact rather than of a live
proceeding.
"""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from enbanc import Continuance, Interrogatory, Verdict
from enbanc._filings import _Continuance, _Interrogatory


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


def _question() -> Interrogatory[LoanDecision]:
    return Interrogatory[LoanDecision](id="r1-q1", to=LoanDecision.DENY, question="Which figure?")


def test_the_filed_continuance_refuses_an_empty_list() -> None:
    with pytest.raises(ValidationError) as caught:
        Continuance[LoanDecision](interrogatories=[])
    assert caught.value.errors()[0]["type"] == "too_short"


def test_the_emitted_continuance_refuses_an_empty_list() -> None:
    with pytest.raises(ValidationError) as caught:
        _Continuance[LoanDecision](interrogatories=[])
    assert caught.value.errors()[0]["type"] == "too_short"


def test_the_field_is_required_on_both_shapes() -> None:
    """Not merely non-empty: a continuance with the key absent is refused too."""
    for shape in (Continuance, _Continuance):
        assert shape.model_fields["interrogatories"].is_required()


def test_one_question_is_enough() -> None:
    assert len(Continuance[LoanDecision](interrogatories=[_question()]).interrogatories) == 1
    assert (
        len(
            _Continuance[LoanDecision](
                interrogatories=[_Interrogatory[LoanDecision](to=LoanDecision.DENY, question="?")]
            ).interrogatories
        )
        == 1
    )


def test_a_persisted_empty_continuance_will_not_validate_back() -> None:
    """The half that makes this a property of the artifact. A transcript hand-edited to hold
    an empty continuance is rejected on read, not quietly accepted."""

    class Record(BaseModel):
        filing: Continuance[LoanDecision]

    with pytest.raises(ValidationError):
        Record.model_validate({"filing": {"kind": "continuance", "interrogatories": []}})


@pytest.mark.parametrize("shape", [Continuance, _Continuance])
def test_the_constraint_reaches_a_model_as_min_items(shape: type[BaseModel]) -> None:
    """A judge asked for a continuance is shown `minItems: 1` in the first place, which is
    what makes a retry carrying Pydantic's own message intelligible rather than arbitrary."""
    schema: dict[str, Any] = shape[LoanDecision].model_json_schema()  # type: ignore[index]
    assert schema["properties"]["interrogatories"]["minItems"] == 1
