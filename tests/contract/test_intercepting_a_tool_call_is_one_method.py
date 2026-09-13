"""Intercepting a tool call is one method.

Pins the finding of the same name in `docs/design/execution.md`. `WrapperToolset.call_tool`
receives the tool name, the validated arguments, the `RunContext` and the resolved tool, and
its return value becomes the `ToolReturnPart` content verbatim. That is the whole interception
point `docs/design/evidence.md#how-a-source-becomes-an-exhibit` needs, and the verbatim rewrite
is what makes the ledgering toolset a rewrite rather than a decoration.

The timeout case is the seam between a degraded advocate and an unheard one
(`docs/decisions/0022-tool-failures-are-recorded.md`): `FunctionToolset.call_tool` converts the
`TimeoutError` into `ModelRetry` itself, so the wrapper sees it, records it, and re-raises it
unchanged — and the `detail` stored in `Transcript.failures` is PydanticAI's own string rather
than one `enbanc` composes.

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

import inspect
from typing import Any

import anyio
from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.toolsets import FunctionToolset, ToolsetTool, WrapperToolset

#: Short enough that the timeout fires immediately, so the case costs no wall-clock time
#: worth measuring, against a tool that would otherwise outlast the suite.
_TIMEOUT = 0.01
_FOREVER = 5.0


class _Ledgering(WrapperToolset[Any]):
    """Stands in for `evidence.md`'s ledgering toolset: observe, rewrite, record failures."""

    observed: list[tuple[str, dict[str, Any], bool, bool]]
    failures: list[tuple[str, str]]

    def __init__(self, wrapped: FunctionToolset[Any]) -> None:
        super().__init__(wrapped)
        self.observed = []
        self.failures = []

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[Any],
        tool: ToolsetTool[Any],
    ) -> Any:
        try:
            result = await super().call_tool(name, tool_args, ctx, tool)
        except ModelRetry as e:
            # `0022`'s one `except` clause. Record, then re-raise unchanged so PydanticAI still
            # turns it into a `RetryPromptPart` and the advocate gets its correction.
            self.failures.append((name, str(e)))
            raise
        self.observed.append((name, tool_args, isinstance(ctx, RunContext), tool is not None))
        return f"REWRITTEN<{result}>"


async def _search(query: str) -> str:
    return f"hits for {query}"


async def _slow() -> str:
    await anyio.sleep(_FOREVER)
    raise AssertionError("unreachable: the timeout fires first")


def _scripted(calls: list[tuple[str, dict[str, Any]]]) -> FunctionModel:
    """A model that makes exactly the listed calls, then stops.

    Finite by construction. A `FunctionModel` that calls unconditionally never terminates: it
    hits PydanticAI's inherited `request_limit` of fifty and reports `UsageLimitExceeded`, a
    failure that names the wrong subsystem entirely.
    """
    remaining = iter(calls)

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nxt = next(remaining, None)
        if nxt is None:
            return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(parts=[ToolCallPart(nxt[0], nxt[1])])

    return FunctionModel(emit)


def test_call_tool_takes_the_name_arguments_context_and_resolved_tool() -> None:
    parameters = list(inspect.signature(WrapperToolset.call_tool).parameters)

    assert parameters == ["self", "name", "tool_args", "ctx", "tool"]


async def test_the_wrappers_return_becomes_the_tool_return_part_verbatim() -> None:
    # The finding that makes the ledgering toolset a rewrite rather than a decoration: what the
    # wrapper returns is what the model reads, so a stamped exhibit can replace a raw retrieval
    # with nothing downstream having to cooperate.
    ledgering = _Ledgering(FunctionToolset(tools=[_search]))
    agent = Agent(_scripted([("_search", {"query": "dti"})]), toolsets=[ledgering])

    result = await agent.run("retrieve")

    returns = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart)]
    assert [p.content for p in returns] == ["REWRITTEN<hits for dti>"]


async def test_the_wrapper_observes_the_call_it_intercepted() -> None:
    ledgering = _Ledgering(FunctionToolset(tools=[_search]))
    agent = Agent(_scripted([("_search", {"query": "dti"})]), toolsets=[ledgering])

    await agent.run("retrieve")

    # The arguments arrive validated and keyed, not as the model's raw JSON string.
    assert ledgering.observed == [("_search", {"query": "dti"}, True, True)]


async def test_a_tool_timeout_surfaces_inside_the_wrapper_as_model_retry() -> None:
    # The per-tool timeout takes precedence over the toolset's, and `FunctionToolset.call_tool`
    # converts `TimeoutError` into `ModelRetry` before the wrapper ever sees it. That is why
    # `enbanc` records a timeout at the same seam as every other tool failure, and why the
    # `detail` it stores is this string rather than one it composed.
    ledgering = _Ledgering(FunctionToolset(tools=[Tool(_slow, timeout=_TIMEOUT)]))
    agent = Agent(_scripted([("_slow", {})]), toolsets=[ledgering], retries={"tools": 2})

    result = await agent.run("retrieve")

    assert ledgering.failures == [("_slow", f"Timed out after {_TIMEOUT} seconds.")]
    # Re-raised unchanged, so the advocate is corrected rather than silently starved. The part
    # carries the bare string — PydanticAI adds its own "Fix the errors and try again" framing
    # when rendering it for the model, which is why `0022`'s `detail` is `content` and not that.
    retries = [p for m in result.all_messages() for p in m.parts if isinstance(p, RetryPromptPart)]
    assert [p.content for p in retries] == [f"Timed out after {_TIMEOUT} seconds."]


async def test_function_toolset_takes_bare_functions_and_tool_instances_alike() -> None:
    # `0020`'s `Tool(fn, timeout=...)` needs no separate registration path — asserted by
    # registering one of each and calling both.
    ledgering = _Ledgering(FunctionToolset(tools=[_search, Tool(_search, name="cited")]))
    agent = Agent(
        _scripted([("_search", {"query": "a"}), ("cited", {"query": "b"})]),
        toolsets=[ledgering],
    )

    await agent.run("retrieve")

    assert [name for name, _, _, _ in ledgering.observed] == ["_search", "cited"]
