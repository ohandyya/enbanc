"""What `enbanc` builds an agent with, read off the wire rather than off the source.

One `Agent` per participant, built inside the proceeding: the instructions a caller can
preview, the two retry budgets, the output tools each participant is offered, the one
concurrency limiter the fan-out shares, and the usage limit `enbanc` deliberately does not
pass. Every assertion here is about a value that reaches PydanticAI or the model — a test that
read the module's own constants back would assert nothing.

`docs/design/execution.md` ("Also in scope", "An output validator forbids a per-run
`output_type`") is the spec, and `docs/implementations/proceeding-core.md` is where the
output-function shape and its consequences are worked out.
"""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic_ai import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from enbanc import Advocate, Case, Judge, Tribunal

Kwargs = Callable[[], dict[str, Any]]


def _turn(messages: list[ModelMessage]) -> str:
    """The user prompt this run opened with — the turn, wherever it sits in the history."""
    return next(
        str(part.content)
        for message in messages
        for part in getattr(message, "parts", ())
        if type(part).__name__ == "UserPromptPart"
    )


def _leaves(error: BaseException) -> list[BaseException]:
    """Every non-group exception inside a possibly nested `ExceptionGroup`."""
    if isinstance(error, BaseExceptionGroup):
        return [leaf for exc in error.exceptions for leaf in _leaves(exc)]
    return [error]


def _recording(seen: list[tuple[str, AgentInfo, list[ModelMessage]]]) -> FunctionModel:
    """A model that records what each request was configured with, then concedes or rules.

    It reads the turn to know which participant it is standing in for, the same way the shared
    bench fixture does — and unlike that fixture it keeps the whole `AgentInfo`, which is where
    the output tools and the run's usage limits are visible.
    """

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompt = _turn(messages)
        who = "judge" if "Deliberation" in prompt else prompt.split('for "')[1].split('"')[0]
        seen.append((who, info, messages))
        if who == "judge":
            tool = next(t.name for t in info.output_tools or () if "Ruling" in t.name)
            return ModelResponse(
                parts=[ToolCallPart(tool, {"verdict": "deny", "reasoning": "Documented."})]
            )
        tool = next(t.name for t in info.output_tools or () if "Concession" in t.name)
        return ModelResponse(parts=[ToolCallPart(tool, {"advocate": who, "reason": "No case."})])

    return FunctionModel(respond)


@pytest.fixture
async def wire(outcomes_kwargs: Kwargs, case: Case) -> list[tuple[str, AgentInfo, Any]]:
    """One proceeding, with everything each participant's agent was built with recorded."""
    seen: list[tuple[str, AgentInfo, Any]] = []
    kwargs = outcomes_kwargs()
    tribunal = Tribunal(**{**kwargs, "model": _recording(seen), "max_concurrency": 2})
    await tribunal.hear(case)
    return seen


async def test_the_instructions_are_the_ones_a_caller_can_preview(
    outcomes_kwargs: Kwargs, case: Case
) -> None:
    """`instructions_for()` is only worth having if it is the same string the agent runs under.

    `tribunal-construction.md` pinned the assembly and left this half here, because only a
    proceeding puts the parts on a wire. PydanticAI resolves instructions per request, so this
    also covers *what the model was actually sent*, not merely what was handed to `Agent()`.
    """
    seen: list[tuple[str, AgentInfo, Any]] = []
    kwargs = outcomes_kwargs()
    tribunal = Tribunal(**{**kwargs, "model": _recording(seen)})

    await tribunal.hear(case)

    for who, _info, messages in seen:
        participant = "judge" if who == "judge" else kwargs["verdicts"](who)
        request = next(m for m in messages if isinstance(m, ModelRequest))
        assert request.instructions == tribunal.instructions_for(participant)


async def test_an_advocate_is_offered_an_argument_and_a_concession(
    wire: list[tuple[str, AgentInfo, Any]],
) -> None:
    """Round 1's output shape, as the model sees it: the two filings it may make, and the tool
    names PydanticAI derives from the classes behind them.

    The names are the dependency's rather than `enbanc`'s prompting surface, so they are not
    covered by `Transcript.procedure` — but they are text a model reads, and
    `docs/design/execution.md`'s worked traces quote them, so they are pinned here.
    """
    advocates = [info for who, info, _ in wire if who != "judge"]

    for info in advocates:
        assert sorted(tool.name for tool in info.output_tools or ()) == [
            "final_result_ConcessionLoanDecision",
            "final_result__ArgumentLoanDecision",
        ]


