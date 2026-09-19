"""The five filing shapes, and what happens to text that does not fit on one line.

Every case here goes through `render(..., JudgeView(since=0))` rather than through the
private block helper: the projection is the thing an agent actually reads, and a test that
reached past it could pass on a renderer no participant ever runs.

Pins `docs/design/prompting.md` ("The turns", "`Transcript.render()`") and the indentation
rule `docs/implementations/rendering.md` settled.
"""

from datetime import UTC, datetime
from typing import Any

from enbanc import (
    Argument,
    Case,
    Concession,
    Continuance,
    Entry,
    Exhibit,
    Interrogatory,
    Response,
    Ruling,
    Statute,
    Transcript,
    Verdict,
)
from enbanc._filings import Filing
from enbanc._prompting import JudgeView, render


class Call(Verdict):
    YES = "yes"
    NO = "no"


def _rendered(*filings: Filing[Call]) -> str:
    """One transcript holding exactly these filings, projected as an agent would see it."""
    transcript = Transcript[Call](
        question="q",
        statute=Statute(text="s"),
        case=Case(),
        verdicts=list(Call),
        max_rounds=3,
        procedure="p1",
        entries=[
            Entry[Call](round=1, filed_at=datetime(2026, 9, 2, tzinfo=UTC), filing=filing)
            for filing in filings
        ],
    )
    return render(transcript, JudgeView(since=0))


def test_an_argument() -> None:
    assert _rendered(
        Argument[Call](
            advocate=Call.YES,
            claim="The filing is timely.",
            exhibits=[
                Exhibit(
                    source="s1",
                    tool="psql",
                    reference='psql(sql="SELECT filed_on FROM returns")',
                    content="filed_on: 2024-04-12",
                    label="Return, 2024",
                )
            ],
        )
    ) == (
        "[round 1] yes argued:\n"
        "  The filing is timely.\n"
        "  Exhibits:\n"
        "    [yes/s1] Return, 2024\n"
        '      psql(sql="SELECT filed_on FROM returns")\n'
        "      filed_on: 2024-04-12"
    )


def test_an_argument_with_no_exhibits_has_no_exhibits_block() -> None:
    assert _rendered(Argument[Call](advocate=Call.YES, claim="On its face.")) == (
        "[round 1] yes argued:\n  On its face."
    )


def test_a_concession() -> None:
    assert _rendered(Concession[Call](advocate=Call.NO, reason="No reading supports it.")) == (
        "[round 1] no conceded:\n  No reading supports it."
    )


def test_a_response() -> None:
    assert _rendered(
        Response[Call](advocate=Call.NO, answering="r1-q2", answer="Only where audited.")
    ) == ("[round 1] no responded to r1-q2:\n  Only where audited.")


def test_a_continuance_lists_every_interrogatory_including_a_peers() -> None:
    """One filing, and the record grants the whole of it. *Targeted* is about who answers."""
    assert _rendered(
        Continuance[Call](
            interrogatories=[
                Interrogatory[Call](id="r1-q1", to=Call.YES, question="Which clause?"),
                Interrogatory[Call](id="r1-q2", to=Call.NO, question="Audited when?"),
            ]
        )
    ) == (
        "[round 1] the judge issued a continuance:\n"
        "  r1-q1 -> yes: Which clause?\n"
        "  r1-q2 -> no: Audited when?"
    )


def test_a_ruling() -> None:
    assert _rendered(Ruling[Call](verdict=Call.NO, reasoning="The clause is unmet.")) == (
        "[round 1] the judge ruled — no:\n  The clause is unmet."
    )


def test_a_verdict_renders_as_its_value_never_as_its_member_name() -> None:
    """`StrEnum`, so `f"{Call.NO}"` is `'no'`. A member name would leak a Python identifier
    into the artifact, which `docs/decisions/0004-verdicts-are-a-strenum.md` rejects."""
    rendered = _rendered(Ruling[Call](verdict=Call.NO, reasoning="."))
    assert "Call.NO" not in rendered
    assert "the judge ruled — no:" in rendered


def test_every_line_of_a_multi_line_value_takes_the_blocks_indent() -> None:
    """Not wrapping: nothing is reflowed, and stripping a fixed prefix recovers the original.

    Without it the second line of a claim starts at column 0 and is indistinguishable from
    the header of the next entry.
    """
    claim = "First line.\nSecond line.\nThird line."
    assert _rendered(Argument[Call](advocate=Call.YES, claim=claim)) == (
        "[round 1] yes argued:\n  First line.\n  Second line.\n  Third line."
    )


def test_a_multi_line_excerpt_is_indented_to_the_exhibit_not_the_filing() -> None:
    assert _rendered(
        Argument[Call](
            advocate=Call.YES,
            claim="See the table.",
            exhibits=[
                Exhibit(
                    source="s1",
                    tool="psql",
                    reference='psql(sql="...")',
                    content="wages: 131,400\nnet profit: 182,000",
                    label="Both figures",
                )
            ],
        )
    ) == (
        "[round 1] yes argued:\n"
        "  See the table.\n"
        "  Exhibits:\n"
        "    [yes/s1] Both figures\n"
        '      psql(sql="...")\n'
        "      wages: 131,400\n"
        "      net profit: 182,000"
    )


def test_a_blank_line_inside_a_value_stays_blank() -> None:
    """Rather than becoming the indent's worth of trailing whitespace, which is noise in the
    artifact and noise a formatter eventually eats out of a golden."""
    rendered = _rendered(Argument[Call](advocate=Call.YES, claim="One.\n\nTwo."))
    assert rendered == "[round 1] yes argued:\n  One.\n\n  Two."
    assert not any(line != line.rstrip() for line in rendered.split("\n"))


def test_a_source_with_no_label_puts_its_reference_on_the_first_line() -> None:
    """Two lines rather than three. A tool returning something other than a `Source` is
    ledgered as one anonymous source whose reference is the call itself, and a bare `[s1]`
    line would carry nothing."""
    assert _rendered(
        Argument[Call](
            advocate=Call.YES,
            claim="The ratio is on file.",
            exhibits=[
                Exhibit(
                    source="s1",
                    tool="dti_for",
                    reference='dti_for(applicant="A. Okonkwo")',
                    content="dti: 0.51",
                )
            ],
        )
    ) == (
        "[round 1] yes argued:\n"
        "  The ratio is on file.\n"
        "  Exhibits:\n"
        '    [yes/s1] dti_for(applicant="A. Okonkwo")\n'
        "      dti: 0.51"
    )


def test_entries_are_separated_by_one_blank_line_in_transcript_order() -> None:
    rendered = _rendered(
        Argument[Call](advocate=Call.YES, claim="A."),
        Concession[Call](advocate=Call.NO, reason="B."),
    )
    assert rendered == "[round 1] yes argued:\n  A.\n\n[round 1] no conceded:\n  B."


def test_an_id_is_qualified_by_the_filer_including_the_filers_own(
    proceeding: Transcript[Any],
) -> None:
    """The join key for an exhibit and its retrieval is `(advocate, id)`, so the qualified
    form is that key spelled out — and a qualified id cannot be pasted into a citation."""
    rendered = render(proceeding, JudgeView(since=0))
    assert "[approve/s1] Schedule C, 2024" in rendered
    assert "[deny/s1] W-2, 2024" in rendered
    assert "\n    [s1]" not in rendered
