"""`Filing`, `Deliberation` and `Outcome` keep their parameters. A plain alias would not.

Pins the note in `docs/design/api.md` ("A note on generic aliases"), which records a
constraint the tooling forces rather than a style preference. The positive assertions are
about `enbanc`'s own aliases; the two negative ones are the tripwire that explains why the
code is written this way, and a failure there means Pydantic moved.

This is a unit test rather than a contract one. `tests/contract/` is scoped to the findings
`docs/design/execution.md` records about `pydantic-ai`
(`docs/decisions/0031-tests-are-tiered.md`), and what this module actually asserts is that
`enbanc`'s aliases parameterize.
"""

from typing import Annotated, Generic, get_args

import pytest
from pydantic import BaseModel, Field
from typing_extensions import TypeAliasType

from enbanc import Argument, Continuance, Deliberation, Filing, Outcome, Ruling, Verdict, VerdictT


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


#: What `Filing = Argument[VerdictT] | Ruling[VerdictT]` silently becomes. At module scope
#: because that is the only place a type alias may be defined — and because module scope is
#: where the library would have written it, had this spelling worked.
COLLAPSED = Annotated[Argument[VerdictT] | Ruling[VerdictT], Field(discriminator="kind")]

#: The same union, declared the way `enbanc` declares its three.
INTACT = TypeAliasType(
    "INTACT",
    Annotated[Argument[VerdictT] | Ruling[VerdictT], Field(discriminator="kind")],
    type_params=(VerdictT,),
)


def test_parameterizing_a_generic_model_with_a_bare_typevar_returns_the_origin() -> None:
    """The fact everything below follows from, and the one a type checker will not catch.

    These two lines are runtime probes of `__class_getitem__`, not annotations — which is
    exactly why a type checker is no help here, and why the note in `api.md` exists.
    """
    assert Argument[VerdictT] is Argument  # type: ignore[misc]
    assert Ruling[VerdictT] is Ruling  # type: ignore[misc]


def test_a_plain_alias_collapses_and_cannot_be_parameterized() -> None:
    """What `Filing = Argument[VerdictT] | Ruling[VerdictT]` would silently become.

    It loses its parameters at definition time and then raises when Pydantic evaluates the
    annotation — only running it surfaces this.
    """
    # The parameters are gone: what was written as `Argument[VerdictT] | Ruling[VerdictT]`
    # is now plain `Argument | Ruling`.
    assert get_args(get_args(COLLAPSED)[0]) == (Argument, Ruling)

    with pytest.raises(TypeError, match="not a generic class"):

        class Broken(BaseModel, Generic[VerdictT]):
            filing: COLLAPSED[VerdictT]  # type: ignore[misc]


def test_the_type_alias_type_form_does_not_collapse() -> None:
    class Works(BaseModel, Generic[VerdictT]):
        filing: INTACT[VerdictT]

    assert isinstance(
        Works[LoanDecision]
        .model_validate({"filing": {"kind": "ruling", "verdict": "deny", "reasoning": "r"}})
        .filing,
        Ruling,
    )


@pytest.mark.parametrize("alias", [Filing, Deliberation, Outcome])
def test_each_exported_alias_is_a_type_alias_type(alias: object) -> None:
    assert isinstance(alias, TypeAliasType)


def test_each_exported_alias_parameterizes_and_binds_the_verdict() -> None:
    """The payoff: `Tribunal(verdicts=LoanDecision)` makes a ruling's verdict a
    `LoanDecision` rather than a `str`, and the type flows all the way through the record."""

    class Bound(BaseModel):
        filing: Filing[LoanDecision]
        deliberation: Deliberation[LoanDecision]
        outcome: Outcome[LoanDecision]

    bound = Bound.model_validate(
        {
            "filing": {"kind": "argument", "advocate": "approve", "claim": "c"},
            "deliberation": {
                "kind": "continuance",
                "interrogatories": [{"id": "r1-q1", "to": "deny", "question": "q"}],
            },
            "outcome": {"kind": "undecided", "reason": "rounds"},
        }
    )
    assert isinstance(bound.filing, Argument)
    assert bound.filing.advocate is LoanDecision.APPROVE
    assert isinstance(bound.deliberation, Continuance)
    assert bound.deliberation.interrogatories[0].to is LoanDecision.DENY
