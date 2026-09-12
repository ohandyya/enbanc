"""What `hear()` returns: the outcome, the record, and what the proceeding spent.

Pins `docs/design/api.md` ("The result", "Usage", "Per participant"),
`docs/design/outcomes.md` § 7, and
`docs/decisions/0014-usage-is-broken-down-per-participant.md`.
"""

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError
from pydantic_ai.usage import RunUsage

from enbanc import (
    Case,
    Entry,
    Hearing,
    Outcome,
    Ruling,
    Statute,
    Transcript,
    Undecided,
    Verdict,
)


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


class Ended(BaseModel):
    outcome: Outcome[LoanDecision]


def _ruling() -> Ruling[LoanDecision]:
    return Ruling[LoanDecision](
        verdict=LoanDecision.DENY, reasoning="Documented income governs; DTI is 0.51."
    )


def _transcript(*filings: Ruling[LoanDecision]) -> Transcript[LoanDecision]:
    return Transcript[LoanDecision](
        question="Shall the bank loan this applicant $500k?",
        statute=Statute(text="DTI < 0.43", name="underwriting-v3"),
        case=Case(applicant="A. Okonkwo", income=182000),  # type: ignore[call-arg]  # open base; see test_inputs.py
        verdicts=list(LoanDecision),
        max_rounds=5,
        procedure="p1",
        entries=[
            Entry[LoanDecision](
                round=2, filed_at=datetime(2026, 9, 2, 14, 3, 44, tzinfo=UTC), filing=filing
            )
            for filing in filings
        ],
    )


def _hearing() -> Hearing[LoanDecision]:
    ruling = _ruling()
    return Hearing[LoanDecision](
        outcome=ruling,
        transcript=_transcript(ruling),
        usage_by_participant={
            LoanDecision.APPROVE: RunUsage(requests=3, input_tokens=14820, output_tokens=1120),
            LoanDecision.DENY: RunUsage(requests=4, input_tokens=18960, output_tokens=1240),
            "judge": RunUsage(requests=2, input_tokens=20312, output_tokens=1240),
        },
        rounds=2,
    )


def test_an_outcome_is_a_ruling_or_undecided() -> None:
    assert isinstance(
        Ended.model_validate(
            {"outcome": {"kind": "ruling", "verdict": "deny", "reasoning": "r"}}
        ).outcome,
        Ruling,
    )
    assert isinstance(
        Ended.model_validate({"outcome": {"kind": "undecided", "reason": "budget"}}).outcome,
        Undecided,
    )


def test_undecided_names_which_envelope_ran_out() -> None:
    assert Undecided(reason="rounds").reason == "rounds"
    assert Undecided(reason="budget").reason == "budget"


def test_undecided_reason_is_required_and_undefaulted() -> None:
    """`kind` has exactly one correct value and `reason` has two, so a default here would be
    a guess that reads as a fact."""
    assert Undecided.model_fields["reason"].is_required()
    with pytest.raises(ValidationError):
        Undecided()  # type: ignore[call-arg]


def test_undecided_only_admits_the_two_envelopes() -> None:
    with pytest.raises(ValidationError):
        Undecided(reason="failure")  # type: ignore[arg-type]


def test_undecided_is_not_generic() -> None:
    """There is no verdict in it to key on."""
    with pytest.raises(TypeError):
        Undecided[LoanDecision]  # type: ignore[index]


def test_undecided_carries_nothing_else() -> None:
    """Not the round count, which is `Hearing.rounds`; not the pending questions, which are
    on the last `Continuance`. Either would be the store-it-twice mistake."""
    assert set(Undecided.model_fields) == {"kind", "reason"}


def test_usage_is_the_sum_of_the_breakdown() -> None:
    hearing = _hearing()
    assert hearing.usage.requests == 3 + 4 + 2
    assert hearing.usage.input_tokens == 14820 + 18960 + 20312
    assert hearing.usage.output_tokens == 1120 + 1240 + 1240


def test_usage_is_computed_so_there_is_no_second_place_to_disagree() -> None:
    """The breakdown is the stored fact. Changing it changes the total, with no accumulator
    beside it to fall out of step."""
    hearing = _hearing()
    before = hearing.usage.requests
    leaner = hearing.model_copy(
        update={"usage_by_participant": {"judge": RunUsage(requests=1)}},
    )
    assert leaner.usage.requests == 1 != before
    assert "usage" not in Hearing.model_fields


def test_the_judges_spend_is_readable_on_its_own() -> None:
    """The reason the breakdown exists: nothing in the aggregate says whether a strong judge
    over cheap advocates paid off."""
    assert _hearing().usage_by_participant["judge"].input_tokens == 20312


def test_the_outcome_is_a_pointer_to_the_terminal_filing() -> None:
    """So callers do not walk the record backwards to find the ruling."""
    hearing = _hearing()
    assert hearing.outcome is hearing.transcript[-1].filing


def test_a_hearing_round_trips_and_the_pointer_becomes_an_equal_copy() -> None:
    """`docs/design/outcomes.md` § 7. In memory the outcome is the terminal filing; through
    JSON it is written twice and read back as two equal objects."""
    hearing = _hearing()
    restored = Hearing[LoanDecision].model_validate_json(hearing.model_dump_json())

    assert isinstance(restored.outcome, Ruling)
    assert restored.outcome.verdict is LoanDecision.DENY
    assert isinstance(restored.transcript[-1].filing, Ruling)
    assert restored.outcome is not restored.transcript[-1].filing
    assert restored.outcome == restored.transcript[-1].filing


def test_the_breakdown_keys_come_back_as_enum_members_and_the_judge_string() -> None:
    restored = Hearing[LoanDecision].model_validate_json(_hearing().model_dump_json())
    assert set(restored.usage_by_participant) == {
        LoanDecision.APPROVE,
        LoanDecision.DENY,
        "judge",
    }
    assert restored.usage == _hearing().usage


def test_an_undecided_hearing_serializes_too() -> None:
    """A proceeding that stopped inside the limits it was given belongs in the audit
    artifact whether or not it decided."""
    spent = Hearing[LoanDecision](
        outcome=Undecided(reason="budget"),
        transcript=_transcript(),
        usage_by_participant={"judge": RunUsage(requests=5)},
        rounds=5,
    )
    restored = Hearing[LoanDecision].model_validate_json(spent.model_dump_json())
    assert isinstance(restored.outcome, Undecided)
    assert restored.outcome.reason == "budget"
    assert restored.rounds == 5


def test_an_undecided_is_not_an_entry_in_the_record() -> None:
    """Nobody filed it: the transcript ends on the judge's last `Continuance`, and the
    outcome is the tribunal's own statement that no round followed it."""
    spent = Hearing[LoanDecision](
        outcome=Undecided(reason="rounds"),
        transcript=_transcript(),
        usage_by_participant={"judge": RunUsage(requests=5)},
        rounds=5,
    )
    assert len(spent.transcript) == 0
