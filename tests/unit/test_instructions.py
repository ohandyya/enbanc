"""What an agent runs under, assembled — the five parts, their order, and the text around them.

`docs/design/testing.md` ("Pinning the prompting surface") makes
`tribunal.instructions_for(participant)` the seam the whole instructions channel is tested
through: synchronous, provider-free, and the same string the agent is built with.

**These goldens pin the assembly, not the procedural prompt.** That text is already pinned
whole by `test_procedural_prompts.py`, and repeating sixty lines of it in four snapshots here
would make one prompt edit show up as the same diff five times in two files. So each golden
anchors the procedural part by identity and snapshots everything after it — which is exactly
the text this PR introduced. A prompt edit fails `test_procedural_prompts.py`; an assembly
reordered fails these; and `PROCEDURE` is asserted in each, because the headings below are
`p1` surface too.

Run `uv run pytest --inline-snapshot=fix` only after the three moves in one commit: the text
in `docs/design/prompting.md`, a new row in its version table, and the constant.
"""

from collections.abc import Callable
from typing import Any

import pytest
from inline_snapshot import snapshot

from enbanc import Advocate, ConfigurationError, Judge, Statute, Tribunal, Verdict
from enbanc._prompting import ADVOCATE_PROCEDURE, JUDGE_PROCEDURE, PROCEDURE, instruction_parts

Kwargs = Callable[[], dict[str, Any]]

#: The steer `docs/design/api.md`'s opening example gives the advocate for denial.
#: `outcomes.md`'s bench leaves every advocate unsteered, so the steered goldens add it here
#: rather than changing the shared fixture for one module's benefit.
DENY_GUIDANCE = "Weigh documented income over stated income."


def after_the_procedural_prompt(instructions: str, procedural: str) -> str:
    """The instructions with their first part removed, having checked it was there.

    One assertion carrying three claims: the procedural part is present, it is *first*, and it
    is joined to what follows by the blank line `InstructionPart.join` uses. What comes back is
    what this module has to say about.
    """
    assert instructions.startswith(procedural + "\n\n")
    return instructions.removeprefix(procedural + "\n\n")


def test_an_advocate_that_was_steered(outcomes_kwargs: Kwargs) -> None:
    kwargs = outcomes_kwargs()
    deny = [verdict for verdict in kwargs["verdicts"] if verdict.value == "deny"][0]
    kwargs["advocates"][deny] = Advocate(guidance=DENY_GUIDANCE)
    tribunal = Tribunal(**kwargs)

    assert PROCEDURE == "p1"
    assert after_the_procedural_prompt(
        tribunal.instructions_for(deny), ADVOCATE_PROCEDURE
    ) == snapshot("""\
## The question

Shall the bank loan this applicant $500k?

## The statute — underwriting-v3

Approve $500k loans only where DTI < 0.43 and ...

## Your assignment

The verdicts this question may be answered with:
  approve
  deny
  refer to a senior underwriter for manual review

You are the advocate for "deny".

## Guidance from the author of this proceeding

Weigh documented income over stated income.\
""")


def test_an_advocate_that_was_not(outcomes_kwargs: Kwargs) -> None:
    """No `## Guidance` heading at all. A heading over nothing would be a claim that someone
    was steered, made in the same words as the claim that they were."""
    tribunal = Tribunal(**outcomes_kwargs())
    approve = next(iter(tribunal.advocates))

    assert PROCEDURE == "p1"
    assert after_the_procedural_prompt(
        tribunal.instructions_for(approve), ADVOCATE_PROCEDURE
    ) == snapshot("""\
## The question

Shall the bank loan this applicant $500k?

## The statute — underwriting-v3

Approve $500k loans only where DTI < 0.43 and ...

## Your assignment

The verdicts this question may be answered with:
  approve
  deny
  refer to a senior underwriter for manual review

You are the advocate for "approve".\
""")


def test_the_judge(outcomes_kwargs: Kwargs) -> None:
    """No `## Your assignment`. The judge is seated for no verdict, and it learns the set from
    the output schema — `Ruling.verdict` is the enum, so PydanticAI puts the values there."""
    tribunal = Tribunal(**outcomes_kwargs())

    assert PROCEDURE == "p1"
    assert after_the_procedural_prompt(
        tribunal.instructions_for("judge"), JUDGE_PROCEDURE
    ) == snapshot("""\
## The question

Shall the bank loan this applicant $500k?

## The statute — underwriting-v3

Approve $500k loans only where DTI < 0.43 and ...

## Guidance from the author of this proceeding

Where the record is ambiguous, deny.\
""")


