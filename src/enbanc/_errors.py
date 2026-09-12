"""Everything `enbanc` raises.

One hierarchy, in one module, because an error hierarchy a caller catches on is one thing to
import — splitting it across three modules would make `EnbancError`'s subclass list something
you assemble rather than read. It sits *below* `_transcript.py` rather than at the top of the
package: `ProceedingFailed` carries the record it reports on.

See `docs/design/api.md` ("When something goes wrong"),
`docs/design/packaging.md` ("Where the errors live"),
`docs/decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md`, and
`docs/decisions/0012-a-failure-cancels-the-round.md`.
"""

from typing import Generic

from pydantic_ai.usage import RunUsage

from ._transcript import Transcript
from ._verdicts import JUDGE, Participant, VerdictT


class EnbancError(Exception):
    """Base for everything `enbanc` raises. Catch this to catch all of them."""


class ConfigurationError(EnbancError):
    """The tribunal could not be built.

    Raised only from `Tribunal(...)`, in four cases: the `advocates` mapping misses a verdict,
    it names one that does not exist, a verdict's value is the reserved string `"judge"`, or a
    `budget` arrives with its `request_limit` still at `UsageLimits`' own default of `50`.

    **Not a proceeding failure**, and it carries no transcript, because nothing ran. The last
    two cases are the same move: each is a configuration that looks ordinary and means
    something the caller did not write, and each would produce a record that misstates what
    happened. A loud construction error is cheaper than any amount of documentation read
    after the fact.
    """


class ProceedingUnfinished(EnbancError):
    """`Proceeding.hearing` was read before there was one.

    Raised by a proceeding that is still running, or one the caller walked away from by
    breaking out of a `hear_stream()` loop. A proceeding that died raises its own
    `ProceedingFailed` from that property instead, rather than reporting this blander thing.
    """


class ProceedingFailed(EnbancError, Generic[VerdictT]):
    """A participant could not be heard, so the proceeding stopped.

    An unreachable model, an advocate tool that raises, a tool that keeps timing out until its
    retries are spent, and output validation that runs out of retries all surface here, with
    the original error as `__cause__`. **No provider exception reaches you bare**, and
    `enbanc` does not classify them further: PydanticAI and httpx already raise specific
    types, and a second taxonomy over them would be one more thing to keep true.

    **A failure is terminal for the whole proceeding**, even when only one advocate is
    affected. Letting the judge rule on what is left produces a decision reached because the
    opposing advocate was knocked offline rather than answered. Concession is how an advocate
    declines to argue; an outage is not a concession.

    **The record survives.** `transcript` is what had been filed at the moment the round was
    cancelled — not what the round would have contained, since advocates fan out concurrently
    and the first failure cancels the siblings still in flight. Two runs of the same outage
    can leave different numbers of entries behind. It cannot carry a `Hearing`, which is the
    point: an outage is not an adjudication and must not be storable as one.

    **`round` says where it stopped, and there is no `rounds`.** A round completes when its
    deliberation is filed, so failing in round *N* always leaves *N-1* behind it.

    **`usage` is a floor, and `usage_by_participant` names everyone who ran.** Every
    participant that was *dispatched* has a key, and absence means "never dispatched" — a
    judge with no key never deliberated. A participant dispatched into a round cancelled
    before its first request holds a `RunUsage` of zeroes, which reads like "spent nothing"
    and means "got nowhere". The total is a floor rather than an exact bill for a reason no
    accumulator can fix: cancellation is client-side and does not un-bill tokens a provider
    has already generated.

    One consequence of being both generic and an exception, worth knowing because it presents
    as a puzzle: `except ProceedingFailed[LoanDecision]` is a **`TypeError` at runtime** —
    Python matches exceptions on the class, not the parameterization. Catch the bare class
    and read `.participant`, which is typed.
    """

    def __init__(
        self,
        *,
        participant: Participant[VerdictT],
        round: int,  # the record's word for it; `round_` here would read as a typo
        transcript: Transcript[VerdictT],
        usage_by_participant: dict[Participant[VerdictT], RunUsage],
    ) -> None:
        # `str(participant)` rather than the member itself: `repr()` of a StrEnum member is
        # `<LoanDecision.DENY: 'deny'>`, and leaking a Python identifier into a message is the
        # defect ADR 0004 rejects for the transcript.
        who = "the judge" if participant == JUDGE else f"advocate {str(participant)!r}"
        super().__init__(f"{who} could not be heard in round {round}")
        self.participant = participant
        self.round = round
        self.transcript = transcript
        self.usage_by_participant = usage_by_participant

    @property
    def usage(self) -> RunUsage:
        """What had been spent when the proceeding stopped — a floor, not a bill.

        The sum of the breakdown, for the same reason `Hearing.usage` is: there is no second
        place for the two to disagree.
        """
        total = RunUsage()
        for spend in self.usage_by_participant.values():
            total += spend
        return total
