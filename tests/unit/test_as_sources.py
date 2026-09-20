"""The shape-sniff: what a tool returned, as the sources it is ledgered as.

Pins `docs/design/evidence.md` ("How a source becomes an exhibit"). A `Source`, or a sequence
of them, is taken as written; anything else becomes one anonymous source whose reference is
the call itself. That branch is what keeps every existing PydanticAI tool and every MCP server
usable with no adaptation — returning `Source` is an upgrade, not an entry fee.

No model and no agent here: `as_sources` is a pure function over a value.
"""

from typing import Any

import pytest
from pydantic import BaseModel

from enbanc import Source
from enbanc._ledgering import as_sources

CALL = 'dti_for(applicant="A. Okonkwo")'

SCHEDULE_C = Source(
    reference="s3://underwriting-docs/okonkwo/schedule-c-2024.pdf",
    label="Schedule C, 2024",
    content="net profit: 182,000",
)
W2 = Source(
    reference="s3://underwriting-docs/okonkwo/w2-2024.pdf",
    label="W-2, 2024",
    content="wages: 131,400",
)


class Cited(Source):
    """A caller's own subclass. `isinstance` is the test, so this is a `Source`."""

    weight: float = 1.0


class Ratio(BaseModel):
    dti: float


@pytest.mark.parametrize(
    ("returned", "expected"),
    [
        (SCHEDULE_C, [SCHEDULE_C]),
        ([SCHEDULE_C, W2], [SCHEDULE_C, W2]),
        ((SCHEDULE_C, W2), [SCHEDULE_C, W2]),
        (Cited(reference="r", content="c"), [Cited(reference="r", content="c")]),
        ([], []),
    ],
)
def test_a_source_or_a_sequence_of_them_is_taken_as_written(
    returned: Any, expected: list[Source]
) -> None:
    assert as_sources(returned, fallback_reference=CALL) == expected


@pytest.mark.parametrize(
    ("returned", "content"),
    [
        ("dti: 0.51", "dti: 0.51"),
        ({"dti": 0.51}, "{'dti': 0.51}"),
        (Ratio(dti=0.51), "dti=0.51"),
        (None, "None"),
        (0.51, "0.51"),
        (["a", "b"], "['a', 'b']"),
        ([SCHEDULE_C, "a stray string"], f"[{SCHEDULE_C!r}, 'a stray string']"),
        (b"bytes", "b'bytes'"),
        ("", ""),
    ],
)
def test_anything_else_is_one_anonymous_source_referencing_the_call(
    returned: Any, content: str
) -> None:
    """The reference is the call, which is reproducible and — for a database or an internal
    API — genuinely is the locator, because there is no URL to point at.

    The mixed list is the case worth staring at: ledgering the `Source` in it and dropping the
    string would put half a tool result in the record under its own id and the other half
    nowhere. All or nothing.
    """
    assert as_sources(returned, fallback_reference=CALL) == [
        Source(reference=CALL, content=content, label=None)
    ]


def test_an_empty_string_is_not_an_empty_sequence_of_sources() -> None:
    """A `str` is a `Sequence`, and `all(...)` over an empty one is vacuously true. Excluding
    `str` and `bytes` explicitly is what keeps `""` from being ledgered as nothing at all."""
    assert as_sources("", fallback_reference=CALL) != []