def test_a_judge_that_was_not_steered(outcomes_kwargs: Kwargs) -> None:
    kwargs = outcomes_kwargs()
    kwargs["judge"] = Judge()
    tribunal = Tribunal(**kwargs)

    assert PROCEDURE == "p1"
    assert after_the_procedural_prompt(
        tribunal.instructions_for("judge"), JUDGE_PROCEDURE
    ) == snapshot("""\
## The question

Shall the bank loan this applicant $500k?

## The statute — underwriting-v3

Approve $500k loans only where DTI < 0.43 and ...\
""")


def test_an_unnamed_statute_loses_the_suffix(outcomes_kwargs: Kwargs) -> None:
    """`statute_heading()` has two callers now — this one and the reviewer render's header —
    and `test_transcript_render.py` only covers the other."""
    kwargs = outcomes_kwargs()
    kwargs["statute"] = Statute(text="Approve $500k loans only where DTI < 0.43 and ...")
    tribunal = Tribunal(**kwargs)

    assert "## The statute\n\nApprove $500k" in tribunal.instructions_for("judge")


@pytest.mark.parametrize(
    ("advocate", "guidance", "expected"),
    [
        pytest.param(
            True,
            "steer",
            ["procedural", "question", "statute", "assignment", "guidance"],
            id="advocate-steered",
        ),
        pytest.param(
            True,
            None,
            ["procedural", "question", "statute", "assignment"],
            id="advocate-unsteered",
        ),
        pytest.param(
            False, "steer", ["procedural", "question", "statute", "guidance"], id="judge-steered"
        ),
        pytest.param(False, None, ["procedural", "question", "statute"], id="judge-unsteered"),
    ],
)
def test_the_parts_and_their_order(
    advocate: bool, guidance: str | None, expected: list[str], deny: Verdict
) -> None:
    """Five, four, four, three — the four shapes
    `docs/design/execution.md` ("The proceeding, as messages") reports from the wire."""
    parts = instruction_parts(
        question="q",
        statute=Statute(text="s"),
        verdicts=[deny],
        advocate=deny if advocate else None,
        guidance=guidance,
    )
    assert [part.name for part in parts] == expected


def test_every_part_is_static(deny: Verdict) -> None:
    """`dynamic=False` is what lets a provider cache the prefix. It is the field's default and
    this is what makes relying on the default a decision rather than an oversight."""
    parts = instruction_parts(
        question="q", statute=Statute(text="s"), verdicts=[deny], advocate=deny, guidance="g"
    )
    assert [part.dynamic for part in parts] == [False] * 5


def test_no_part_name_is_one_pydantic_ai_rejects(deny: Verdict) -> None:
    """A name may not contain `:` — the instruction-id delimiter — and may not be `agent`,
    which is the key of the agent's own instructions. Neither is reachable by accident today;
    this is what would say so if a part were renamed."""
    parts = instruction_parts(
        question="q", statute=Statute(text="s"), verdicts=[deny], advocate=deny, guidance="g"
    )
    for part in parts:
        assert part.name is not None
        assert ":" not in part.name
        assert part.name != "agent"


def test_the_shared_block_is_byte_identical_across_advocates(outcomes_kwargs: Kwargs) -> None:
    """The claim that justifies the part order: the first three parts are the same bytes for
    every advocate in a tribunal, so the round-1 fan-out shares a cache prefix and only the
    assignment and the guidance differ. A cache prefix is a prefix — that is the whole reason
    the shared block comes first."""
    kwargs = outcomes_kwargs()
    tribunal = Tribunal(**kwargs)
    bench = list(tribunal.advocates)
    assert len(bench) == 3

    shared = [
        [
            part.content
            for part in instruction_parts(
                question=tribunal.question,
                statute=tribunal.statute,
                verdicts=bench,
                advocate=advocate,
                guidance=tribunal.advocates[advocate].guidance,
            )[:3]
        ]
        for advocate in bench
    ]
    assert shared[0] == shared[1] == shared[2]

    # And the parts after it do not collapse with them — otherwise the assertion above would
    # hold over a tribunal whose advocates were indistinguishable, which is not the claim.
    assignments = [tribunal.instructions_for(advocate) for advocate in bench]
    assert len(set(assignments)) == 3


def test_a_participant_this_tribunal_does_not_seat(outcomes_kwargs: Kwargs) -> None:
    """The constructor guarantees every verdict is seated, so the only argument that can fail
    is one from outside this tribunal."""
    tribunal = Tribunal(**outcomes_kwargs())

    class Escalation(Verdict):
        HANDLE = "handle"

    with pytest.raises(ConfigurationError) as excinfo:
        tribunal.instructions_for(Escalation.HANDLE)  # pyright: ignore[reportArgumentType]
    assert str(excinfo.value) == snapshot(
        "this tribunal seats no participant 'handle': pass a verdict of LoanDecision, or 'judge'"
    )

    with pytest.raises(ConfigurationError):
        tribunal.instructions_for("bench")  # pyright: ignore[reportArgumentType]
