"""The ledgering toolset, driven the way a proceeding drives it.

Pins `docs/design/evidence.md` ("How a source becomes an exhibit", "The ledger is part of the
record", "A call that returned nothing is recorded too") and
`docs/design/execution.md`'s piece 2.

**Every test here goes through a real `Agent`, and that is not incidental.** The toolset is
`replace()`d for each run (`tests/contract/test_a_wrapper_toolset_is_rebuilt_per_run.py`), and
that copy happens inside `Agent.run`. A test that called `ledgering.call_tool(...)` directly
would run on the original instance, where a counter field and a shared list behave
identically — so it would pass against the one implementation this module must not have. The
`CombinedToolset` is not optional either: wrapping a bare `FunctionToolset` skips the replace
entirely.

Offline throughout: a `FunctionModel`, plain async functions, and `Tool(fn, timeout=...)` for
the timeout.
"""

from typing import Any

import anyio
import pytest
from pydantic_ai import Agent, AgentRunResult, ModelRetry, Tool
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.toolsets import CombinedToolset, FunctionToolset

from enbanc import Retrieval, Source, ToolFailure, Verdict
from enbanc._ledgering import Ledgering

#: Short enough that the timeout fires immediately, against a tool that would otherwise
#: outlast the suite.
TIMEOUT = 0.01
FOREVER = 5.0

SCHEDULE_C = "s3://underwriting-docs/okonkwo/schedule-c-2024.pdf"
W2 = "s3://underwriting-docs/okonkwo/w2-2024.pdf"


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


async def find_filings(applicant: str) -> list[Source]:
    """Search the document store for filings belonging to the applicant."""
    return [
        Source(reference=SCHEDULE_C, label="Schedule C, 2024", content="net profit: 182,000"),
        Source(reference=W2, label="W-2, 2024", content="wages: 131,400"),
    ]


async def dti_for(applicant: str) -> str:
    """Look up the applicant's debt-to-income ratio from the warehouse."""
    return "dti: 0.51"


async def explodes() -> str:
    """Raise something that is not a `ModelRetry`."""
    raise RuntimeError("the warehouse is down")


async def corrects() -> str:
    """Raise a `ModelRetry` the way a tool correcting the model does."""
    raise ModelRetry("narrow the query")


async def slow() -> str:
    """Outlast its own timeout."""
    await anyio.sleep(FOREVER)
    raise AssertionError("unreachable: the timeout fires first")


def scripted(*calls: tuple[str, dict[str, Any]]) -> FunctionModel:
    """A model that makes exactly the listed calls, then stops.

    Finite by construction: a `FunctionModel` that calls unconditionally hits PydanticAI's
    inherited `request_limit` of fifty and reports `UsageLimitExceeded`, a failure that names
    the wrong subsystem entirely.
    """
    remaining = iter(calls)

    def emit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nxt = next(remaining, None)
        if nxt is None:
            return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(parts=[ToolCallPart(nxt[0], nxt[1])])

    return FunctionModel(emit)


def ledgering(
    verdict: LoanDecision,
    ledger: list[Retrieval[LoanDecision]],
    failures: list[ToolFailure[LoanDecision]],
    *tools: Any,
) -> Ledgering[LoanDecision]:
    """The construction `docs/design/execution.md` prescribes, which the orchestrator makes.

    One wrapper over one `CombinedToolset`, and the lists are the caller's — they stand in for
    `transcript.ledger` and `transcript.failures`.
    """
    return Ledgering[LoanDecision](
        wrapped=CombinedToolset([FunctionToolset(tools=list(tools))]),
        advocate=verdict,
        ledger=ledger,
        failures=failures,
    )


def advocate(
    model: FunctionModel, toolset: Ledgering[LoanDecision], **kwargs: Any
) -> Agent[None, str]:
    """One advocate's agent, built the way `_proceeding.py` will have to build it.

    **`deps_type=type(None)` is not decoration.** `Agent.__init__` defaults that parameter to
    `object` while solving `AgentDepsT` from `toolsets`, so handing it an
    `AbstractToolset[None]` and letting the default stand is a type error about a value
    neither call site wrote. Naming the type is the fix, and the orchestrator owes the same
    line.
    """
    return Agent(model, toolsets=[toolset], deps_type=type(None), **kwargs)


