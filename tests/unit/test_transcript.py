"""The record: a sequence of entries that is also a self-contained audit artifact.

Pins `docs/design/api.md` ("The record"),
`docs/decisions/0019-the-ledger-is-part-of-the-record.md`, and
`docs/decisions/0025-the-record-includes-what-steered-it.md`.
"""

from datetime import UTC, datetime

from enbanc import (
    Argument,
    Case,
    Continuance,
    Entry,
    Exhibit,
    Interrogatory,
    Response,
    Retrieval,
    Ruling,
    Statute,
    ToolFailure,
    Transcript,
    Verdict,
)


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"
    REFER = "refer to a senior underwriter for manual review"


class LoanApplication(Case):
    applicant: str
    income: int


def _at(second: int) -> datetime:
    return datetime(2026, 9, 2, 14, 3, second, tzinfo=UTC)


def _transcript() -> Transcript[LoanDecision]:
    """Round 1 of `docs/design/outcomes.md` § 1, reduced to what a schema test needs.

    APPROVE retrieves two sources and files one; the id it leaves out is the join below.
    """
    return Transcript[LoanDecision](
        question="Shall the bank loan this applicant $500k?",
        statute=Statute(text="Approve $500k loans only where DTI < 0.43", name="underwriting-v3"),
        case=LoanApplication(applicant="A. Okonkwo", income=182000),
        verdicts=list(LoanDecision),
        max_rounds=5,
        guidance={"judge": "Where the record is ambiguous, deny."},
        procedure="p1",
        entries=[
            Entry[LoanDecision](
                round=1,
                filed_at=_at(11),
                filing=Argument[LoanDecision](
                    advocate=LoanDecision.APPROVE,
                    claim="DTI is 0.38 on documented income.",
                    exhibits=[
                        Exhibit(
                            source="s1",
                            tool="psql",
                            reference='psql(sql="SELECT net_profit FROM schedule_c ...")',
                            content="schedule_c_2024: 182000",
                        )
                    ],
                ),
            ),
            Entry[LoanDecision](
                round=1,
                filed_at=_at(22),
                filing=Continuance[LoanDecision](
                    interrogatories=[
                        Interrogatory[LoanDecision](
                            id="r1-q1",
                            to=LoanDecision.APPROVE,
                            question="Which income figure does §4.2 require?",
                        )
                    ]
                ),
            ),
        ],
        ledger=[
            Retrieval[LoanDecision](
                id="s1",
                round=1,
                advocate=LoanDecision.APPROVE,
                tool="psql",
                reference='psql(sql="SELECT net_profit FROM schedule_c ...")',
                content="schedule_c_2024: 182000",
            ),
            Retrieval[LoanDecision](
                id="s2",
                round=1,
                advocate=LoanDecision.APPROVE,
                tool="psql",
                reference='psql(sql="SELECT verification_status FROM income_docs ...")',
                content="verification_status: none",
            ),
        ],
        failures=[
            ToolFailure[LoanDecision](
                round=1,
                advocate=LoanDecision.APPROVE,
                tool="web_search",
                reference='web_search(query="self-employment income verification")',
                detail="Timed out after 15.0 seconds.",
            )
        ],
    )


def test_a_transcript_iterates_over_its_entries() -> None:
    assert [type(filing.filing).__name__.split("[")[0] for filing in _transcript()] == [
        "Argument",
        "Continuance",
    ]


def test_a_transcript_is_sized_and_indexable_including_from_the_end() -> None:
    transcript = _transcript()
    assert len(transcript) == 2
    assert isinstance(transcript[0].filing, Argument)
    assert isinstance(transcript[-1].filing, Continuance)


def test_an_entry_less_transcript_is_falsy() -> None:
    """A consequence of `__len__`, documented rather than papered over: test for the record
    with `is not None`, and for filings with `len(...)`."""
    empty = Transcript[LoanDecision](
        question="q",
        statute=Statute(text="rule"),
        case=Case(),
        verdicts=list(LoanDecision),
        max_rounds=5,
        procedure="p1",
    )
    assert not empty
    assert empty is not None
    assert len(empty) == 0


def test_the_standing_record_is_carried_alongside_the_entries() -> None:
    """A transcript dumped to JSON is a complete account on its own, not a fragment that
    needs the `Hearing` to be legible."""
    transcript = _transcript()
    assert transcript.question.startswith("Shall the bank")
    assert transcript.statute.name == "underwriting-v3"
    assert transcript.verdicts == list(LoanDecision)
    assert transcript.max_rounds == 5
    assert transcript.procedure == "p1"


