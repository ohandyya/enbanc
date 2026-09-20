"""The tool-result format, pinned to the version that names it.

`docs/design/prompting.md` ("How ledger ids reach the model") fixes this text, and
`Transcript.procedure` versions it alongside the procedural prompts, the turn templates and
the render format. So this module is a golden like `test_procedural_prompts.py`, with
`PROCEDURE` asserted beside each one: an edit here fails a test whose other assertion is the
version — the reminder that the edit is three moves in one commit, the text in
`prompting.md`, a new row in its version table, and the constant.

The two rendered examples are `prompting.md`'s own, reproduced rather than paraphrased, and
the sources are the ones `conftest.py`'s `proceeding` fixture carries as ledger rows — so a
tool result and the row it became are the same bytes in two test modules.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from inline_snapshot import snapshot

from enbanc import Retrieval, Verdict
from enbanc._ledgering import render_call, render_results
from enbanc._prompting import PROCEDURE

SCHEDULE_C = "s3://underwriting-docs/okonkwo/schedule-c-2024.pdf"
W2 = "s3://underwriting-docs/okonkwo/w2-2024.pdf"


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


def row(
    id: str, tool: str, reference: str, content: str, label: str | None = None
) -> Retrieval[LoanDecision]:
    return Retrieval[LoanDecision](
        id=id,
        round=1,
        advocate=LoanDecision.APPROVE,
        tool=tool,
        reference=reference,
        content=content,
        label=label,
    )


def test_a_tool_returning_sources() -> None:
    assert PROCEDURE == "p1"
    rendered = render_results(
        'find_filings(applicant="A. Okonkwo")',
        [
            row("s1", "find_filings", SCHEDULE_C, "net profit: 182,000", "Schedule C, 2024"),
            row("s2", "find_filings", W2, "wages: 131,400", "W-2, 2024"),
        ],
    )

    assert rendered == snapshot("""\
find_filings(applicant="A. Okonkwo") returned 2 sources.

[s1] Schedule C, 2024
  s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
  net profit: 182,000

[s2] W-2, 2024
  s3://underwriting-docs/okonkwo/w2-2024.pdf
  wages: 131,400\
""")


def test_a_tool_returning_anything_else() -> None:
    """The anonymous source: its reference is the call, and with no label that reference takes
    the first line, so the row is two lines rather than three."""
    assert PROCEDURE == "p1"
    call = 'dti_for(applicant="A. Okonkwo")'
    rendered = render_results(call, [row("s3", "dti_for", call, "dti: 0.51")])

    assert rendered == snapshot("""\
dti_for(applicant="A. Okonkwo") returned 1 source.

[s3] dti_for(applicant="A. Okonkwo")
  dti: 0.51\
""")


def test_a_call_that_found_nothing_is_the_header_alone() -> None:
    """Zero is plural, and there is nothing under it. The count is still a fact about the
    call: an advocate that searched and found nothing is not one that did not search."""
    assert PROCEDURE == "p1"

    assert render_results('find_filings(applicant="Nobody")', []) == snapshot(
        'find_filings(applicant="Nobody") returned 0 sources.'
    )


def test_a_multi_line_retrieval_keeps_its_block_indent() -> None:
    """Content is reproduced exactly, un-truncated, and every line of it takes the indent —
    which is `render_source`'s rule, reached through this caller."""
    assert render_results(
        'psql(query="select 1")',
        [row("s1", "psql", "psql(...)", "one\n\ntwo", "Rows")],
    ) == snapshot("""\
psql(query="select 1") returned 1 source.

[s1] Rows
  psql(...)
  one

  two\
""")


@pytest.mark.parametrize(
    ("tool_args", "expected"),
    [
        ({"applicant": "A. Okonkwo"}, 'find_filings(applicant="A. Okonkwo")'),
        (
            {"applicant": "A. Okonkwo", "year": 2024},
            'find_filings(applicant="A. Okonkwo", year=2024)',
        ),
        ({}, "find_filings()"),
        ({"verified": True, "since": None}, "find_filings(verified=true, since=null)"),
        ({"applicant": "Ana Sánchez"}, 'find_filings(applicant="Ana Sánchez")'),
        ({"limit": 0.5}, "find_filings(limit=0.5)"),
    ],
)
def test_a_call_renders_as_a_reference_a_reviewer_can_re_run(
    tool_args: dict[str, Any], expected: str
) -> None:
    """`json.dumps`, so a string argument is double-quoted and a number is bare — the format
    `evidence.md` fixed. `ensure_ascii=False` keeps a non-ASCII value legible rather than
    escaping it into the record."""
    assert render_call("find_filings", tool_args) == expected


def test_an_argument_json_cannot_serialize_degrades_rather_than_raising() -> None:
    """A tool call must never fail because `enbanc` could not print it."""
    rendered = render_call("filed_after", {"when": datetime(2026, 9, 2, tzinfo=UTC)})

    assert rendered == snapshot(
        'filed_after(when="datetime.datetime(2026, 9, 2, 0, 0, tzinfo=datetime.timezone.utc)")'
    )
