"""A wrapper toolset is rebuilt for every run.

Pins the finding of the same name in `docs/design/execution.md`. `CombinedToolset.for_run`
returns `replace(self, toolsets=...)` unconditionally, so a `WrapperToolset` around one always
sees a new `wrapped` and always replaces itself — and `dataclasses.replace` re-constructs the
instance from its fields. The object `call_tool` runs on is therefore never the object the
agent was given.

That is what forces the shape of `enbanc._ledgering`: every piece of state is a dataclass
field, and anything that must accumulate across runs is a mutable container shared by
reference. `replace()` is shallow, so a `list` field is the same list in the copy while an
`int` field is a value the copy mutates alone — a ledger id counted into an `int` would
restart at `s1` at the top of every round, silently, and the id is the join key an exhibit
resolves through (`docs/decisions/0019-the-ledger-is-part-of-the-record.md`). It is also
`docs/decisions/0016-exhibits-are-stamped-citations.md`'s closing constraint, which said this
was "true today and is not a documented guarantee" — which is precisely what this tier is for.

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.toolsets import (
    AbstractToolset,
    CombinedToolset,
    FunctionToolset,
    ToolsetTool,
    WrapperToolset,
)


@dataclass(kw_only=True)
class _Probe(WrapperToolset[Any]):
    """A wrapper that records what it was when it ran, and mutates one field of each kind."""

    original: object = None
    identities: list[bool] = field(default_factory=list)
    rounds: list[int] = field(default_factory=list)
    shared: list[str] = field(default_factory=list)
    counted: int = 0
    round: int = 1

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[Any],
        tool: ToolsetTool[Any],
    ) -> Any:
        self.identities.append(self is self.original)
        self.rounds.append(self.round)
        self.shared.append(name)
        self.counted += 1
        return await super().call_tool(name, tool_args, ctx, tool)


async def _search(query: str) -> str:
    return f"hits for {query}"


def _scripted(calls: list[tuple[str, dict[str, Any]]]) -> FunctionModel:
    """A model that makes exactly the listed calls, then stops.

    Finite by construction, for the reason
    `test_intercepting_a_tool_call_is_one_method.py` gives: a `FunctionModel` that calls
    unconditionally hits PydanticAI's inherited `request_limit` of fifty and reports
    `UsageLimitExceeded`, a failure that names the wrong subsystem entirely.
    """
    remaining = iter(calls)

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nxt = next(remaining, None)
        if nxt is None:
            return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(parts=[ToolCallPart(nxt[0], nxt[1])])

    return FunctionModel(emit)


def _probe(wrapped: AbstractToolset[Any]) -> _Probe:
    probe = _Probe(wrapped=wrapped)
    probe.original = probe
    return probe


def _combined() -> CombinedToolset[Any]:
    return CombinedToolset([FunctionToolset(tools=[_search])])


async def test_a_combined_toolset_returns_a_new_object_from_for_run() -> None:
    # The root of the whole finding, and the one asymmetry worth naming: `for_run_step` keeps
    # identity when every child is unchanged, and `for_run` does not even look.
    combined = _combined()
    probe = _probe(combined)
    agent = Agent(_scripted([("_search", {"query": "dti"})]), toolsets=[probe])

    await agent.run("retrieve")

    assert probe.identities == [False]
    assert probe.wrapped is combined


async def test_a_scalar_field_mutated_during_a_run_does_not_reach_the_original() -> None:
    # The hazard, stated as a passing test: the copy counted, the original did not.
    probe = _probe(_combined())
    agent = Agent(
        _scripted([("_search", {"query": "a"}), ("_search", {"query": "b"})]),
        toolsets=[probe],
    )

    await agent.run("retrieve")

    assert probe.counted == 0


async def test_a_list_field_is_the_same_list_in_the_copy() -> None:
    # `replace()` is shallow, which is the whole reason a ledger can be accumulated at all.
    probe = _probe(_combined())
    agent = Agent(
        _scripted([("_search", {"query": "a"}), ("_search", {"query": "b"})]),
        toolsets=[probe],
    )

    await agent.run("retrieve")

    assert probe.shared == ["_search", "_search"]


async def test_state_accumulates_across_runs_only_through_the_shared_list() -> None:
    # Two runs of one toolset, which is an advocate answering in round 1 and again in round 2.
    # The list carries; the counter does not, and that is the failure mode this module exists
    # to make loud.
    probe = _probe(_combined())

    await Agent(_scripted([("_search", {"query": "a"})]), toolsets=[probe]).run("retrieve")
    await Agent(_scripted([("_search", {"query": "b"})]), toolsets=[probe]).run("retrieve")

    assert probe.shared == ["_search", "_search"]
    assert probe.counted == 0


async def test_a_field_written_between_runs_reaches_the_next_runs_copy() -> None:
    # The direction that does work, and the seam `enbanc` sets `round` through: the
    # orchestrator writes it on the original before dispatch, and `for_run` copies it in.
    probe = _probe(_combined())

    await Agent(_scripted([("_search", {"query": "a"})]), toolsets=[probe]).run("retrieve")
    probe.round = 2
    await Agent(_scripted([("_search", {"query": "b"})]), toolsets=[probe]).run("retrieve")

    assert probe.rounds == [1, 2]


async def test_a_wrapper_over_a_bare_function_toolset_is_not_replaced() -> None:
    # The discriminating case. `AbstractToolset.for_run` defaults to returning `self`, and
    # `WrapperToolset.for_run` replaces only when its wrapped toolset changed — so a wrapper
    # over a plain `FunctionToolset` keeps its identity and accumulates in an `int` quite
    # happily. A test written that way would pass against an implementation that is broken
    # the moment the design's `CombinedToolset` is put underneath it.
    probe = _probe(FunctionToolset(tools=[_search]))
    agent = Agent(_scripted([("_search", {"query": "dti"})]), toolsets=[probe])

    await agent.run("retrieve")

    assert probe.identities == [True]
    assert probe.counted == 1