async def test_the_judge_is_offered_a_ruling_and_a_continuance(
    wire: list[tuple[str, AgentInfo, Any]],
) -> None:
    """A `Ruling` or a `_Continuance`, never free text — and the continuance is the private
    shape, because a continuance's ids are the tribunal's to stamp."""
    judge = next(info for who, info, _ in wire if who == "judge")

    assert sorted(tool.name for tool in judge.output_tools or ()) == [
        "final_result_RulingLoanDecision",
        "final_result__ContinuanceLoanDecision",
    ]


async def test_the_verdict_values_reach_the_model_in_the_output_schema(
    wire: list[tuple[str, AgentInfo, Any]],
) -> None:
    """The judge learns the bench from `Ruling.verdict`'s own schema, which is why it gets no
    assignment instruction part.

    This is what a filing parameterized with a bare `TypeVar` would silently lose: Pydantic
    returns the origin class for one, and the enum would arrive as `enum: []` — every verdict
    the caller declared rejected, and the output budget exhausted explaining it.
    """
    judge = next(info for who, info, _ in wire if who == "judge")
    ruling = next(t for t in judge.output_tools or () if "Ruling" in t.name)

    defs = ruling.parameters_json_schema["$defs"]
    assert defs["LoanDecision"]["enum"] == [
        "approve",
        "deny",
        "refer to a senior underwriter for manual review",
    ]


async def test_an_output_tool_carries_no_enbanc_authored_description(
    wire: list[tuple[str, AgentInfo, Any]],
) -> None:
    """An output function's docstring becomes the tool's description — so the ones `enbanc`
    builds carry none, and the model reads PydanticAI's own generic sentence.

    Prompt text is `docs/design/prompting.md`'s and is versioned by `Transcript.procedure`; a
    sentence that slipped in here would be neither.
    """
    for _who, info, _messages in wire:
        for tool in info.output_tools or ():
            assert tool.description is not None
            assert tool.description.endswith("The final response which ends this conversation")


async def test_both_retry_budgets_are_set_on_every_agent(
    outcomes_kwargs: Kwargs, case: Case
) -> None:
    """`{'tools': 3, 'output': 2}`, and they are independent: three failures of the *same* tool
    before an advocate is treated as unheard, two corrections of an output that will not
    validate. Neither is configurable through `enbanc` (`0030`)."""
    seen: list[tuple[str, AgentInfo, Any]] = []
    kwargs = outcomes_kwargs()
    tribunal = Tribunal(**{**kwargs, "model": _recording(seen)})

    async with tribunal.hear_stream(case) as proceeding:
        async for _ in proceeding:
            pass

    # Read off the orchestrator the proceeding is running, which is the object that built the
    # agents — the tribunal deliberately holds none of this.
    orchestrator = proceeding._orchestrator  # noqa: SLF001
    agents = [*orchestrator.advocate_agents.values(), orchestrator.judge_agent]
    assert [(a._max_tool_retries, a._max_output_retries) for a in agents] == [(3, 2)] * len(agents)  # noqa: SLF001


async def test_one_limiter_is_shared_by_every_advocate_and_the_judge_gets_none(
    outcomes_kwargs: Kwargs, case: Case
) -> None:
    """`max_concurrency` bounds the fan-out, and it is an `Agent.__init__` parameter — so one
    limiter per advocate would be no limit across the bench at all.

    The judge is never given a slot: it runs alone, and the fan-out is the only place
    concurrency exists in a proceeding (`0024`).
    """
    kwargs = outcomes_kwargs()
    tribunal = Tribunal(**{**kwargs, "model": _recording([]), "max_concurrency": 2})

    async with tribunal.hear_stream(case) as proceeding:
        async for _ in proceeding:
            pass

    orchestrator = proceeding._orchestrator  # noqa: SLF001
    limiters = {id(a._concurrency_limiter) for a in orchestrator.advocate_agents.values()}  # noqa: SLF001
    assert limiters == {id(orchestrator.limiter)}
    assert orchestrator.limiter is not None
    assert orchestrator.judge_agent._concurrency_limiter is None  # noqa: SLF001


async def test_an_unbounded_tribunal_builds_no_limiter(outcomes_kwargs: Kwargs, case: Case) -> None:
    """`max_concurrency=None` is the default, and it stays `None` rather than becoming a
    limiter with a very large number in it."""
    tribunal = Tribunal(**{**outcomes_kwargs(), "model": _recording([])})

    async with tribunal.hear_stream(case) as proceeding:
        async for _ in proceeding:
            pass

    assert proceeding._orchestrator.limiter is None  # noqa: SLF001


