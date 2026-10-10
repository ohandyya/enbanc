"""An agent carrying an output validator cannot be given a run-level `output_type`.

Pins the finding of the same name in `docs/design/execution.md`. It is the constraint that
decided how `enbanc` attaches its citation check: an advocate's output shape varies by round
— `_Argument | Concession` in round 1, `_Response` after — while there is one `Agent` per
participant, and those two cannot both hold while the check is an agent-level validator.

So the check rides on the output type instead, as an **output function**. The three claims
that make that substitution invisible are pinned here too: the tool a model is offered is
derived from the function's single parameter, a `ModelRetry` raised inside it spends the
`output` budget, and it reaches the model as a `RetryPromptPart`.

A round-2 advocate is given a function of **several** parameters — `answer` and `exhibits`,
with `advocate` and `answering` filled from the dispatch
(`docs/decisions/0039-a-response-is-asked-for-its-answer-alone.md`). That leans on two more
claims, pinned below: such a function is offered as an object schema of exactly its
parameters, and its `ModelRetry` spends the `output` budget the same way.

If any of this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

from typing import Literal

import pytest
from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, UnexpectedModelBehavior, UserError
from pydantic_ai.agent import AgentRetries
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import ToolDefinition


class _Argument(BaseModel):
    """An advocate's round-1 shape, reduced to what the finding needs."""

    kind: Literal["argument"] = "argument"
    claim: str


class Concession(BaseModel):
    kind: Literal["concession"] = "concession"
    reason: str


class _Response(BaseModel):
    """The round-2 shape the same agent would have to be given later."""

    kind: Literal["response"] = "response"
    answer: str


def _offered(model: TestModel) -> list[ToolDefinition]:
    """The output tools the last request carried. Asserted non-empty, because every agent in
    this module has a structured output type and a run that offered none would make the
    comparisons below vacuously true."""
    parameters = model.last_model_request_parameters
    assert parameters is not None, "the model was never asked for anything"
    assert parameters.output_tools
    return parameters.output_tools


def _files_whatever_it_is_offered() -> FunctionModel:
    """A model that calls the first output tool, filling its required fields with text.

    Built from the schema rather than from a hard-coded name, because half of what this module
    pins is *what the tool is called* — a stand-in that assumed the name would beg the
    question, and would break on the single-output case where it is plain `final_result`.
    """

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool = (info.output_tools or [])[0]
        required = tool.parameters_json_schema.get("required", [])
        return ModelResponse(
            parts=[ToolCallPart(tool.name, dict.fromkeys(required, "text the model wrote"))]
        )

    return FunctionModel(emit)


async def test_a_validator_forbids_a_run_level_output_type() -> None:
    """The constraint itself, and it is unconditional — the refusal does not care whether the
    override would have produced a valid schema."""
    agent = Agent(TestModel(), output_type=[_Argument, Concession])
    agent.output_validator(lambda output: output)

    with pytest.raises(UserError, match="Cannot set a custom run `output_type`"):
        await agent.run("file", output_type=_Response)


async def test_it_refuses_even_an_override_identical_to_the_agents_own() -> None:
    """The half that rules out the obvious workaround of passing the same type every time."""
    agent = Agent(TestModel(), output_type=_Argument)
    agent.output_validator(lambda output: output)

    with pytest.raises(UserError, match="Cannot set a custom run `output_type`"):
        await agent.run("file", output_type=_Argument)


async def test_without_a_validator_the_override_is_allowed() -> None:
    """The other side of the same claim: it is the validator that forbids it, not the override
    itself — which is what makes moving the check off the agent a fix rather than a dodge."""
    agent = Agent(_files_whatever_it_is_offered(), output_type=[_Argument])

    first = await agent.run("file")
    second = await agent.run(
        "respond",
        message_history=first.all_messages(),
        output_type=[_Response],
    )

    assert isinstance(first.output, _Argument)
    assert isinstance(second.output, _Response)


async def test_an_output_function_is_named_and_shaped_by_its_parameter() -> None:
    """The substitution is invisible on the wire: the tool name, the description and the JSON
    schema come from the parameter's type, not from the function.

    That is what lets the check move without changing a byte the model reads — and it is why
    `enbanc`'s output functions carry no docstring, since one *does* reach the model, as the
    tool's description.
    """

    def file_argument(argument: _Argument) -> _Argument:
        return argument

    bare = TestModel()
    wrapped = TestModel()
    await Agent(bare, output_type=[_Argument, Concession]).run("file")
    await Agent(wrapped, output_type=[file_argument, Concession]).run("file")

    def described(tools: list[ToolDefinition]) -> list[tuple[str, str | None, object]]:
        return [(t.name, t.description, t.parameters_json_schema) for t in tools]

    assert described(_offered(wrapped)) == described(_offered(bare))


async def test_a_docstring_on_an_output_function_becomes_the_tools_description() -> None:
    """The trap the sentence above guards against, pinned so it cannot change quietly: prompt
    text `docs/design/prompting.md` does not own would otherwise reach a model through a
    docstring, and `Transcript.procedure` would not version it."""

    def file_argument(argument: _Argument) -> _Argument:
        """Cite the ledger ids you were issued."""
        return argument

    model = TestModel()
    await Agent(model, output_type=[file_argument, Concession]).run("file")

    described = next(tool for tool in _offered(model) if "Argument" in tool.name)
    assert described.description == "Cite the ledger ids you were issued."