def test_guidance_is_keyed_by_participant_and_holds_only_those_that_got_one() -> None:
    """Absence means none was given — there is no empty-string placeholder."""
    transcript = _transcript()
    assert transcript.guidance == {"judge": "Where the record is ambiguous, deny."}

    steered = transcript.model_copy(
        update={"guidance": {"judge": "deny", LoanDecision.DENY: "Weigh documented income."}}
    )
    assert steered.guidance[LoanDecision.DENY] == "Weigh documented income."


def test_a_subclass_case_keeps_its_fields_through_serialization() -> None:
    """Without `SerializeAsAny` this dumps as a bare `Case` and every subclass field
    disappears — silently, out of the artifact whose whole job is to be complete."""
    dumped = _transcript().model_dump()
    assert dumped["case"] == {"applicant": "A. Okonkwo", "income": 182000}


def test_a_populated_transcript_round_trips() -> None:
    transcript = _transcript()
    restored = Transcript[LoanDecision].model_validate_json(transcript.model_dump_json())

    assert len(restored) == 2
    assert isinstance(restored[0].filing, Argument)
    assert restored[0].filing.advocate is LoanDecision.APPROVE
    assert restored[0].filed_at == _at(11)
    assert isinstance(restored[-1].filing, Continuance)
    assert restored[-1].filing.interrogatories[0].id == "r1-q1"
    assert restored.verdicts == list(LoanDecision)
    assert restored.case.model_dump() == {"applicant": "A. Okonkwo", "income": 182000}


def test_the_ledger_records_what_was_retrieved_not_only_what_was_filed() -> None:
    transcript = _transcript()
    assert [row.id for row in transcript.ledger] == ["s1", "s2"]
    assert all(row.advocate is LoanDecision.APPROVE for row in transcript.ledger)


def test_suppression_is_found_by_joining_on_advocate_and_id() -> None:
    """The schema half of `outcomes.md` § 1's join: the record *supports* the question
    "what was left out?". That a real proceeding produces exactly one buried source is the
    round loop's claim, asserted over a proceeding rather than over a hand-built record.
    """
    transcript = _transcript()
    cited = {
        (entry.filing.advocate, exhibit.source)
        for entry in transcript
        if isinstance(entry.filing, Argument | Response)
        for exhibit in entry.filing.exhibits
    }
    buried = [
        (row.advocate, row.id) for row in transcript.ledger if (row.advocate, row.id) not in cited
    ]
    assert buried == [(LoanDecision.APPROVE, "s2")]


def test_the_join_key_is_the_pair_because_ids_are_numbered_per_advocate() -> None:
    """`APPROVE`'s `s1` and `DENY`'s `s1` are different retrievals."""
    transcript = _transcript()
    with_deny = transcript.model_copy(
        update={
            "ledger": [
                *transcript.ledger,
                Retrieval[LoanDecision](
                    id="s1",
                    round=1,
                    advocate=LoanDecision.DENY,
                    tool="psql",
                    reference='psql(sql="SELECT wages FROM w2 ...")',
                    content="w2_2024: 131400",
                ),
            ]
        }
    )
    ids = [row.id for row in with_deny.ledger]
    assert ids.count("s1") == 2
    assert len({(row.advocate, row.id) for row in with_deny.ledger}) == 3


def test_a_failed_call_is_recorded_and_carries_no_id() -> None:
    """A `Retrieval` has an id so an `Exhibit.source` can name it. A failed call produced
    nothing and can never be cited, and the absent id is the type saying so."""
    failure = _transcript().failures[0]
    assert failure.tool == "web_search"
    assert failure.detail == "Timed out after 15.0 seconds."
    assert "id" not in ToolFailure.model_fields


def test_the_transcript_holds_no_renderer_yet() -> None:
    """`render()` lands with `_prompting.py` — see `docs/implementations/rendering.md`."""
    assert not hasattr(Transcript, "render")


def test_a_ruling_is_a_filing_like_any_other() -> None:
    transcript = _transcript()
    ruled = transcript.model_copy(
        update={
            "entries": [
                *transcript.entries,
                Entry[LoanDecision](
                    round=2,
                    filed_at=_at(44),
                    filing=Ruling[LoanDecision](
                        verdict=LoanDecision.DENY, reasoning="Documented income governs."
                    ),
                ),
            ]
        }
    )
    assert isinstance(ruled[-1].filing, Ruling)
    assert len(ruled) == 3