async def test_no_usage_limit_is_passed_into_a_run(outcomes_kwargs: Kwargs, case: Case) -> None:
    """`enbanc` passes none, so PydanticAI's inherited default stands: fifty model requests per
    participant per round.

    Asserted where it is observable — an advocate that never stops searching is stopped by that
    ceiling, and a run that exhausts it is a participant that could not be heard. Passing a
    limit of `enbanc`'s own would move this number; passing an unlimited one would hang the
    test rather than fail it, which is why the loop is unbounded on purpose.

    That fifty is not `enbanc`'s number, and it is at a different scope from a `budget`'s
    `request_limit` — one bounds a single run, the other the whole proceeding — which is why
    the latter may not be inherited (`0029`).
    """

    def never_files(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart("psql", {"query": "select wages"})])

    tribunal = Tribunal(**{**outcomes_kwargs(), "model": FunctionModel(never_files)})

    with pytest.raises(BaseExceptionGroup) as caught:
        await tribunal.hear(case)

    # Every advocate that got that far hits it, because the task group here is the plain one:
    # nothing cancels the siblings until `docs/implementations/failures.md` adds the
    # first-failure slot. How many is scheduling, so the assertion is about what they are.
    stopped = _leaves(caught.value)
    assert stopped
    assert all(isinstance(exc, UsageLimitExceeded) for exc in stopped)
    assert all("request_limit of 50" in str(exc) for exc in stopped)


async def test_a_per_advocate_model_overrides_the_tribunals(
    outcomes_kwargs: Kwargs, case: Case
) -> None:
    """A strong judge over cheap advocates is advertised as a one-line change, so the override
    has to actually reach the agent that was built for that participant."""
    tribunal_seen: list[tuple[str, AgentInfo, Any]] = []
    advocate_seen: list[tuple[str, AgentInfo, Any]] = []
    judge_seen: list[tuple[str, AgentInfo, Any]] = []
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    kwargs["advocates"][deny] = Advocate(tools=[], model=_recording(advocate_seen))
    kwargs["judge"] = Judge(
        guidance="Where the record is ambiguous, deny.", model=_recording(judge_seen)
    )
    tribunal = Tribunal(**{**kwargs, "model": _recording(tribunal_seen)})

    await tribunal.hear(case)

    assert [who for who, _, _ in advocate_seen] == [deny.value]
    assert [who for who, _, _ in judge_seen] == ["judge"]
    assert sorted(who for who, _, _ in tribunal_seen) == sorted([approve.value, refer.value])


async def test_a_callable_toolset_reaches_the_ledger(outcomes_kwargs: Kwargs, case: Case) -> None:
    """`Advocate.toolsets` admits the callable form PydanticAI resolves per run, and handing one
    straight to the agent would put its tool calls outside the wrapper — so it is wrapped in
    the same `DynamicToolset` the agent would have wrapped it in.

    The assertion is a ledger row: the call was intercepted, which is the only thing that makes
    *everything your tools return is recorded* true of this form too.
    """
    from pydantic_ai import RunContext
    from pydantic_ai.toolsets import FunctionToolset

    from enbanc import Source

    async def fetch_filing(applicant: str) -> list[Source]:
        """Pull a filing from the archive."""
        return [Source(reference="archive://2024", content="filed 2024-04-01")]

    def archive(ctx: RunContext[None]) -> FunctionToolset[None]:
        return FunctionToolset[None](tools=[fetch_filing])

    def call_the_dynamic_tool(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompt = _turn(messages)
        if "Deliberation" in prompt:
            tool = next(t.name for t in info.output_tools or () if "Ruling" in t.name)
            return ModelResponse(
                parts=[ToolCallPart(tool, {"verdict": "deny", "reasoning": "Documented."})]
            )
        who = prompt.split('for "')[1].split('"')[0]
        already_fetched = any(
            "fetch_filing" in str(getattr(part, "tool_name", ""))
            for message in messages
            for part in getattr(message, "parts", ())
        )
        if already_fetched:
            tool = next(t.name for t in info.output_tools or () if "Argument" in t.name)
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool,
                        {
                            "advocate": who,
                            "claim": "The archive has it.",
                            "exhibits": [{"source": "s1", "content": "filed 2024-04-01"}],
                        },
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("fetch_filing", {"applicant": "A. Okonkwo"})])

    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    kwargs["advocates"] = {v: Advocate(toolsets=[archive]) for v in (approve, deny, refer)}
    tribunal = Tribunal(**{**kwargs, "model": FunctionModel(call_the_dynamic_tool)})

    hearing = await tribunal.hear(case)

    assert {(row.tool, row.reference) for row in hearing.transcript.ledger} == {
        ("fetch_filing", "archive://2024")
    }
    assert len(hearing.transcript.ledger) == 3