def returns(result: AgentRunResult[str]) -> list[Any]:
    return [
        p.content for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart)
    ]


async def test_every_source_a_tool_returned_is_ledgered() -> None:
    ledger: list[Retrieval[LoanDecision]] = []
    toolset = ledgering(LoanDecision.APPROVE, ledger, [], find_filings, dti_for)
    agent = advocate(scripted(("find_filings", {"applicant": "A. Okonkwo"})), toolset)

    await agent.run("retrieve")

    assert [(row.id, row.tool, row.reference, row.label) for row in ledger] == [
        ("s1", "find_filings", SCHEDULE_C, "Schedule C, 2024"),
        ("s2", "find_filings", W2, "W-2, 2024"),
    ]
    # Verbatim, as the tool returned it. `enbanc` truncates nothing.
    assert [row.content for row in ledger] == ["net profit: 182,000", "wages: 131,400"]


async def test_two_sources_from_one_call_get_two_ids() -> None:
    """The bug a single-source test cannot see.

    `base` is read once, before any row is built. A `next_id()` that counted the ledger per
    row would issue `s1` twice, because nothing is appended until the `extend`.
    """
    ledger: list[Retrieval[LoanDecision]] = []
    toolset = ledgering(LoanDecision.DENY, ledger, [], find_filings)
    agent = advocate(scripted(("find_filings", {"applicant": "A. Okonkwo"})), toolset)

    await agent.run("retrieve")

    assert [row.id for row in ledger] == ["s1", "s2"]


async def test_ids_do_not_restart_between_rounds() -> None:
    """`0016`'s whole point: a round-3 response can cite a round-1 find.

    This is also the test that fails if the id is counted into an `int` field, because the
    second run's copy would be built from a value the first run never wrote back.
    """
    ledger: list[Retrieval[LoanDecision]] = []
    toolset = ledgering(LoanDecision.DENY, ledger, [], find_filings, dti_for)

    await advocate(scripted(("find_filings", {"applicant": "A. Okonkwo"})), toolset).run("round 1")
    toolset.round = 2
    await advocate(scripted(("dti_for", {"applicant": "A. Okonkwo"})), toolset).run("round 2")

    assert [(row.id, row.round) for row in ledger] == [("s1", 1), ("s2", 1), ("s3", 2)]


async def test_round_is_stamped_from_the_attribute_the_orchestrator_sets() -> None:
    ledger: list[Retrieval[LoanDecision]] = []
    toolset = ledgering(LoanDecision.APPROVE, ledger, [], dti_for)
    toolset.round = 4

    await advocate(scripted(("dti_for", {"applicant": "A. Okonkwo"})), toolset).run("go")

    assert [row.round for row in ledger] == [4]


async def test_two_advocates_number_independently_over_one_ledger() -> None:
    """Ids are numbered within an advocate, which is why the join key is `(advocate, id)`.

    One shared list, two toolsets: `APPROVE`'s `s1` and `DENY`'s `s1` are different
    retrievals, and neither can see the other's count.
    """
    ledger: list[Retrieval[LoanDecision]] = []
    approve = ledgering(LoanDecision.APPROVE, ledger, [], dti_for)
    deny = ledgering(LoanDecision.DENY, ledger, [], dti_for)

    for toolset in (approve, deny, approve):
        await advocate(scripted(("dti_for", {"applicant": "A. Okonkwo"})), toolset).run("go")

    assert [(str(row.advocate), row.id) for row in ledger] == [
        ("approve", "s1"),
        ("deny", "s1"),
        ("approve", "s2"),
    ]


async def test_the_advocate_reads_the_rewritten_result() -> None:
    """The rewrite is what makes an id citable: the wrapper's return *is* the tool return."""
    toolset = ledgering(LoanDecision.APPROVE, [], [], dti_for)
    agent = advocate(scripted(("dti_for", {"applicant": "A. Okonkwo"})), toolset)

    result = await agent.run("retrieve")

    assert returns(result) == [
        'dti_for(applicant="A. Okonkwo") returned 1 source.\n\n'
        '[s1] dti_for(applicant="A. Okonkwo")\n'
        "  dti: 0.51"
    ]


