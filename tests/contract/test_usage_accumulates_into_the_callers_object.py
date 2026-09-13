"""Usage accumulates into an object the caller owns.

Pins the finding of the same name in `docs/design/execution.md`. `Agent.run(usage=u)` mutates
`u` in place and `result.usage` *is* `u`, which is what lets `hear()` mint one `RunUsage` per
participant and read `usage_by_participant` off the dict of them
(`docs/decisions/0014-usage-is-broken-down-per-participant.md`). The half that matters is the
failure path: because the object was never the run's to begin with, a run that dies mid-flight
leaves its partial spend behind, so every participant that was dispatched has a key on a
`ProceedingFailed` as well as on a `Hearing` and absence means *never dispatched*
(`docs/decisions/0028-usage-accumulates-per-participant.md`).

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import RunUsage


def _answers(text: str) -> FunctionModel:
    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(text)])

    return FunctionModel(emit)


def _calls(tool_name: str) -> FunctionModel:
    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(tool_name, {})])

    return FunctionModel(emit)


async def test_usage_accumulates_across_runs_into_the_callers_object() -> None:
    # Accumulation, not replacement: were the object reset per run, a participant's total
    # would be its last round's spend and `Hearing.usage` would under-report the proceeding.
    usage = RunUsage()
    agent = Agent(_answers("ok"))

    await agent.run("round 1", usage=usage)
    after_one = (usage.requests, usage.input_tokens)
    await agent.run("round 2", usage=usage)

    assert usage.requests > after_one[0]
    assert usage.input_tokens > after_one[1]


async def test_result_usage_is_the_callers_object() -> None:
    # Identity, not equality, and a property rather than a method. `0014`'s breakdown is
    # stored in the caller's dict; an equal-but-distinct copy would leave the dict frozen at
    # whatever the object held when it was handed over.
    usage = RunUsage()

    result = await Agent(_answers("ok")).run("deliberate", usage=usage)

    assert result.usage is usage


async def test_a_run_that_dies_mid_flight_leaves_its_partial_spend() -> None:
    # The load-bearing half. A tool that raises propagates unchanged — it is not wrapped into
    # `UnexpectedModelBehavior` — and the spend incurred getting there stays in the object.
    usage = RunUsage()

    async def explode() -> str:
        raise RuntimeError("tool exploded")

    agent = Agent(_calls("explode"), tools=[explode])

    with pytest.raises(RuntimeError, match="tool exploded"):
        await agent.run("go", usage=usage)

    # `>=` and non-zero, never an exact count: `testing.md#what-must-not-be-asserted` makes
    # the total after a failure a floor, and the rule binds the probe that establishes the
    # mechanic as much as the tests that rely on it. The claim is *the spend survives*.
    assert usage.requests >= 1
    assert usage.input_tokens > 0
