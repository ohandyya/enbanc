"""`Transcript.render()`: the reviewer's viewpoint, and the whole artifact.

Pins `docs/design/prompting.md` ("`Transcript.render()`") and the part of
`docs/design/api.md` ("The record") that says suppression is found by joining rather than by
a stored flag.

The golden here is versioned for the same reason the prompts are: the reviewer view is part
of the surface `Transcript.procedure` names, because the same renderer feeds the agents.
"""

from typing import Any

from inline_snapshot import snapshot

from enbanc import Case, Statute, Transcript, Verdict
from enbanc._prompting import PROCEDURE, ReviewerView, render


def test_the_whole_artifact(proceeding: Transcript[Any]) -> None:
    assert PROCEDURE == "p1"
    assert proceeding.render() == snapshot("""\
# Proceeding

## The question

Shall the bank loan this applicant $500k?

## The statute — underwriting-v3

Approve $500k loans only where DTI < 0.43 and ...

## The case

{
  "applicant": "A. Okonkwo",
  "income": 182000,
  "dti": 0.51,
  "documents": [
    "w2-2024",
    "schedule-c-2024"
  ]
}

## The bench

Verdicts: approve, deny, refer to a senior underwriter for manual review
Deliberations allowed: 5
Procedure: p1

Guidance given:
  judge: Where the record is ambiguous, deny.
  deny: Weigh documented income over stated income.

## The record

[round 1] approve argued:
  DTI is 0.38 on documented income.
  Exhibits:
    [approve/s1] Schedule C, 2024
      s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
      net profit: 182,000

[round 1] deny argued:
  Documented wages put DTI at 0.51.
  Exhibits:
    [deny/s1] W-2, 2024
      s3://underwriting-docs/okonkwo/w2-2024.pdf
      wages: 131,400

[round 1] refer to a senior underwriter for manual review conceded:
  The ratios are unambiguous; nothing here calls for manual review.

[round 1] the judge issued a continuance:
  r1-q1 -> approve: Does the W-2 reconcile with the Schedule C figure?
  r1-q2 -> deny: Is stated income disqualifying when documented income is on file?
  r1-q3 -> deny: Would a verified 2024 return change your answer?

[round 2] approve responded to r1-q1:
  The Schedule C figure is gross; the W-2 is the reconciled number.
  Exhibits:
    [approve/s2] W-2, 2024
      s3://underwriting-docs/okonkwo/w2-2024.pdf
      wages: 131,400

[round 2] deny responded to r1-q2:
  Yes — the statute's ceiling is on documented income.
  Exhibits:
    [deny/s2] W-2, 2024
      s3://underwriting-docs/okonkwo/w2-2024.pdf
      wages: 131,400

[round 2] deny responded to r1-q3:
  No — a verified return restates the same wages.

[round 2] the judge ruled — deny:
  Documented income governs. The W-2 record puts DTI at 0.51, above the 0.43 ceiling; the stated figure is unverified.

## The ledger

Everything the advocates' tools returned. A retrieval no exhibit cites is one
the record did not rest on.

[approve/s1] Schedule C, 2024 — cited
  s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
  net profit: 182,000

[approve/s2] W-2, 2024 — cited
  s3://underwriting-docs/okonkwo/w2-2024.pdf
  wages: 131,400

[approve/s3] dti_for(applicant="A. Okonkwo") — not cited
  dti: 0.51

[deny/s1] W-2, 2024 — cited
  s3://underwriting-docs/okonkwo/w2-2024.pdf
  wages: 131,400

[deny/s2] W-2, 2024 — cited
  s3://underwriting-docs/okonkwo/w2-2024.pdf
  wages: 131,400

## Failed calls

[round 1] deny — find_filings(applicant="A. Okonkwo")
  Timed out after 30.0 seconds.\
""")


def test_render_is_the_reviewer_viewpoint(proceeding: Transcript[Any]) -> None:
    """`Transcript.render()` is the only public way into the renderer, and it adds nothing."""
    assert proceeding.render() == render(proceeding, ReviewerView())


