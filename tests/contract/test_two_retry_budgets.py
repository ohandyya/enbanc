"""Two retry budgets, not one.

Pins the finding of the same name in `docs/design/execution.md`. `Agent(retries=...)` takes
`int | AgentRetries`, where `AgentRetries` is `{'tools': int, 'output': int}`; both default to
`1` and the two are independent. That independence is what
`docs/decisions/0030-the-retry-budgets.md` rests on: a flaky tool cannot exhaust the budget
guarding citation integrity, and vice versa.

Tool retries are counted per *tool name*, which is what makes
`docs/decisions/0020-tool-timeouts-ride-on-the-tool.md`'s "reach for another tool" a real move
rather than a figure of speech, and `Tool(max_retries=...)` is what
`execution.md#also-in-scope` hands to the caller while keeping the `output` budget unreachable.

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Literal

import anyio
import pytest
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

#: A tool that outlives its own timeout: what every case here uses to spend a retry.
_Slow = Callable[[], Awaitable[str]]

#: Short enough that a timeout fires immediately. Each case below costs no wall-clock time
#: worth measuring even though the timeouts are real ones.
_TIMEOUT = 0.01
_FOREVER = 5.0

#: The retry ceiling PydanticAI reports when a budget is spent. A prefix, not the whole
#: sentence: the message continues "Consider raising the retry limit, or see the docs ...".
_EXCEEDED = "Tool '{name}' exceeded max retries count of {n}"


class _Continuance(BaseModel):
    """The output type whose constraint spends the *other* budget."""

    kind: Literal["continuance"] = "continuance"
    interrogatories: list[str] = Field(min_length=1)


async def _alpha() -> str:
    await anyio.sleep(_FOREVER)
    raise AssertionError("unreachable: the timeout fires first")


async def _beta() -> str:
    await anyio.sleep(_FOREVER)
    raise AssertionError("unreachable: the timeout fires first")


def _scripted(calls: list[str], *, then: dict[str, Any] | None = None) -> FunctionModel:
    """A model that makes exactly the listed tool calls, then finishes.

    **Finite by construction, and that is the point.** A `FunctionModel` that calls its tool
    unconditionally never terminates: it hits PydanticAI's inherited `request_limit` of fifty
    and reports `UsageLimitExceeded`, a green-looking failure that says nothing about retries
    and names the wrong subsystem. Each case emits its calls from an iterator and falls through
    to a final response when the iterator is spent.
    """
    remaining = iter(calls)

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nxt = next(remaining, None)
        if nxt is not None:
            return ModelResponse(parts=[ToolCallPart(nxt, {})])
        if then is not None:
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, then)])
        return ModelResponse(parts=[TextPart("done")])

    return FunctionModel(emit)


def _timing_out(*tools: _Slow) -> list[Tool[Any]]:
    return [Tool(tool, timeout=_TIMEOUT) for tool in tools]


async def test_both_budgets_default_to_one() -> None:
    # One timeout is forgiven and two are not, which is what "defaults to 1" means where it
    # is felt. `retries` is left unset so the default is the thing under test.
    forgiven = Agent(_scripted(["_alpha"]), tools=_timing_out(_alpha))
    assert (await forgiven.run("go")).output == "done"

    spent = Agent(_scripted(["_alpha", "_alpha"]), tools=_timing_out(_alpha))
    with pytest.raises(UnexpectedModelBehavior, match=_EXCEEDED.format(name="_alpha", n=1)):
        await spent.run("go")


async def test_the_tools_and_output_budgets_are_independent() -> None:
    # A `tools` budget fully spent by a timeout leaves the `output` retries intact. Were there
    # one shared budget, the timeout below would have consumed the correction the empty
    # continuance needs and this run would fail on the tool rather than succeed.
    agent = Agent(
        _scripted(["_alpha"], then={"interrogatories": ["what is the documented income?"]}),
        tools=_timing_out(_alpha),
        output_type=_Continuance,
        retries={"tools": 1, "output": 2},
    )

    result = await agent.run("go")

    assert result.output.interrogatories == ["what is the documented income?"]


async def test_tool_retries_are_counted_per_tool_name() -> None:
    # `alpha` failing once and `beta` failing once both succeed under a budget of 1. A per-run
    # budget would have been spent by `alpha` and `beta`'s timeout would end the run — so this
    # case gives a different answer depending on which budget is consulted, which is the only
    # kind of case worth writing here.
    agent = Agent(
        _scripted(["_alpha", "_beta"]), tools=_timing_out(_alpha, _beta), retries={"tools": 1}
    )

    result = await agent.run("go")

    assert result.output == "done"


async def test_a_tools_own_max_retries_overrides_the_agent_default() -> None:
    # `max_retries` resolves tool -> toolset -> ctx. The same two failures that exhaust the
    # agent-level budget pass when the tool carries its own, which is the override
    # `execution.md#also-in-scope` hands to the caller.
    calls = ["_alpha", "_alpha"]

    strict = Agent(_scripted(calls), tools=_timing_out(_alpha), retries={"tools": 1})
    with pytest.raises(UnexpectedModelBehavior, match=_EXCEEDED.format(name="_alpha", n=1)):
        await strict.run("go")

    tolerant = Agent(
        _scripted(calls),
        tools=[Tool(_alpha, timeout=_TIMEOUT, max_retries=3)],
        retries={"tools": 1},
    )
    assert (await tolerant.run("go")).output == "done"
