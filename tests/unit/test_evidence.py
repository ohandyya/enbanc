"""What a tool returns, what an advocate emits, and what the tribunal files.

Pins `docs/design/evidence.md` and
`docs/decisions/0016-exhibits-are-stamped-citations.md`. The load-bearing assertion is the
last one: `_Exhibit` holds only the two fields an advocate may author, so a fabricated
reference is not a shape the library can express.
"""

import pytest
from pydantic import ValidationError

from enbanc import Exhibit, Source
from enbanc._evidence import _Exhibit


def test_a_source_is_a_reference_its_content_and_an_optional_label() -> None:
    bare = Source(reference="https://www.irs.gov/about-schedule-c", content="Net profit ...")
    assert bare.label is None

    named = Source(reference="s3://policies/underwriting.pdf", content="...", label="Policy")
    assert named.label == "Policy"


def test_a_reference_is_opaque() -> None:
    """A URL, an object key, a file path, a query — `enbanc` parses none of them."""
    for reference in (
        "https://www.irs.gov/forms-pubs/about-schedule-c-form-1040",
        "s3://underwriting/policy-v3.pdf",
        "./policy.md#L40-L52",
        'psql(sql="SELECT wages FROM w2 WHERE applicant = ...")',
    ):
        assert Source(reference=reference, content="...").reference == reference


def test_an_exhibit_carries_the_advocates_excerpt_beside_the_stamped_citation() -> None:
    exhibit = Exhibit(
        source="s3",
        tool="web_search",
        reference="https://www.irs.gov/forms-pubs/about-schedule-c-form-1040",
        content="Net profit from Schedule C is reportable self-employment income.",
        label="About Schedule C (Form 1040)",
    )
    assert exhibit.source == "s3"
    assert exhibit.label == "About Schedule C (Form 1040)"


def test_an_exhibits_label_is_optional_because_a_source_may_have_had_none() -> None:
    assert Exhibit(source="s1", tool="psql", reference="psql(...)", content="182000").label is None


def test_what_an_advocate_emits_holds_only_what_it_may_author() -> None:
    """The four stamped fields are not on the emit-shape, so they cannot be model-authored.

    This is the whole mechanism: a model is asked only for the id it is citing and the passage
    it relies on, and every field whose correctness the record depends on is filled by the
    tribunal from something it observed.
    """
    assert set(_Exhibit.model_fields) == {"source", "content"}
    assert set(Exhibit.model_fields) - set(_Exhibit.model_fields) == {
        "tool",
        "reference",
        "label",
    }


def test_both_fields_of_the_emit_shape_are_required() -> None:
    with pytest.raises(ValidationError):
        _Exhibit(source="s2")  # type: ignore[call-arg]
