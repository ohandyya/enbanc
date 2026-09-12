"""The error hierarchy, and what a failed proceeding hands back.

Pins `docs/design/api.md` ("When something goes wrong"),
`docs/design/outcomes.md` § 4 — including the message text, which that document prints —
`docs/design/packaging.md` ("Where the errors live"), and
`docs/decisions/0012-a-failure-cancels-the-round.md`.
"""

import pytest
from pydantic_ai.usage import RunUsage

from enbanc import (
    Case,
    ConfigurationError,
    EnbancError,
    ProceedingFailed,
    ProceedingUnfinished,
    Statute,
    Transcript,
    Verdict,
)


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


def _transcript() -> Transcript[LoanDecision]:
    return Transcript[LoanDecision](
        question="Shall the bank loan this applicant $500k?",
        statute=Statute(text="DTI < 0.43", name="underwriting-v3"),
        case=Case(applicant="A. Okonkwo", income=182000),  # type: ignore[call-arg]  # open base; see test_inputs.py
        verdicts=list(LoanDecision),
        max_rounds=5,
        procedure="p1",
    )


def _failure(
    participant: LoanDecision | str = LoanDecision.DENY, round: int = 1
) -> ProceedingFailed[LoanDecision]:
    return ProceedingFailed[LoanDecision](
        participant=participant,  # type: ignore[arg-type]
        round=round,
        transcript=_transcript(),
        usage_by_participant={
            LoanDecision.APPROVE: RunUsage(requests=2, input_tokens=7020),
            LoanDecision.DENY: RunUsage(requests=1, input_tokens=3480),
        },
    )


@pytest.mark.parametrize("error", [ConfigurationError, ProceedingFailed, ProceedingUnfinished])
def test_everything_descends_from_one_base(error: type[Exception]) -> None:
    """An error hierarchy a caller catches on is one thing to import."""
    assert issubclass(error, EnbancError)
    assert issubclass(error, Exception)


def test_the_base_is_what_a_caller_catches() -> None:
    with pytest.raises(EnbancError):
        raise _failure()


def test_a_failure_carries_the_record_as_it_stood() -> None:
    failure = _failure()
    assert failure.participant is LoanDecision.DENY
    assert failure.round == 1
    assert failure.transcript.question.startswith("Shall the bank")
    assert set(failure.usage_by_participant) == {LoanDecision.APPROVE, LoanDecision.DENY}


def test_the_message_names_the_advocate_by_its_value() -> None:
    """`docs/design/outcomes.md` § 4 prints this text.

    `str(participant)`, not the member: `repr()` of a StrEnum member is
    `<LoanDecision.DENY: 'deny'>`, and leaking a Python identifier into a message is the
    defect ADR 0004 rejects for the transcript.
    """
    assert str(_failure()) == "advocate 'deny' could not be heard in round 1"


def test_the_message_names_the_judge_as_the_judge() -> None:
    assert str(_failure(participant="judge", round=2)) == (
        "the judge could not be heard in round 2"
    )


def test_absence_from_the_breakdown_means_never_dispatched() -> None:
    """A judge with no key never deliberated — the same thing the missing `Continuance` in
    the transcript says from the other side."""
    assert "judge" not in _failure().usage_by_participant


def test_usage_is_the_sum_of_the_breakdown() -> None:
    """A floor rather than an exact bill: cancellation is client-side and does not un-bill
    tokens a provider has already generated."""
    failure = _failure()
    assert failure.usage.requests == 3
    assert failure.usage.input_tokens == 7020 + 3480


def test_a_failure_cannot_carry_a_hearing() -> None:
    """An outage is not an adjudication and must not be storable as one."""
    assert not hasattr(_failure(), "hearing")
    assert not hasattr(_failure(), "outcome")


def test_there_is_no_rounds_field() -> None:
    """A round completes when its deliberation is filed, so failing in round N always leaves
    N-1 behind it. Carrying both would store one fact twice."""
    failure = _failure(round=2)
    assert failure.round == 2
    assert not hasattr(failure, "rounds")


def test_the_original_error_survives_as_the_cause() -> None:
    """No provider exception reaches you bare, and none is thrown away either."""
    cause = ConnectionError("Connection error.")
    with pytest.raises(ProceedingFailed) as caught:
        try:
            raise cause
        except ConnectionError as exc:
            raise _failure() from exc
    assert caught.value.__cause__ is cause


def test_catching_the_parameterized_class_is_a_runtime_type_error() -> None:
    """Python matches exceptions on the class, not the parameterization. Catch the bare
    class and read `.participant`, which is typed."""
    with pytest.raises(TypeError, match="do not inherit from BaseException"):
        try:
            raise _failure()
        except ProceedingFailed[LoanDecision]:  # type: ignore[misc]
            pass


def test_a_configuration_error_carries_nothing_because_nothing_ran() -> None:
    error = ConfigurationError("advocates is missing a verdict: 'deny'")
    assert not hasattr(error, "transcript")
    assert str(error) == "advocates is missing a verdict: 'deny'"


def test_an_unfinished_proceeding_is_its_own_thing() -> None:
    """Reserved for a proceeding still running or one the caller walked away from — a
    proceeding that died re-raises its own `ProceedingFailed` instead."""
    assert not issubclass(ProceedingUnfinished, ProceedingFailed)