async def test_a_tool_timeout_is_recorded_and_re_raised() -> None:
    """The seam between a degraded advocate and an unheard one.

    PydanticAI converts the `TimeoutError` into `ModelRetry` before the wrapper sees it, so
    `detail` is its string rather than one `enbanc` composed — and the bare `raise` is what
    lets the advocate be corrected rather than silently starved.
    """
    ledger: list[Retrieval[LoanDecision]] = []
    failures: list[ToolFailure[LoanDecision]] = []
    toolset = ledgering(LoanDecision.DENY, ledger, failures, Tool(slow, timeout=TIMEOUT))
    toolset.round = 2
    agent = advocate(scripted(("slow", {})), toolset, retries={"tools": 2})

    result = await agent.run("retrieve")

    assert [(f.round, str(f.advocate), f.tool, f.reference, f.detail) for f in failures] == [
        (2, "deny", "slow", "slow()", f"Timed out after {TIMEOUT} seconds.")
    ]
    # No source came back, so no `Retrieval` — the absent id is the type saying a failed call
    # can never be cited.
    assert ledger == []
    retries = [p for m in result.all_messages() for p in m.parts if isinstance(p, RetryPromptPart)]
    assert [p.content for p in retries] == [f"Timed out after {TIMEOUT} seconds."]


async def test_a_model_retry_a_tool_raised_itself_is_recorded_too() -> None:
    """One row per attempt, and a deliberate `ModelRetry` is still a call that returned
    nothing."""
    failures: list[ToolFailure[LoanDecision]] = []
    toolset = ledgering(LoanDecision.DENY, [], failures, corrects)
    agent = advocate(
        scripted(("corrects", {}), ("corrects", {})),
        toolset,
        retries={"tools": 3},  # `enbanc`'s own default, set where agents are built
    )

    await agent.run("retrieve")

    assert [(f.tool, f.detail) for f in failures] == [
        ("corrects", "narrow the query"),
        ("corrects", "narrow the query"),
    ]


async def test_a_tool_that_raises_anything_else_propagates() -> None:
    """An advocate that could not gather evidence has not been heard.

    It is not caught, not retried, and not recorded — the one `except` clause is the whole
    distinction, so a test that this exception reaches the caller is a test of that clause.
    """
    ledger: list[Retrieval[LoanDecision]] = []
    failures: list[ToolFailure[LoanDecision]] = []
    toolset = ledgering(LoanDecision.DENY, ledger, failures, explodes)
    agent = advocate(scripted(("explodes", {})), toolset)

    with pytest.raises(RuntimeError, match="the warehouse is down"):
        await agent.run("retrieve")

    assert ledger == []
    assert failures == []


async def test_a_tool_that_came_up_empty_writes_nothing_either_way() -> None:
    """It neither found anything nor failed, so it is neither a retrieval nor a failure."""

    async def nothing_found(applicant: str) -> list[Source]:
        """Search, and come up empty."""
        return []

    ledger: list[Retrieval[LoanDecision]] = []
    failures: list[ToolFailure[LoanDecision]] = []
    toolset = ledgering(LoanDecision.APPROVE, ledger, failures, nothing_found)
    agent = advocate(scripted(("nothing_found", {"applicant": "A. Okonkwo"})), toolset)

    result = await agent.run("retrieve")

    assert ledger == []
    assert failures == []
    assert returns(result) == ['nothing_found(applicant="A. Okonkwo") returned 0 sources.']


async def test_the_wrapper_offers_the_model_the_tools_it_wrapped() -> None:
    """`get_tools` is not overridden: the interception is invisible to a tool author."""
    seen: list[list[str]] = []

    def record(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append([tool.name for tool in info.function_tools])
        return ModelResponse(parts=[TextPart("done")])

    toolset = ledgering(LoanDecision.APPROVE, [], [], find_filings, dti_for)

    await advocate(FunctionModel(record), toolset).run("retrieve")

    assert seen[0] == ["find_filings", "dti_for"]
