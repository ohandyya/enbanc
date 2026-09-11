"""A failing output schema spends the `output` retry budget, not the `tools` one.

Pins the finding of the same name in `docs/design/execution.md`. `Agent(retries=...)` carries
two independent budgets, and `docs/decisions/0030-the-retry-budgets.md` names an unresolvable
`_Exhibit.source` — an *output validator* — as what spends `output`. A Pydantic constraint on
the output type is a second path to the same budget, and it is the one
`docs/decisions/0036-a-continuance-carries-at-least-one-interrogatory.md` rests on: a judge
that emits a continuance with no interrogatories is corrected, and then treated as a
participant whose output will not validate.

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

from typing import Literal

import pytest
from pydantic import BaseModel, Field
from pydantic_ai import Agent, UnexpectedModelBehavior
from pydantic_ai.agent import AgentRetries
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


class _Continuance(BaseModel):
    """`docs/design/api.md`'s emit-shape, reduced to the constraint under test."""

    kind: Literal["continuance"] = "continuance"
    interrogatories: list[str] = Field(min_length=1)


def _always_empty(attempts: list[None]) -> FunctionModel:
    """A model that files a continuance with nothing to ask, every time it is asked."""

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        attempts.append(None)
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"interrogatories": []})]
        )

    return FunctionModel(emit)


@pytest.mark.parametrize(
    ("retries", "expected_attempts"),
    [
        ({"tools": 5, "output": 1}, 2),
        ({"tools": 1, "output": 4}, 5),
    ],
)
async def test_attempts_track_the_output_budget_alone(
    retries: AgentRetries, expected_attempts: int
) -> None:
    # The two cases are chosen so that consulting the wrong budget gives a different count:
    # were it `tools`, the first would allow six attempts and the second two.
    attempts: list[None] = []
    agent = Agent(_always_empty(attempts), output_type=_Continuance, retries=retries)

    with pytest.raises(UnexpectedModelBehavior, match="Exceeded maximum output retries"):
        await agent.run("deliberate")

    assert len(attempts) == expected_attempts


async def test_the_constraint_reaches_the_model_as_min_items() -> None:
    # The correction is only fair if the model was told the rule in the first place.
    schemas: list[dict[str, object]] = []

    def peek(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        schemas.append(info.output_tools[0].parameters_json_schema)
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"interrogatories": ["q"]})]
        )

    await Agent(FunctionModel(peek), output_type=_Continuance).run("deliberate")

    interrogatories = schemas[0]["properties"]["interrogatories"]  # type: ignore[index]
    assert interrogatories["minItems"] == 1


async def test_the_retry_prompt_names_the_constraint() -> None:
    # `0021` keeps retry prompts outside the transcript invariant on the grounds that one
    # reports a mechanical failure of the agent's own last action. This is what one says.
    prompts: list[str] = []

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts.extend(
            part.model_response()
            for message in messages
            for part in getattr(message, "parts", ())
            if isinstance(part, RetryPromptPart)
        )
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"interrogatories": []})]
        )

    agent = Agent(FunctionModel(emit), output_type=_Continuance, retries={"tools": 3, "output": 1})
    with pytest.raises(UnexpectedModelBehavior):
        await agent.run("deliberate")

    assert "List should have at least 1 item after validation, not 0" in prompts[0]
