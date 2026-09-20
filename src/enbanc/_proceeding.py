"""One proceeding, running: the agents, the fan-out, the filing clerk, and the live handle.

`execution.md`'s piece 3, up to a single round and one deliberation. Everything here is built
when a proceeding starts and discarded when it ends — one `Agent` per participant, one
`Ledgering` per advocate, one `RunUsage` per participant, the history dict and the `since`
dict. That split is what makes `hear()` safe to call twice and safe to run concurrently over
several cases: a `Judge` or an `Advocate` is a description the caller may share, and none of
the state below is on it.

**This module takes the pieces, not the `Tribunal`.** `_tribunal` imports `_proceeding` and
never the reverse, so the loop is constructible from a test without building a `Tribunal`
first. `Judge` and `Advocate` are imported for annotations only, which is the second
annotation-only break in an otherwise one-directional import graph and is safe for the same
reason the renderer's is: nothing here constructs either type or dispatches on it — the
orchestrator reads `.model`, `.guidance`, `.tools` and `.toolsets`, and that is all.

**The citation check rides on the output type, not on the agent.** PydanticAI refuses a
run-level `output_type` once an agent carries an output validator, and an advocate's output
shape varies by round — so `check_citations` is called from an output function instead. The
tool name, description and JSON schema a model sees are derived from the function's single
*parameter*, so nothing about the wire changes; see `docs/design/execution.md` ("An output
validator forbids a per-run `output_type`"). Those functions carry **no docstring**, because
a docstring on one becomes the output tool's description — text a model reads, which
`docs/design/prompting.md` would then have to own.

See `docs/design/execution.md` ("Piece 3 — round orchestration"),
`docs/design/api.md` ("Watching it live"),
`docs/decisions/0010-streaming-yields-the-record.md`,
`docs/decisions/0016-exhibits-are-stamped-citations.md`, and
`docs/decisions/0028-usage-accumulates-per-participant.md`.
"""

from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, Generic, TypeVar

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel
from pydantic_ai import Agent, AgentRetries, AnyConcurrencyLimit
from pydantic_ai.concurrency import AbstractConcurrencyLimiter, normalize_to_limiter
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from pydantic_ai.toolsets import AbstractToolset, CombinedToolset, DynamicToolset, FunctionToolset
from pydantic_ai.usage import RunUsage, UsageLimits
from typing_extensions import TypeAliasType

from ._errors import ProceedingUnfinished
from ._evidence import Exhibit, _Exhibit
from ._filings import Argument, Concession, Filing, Ruling, _Argument, _Continuance
from ._hearing import Hearing
from ._inputs import Case, Statute
from ._ledgering import Ledgering
from ._prompting import PROCEDURE, argument_turn, deliberation_turn, instruction_parts
from ._transcript import Entry, Transcript
from ._verdicts import JUDGE, Participant, VerdictT

if TYPE_CHECKING:
    # Annotation-only, and the second break in the package's import graph — see the module
    # docstring and `docs/design/packaging.md` ("What imports what"). `_tribunal` imports this
    # module for real, so this direction is the one that must not run at import time. It stays
    # annotation-only because nothing here constructs a `Judge` or an `Advocate`, and nothing
    # dispatches on either type.
    from ._tribunal import Advocate, Judge

#: The two retry budgets `enbanc` sets on every agent it builds, and they are independent:
#: `tools` absorbs a timed-out tool and is counted per tool name, `output` guards the
#: `Ruling | Continuance` contract and an exhibit's citation. Neither is configurable through
#: `enbanc` — the `tools` half is overridable per tool with `Tool(fn, max_retries=...)`, where
#: `docs/decisions/0020-tool-timeouts-ride-on-the-tool.md` already put the timeout. See
#: `docs/decisions/0030-the-retry-budgets.md`.
RETRIES: Final[AgentRetries] = {"tools": 3, "output": 2}

