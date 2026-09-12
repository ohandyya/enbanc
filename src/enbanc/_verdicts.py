"""The verdict enum every other type is keyed on, and the participant it is half of.

`Verdict` is the closed set of answers a tribunal may reach. You subclass it and enumerate
the values; the set determines how many advocates exist, and `VerdictT` carries that type
through every filing, the transcript, the outcome, and the hearing.

See `docs/design/api.md` ("Verdicts") and
`docs/decisions/0004-verdicts-are-a-strenum.md`.
"""

from enum import StrEnum
from typing import Final, Literal, TypeVar


class Verdict(StrEnum):
    """The enum of allowed answers. Subclass it and enumerate the values.

    Declares no members, which is exactly what makes it subclassable — Python permits
    extending an `Enum` only while it is empty.

    `StrEnum` rather than `(str, Enum)` because verdict values are interpolated into prompts
    and written into the transcript. Under `StrEnum`, `f"{LoanDecision.APPROVE}"` is
    `'approve'`; under `(str, Enum)` it is `'LoanDecision.APPROVE'`, which leaks a Python
    identifier into the audit artifact silently and reaches the model as noise.

    Nothing carries a separate description of what a verdict *means*, and nothing needs to:
    the member name is the code identity and the **value is what the model reads**. Where a
    bare word would be ambiguous, write the explanation into the value.

        class LoanDecision(Verdict):
            APPROVE = "approve"
            DENY = "deny"
            REFER = "refer to a senior underwriter for manual review"
    """


VerdictT = TypeVar("VerdictT", bound=Verdict)

#: The judge's key wherever participants are enumerated — `Transcript.guidance`,
#: `Hearing.usage_by_participant`, `ProceedingFailed.participant`. It is *reserved*: a verdict
#: whose value is this string would be equal to and hash with it, collapsing that advocate and
#: the judge into one entry of the artifact that exists to attribute spend, so `Tribunal(...)`
#: raises `ConfigurationError` for one. See
#: `docs/decisions/0014-usage-is-broken-down-per-participant.md`.
JUDGE: Final[Literal["judge"]] = "judge"

#: Anyone a proceeding can address: an advocate, named by the verdict it argues for, or the
#: judge. Private — `docs/design/api.md` spells this union inline at every appearance because
#: the name is not exported, not because the code may not use it.
#:
#: A plain alias rather than a `TypeAliasType`, unlike `Filing`, `Deliberation` and `Outcome`.
#: Those need one because Pydantic's `__class_getitem__` returns the origin class for a
#: parameterized generic *model*, so a plain alias over them collapses and loses its
#: parameters. A union of a bare `TypeVar` and a `Literal` holds no such model and does not
#: collapse: `Participant[LoanDecision]` is `Union[LoanDecision, Literal['judge']]`, and it
#: works unchanged as a Pydantic field annotation.
Participant = VerdictT | Literal["judge"]
