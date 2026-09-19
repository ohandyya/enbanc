"""The four turn templates, over the proceeding `execution.md` and `prompting.md` share.

A turn is the renderer's output plus the template around it. The headings and the closing
instruction belong to the template; the rendered record between them is the projection, and
nothing is added inside it — which is what keeps every agent view a strict subset of the
reviewer's rather than a subset with instructions mixed in
(`docs/decisions/0026-one-renderer-serves-both-audiences.md`).

Goldens, because this text is part of the surface `Transcript.procedure` names. Editing a
template is a procedure bump; see `test_procedural_prompts.py`.

Pins `docs/design/prompting.md` ("The turns").
"""

from typing import Any

from inline_snapshot import snapshot

from enbanc import Case, Continuance, Interrogatory, Transcript, Verdict
from enbanc._prompting import PROCEDURE, argument_turn, deliberation_turn, response_turn


def _snapshot_of(proceeding: Transcript[Any], *entries: int) -> Transcript[Any]:
    """A snapshot holding exactly the 1-indexed entries named, as `execution.md` numbers them.

    `model_copy` rather than a constructor call: a snapshot differs from the transcript only
    in which entries it holds, which is also how the orchestrator will build one.
    """
    kept = [proceeding.entries[n - 1] for n in entries]
    return proceeding.model_copy(update={"entries": kept})


def _question(proceeding: Transcript[Any], n: int) -> Interrogatory[Any]:
    """The nth interrogatory of the round-1 continuance, which is entry 4."""
    continuance = proceeding.entries[3].filing
    assert isinstance(continuance, Continuance)
    return continuance.interrogatories[n - 1]


def test_round_one_advocate(case: Case, deny: Verdict) -> None:
    """The only turn carrying the case, and the only advocate turn with no record in it."""
    assert PROCEDURE == "p1"
    assert argument_turn(case, deny) == snapshot("""\
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

Round 1. File your argument for "deny", or concede.\
""")


def test_round_two_advocate_first_run(proceeding: Transcript[Any], deny: Verdict) -> None:
    """Run 6 of `execution.md`'s table: `since=0`, and the whole of round 1 in the delta.

    The whole continuance is rendered, including the questions put to peers. It is one filing,
    and *targeted* is a duty about who must answer rather than a rule about who may read.
    """
    assert PROCEDURE == "p1"
    assert response_turn(
        _snapshot_of(proceeding, 1, 2, 3, 4),
        advocate=deny,
        since=0,
        round=2,
        interrogatory=_question(proceeding, 2),
    ) == snapshot("""\
## Filed since you last filed

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

## Addressed to you

r1-q2: Is stated income disqualifying when documented income is on file?

Round 2. Answer r1-q2 and file your response.\
""")


def test_round_two_advocate_second_run(proceeding: Transcript[Any], deny: Verdict) -> None:
    """Run 7: the turn is small, and the delta is the advocate's own stamped response alone.

    Its own filing is not carved out. What it emitted was a bare ledger id and an excerpt;
    what entered the record has the tool and the reference stamped beside them, so showing it
    back is showing it something it has not seen.
    """
    assert PROCEDURE == "p1"
    assert response_turn(
        _snapshot_of(proceeding, 1, 2, 3, 4, 6),
        advocate=deny,
        since=1,
        round=2,
        interrogatory=_question(proceeding, 3),
    ) == snapshot("""\
## Filed since you last filed

[round 2] deny responded to r1-q2:
  Yes — the statute's ceiling is on documented income.
  Exhibits:
    [deny/s2] W-2, 2024
      s3://underwriting-docs/okonkwo/w2-2024.pdf
      wages: 131,400

## Addressed to you

r1-q3: Would a verified 2024 return change your answer?

Round 2. Answer r1-q3 and file your response.\
""")


def test_deliberation_one(proceeding: Transcript[Any]) -> None:
    """Run 4: `## Round 1`, and the three round-1 filings that closed it."""
    assert PROCEDURE == "p1"
    assert deliberation_turn(
        _snapshot_of(proceeding, 1, 2, 3), since=0, deliberation=1, max_rounds=5
    ) == snapshot("""\
## Round 1

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

Deliberation 1 of 5. Rule, or issue a continuance.\
""")


def test_deliberation_two(proceeding: Transcript[Any]) -> None:
    """Run 8: `## Filed since you last deliberated`, and only what is new."""
    assert PROCEDURE == "p1"
    assert deliberation_turn(
        _snapshot_of(proceeding, 1, 2, 3, 4, 5, 6, 7), since=1, deliberation=2, max_rounds=5
    ) == snapshot("""\
## Filed since you last deliberated

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

Deliberation 2 of 5. Rule, or issue a continuance.\
""")


def test_the_judge_is_told_the_count_and_never_the_budget(proceeding: Transcript[Any]) -> None:
    """*Deliberation 2 of 5* is two facts the record holds; a budget is not one of them.

    `docs/decisions/0025-the-record-includes-what-steered-it.md` carries the cost: disclosing
    spend would push the judge to rule for reasons the record could never show.
    """
    turn = deliberation_turn(
        _snapshot_of(proceeding, 1, 2, 3), since=0, deliberation=1, max_rounds=5
    )
    assert turn.endswith("Deliberation 1 of 5. Rule, or issue a continuance.")
    for spent in ("budget", "token", "$", "usage", "limit"):
        assert spent not in turn.lower()