#: One filing shape an agent may emit, for the output-function helper below. Bound to
#: `BaseModel` rather than to a filing union, because what the helper needs is only that
#: PydanticAI can derive a schema from it.
_FilingT = TypeVar("_FilingT", bound=BaseModel)

_Emitted = TypeAliasType(
    "_Emitted",
    _Argument[VerdictT] | Concession[VerdictT] | Ruling[VerdictT],
    type_params=(VerdictT,),
)
"""What a participant may emit today — the private shapes beside the public ones.

`_Response` and `_Continuance` join it with the dispatch that produces them
(`docs/implementations/round-loop.md`). It is local to this module because nothing outside
the orchestrator ever holds a filing before the clerk has converted it, and it is a
`TypeAliasType` for the reason `Filing` is: a plain alias over Pydantic generics
parameterized by a bare `TypeVar` collapses and loses its parameters.
"""


def _filing_output(
    filing_type: type[_FilingT], check: Callable[[_FilingT], None]
) -> Callable[[_FilingT], _FilingT]:
    """An output function over one filing type, carrying the check it may retry on.

    PydanticAI takes an output function's tool name, description and JSON schema from its
    single **parameter**, so this is indistinguishable on the wire from handing `filing_type`
    over as the output type directly — and it is what lets the check ride on the output type
    rather than on the agent, which is what keeps a per-run `output_type` legal.

    Two things about it are load-bearing and neither is guessable:

    * **The annotation is assigned rather than written.** A literal `_Argument[VerdictT]`
      annotation is evaluated at runtime and collapses to the origin class, because Pydantic
      returns it for a bare `TypeVar` — and an unparameterized filing puts `enum: []` in the
      schema, so no verdict the caller declared is a valid answer and every run exhausts the
      output budget. The caller resolves `filing_type` from the tribunal's own enum, and this
      is how that reaches the schema.
    * **There is no docstring on the inner function.** PydanticAI uses one as the output
      tool's *description*, which would be prompt text `docs/design/prompting.md` does not own
      and `Transcript.procedure` would not version. Without one the model reads PydanticAI's
      own generic sentence, exactly as it would for a bare model output type.
    """

    def file(filing: _FilingT) -> _FilingT:
        check(filing)
        return filing

    file.__annotations__ = {"filing": filing_type, "return": filing_type}
    return file


@dataclass(slots=True)
class _Filed(Generic[VerdictT]):
    """One filing on its way to the clerk, and the acknowledgment coming back.

    `done` is what makes an advocate's next run wait for the record to hold its last one —
    `docs/decisions/0027-an-advocate-answers-its-interrogatories-in-order.md` needs it
    independently of the clerk's ordering promise. `entry` is the stamped result, written
    before `done` is set: the task that filed needs the *public* entry for its own snapshot
    extension, and reading `transcript.entries[-1]` after the wait would be a race a
    concurrent sibling wins.

    `round` shadows the builtin deliberately. It is `Entry.round`'s word for the thing, the
    builtin is not used in this module, and renaming it would make the field say something
    other than what the record says.
    """

    filing: _Emitted[VerdictT]
    round: int
    done: anyio.Event
    entry: Entry[VerdictT] | None = None


