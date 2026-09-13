"""Instructions are re-resolved every run and never enter history.

Pins the finding of the same name in `docs/design/execution.md`. Two claims, and the second is
the one `docs/design/prompting.md` spends money on.

Re-resolution is why `docs/design/api.md#design-commitments` has to build an agent inside
`hear()` and discard it: instructions are read from the agent at every request, so changing
them between runs would apply retroactively to a whole conversation. And because what reaches
the provider is resolved fresh rather than stored as a part, `assert_invariant_held`
(`docs/design/testing.md#the-transcript-invariant`) can walk message parts and never see an
instruction — the instructions channel is accounted for separately, through
`tribunal.instructions_for(participant)`.

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.

The Anthropic test below is deliberately fragile in two ways: it imports `anthropic`, which
arrives transitively rather than by declaration, and it calls the private `_map_message`.
Either breaking is this tier reporting that the dependency moved, which is the tier's job —
do not "fix" it by deleting it. It reaches no network: constructing a provider with a fake
key opens no connection, and the socket guard in `conftest.py` is satisfied.
"""

from collections.abc import Iterator

from pydantic_ai import Agent
from pydantic_ai.messages import (
    InstructionPart,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.providers.anthropic import AnthropicProvider

#: What an `enbanc` agent's instructions look like at the seam under test: the procedural
#: preamble and the statute, concatenated, identical across the conversation's requests.
_INSTRUCTIONS = "PROCEDURAL\n\nSTATUTE"


async def _two_runs(seen: list[str | None]) -> list[ModelMessage]:
    """Run an agent twice, the second time carrying the first run's history."""

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info.instructions)
        return ModelResponse(parts=[TextPart("ok")])

    resolved: Iterator[str] = iter(("FIRST", "SECOND"))
    agent = Agent(FunctionModel(emit), instructions=lambda: next(resolved))

    first = await agent.run("round 1")
    second = await agent.run("round 2", message_history=first.all_messages())
    return second.all_messages()


async def test_instructions_are_resolved_per_request_not_frozen_at_the_first_run() -> None:
    # A sharper probe than `execution.md`'s wire capture, which shows two identical strings and
    # so cannot distinguish re-resolution from freezing. `AgentInfo.instructions` is the
    # *effective* instructions for the request, so a callable that changes its answer makes the
    # difference visible: frozen would read ['FIRST', 'FIRST'].
    seen: list[str | None] = []

    await _two_runs(seen)

    assert seen == ["FIRST", "SECOND"]


async def test_no_instruction_part_ever_enters_history() -> None:
    seen: list[str | None] = []

    messages = await _two_runs(seen)

    assert not [p for m in messages for p in m.parts if isinstance(p, InstructionPart)]


async def test_each_historical_request_keeps_the_string_it_was_sent_with() -> None:
    # The looser reading of "never enter history", stated precisely because a later PR depends
    # on it. Instructions *are* in history, on the `ModelRequest.instructions` attribute, and
    # each stored request keeps its own string. What never enters is a *part*. What reaches the
    # provider is resolved fresh for each request — which is why one changed instruction governs
    # the whole conversation even though the stored records disagree with each other.
    seen: list[str | None] = []

    messages = await _two_runs(seen)

    assert [m.instructions for m in messages if isinstance(m, ModelRequest)] == ["FIRST", "SECOND"]


async def test_anthropic_hoists_the_instructions_once_into_system() -> None:
    # `prompting.md#how-an-agent-is-assembled`'s shared-cache-prefix claim, which is currently
    # true on the strength of a source comment nothing checks — and a proceeding's whole cost
    # story rests on it. Given a history whose two requests carry identical instructions, the
    # text appears once at the top level and in none of the mapped messages; were it re-emitted
    # per request the cache prefix would differ between rounds and nothing would be reused.
    history: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart("round 1")], instructions=_INSTRUCTIONS),
        ModelResponse(parts=[TextPart("ok")]),
        ModelRequest(parts=[UserPromptPart("round 2")], instructions=_INSTRUCTIONS),
    ]
    model = AnthropicModel(
        "claude-sonnet-4-5", provider=AnthropicProvider(api_key="not-a-real-key")
    )

    system, messages = await model._map_message(history, ModelRequestParameters(), {})  # noqa: SLF001

    assert system == [{"type": "text", "text": _INSTRUCTIONS}]
    assert len(messages) == len(history)
    assert not [m for m in messages if _INSTRUCTIONS in str(m)]