def test_cited_is_computed_from_the_join(proceeding: Transcript[Any]) -> None:
    """`(advocate, id)`, not a flag — there is deliberately no `cited: bool` on `Retrieval`.

    `approve/s3` is the fixture's buried source: retrieved in round 1, never filed. Every
    other row is cited, including `approve/s2`, which a round-2 response cites — the case a
    stored flag would have had to be rewritten for.
    """
    rendered = proceeding.render()
    assert '[approve/s3] dti_for(applicant="A. Okonkwo") — not cited' in rendered
    assert "[approve/s1] Schedule C, 2024 — cited" in rendered
    assert "[approve/s2] W-2, 2024 — cited" in rendered
    assert rendered.count("— not cited") == 1


def test_a_statute_with_no_name_loses_the_heading_suffix(proceeding: Transcript[Any]) -> None:
    """`Statute.name` is optional and the heading is the only place it renders."""
    anonymous = proceeding.model_copy(update={"statute": Statute(text="Approve only where ...")})
    assert "## The statute\n\nApprove only where ..." in anonymous.render()
    assert "## The statute —" not in anonymous.render()
    assert "## The statute — underwriting-v3" in proceeding.render()


def test_guidance_renders_judge_first_then_in_verdicts_order(
    proceeding: Transcript[Any], deny: Verdict
) -> None:
    """Not in dict order: the same proceeding has to render to the same bytes every time."""
    reversed_insertion = proceeding.model_copy(
        update={
            "guidance": {
                deny: "Weigh documented income over stated income.",
                "judge": "Where the record is ambiguous, deny.",
            }
        }
    )
    block = (
        "Guidance given:\n"
        "  judge: Where the record is ambiguous, deny.\n"
        "  deny: Weigh documented income over stated income."
    )
    assert block in proceeding.render()
    assert block in reversed_insertion.render()


def test_an_unsteered_proceeding_has_no_guidance_block(proceeding: Transcript[Any]) -> None:
    """The heading is a claim that someone was steered. An empty one claims the opposite."""
    unsteered = proceeding.model_copy(update={"guidance": {}}).render()
    assert "Guidance given:" not in unsteered
    assert unsteered.split("## The bench\n\n")[1].startswith("Verdicts: approve, deny,")
    assert "\n\n## The record" in unsteered


def test_an_empty_record_and_an_empty_ledger_say_so(proceeding: Transcript[Any]) -> None:
    """Both are standing halves of the artifact, so nothing-was-filed is a fact it states.

    `entries` says what the ruling rests on and `ledger` says what was available to rest on;
    an absent section would leave *nothing was available* indistinguishable from *this
    renderer does not show a ledger*.
    """
    bare = proceeding.model_copy(update={"entries": [], "ledger": [], "failures": []}).render()
    assert "## The record\n\n(none)" in bare
    assert "the record did not rest on.\n\n(none)" in bare


def test_failed_calls_appears_only_when_something_failed(proceeding: Transcript[Any]) -> None:
    """An exception log, not a standing section. A populated `failures` is not a finding."""
    assert "## Failed calls" in proceeding.render()
    assert '[round 1] deny — find_filings(applicant="A. Okonkwo")' in proceeding.render()
    assert "## Failed calls" not in proceeding.model_copy(update={"failures": []}).render()


def test_a_subclass_case_renders_whole(proceeding: Transcript[Any]) -> None:
    """`SerializeAsAny` on `Transcript.case`, seen from the renderer's end.

    A case renders as `model_dump_json(indent=2)` because `enbanc` reads no field of one. If
    the field serialized by its declared type, every subclass field would vanish from the
    artifact whose whole job is to be complete.
    """
    rendered = proceeding.render()
    assert '"applicant": "A. Okonkwo"' in rendered
    assert '"documents": [\n    "w2-2024",\n    "schedule-c-2024"\n  ]' in rendered
    assert "## The case\n\n{}" in proceeding.model_copy(update={"case": Case()}).render()