class Proceeding(Generic[VerdictT]):
    """The live handle: the record as it is written, and the hearing once there is one.

        async with tribunal.hear_stream(case) as proceeding:
            async for entry in proceeding:
                print(f"round {entry.round}: {entry.filing.kind}")

        hearing = proceeding.hearing

    **What it yields is the record.** Each value is the `Entry` appended to the transcript at
    that moment — the same object, in filing order, and nothing else. There are no lifecycle
    events, no partial filings, and no token deltas: a viewer that saw something the
    transcript does not contain would be watching a second channel
    (`docs/decisions/0010-streaming-yields-the-record.md`).

    **A handle, not a record**, which is why it is not a `BaseModel`. It holds no fact of its
    own — `transcript` and `hearing` are views of things that exist anyway — it is never
    serialized, and it never appears on a result.

    **Abandoning is allowed.** Break out of the loop and the block exits: the in-flight runs
    are cancelled, `transcript` holds everything filed up to that point, and `hearing` raises
    `ProceedingUnfinished`.
    """

    def __init__(
        self,
        orchestrator: "_Orchestrator[VerdictT]",
        entries: MemoryObjectReceiveStream[Entry[VerdictT]],
    ) -> None:
        self._orchestrator = orchestrator
        self._entries = entries
        #: The same object the orchestrator appends to, not a copy: the entry just yielded is
        #: its last.
        self.transcript = orchestrator.transcript

    def __aiter__(self) -> AsyncIterator[Entry[VerdictT]]:
        return self._entries.__aiter__()

    @property
    def hearing(self) -> Hearing[VerdictT]:
        """The `Hearing` `hear()` would have returned, or `ProceedingUnfinished`.

        Raised by a proceeding that is still running, and by one the caller walked away from.
        A proceeding that *died* re-raises its own `ProceedingFailed` from here instead —
        that half arrives with `docs/implementations/failures.md`.
        """
        hearing = self._orchestrator.hearing
        if hearing is None:
            raise ProceedingUnfinished(
                "this proceeding has not produced a hearing: it is still running, or the "
                "caller stopped consuming it"
            )
        return hearing


