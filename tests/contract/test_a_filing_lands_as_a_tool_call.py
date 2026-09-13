"""A filing lands in history as a tool call, not as text.

Pins the finding of the same name in `docs/design/execution.md`. An agent whose `output_type`
is a union gets one output tool per member, named from the member's class, and the filing
arrives as a `ToolCallPart` followed by a `ToolReturnPart` receipt. There is no `TextPart` on
the path an `enbanc` participant takes, ever — which is what lets `assert_invariant_held`
(`docs/design/testing.md#the-transcript-invariant`) treat a stray `TextPart` as a leak rather
than as ordinary traffic.

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel


class ArgumentLoanDecision(BaseModel):
    """`docs/design/api.md`'s filing shape, reduced to what the union needs.

    Deliberately not `_`-prefixed, unlike this tier's other helpers: PydanticAI derives the
    output tool name from the class name, and the assertion below is the exact string
    `execution.md` records. A leading underscore would land in it.
    """

    kind: Literal["argument"] = "argument"
    claim: str


class ConcessionLoanDecision(BaseModel):
    kind: Literal["concession"] = "concession"
    claim: str


_FILING = {"claim": "DTI is 0.38 on documented income."}


def _files_the_first_output_tool(seen: list[list[str]]) -> FunctionModel:
    """A model that records the tools it was offered and fills the first one."""

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append([tool.name for tool in info.output_tools])
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, _FILING)])

    return FunctionModel(emit)


def _advocate(seen: list[list[str]]) -> Agent[None, ArgumentLoanDecision | ConcessionLoanDecision]:
    return Agent(
        _files_the_first_output_tool(seen),
        output_type=ArgumentLoanDecision | ConcessionLoanDecision,
    )


async def test_a_union_output_type_yields_one_tool_per_member() -> None:
    # Asserted as the exact names, because the finding's point is that renaming a filing class
    # silently changes a string the model reads. The names are PydanticAI's, derived from the
    # class names, and are not covered by `Transcript.procedure`
    # (`docs/design/prompting.md#procedure-versions`) — so nothing else would catch the rename.
    seen: list[list[str]] = []

    await _advocate(seen).run("file")

    assert seen[0] == ["final_result_ArgumentLoanDecision", "final_result_ConcessionLoanDecision"]


async def test_a_filing_is_a_tool_call_carrying_the_models_arguments() -> None:
    seen: list[list[str]] = []

    result = await _advocate(seen).run("file")

    calls = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolCallPart)]
    assert len(calls) == 1
    assert calls[0].args_as_dict() == _FILING


async def test_the_receipt_is_the_string_the_invariant_whitelists() -> None:
    # Asserted verbatim: `testing.md#the-transcript-invariant`'s escape 3 whitelists this exact
    # text, so the invariant helper starts failing honest proceedings the moment it changes.
    seen: list[list[str]] = []

    result = await _advocate(seen).run("file")

    returns = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart)]
    assert [p.content for p in returns] == ["Final result processed."]


async def test_no_text_part_is_on_the_path() -> None:
    seen: list[list[str]] = []

    result = await _advocate(seen).run("file")

    assert not [p for m in result.all_messages() for p in m.parts if isinstance(p, TextPart)]