@pytest.mark.parametrize(
    ("retries", "expected_attempts"),
    [
        ({"tools": 5, "output": 1}, 2),
        ({"tools": 1, "output": 3}, 4),
    ],
)
async def test_a_model_retry_from_an_output_function_spends_the_output_budget(
    retries: AgentRetries, expected_attempts: int
) -> None:
    """The property `docs/decisions/0030-the-retry-budgets.md` requires of the citation check.

    The two cases are chosen so that consulting the wrong budget gives a different count: were
    it `tools`, the first would allow six attempts and the second two. A flapping search tool
    therefore cannot eat the budget that guards citation integrity, and a healthy one cannot
    mask an advocate inventing citations.
    """
    attempts: list[None] = []

    def file_argument(argument: _Argument) -> _Argument:
        attempts.append(None)
        raise ModelRetry("[s7] was not issued to you.")

    agent = Agent(
        _files_whatever_it_is_offered(),
        output_type=[file_argument],
        retries=retries,
    )

    with pytest.raises(UnexpectedModelBehavior, match="Exceeded maximum output retries"):
        await agent.run("file")

    assert len(attempts) == expected_attempts


async def test_the_retry_reaches_the_model_as_a_retry_prompt() -> None:
    """The correction is only useful if the advocate is told what was wrong with what it filed,
    in `enbanc`'s own words — `check_citations` composes that message, and this is the channel
    it arrives on."""
    prompts: list[str] = []
    attempts: list[None] = []

    def file_argument(argument: _Argument) -> _Argument:
        attempts.append(None)
        if len(attempts) == 1:
            raise ModelRetry("[s7] was not issued to you. The ids you may cite are: s1.")
        return argument

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts.extend(
            part.model_response()
            for message in messages
            for part in getattr(message, "parts", ())
            if isinstance(part, RetryPromptPart)
        )
        tool = (info.output_tools or [])[0]
        return ModelResponse(parts=[ToolCallPart(tool.name, {"claim": "DTI is 0.38."})])

    result = await Agent(FunctionModel(emit), output_type=[file_argument]).run("file")

    # PydanticAI appends its own closing instruction, which is why the message `enbanc`
    # composes is asserted as a prefix rather than as the whole prompt.
    assert prompts == [
        "[s7] was not issued to you. The ids you may cite are: s1.\n\nFix the errors and try again."
    ]
    assert isinstance(result.output, _Argument)


async def test_a_sole_output_type_is_named_final_result() -> None:
    """A union gets one tool per member, named from the class; a single member gets the bare
    `final_result`.

    Worth pinning because it is the shape a round-2 advocate is given — one output function
    and nothing else — so `execution.md`'s round-2 traces show the bare name.
    """
    single = TestModel()
    union = TestModel()
    await Agent(single, output_type=[_Argument]).run("file")
    await Agent(union, output_type=[_Argument, Concession]).run("file")

    assert [tool.name for tool in _offered(single)] == ["final_result"]
    assert sorted(tool.name for tool in _offered(union)) == [
        "final_result_Concession",
        "final_result__Argument",
    ]


async def test_a_function_of_several_parameters_is_offered_as_an_object_of_them() -> None:
    """The round-2 shape, as a per-run override on an agent built for round 1.

    The schema is the parameters and nothing else — a field the function does not take is a
    field the model is not asked for, which is the whole of how `answering` stays off the
    wire. A defaulted parameter is offered but not required, and with no docstring the
    description is PydanticAI's generic sentence.
    """

    def respond(answer: str, exhibits: list[str] = []) -> _Response:  # noqa: B006
        return _Response(answer=answer)

    model = TestModel()
    agent = Agent(model, output_type=[_Argument, Concession])
    await agent.run("respond", output_type=respond)

    (tool,) = _offered(model)
    assert tool.name == "final_result"
    assert sorted(tool.parameters_json_schema["properties"]) == ["answer", "exhibits"]
    assert tool.parameters_json_schema["required"] == ["answer"]
    assert tool.description is not None
    assert tool.description.endswith("The final response which ends this conversation")


@pytest.mark.parametrize(
    ("retries", "expected_attempts"),
    [
        ({"tools": 5, "output": 1}, 2),
        ({"tools": 1, "output": 3}, 4),
    ],
)
async def test_a_model_retry_from_a_function_of_several_parameters_spends_the_output_budget(
    retries: AgentRetries, expected_attempts: int
) -> None:
    """The citation check runs inside the round-2 output function too, so the budget it
    spends must be the same one — or a miscited response would be governed differently from a
    miscited argument."""
    attempts: list[None] = []

    def respond(answer: str, exhibits: list[str] = []) -> _Response:  # noqa: B006
        attempts.append(None)
        raise ModelRetry("[s7] was not issued to you.")

    agent = Agent(_files_whatever_it_is_offered(), output_type=[respond], retries=retries)

    with pytest.raises(UnexpectedModelBehavior, match="Exceeded maximum output retries"):
        await agent.run("respond")

    assert len(attempts) == expected_attempts