@dataclass(kw_only=True)
class _Orchestrator(Generic[VerdictT]):
    """Everything one proceeding owns, and the loop that spends it.

    Constructed by `proceed()` from the pieces a `Tribunal` holds. The four dicts below are
    `execution.md`'s piece 1 — the history, the `since` cursor, the usage accumulators, and
    the per-advocate ledgering toolsets — and all four are discarded with this object.
    """

    question: str
    statute: Statute
    case: Case
    #: The enum *class*, as `Tribunal` holds it — not a list of members. The output types
    #: below are parameterized with it at runtime, and that is what puts the verdict values in
    #: the JSON schema a model reads (see `_filing_output`).
    verdicts: type[VerdictT]
    judge: "Judge"
    advocates: Mapping[VerdictT, "Advocate"]
    model: Model
    max_rounds: int
    #: Held and not read until the budget check, which arrives with the round loop
    #: (`docs/implementations/round-loop.md`). A proceeding that runs one round and rules
    #: spends nothing it could be stopped for: there is no boundary to check at.
    budget: UsageLimits | None = None
    max_concurrency: AnyConcurrencyLimit = None

    transcript: Transcript[VerdictT] = field(init=False)
    history: dict[Participant[VerdictT], list[ModelMessage]] = field(
        init=False, default_factory=dict
    )
    since: dict[Participant[VerdictT], int] = field(init=False, default_factory=dict)
    usage_by_participant: dict[Participant[VerdictT], RunUsage] = field(
        init=False, default_factory=dict
    )
    ledgerings: dict[VerdictT, Ledgering[VerdictT]] = field(init=False, default_factory=dict)
    advocate_agents: dict[VerdictT, Agent[None, "_Argument[VerdictT] | Concession[VerdictT]"]] = (
        field(init=False, default_factory=dict)
    )
    judge_agent: Agent[None, "Ruling[VerdictT] | _Continuance[VerdictT]"] = field(init=False)
    #: Normalized once and handed to every advocate agent, so the fan-out shares one budget of
    #: slots. `None` when the caller set no ceiling.
    limiter: AbstractConcurrencyLimiter | None = field(init=False, default=None)
    hearing: Hearing[VerdictT] | None = field(init=False, default=None)
    rounds: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        # The transcript first, and the toolsets after it. Pydantic *copies* a list field at
        # construction, so a `Ledgering` handed a list that is later passed to
        # `Transcript(ledger=...)` writes into an orphan and the record comes back empty from
        # a proceeding that retrieved plenty — with nothing raising. Passing
        # `transcript.ledger` is the one spelling that satisfies `0016`'s ownership
        # constraint, and this order is what makes it available.
        self.transcript = Transcript[VerdictT](
            question=self.question,
            statute=self.statute,
            case=self.case,
            verdicts=list(self.verdicts),
            max_rounds=self.max_rounds,
            guidance=self._guidance(),
            procedure=PROCEDURE,
        )
        # Normalized once and shared by every advocate agent. `max_concurrency` is an
        # `Agent.__init__` parameter rather than a `run()` argument, so the alternative would
        # be one limiter per advocate — which is no limit at all across the fan-out. The judge
        # is never given one: it runs alone.
        self.limiter = normalize_to_limiter(self.max_concurrency)
        self.since = dict.fromkeys(self._participants(), 0)
        for verdict, advocate in self.advocates.items():
            self.ledgerings[verdict] = self._ledgering(verdict, advocate)
            self.advocate_agents[verdict] = self._advocate_agent(verdict, advocate)
        self.judge_agent = self._judge_agent()

    def _participants(self) -> list[Participant[VerdictT]]:
        """The judge first, then the bench in declaration order."""
        return [JUDGE, *self.advocates]

    def _guidance(self) -> dict[Participant[VerdictT], str]:
        """Who was steered, keyed on `guidance is not None`.

        The same predicate `instruction_parts` emits the guidance part on, so the record and
        the prompt agree about who was steered and an `Advocate(guidance="")` is recorded as
        steered because it was. See
        `docs/decisions/0025-the-record-includes-what-steered-it.md`.
        """
        steered: dict[Participant[VerdictT], str] = {}
        if self.judge.guidance is not None:
            steered[JUDGE] = self.judge.guidance
        for verdict, advocate in self.advocates.items():
            if advocate.guidance is not None:
                steered[verdict] = advocate.guidance
        return steered

    def _ledgering(self, verdict: VerdictT, advocate: "Advocate") -> Ledgering[VerdictT]:
        """One wrapper over one combined toolset, per advocate, living the whole proceeding.

        Routing everything through one wrapper is what makes *intercepts every call* true of
        an MCP server as well as of a plain function. A toolset may also be the **callable**
        form PydanticAI accepts — a function resolved per run — and handing one straight to
        the agent would put its calls outside the wrapper, so it is wrapped in the
        `DynamicToolset` the agent would have wrapped it in itself.
        """
        return Ledgering[VerdictT](
            wrapped=CombinedToolset[None](
                [
                    FunctionToolset[None](tools=advocate.tools),
                    *(
                        toolset
                        if isinstance(toolset, AbstractToolset)
                        else DynamicToolset[None](toolset_func=toolset)
                        for toolset in advocate.toolsets
                    ),
                ]
            ),
            advocate=verdict,
            ledger=self.transcript.ledger,
            failures=self.transcript.failures,
        )

    def _advocate_agent(
        self, verdict: VerdictT, advocate: "Advocate"
    ) -> Agent[None, "_Argument[VerdictT] | Concession[VerdictT]"]:
        """The advocate's agent, carrying its citation check on its output type.

        **Round 1's shape only** — an argument, or a concession. The response shape is a
        per-run `output_type` on this same agent, which is exactly what the output function
        keeps legal (`docs/implementations/round-loop.md`).

        **Both output types are parameterized from the tribunal's own enum.** `Concession` is
        subscripted with `self.verdicts` rather than with `VerdictT` for the reason
        `_filing_output` gives: a bare `TypeVar` collapses to the origin class, and the
        advocate would be shown `enum: []` where its own verdict should be.
        """
        ledgering = self.ledgerings[verdict]

        return Agent(
            advocate.model or self.model,
            output_type=[
                _filing_output(_Argument[self.verdicts], ledgering.check_citations),
                Concession[self.verdicts],
            ],
            instructions=instruction_parts(
                question=self.question,
                statute=self.statute,
                verdicts=list(self.verdicts),
                advocate=verdict,
                guidance=advocate.guidance,
            ),
            toolsets=[ledgering],
            # Forced: `Agent.__init__` declares `deps_type: type[AgentDepsT] = object` while
            # also solving `AgentDepsT` from `toolsets`, so a toolset typed
            # `AbstractToolset[None]` against that default is a type error about a value
            # neither call site wrote. The judge carries it too, so both read the same way.
            deps_type=type(None),
            retries=RETRIES,
            max_concurrency=self.limiter,
        )

    def _judge_agent(self) -> Agent[None, "Ruling[VerdictT] | _Continuance[VerdictT]"]:
        """The judge's agent: no tools, no toolsets, no concurrency slot.

        `advocate=None` is how `instruction_parts` spells *seated for no verdict* — the judge
        gets no assignment part, and learns the verdict set from `Ruling.verdict`'s own JSON
        schema. Its output pair is public `Ruling` and private `_Continuance`, because a
        continuance's ids are stamped by the tribunal and are not the judge's to write.
        """
        return Agent(
            self.judge.model or self.model,
            output_type=[Ruling[self.verdicts], _Continuance[self.verdicts]],
            instructions=instruction_parts(
                question=self.question,
                statute=self.statute,
                verdicts=list(self.verdicts),
                advocate=None,
                guidance=self.judge.guidance,
            ),
            deps_type=type(None),
            retries=RETRIES,
        )

    def _usage(self, participant: Participant[VerdictT]) -> RunUsage:
        """This participant's accumulator, minted the first time it is dispatched.

        Minted at dispatch rather than up front, because **absence means never dispatched**
        (`docs/design/api.md`) — a pre-populated dict would put a judge row of zeroes on a
        `ProceedingFailed` from round 1 and make that absence unreadable. The object is the
        proceeding's from then on and is mutated in place by every run the participant makes,
        so a run that dies or is cancelled still leaves what it spent
        (`docs/decisions/0028-usage-accumulates-per-participant.md`).
        """
        return self.usage_by_participant.setdefault(participant, RunUsage())

    def _snapshot(self) -> Transcript[VerdictT]:
        """The record as it stands, frozen for one turn's rendering.

        A `Transcript` rather than a list, because `render()` takes one type; a
        `model_copy(update=...)` rather than a validated rebuild, because the copy differs
        from the transcript only in which entries it holds. `since` selects *which rounds*
        render; the snapshot decides *which filings of those rounds exist to select from*.
        """
        return self.transcript.model_copy(update={"entries": list(self.transcript.entries)})

    async def run(self, out: MemoryObjectSendStream[Entry[VerdictT]]) -> None:
        """One proceeding, start to finish: the clerk, round 1, and the deliberation.

        The clerk runs for as long as the inbox is open, so closing the send end is what ends
        it — and the task group below is what makes the two lifetimes one. `out` is closed
        **after** the hearing is bound, which is what lets a consumer read
        `proceeding.hearing` the moment its `async for` ends.
        """
        inbox_send, inbox_receive = anyio.create_memory_object_stream[_Filed[VerdictT]](0)
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._clerk, inbox_receive, out)
            async with inbox_send:
                await self._round(1, inbox_send)
                outcome = await self._deliberate(1, inbox_send)
                # Bound here rather than after the group, because `_deliberate` returns only
                # once the clerk has appended *and* delivered the ruling — so the record is
                # complete at this line, and a consumer that reads `proceeding.hearing` the
                # moment its iteration ends finds one.
                self.hearing = Hearing[VerdictT](
                    outcome=outcome,
                    transcript=self.transcript,
                    usage_by_participant=self.usage_by_participant,
                    rounds=self.rounds,
                )
        await out.aclose()

    async def _clerk(
        self,
        inbox: MemoryObjectReceiveStream[_Filed[VerdictT]],
        out: MemoryObjectSendStream[Entry[VerdictT]],
    ) -> None:
        """One coroutine owns the transcript. Everything else asks it to file.

        This exists to make one sentence true by construction:
        `docs/decisions/0010-streaming-yields-the-record.md` promises that *the entry just
        received is the last entry of `proceeding.transcript`*. If each task appended and then
        sent, a sibling could append between the two and a consumer would receive entry 5
        while `transcript[-1]` was entry 6 — the live view and the record disagreeing about a
        proceeding whose whole product is that they do not. With a single owner there is no
        interleaving to reason about: appending, sending and acknowledging are one
        uninterrupted sequence in one task.

        **Both private-to-public conversions happen here**, at the filing seam, because every
        field whose correctness the record depends on is filled by the tribunal at the moment
        a filing enters the record — the same principle as the `Entry` envelope around it.
        """
        async with inbox:
            async for filed in inbox:
                entry = Entry[VerdictT](
                    round=filed.round,
                    filed_at=datetime.now(UTC),
                    filing=self._public(filed.filing),
                )
                self.transcript.entries.append(entry)
                await out.send(entry)
                filed.entry = entry
                filed.done.set()

    def _public(self, filing: _Emitted[VerdictT]) -> Filing[VerdictT]:
        """The filing as it enters the record.

        A `Concession` and a `Ruling` carry nothing stamped and pass through as themselves —
        which is also why neither has a private counterpart. An `_Argument`'s exhibits are
        bare ids and excerpts, and become public `Exhibit`s resolved against the ledger.
        """
        if isinstance(filing, _Argument):
            return Argument[VerdictT](
                advocate=filing.advocate,
                claim=filing.claim,
                exhibits=self._stamp(filing.advocate, filing.exhibits),
            )
        return filing

    def _stamp(self, advocate: VerdictT, exhibits: Sequence[_Exhibit]) -> list[Exhibit]:
        """Resolve each cited id against the ledger, and stamp what the advocate cannot write.

        The join key is `(advocate, id)` — ids are numbered within an advocate, so `APPROVE`'s
        `s1` and `DENY`'s `s1` are different retrievals — and the advocate comes from the
        enclosing filing, never from the exhibit. `content` stays the advocate's excerpt while
        `tool`, `reference` and `label` come from the row: the two contents are different
        facts about one source, and reading them side by side is how a misquote is caught.

        **A miss is an `AssertionError`.** By the time a filing reaches the clerk the output
        function has already rejected every id this advocate was not issued, so an
        unresolvable one here is a bug in `enbanc` rather than a model behaving badly.
        """
        rows = {(row.advocate, row.id): row for row in self.transcript.ledger}
        stamped: list[Exhibit] = []
        for exhibit in exhibits:
            row = rows.get((advocate, exhibit.source))
            if row is None:
                raise AssertionError(
                    f"{advocate}'s exhibit cites {exhibit.source!r}, which is not in the "
                    f"ledger — citation validation should have rejected it"
                )
            stamped.append(
                Exhibit(
                    source=exhibit.source,
                    tool=row.tool,
                    reference=row.reference,
                    content=exhibit.content,
                    label=row.label,
                )
            )
        return stamped

    async def _round(self, round: int, inbox: MemoryObjectSendStream[_Filed[VerdictT]]) -> None:
        """One task per addressed advocate. Round 1 addresses the whole bench.

        The task group here is the plain one: a child that fails propagates an
        `ExceptionGroup` and cancels its siblings, and the first-failure slot that turns that
        into a singular `ProceedingFailed` arrives with
        `docs/implementations/failures.md`.
        """
        async with anyio.create_task_group() as tg:
            for verdict in self.advocates:
                tg.start_soon(self._argue, verdict, round, inbox)

    async def _argue(
        self, verdict: VerdictT, round: int, inbox: MemoryObjectSendStream[_Filed[VerdictT]]
    ) -> None:
        """One advocate's round-1 turn: the case, and nothing else.

        **No snapshot and no history.** An advocate arguing blind was shown nothing, which is
        `docs/decisions/0023-advocates-argue-blind-and-rebut-informed.md` as a missing
        argument rather than as a filter, and its first run has no conversation to carry. For
        the same reason round 1 does not advance `since`: filing and being shown are different
        events.
        """
        ledgering = self.ledgerings[verdict]
        ledgering.round = round
        result = await self.advocate_agents[verdict].run(
            argument_turn(self.case, verdict),
            message_history=self.history.get(verdict),
            usage=self._usage(verdict),
        )
        self.history[verdict] = result.all_messages()
        await self._file(result.output, round=round, inbox=inbox)

    async def _deliberate(
        self, deliberation: int, inbox: MemoryObjectSendStream[_Filed[VerdictT]]
    ) -> Ruling[VerdictT]:
        """The judge reads what was filed since it last looked, and rules.

        A continuance is what the round loop is for, and there is no round loop yet — see
        `docs/implementations/round-loop.md`. Raising here rather than filing it and calling
        the proceeding undecided is deliberate: `Undecided(reason='rounds')` is correct only
        for `max_rounds=1` and is a false record for every other tribunal.
        """
        snapshot = self._snapshot()
        result = await self.judge_agent.run(
            deliberation_turn(
                snapshot,
                since=self.since[JUDGE],
                deliberation=deliberation,
                max_rounds=self.max_rounds,
            ),
            message_history=self.history.get(JUDGE),
            usage=self._usage(JUDGE),
        )
        self.history[JUDGE] = result.all_messages()
        self.since[JUDGE] = deliberation
        self.rounds = deliberation
        outcome = result.output
        if isinstance(outcome, _Continuance):
            raise NotImplementedError(
                "the judge issued a continuance, and the round it starts is not built yet — "
                "see docs/implementations/round-loop.md"
            )
        await self._file(outcome, round=deliberation, inbox=inbox)
        return outcome

    async def _file(
        self,
        filing: _Emitted[VerdictT],
        *,
        round: int,
        inbox: MemoryObjectSendStream[_Filed[VerdictT]],
    ) -> Entry[VerdictT]:
        """Hand one filing to the clerk and wait for the record to hold it."""
        filed = _Filed[VerdictT](filing=filing, round=round, done=anyio.Event())
        await inbox.send(filed)
        await filed.done.wait()
        if filed.entry is None:  # pragma: no cover
            # Unreachable: the clerk writes `entry` before it sets `done`.
            raise AssertionError("the clerk acknowledged a filing without stamping it")
        return filed.entry


