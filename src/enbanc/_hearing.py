"""What `hear()` returns, and the two ways a proceeding can end inside its own envelope.

A `Hearing` exists only when the tribunal ran to the end of its own process. When it could
not, `hear()` raises and there is no `Hearing` at all — see `_errors.py`.

See `docs/design/api.md` ("The result", "Usage"),
`docs/decisions/0005-hear-returns-a-hearing.md`,
`docs/decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md`, and
`docs/decisions/0014-usage-is-broken-down-per-participant.md`.
"""

from typing import Annotated, Generic, Literal

from pydantic import BaseModel, Field, computed_field
from pydantic_ai.usage import RunUsage
from typing_extensions import TypeAliasType

from ._filings import Ruling
from ._transcript import Transcript
from ._verdicts import Participant, VerdictT


class Undecided(BaseModel):
    """The proceeding ran out of the envelope it was given without reaching a verdict.

    **It carries one thing: which envelope ran out.** Not the round count, which is
    `Hearing.rounds`; not the questions the judge still wanted answered, which are the
    interrogatories on the last `Continuance` in the transcript. Either would store one fact
    twice.

    `reason` is not that mistake — it is the one fact nothing else carries, and `rounds`
    cannot stand in for it, because a proceeding can spend its budget on the round it would
    have spent its last deliberation. It is undefaulted for the same reason `kind` is
    defaulted: `kind` has exactly one correct value and `reason` has two, so a default would
    be a guess that reads as a fact.

    Not generic, because there is no verdict in it to key on.

    **An `Undecided` is not an entry.** Nobody filed it: the transcript ends on the judge's
    last `Continuance`, and this is the tribunal's own statement that no round followed it.
    """

    kind: Literal["undecided"] = "undecided"
    reason: Literal["rounds", "budget"]


Outcome = TypeAliasType(
    "Outcome",
    Annotated[Ruling[VerdictT] | Undecided, Field(discriminator="kind")],
    type_params=(VerdictT,),
)
"""How the proceeding ended: a `Ruling`, or `Undecided`.

**A union, not an optional.** `Ruling | None` would let a caller reach a verdict without
acknowledging that there might not be one; a discriminated union makes the type checker
insist on the narrowing first. What is *not* in it is failure — if a participant cannot be
heard, `hear()` raises and there is no `Hearing`.

`TypeAliasType` for the same forced reason as `Filing` and `Deliberation`; see
`docs/design/api.md` ("A note on generic aliases").
"""


class Hearing(BaseModel, Generic[VerdictT]):
    """A proceeding that ran to the end of its own process.

    `hear()` returns this, not a widened `Ruling`. The judge's output may only carry what the
    judge knows; the transcript and the usage are the tribunal's. And the two ways a
    proceeding can end have to land somewhere — a widened `Ruling` could express the second
    only as `verdict: V | None`, which re-admits exactly the invalid state the
    `Ruling | Continuance` union exists to rule out.

    **The outcome is the final entry's filing only when it is a `Ruling`.** There the field is
    a pointer, not a copy, so callers do not walk the record backwards to find the terminal
    ruling. Through JSON it is written twice and read back as two equal objects.

    **Every participant appears in `usage_by_participant`.** Round 1 fans out to every
    advocate, so each has an entry even if it conceded immediately, and the judge has one
    because a proceeding that produced a `Hearing` deliberated at least once. No key is a
    zero placeholder. That guarantee is a `Hearing`'s alone — on a `ProceedingFailed`, keys
    can be missing, and absence there means "never dispatched".
    """

    outcome: Outcome[VerdictT]
    transcript: Transcript[VerdictT]
    usage_by_participant: dict[Participant[VerdictT], RunUsage]
    rounds: int

    @computed_field
    @property
    def usage(self) -> RunUsage:
        """What the whole proceeding spent, judge plus advocates.

        **The breakdown is the stored fact and this is its sum.** `RunUsage` adds, so the
        total is computed from the mapping rather than accumulated beside it: there is no
        second place for the two to disagree. It stays on the surface because "what did this
        proceeding cost?" is the common question and should not require a fold.

        Two of its fields are easy to read wrong. Token buckets are **inclusive**, not
        disjoint — `input_tokens` already contains `cache_read_tokens` — and `cost is None`
        means **unpriceable, not free**. Adding `RunUsage`s treats a `None` cost as zero, so a
        total whose parts are mixed reports the sum of the priceable ones and looks like a
        complete figure; the participant with `cost=None` names itself in the breakdown.
        """
        total = RunUsage()
        for spend in self.usage_by_participant.values():
            total += spend
        return total
