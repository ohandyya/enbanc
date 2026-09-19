"""The three things a caller builds, and the four ways building one refuses.

`Judge` and `Advocate` are descriptions — model, tools, guidance — that you construct once and
may share across tribunals. `Tribunal` holds them, the question, the statute, and the limits a
proceeding runs inside. None of the three is in the audit artifact, which is why none of them
is a `BaseModel`: between them they hold a `pydantic_ai.models.Model`, plain async functions,
toolsets, a `UsageLimits` and a concurrency limiter, and none of that serializes.

**`ConfigurationError` is raised here and nowhere else.** A tribunal that cannot be built has
nothing to record and no transcript to carry, so the four checks run at construction and
`hear()` never repeats them. That sentence is only true while a built tribunal cannot be
edited afterwards, which is what the frozen dataclasses and the copies in `__post_init__` are
for.

**This class lands without its main methods.** `hear()` and `hear_stream()` arrive with
`_proceeding.py`; what works today is construction, its refusals, and `instructions_for()`.

See `docs/design/api.md` ("What each piece carries", "The governors"),
`docs/design/execution.md` ("`ConfigurationError` has four cases"),
`docs/design/prompting.md` ("Previewing what an agent will run under"),
`docs/decisions/0003-models-and-guidance-are-injected.md`,
`docs/decisions/0014-usage-is-broken-down-per-participant.md`, and
`docs/decisions/0029-a-budgets-request-limit-must-be-chosen.md`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Generic

from pydantic_ai import AnyConcurrencyLimit
from pydantic_ai.messages import InstructionPart
from pydantic_ai.models import Model
from pydantic_ai.tools import Tool, ToolFuncEither
from pydantic_ai.toolsets import AgentToolset
from pydantic_ai.usage import UsageLimits

from ._errors import ConfigurationError
from ._inputs import Statute
from ._prompting import instruction_parts
from ._verdicts import JUDGE, Participant, Verdict, VerdictT

#: What `UsageLimits` puts in `request_limit` when the caller does not. Read off the dataclass
#: rather than written down as `50`, so the check below tracks the dependency instead of
#: drifting from it — `docs/decisions/0029-a-budgets-request-limit-must-be-chosen.md` names
#: that explicitly, and names the day it matters: if PydanticAI ever defaults this to `None`,
#: the check becomes dead code to remove rather than a check that quietly stops firing.
INHERITED_REQUEST_LIMIT: Final = UsageLimits().request_limit


@dataclass(frozen=True, kw_only=True)
class Judge:
    """The one participant that weighs every advocate, and it has no tools.

    It reasons only over what advocates put into the record, which is what keeps the transcript
    a complete explanation of the ruling. Its output type belongs to the library and is derived
    from your `Verdict` enum — a `Ruling` or a `Continuance`, never free text — so there is
    nothing to configure there.

    `model` overrides the tribunal's, which is what makes a strong judge over cheap advocates a
    one-line change. `guidance` is prose you write, appended to the procedural prompt `enbanc`
    owns and never substituted for it.

    **The set of judge implementations is closed.** This is a concrete class, not a protocol
    you implement: the guarantees that make a transcript auditable are enforceable only while
    `enbanc` owns every judge. See `docs/decisions/0002-the-judge-is-a-role.md`.
    """

    model: Model | None = None
    guidance: str | None = None


@dataclass(frozen=True, kw_only=True)
class Advocate:
    """One seat at the bench, assigned the verdict it is keyed on in `Tribunal.advocates`.

    `tools` and `toolsets` are PydanticAI's, passed through as they are: a tool is a plain
    async function, and `enbanc` defines no tool base class and no tool decorator. They are
    per-advocate on purpose — the advocate for approval may need different evidence sources
    than the advocate for denial, and giving both the same toolbox would flatten a real
    asymmetry.

    **There is no `deps=`.** Credentials, clients and connection pools are closed over by a
    factory, because a closure already does it and inventing a second place to configure the
    same thing is the division `docs/decisions/0009-model-settings-live-on-the-model.md` draws
    for model settings, applied here. That is why the deps type is fixed at `None`.

    `tools` and `toolsets` are copied into tuples at construction, for the reason
    `Tribunal.__post_init__` copies the bench.
    """

    tools: Sequence[Tool[None] | ToolFuncEither[None, ...]] = ()
    toolsets: Sequence[AgentToolset[None]] = ()
    model: Model | None = None
    guidance: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tools", tuple(self.tools))
        object.__setattr__(self, "toolsets", tuple(self.toolsets))


@dataclass(frozen=True, kw_only=True)
class Tribunal(Generic[VerdictT]):
    """One question, one statute, one judge, and one advocate per verdict.

        tribunal = Tribunal(
            question="Shall the bank loan this applicant $500k?",
            verdicts=LoanDecision,
            statute=statute,
            model=AnthropicModel("claude-sonnet-5"),
            judge=Judge(guidance="Where the record is ambiguous, deny."),
            advocates={
                LoanDecision.APPROVE: Advocate(tools=[psql]),
                LoanDecision.DENY: Advocate(tools=[psql]),
            },
            max_rounds=5,
        )

    `verdicts` and the keys of `advocates` both bind the type parameter, so
    `Tribunal[LoanDecision]` is inferred at the call site and a bench keyed by some other enum
    is a type error before it is a `ConfigurationError`.

    **Three limits, and only the first is required.** `max_rounds` counts deliberations and is
    what makes a proceeding terminate at all. `budget` is PydanticAI's `UsageLimits` scoped to
    the whole proceeding rather than to one run, checked between rounds. `max_concurrency`
    bounds how many advocates run at once; the judge is never given a slot.

    **`hear()` and `hear_stream()` do not exist yet.** See `docs/design/api.md` for the surface
    being built toward, and `docs/implementations/` for the order the rest of it arrives in.
    """

    question: str
    verdicts: type[VerdictT]
    statute: Statute
    model: Model
    judge: Judge
    advocates: Mapping[VerdictT, Advocate]
    max_rounds: int
    budget: UsageLimits | None = None
    max_concurrency: AnyConcurrencyLimit = None

    def __post_init__(self) -> None:
        # Copied before it is checked, and read-only after. A frozen dataclass stops
        # `tribunal.advocates = {}` but not `caller_dict[key] = value` on the mapping the
        # caller still holds — and a bench mutated after validation is exactly a
        # `ConfigurationError` surfacing from `hear()` instead, or not at all. A plain dict
        # copy plugs half that hole; half an invariant is harder to reason about than none.
        object.__setattr__(self, "advocates", MappingProxyType(dict(self.advocates)))
        self._check_no_reserved_verdict()
        self._check_the_bench_is_complete()
        self._check_the_budget_was_chosen()

    def _check_no_reserved_verdict(self) -> None:
        """First, because it is a fact about the enum rather than about the mapping.

        An advocate keyed on a `"judge"`-valued member would otherwise be reported as missing
        or unknown below, which describes the symptom and hides the cause.

        `member.value == JUDGE` rather than `JUDGE in self.verdicts`: `EnumType.__contains__`
        raised `TypeError` for a non-member value until Python 3.12, and `requires-python` is
        `>=3.11`. The obvious spelling passes on 3.13 and fails on the floor leg of `ci.yml`
        alone. Reading `.value` also says what the check is actually about — the *value* being
        the reserved string — without knowing which enum base is underneath.
        """
        if any(member.value == JUDGE for member in self.verdicts):
            raise ConfigurationError(
                f"{JUDGE!r} is a reserved verdict value: it would collide with the judge's "
                f"key in usage_by_participant"
            )

    def _check_the_bench_is_complete(self) -> None:
        """Every verdict seated, and nothing seated that is not a verdict.

        Missing is reported before unknown: one mistyped key produces both, and the verdict the
        caller *meant* to seat is the more useful half of that pair. Where two cases apply the
        first one reached is the one raised — `docs/design/outcomes.md` shows one message per
        mistake, and a combined message would need an ordering of its own anyway.

        Both messages have a singular and a plural form, because *missing a verdict: 'a', 'b'*
        makes a reader stop. The singular is the string `outcomes.md` asserts, unchanged.
        """
        seated = set(self.advocates)
        missing = [member for member in self.verdicts if member not in seated]
        if missing:
            listed = ", ".join(repr(str(member)) for member in missing)
            noun = "a verdict" if len(missing) == 1 else "verdicts"
            raise ConfigurationError(f"advocates is missing {noun}: {listed}")

        # Insertion order, there being no enum order to appeal to for a key that is not in
        # the enum.
        unknown = [key for key in self.advocates if key not in set(self.verdicts)]
        if unknown:
            # `str` for a `Verdict` and `repr` for everything else, which is the split
            # `_errors.py` already makes: `repr` of a `StrEnum` member is
            # `<Reserved.JUDGE: 'judge'>`, and leaking a Python identifier into a message is
            # the defect ADR 0004 rejects. A key that is not a verdict at all has no such
            # form to prefer, and `repr` is what distinguishes `'approve!'` from `approve!`.
            listed = ", ".join(
                repr(str(key)) if isinstance(key, Verdict) else repr(key) for key in unknown
            )
            noun = (
                "a key that is not a verdict" if len(unknown) == 1 else "keys that are not verdicts"
            )
            raise ConfigurationError(
                f"advocates names {noun} of {self.verdicts.__name__}: {listed}"
            )

    def _check_the_budget_was_chosen(self) -> None:
        """`UsageLimits` defaults `request_limit` to 50, and that fifty is not the caller's.

        Applied to a whole proceeding rather than to one run it would stop a cheap hearing
        after about five rounds and record `Undecided(reason='budget')` for it — the audit
        artifact stating that the money ran out when it had not.

        The second clause is the guard `0029` asked for without spelling: if PydanticAI ever
        defaults the field to `None`, an unguarded check would start rejecting
        `request_limit=None`, which is the spelling that ADR *recommends*.
        """
        if (
            self.budget is not None
            and INHERITED_REQUEST_LIMIT is not None
            and self.budget.request_limit == INHERITED_REQUEST_LIMIT
        ):
            raise ConfigurationError(
                f"budget.request_limit is {INHERITED_REQUEST_LIMIT}, which is UsageLimits' "
                f"own per-run default rather than a proceeding-wide figure you chose. Pass "
                f"request_limit=None for no cap, or an explicit number."
            )

    def instructions_for(self, participant: Participant[VerdictT]) -> str:
        """The assembled system prompt one participant will run under.

            tribunal.instructions_for(LoanDecision.DENY)
            tribunal.instructions_for("judge")

        `enbanc`'s procedural text, the question, the statute, the assignment, and your
        `guidance` — the same string the agent is built with, parts joined as PydanticAI joins
        them. It takes no case, because a case is not in the instructions, so you can read what
        your guidance did before spending anything on a proceeding.

        The constructor guarantees every verdict is seated, so the only argument that can fail
        is one from outside this tribunal: a member of another enum, or a string that is not
        `"judge"`. Both are type errors statically and both raise `ConfigurationError`.
        """
        if participant == JUDGE:
            guidance = self.judge.guidance
            advocate: Verdict | None = None
        elif isinstance(participant, Verdict) and participant in self.advocates:
            guidance = self.advocates[participant].guidance
            advocate = participant
        else:
            raise ConfigurationError(
                f"this tribunal seats no participant {str(participant)!r}: pass a verdict of "
                f"{self.verdicts.__name__}, or {JUDGE!r}"
            )
        joined = InstructionPart.join(
            instruction_parts(
                question=self.question,
                statute=self.statute,
                verdicts=list(self.verdicts),
                advocate=advocate,
                guidance=guidance,
            )
        )
        if joined is None:  # pragma: no cover
            # `join` narrows an all-empty part list to `None`. Unreachable: `procedural` is
            # always present and never empty.
            raise AssertionError("instruction parts joined to nothing")
        return joined