@asynccontextmanager
async def proceed(
    *,
    question: str,
    statute: Statute,
    case: Case,
    verdicts: type[VerdictT],
    judge: "Judge",
    advocates: Mapping[VerdictT, "Advocate"],
    model: Model,
    max_rounds: int,
    budget: UsageLimits | None = None,
    max_concurrency: AnyConcurrencyLimit = None,
) -> AsyncIterator[Proceeding[VerdictT]]:
    """Run one proceeding, handing back the live record while it runs.

    `Tribunal.hear_stream()` is this with a tribunal's fields unpacked into it, and
    `Tribunal.hear()` is this consumed to exhaustion — so there is one implementation of a
    proceeding and the two entry points cannot come apart.

    **The `finally` is load-bearing.** A consumer that breaks out of the loop leaves the clerk
    blocked on a rendezvous send nobody will ever receive; cancelling the scope on the way out
    is what makes `docs/design/api.md`'s *abandoning is allowed* true rather than a hang. On
    the finished path it is a no-op — every task has already returned.
    """
    orchestrator = _Orchestrator(
        question=question,
        statute=statute,
        case=case,
        verdicts=verdicts,
        judge=judge,
        advocates=advocates,
        model=model,
        max_rounds=max_rounds,
        budget=budget,
        max_concurrency=max_concurrency,
    )
    send, receive = anyio.create_memory_object_stream[Entry[VerdictT]](0)
    proceeding = Proceeding(orchestrator, receive)
    # Both ends are closed on the way out, on every path. A memory object stream collected
    # without being closed warns from `__del__`, and a library that leaves a warning behind in
    # a caller's test suite is a library with a resource leak — the caller's process is the one
    # that reports it.
    async with send, receive, anyio.create_task_group() as tg:
        tg.start_soon(orchestrator.run, send)
        try:
            yield proceeding
        finally:
            tg.cancel_scope.cancel()
