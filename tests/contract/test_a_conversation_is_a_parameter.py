"""Carrying a conversation is a parameter, not a subsystem.

Pins the finding of the same name in `docs/design/execution.md`. `message_history` is an
`Agent.run` argument and `result.all_messages()` hands the conversation back, which is the
whole of the dict in `execution.md#history-is-a-dict-written-after-each-run`: a participant's
history is per-call state the orchestrator owns, not something the agent accumulates. That is
the mirror image of the `max_concurrency` finding, and together the two settle what belongs
on an agent and what belongs to a proceeding
(`docs/design/api.md#design-commitments`, "Agents are reusable; a proceeding's state is not").

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.
"""

import inspect

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


def _answers(text: str) -> FunctionModel:
    """A model that says one thing and consults nothing."""

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(text)])

    return FunctionModel(emit)


def test_message_history_is_a_run_argument() -> None:
    assert "message_history" in inspect.signature(Agent.run).parameters


def test_message_history_is_not_an_init_parameter() -> None:
    # The half that constrains the design, and the mirror of `max_concurrency`. Were history
    # an `__init__` parameter, a participant's conversation would be agent state and `hear()`
    # could not build an agent once and run it across rounds against a changing record.
    assert "message_history" not in inspect.signature(Agent.__init__).parameters


async def test_a_first_run_passes_none() -> None:
    # Every advocate in round 1 and the judge at deliberation 1 take this path.
    result = await Agent(_answers("ok")).run("round 1", message_history=None)

    assert [type(part).__name__ for message in result.all_messages() for part in message.parts] == [
        "UserPromptPart",
        "TextPart",
    ]


async def test_run_two_returns_run_ones_messages_unchanged_as_a_prefix() -> None:
    # Asserted as a prefix rather than by length: a length is satisfied by a history that
    # rewrote its own past, and the round-trip is worthless if run 1's record can be edited
    # by run 2. `execution.md`'s dict assigns `all_messages()` wholesale each round, so a
    # rewrite would silently propagate into every later snapshot.
    agent = Agent(_answers("ok"))

    first = await agent.run("round 1")
    second = await agent.run("round 2", message_history=first.all_messages())

    before = first.all_messages()
    after = second.all_messages()
    assert after[: len(before)] == before
    assert len(after) > len(before)
