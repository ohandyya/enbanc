"""The unit tier: `enbanc`'s own behaviour, offline and enforced.

This is the bulk of the suite and the only tier that tests edge cases. A complete
multi-round proceeding belongs here, not in `e2e`: ADR 0003 makes the model injected, so a
whole proceeding runs with no provider in the loop.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from enbanc import (
    Advocate,
    Argument,
    Case,
    Concession,
    Continuance,
    Entry,
    Exhibit,
    Interrogatory,
    Judge,
    Response,
    Retrieval,
    Ruling,
    Source,
    Statute,
    ToolFailure,
    Transcript,
    Verdict,
)
from enbanc.tools import web_search


@pytest.fixture(autouse=True)
def _offline(block_network: None) -> None:
    """Every test in this tier runs with the network blocked. See `../conftest.py`."""


#: The proceeding `docs/design/execution.md` ("The proceeding, as messages") writes out and
#: `docs/design/prompting.md` ("The turns") renders: three advocates, two rounds, `REFER`
#: conceding, and `DENY` asked two questions so that it runs twice in round 2. The two design
#: documents are deliberately written against the same proceeding so they cannot drift, and
#: this fixture is the third copy of it — which is why it lives here rather than in one test
#: module. `docs/implementations/rendering.md` explains the precedent; the short version is
#: that `tribunal-construction.md` and `proceeding-core.md` assert against this same record.
#:
#: Note this is **not** `outcomes.md` § 1, which is a seven-entry proceeding with a different
#: continuance. That one is the spine of the round loop's tests, and it arrives with them.


class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"
    REFER = "refer to a senior underwriter for manual review"


class LoanApplication(Case):
    applicant: str
    income: int
    dti: float
    documents: list[str]


def _at(second: int) -> datetime:
    return datetime(2026, 9, 2, 14, 3, second, tzinfo=UTC)


W2 = "s3://underwriting-docs/okonkwo/w2-2024.pdf"
SCHEDULE_C = "s3://underwriting-docs/okonkwo/schedule-c-2024.pdf"


@pytest.fixture
def deny() -> Verdict:
    """The one verdict member the tests below name directly.

    A fixture rather than an import: a `conftest.py` is not a module a test may import from,
    so anything a test needs out of this file reaches it as a fixture value. A member rather
    than the enum class, because `type[Verdict]` has no members to a type checker — the base
    declares none, which is exactly what makes it subclassable. A test that needs the whole
    bench reads `proceeding.verdicts`, which is the same list and is typed.
    """
    return LoanDecision.DENY


@pytest.fixture
def case() -> LoanApplication:
    """The case `prompting.md`'s round-1 turn renders. Nested enough to be worth rendering."""
    return LoanApplication(
        applicant="A. Okonkwo",
        income=182000,
        dti=0.51,
        documents=["w2-2024", "schedule-c-2024"],
    )


async def psql(query: str) -> list[Source]:
    """The warehouse tool every advocate in `outcomes.md` is given.

    A real async function with a docstring, because that is what PydanticAI derives a tool
    schema from and what an `Advocate` is annotated to take. It returns one source, so an
    advocate that searches is issued `s1` and the exhibit it files resolves against a ledger
    row the proceeding actually wrote — rather than against a row a test hand-built.
    """
    return [Source(reference=W2, content="wages: 131,400", label="W-2, 2024")]


@pytest.fixture
def outcomes_kwargs() -> Callable[[], dict[str, Any]]:
    """The tribunal `docs/design/outcomes.md` works every ending through, as keyword arguments.

    **Kwargs rather than a built `Tribunal`**, which is what
    `docs/design/testing.md` ("`outcomes.md` is the spine") asks for in the general case. § 5
    cannot use a factory that returns the object: it tests a constructor that *raises*, so the
    factory would raise first. A test varies one key and calls `Tribunal(**kwargs)` itself;
    one that wants the object writes `Tribunal(**outcomes_kwargs())`.

    A callable rather than a dict so that a test mutating what it got cannot reach the next
    test. `advocates` is rebuilt per call for the same reason — a shallow `dict(...)` of a
    module-level mapping would share the inner dict.

    `web_search` is the real factory with a key that is not one: its `__init__` builds an
    `httpx.AsyncClient` and performs no I/O, so the object `outcomes.md` shows is the object
    the fixture holds, and the socket guard has nothing to catch.
    """

    def build() -> dict[str, Any]:
        return {
            "question": "Shall the bank loan this applicant $500k?",
            "verdicts": LoanDecision,
            "statute": Statute(
                text="Approve $500k loans only where DTI < 0.43 and ...",
                name="underwriting-v3",
            ),
            "model": TestModel(),
            "judge": Judge(guidance="Where the record is ambiguous, deny."),
            "advocates": {
                LoanDecision.APPROVE: Advocate(
                    tools=[psql, web_search(api_key="tvly-not-a-real-key")]
                ),
                LoanDecision.DENY: Advocate(tools=[psql]),
                LoanDecision.REFER: Advocate(tools=[psql]),
            },
            "max_rounds": 5,
        }

    return build


@pytest.fixture
def proceeding(case: LoanApplication) -> Transcript[LoanDecision]:
    """The whole eight-entry record, with a ledger and one failed call.

    The ledger holds one row no exhibit cites — `approve/s3`, which is also the fixture's
    anonymous source, so the `not cited` join and the two-line no-label shape are both
    exercised by real data rather than by a hand-built row.
    """
    return Transcript[LoanDecision](
        question="Shall the bank loan this applicant $500k?",
        statute=Statute(
            text="Approve $500k loans only where DTI < 0.43 and ...",
            name="underwriting-v3",
        ),
        case=case,
        verdicts=list(LoanDecision),
        max_rounds=5,
        guidance={
            "judge": "Where the record is ambiguous, deny.",
            LoanDecision.DENY: "Weigh documented income over stated income.",
        },
        procedure="p1",
        entries=[
            Entry[LoanDecision](
                round=1,
                filed_at=_at(11),
                filing=Argument[LoanDecision](
                    advocate=LoanDecision.APPROVE,
                    claim="DTI is 0.38 on documented income.",
                    exhibits=[
                        Exhibit(
                            source="s1",
                            tool="psql",
                            reference=SCHEDULE_C,
                            content="net profit: 182,000",
                            label="Schedule C, 2024",
                        )
                    ],
                ),
            ),
            Entry[LoanDecision](
                round=1,
                filed_at=_at(14),
                filing=Argument[LoanDecision](
                    advocate=LoanDecision.DENY,
                    claim="Documented wages put DTI at 0.51.",
                    exhibits=[
                        Exhibit(
                            source="s1",
                            tool="psql",
                            reference=W2,
                            content="wages: 131,400",
                            label="W-2, 2024",
                        )
                    ],
                ),
            ),
            Entry[LoanDecision](
                round=1,
                filed_at=_at(15),
                filing=Concession[LoanDecision](
                    advocate=LoanDecision.REFER,
                    reason="The ratios are unambiguous; nothing here calls for manual review.",
                ),
            ),
            Entry[LoanDecision](
                round=1,
                filed_at=_at(22),
                filing=Continuance[LoanDecision](
                    interrogatories=[
                        Interrogatory[LoanDecision](
                            id="r1-q1",
                            to=LoanDecision.APPROVE,
                            question="Does the W-2 reconcile with the Schedule C figure?",
                        ),
                        Interrogatory[LoanDecision](
                            id="r1-q2",
                            to=LoanDecision.DENY,
                            question=(
                                "Is stated income disqualifying when documented income is on file?"
                            ),
                        ),
                        Interrogatory[LoanDecision](
                            id="r1-q3",
                            to=LoanDecision.DENY,
                            question="Would a verified 2024 return change your answer?",
                        ),
                    ]
                ),
            ),
            Entry[LoanDecision](
                round=2,
                filed_at=_at(31),
                filing=Response[LoanDecision](
                    advocate=LoanDecision.APPROVE,
                    answering="r1-q1",
                    answer="The Schedule C figure is gross; the W-2 is the reconciled number.",
                    exhibits=[
                        Exhibit(
                            source="s2",
                            tool="psql",
                            reference=W2,
                            content="wages: 131,400",
                            label="W-2, 2024",
                        )
                    ],
                ),
            ),
            Entry[LoanDecision](
                round=2,
                filed_at=_at(35),
                filing=Response[LoanDecision](
                    advocate=LoanDecision.DENY,
                    answering="r1-q2",
                    answer="Yes — the statute's ceiling is on documented income.",
                    exhibits=[
                        Exhibit(
                            source="s2",
                            tool="psql",
                            reference=W2,
                            content="wages: 131,400",
                            label="W-2, 2024",
                        )
                    ],
                ),
            ),
            Entry[LoanDecision](
                round=2,
                filed_at=_at(39),
                filing=Response[LoanDecision](
                    advocate=LoanDecision.DENY,
                    answering="r1-q3",
                    answer="No — a verified return restates the same wages.",
                ),
            ),
            Entry[LoanDecision](
                round=2,
                filed_at=_at(44),
                filing=Ruling[LoanDecision](
                    verdict=LoanDecision.DENY,
                    reasoning=(
                        "Documented income governs. The W-2 record puts DTI at 0.51, above "
                        "the 0.43 ceiling; the stated figure is unverified."
                    ),
                ),
            ),
        ],
        ledger=[
            Retrieval[LoanDecision](
                id="s1",
                round=1,
                advocate=LoanDecision.APPROVE,
                tool="psql",
                reference=SCHEDULE_C,
                content="net profit: 182,000",
                label="Schedule C, 2024",
            ),
            Retrieval[LoanDecision](
                id="s2",
                round=2,
                advocate=LoanDecision.APPROVE,
                tool="psql",
                reference=W2,
                content="wages: 131,400",
                label="W-2, 2024",
            ),
            # No label, and nothing cites it: the anonymous-source shape and the suppression
            # join, in one row.
            Retrieval[LoanDecision](
                id="s3",
                round=1,
                advocate=LoanDecision.APPROVE,
                tool="dti_for",
                reference='dti_for(applicant="A. Okonkwo")',
                content="dti: 0.51",
            ),
            Retrieval[LoanDecision](
                id="s1",
                round=1,
                advocate=LoanDecision.DENY,
                tool="psql",
                reference=W2,
                content="wages: 131,400",
                label="W-2, 2024",
            ),
            Retrieval[LoanDecision](
                id="s2",
                round=2,
                advocate=LoanDecision.DENY,
                tool="psql",
                reference=W2,
                content="wages: 131,400",
                label="W-2, 2024",
            ),
        ],
        failures=[
            ToolFailure[LoanDecision](
                round=1,
                advocate=LoanDecision.DENY,
                tool="find_filings",
                reference='find_filings(applicant="A. Okonkwo")',
                detail="Timed out after 30.0 seconds.",
            )
        ],
    )


# ---------------------------------------------------------------------------------------------
# A proceeding, faked: the bench that scripts every participant, and the invariant it is
# checked against. Both are fixtures rather than importable helpers because a `conftest.py` is
# not a module a test may import from — see `deny` above.
# ---------------------------------------------------------------------------------------------

#: How a participant is identified from the turn it was handed. The fake reads the same prompt
#: a real model reads, rather than being told out of band which agent it is standing in for, so
#: a turn template that stopped naming the advocate would break the bench loudly.
_ADVOCATE_TURN = re.compile(r'File your argument for "(?P<verdict>.+)", or concede\.')

#: Message parts that carry something no rendered turn contains, and are accounted for rather
#: than derived. `docs/design/execution.md` ("What lands in history that no rendered turn
#: contains") enumerates exactly these: tool traffic covered by `Transcript.ledger`, retry
#: prompts (`0021`), the output tool's receipt, and the agent's own pre-stamp output — which is
#: a `ToolCallPart`, because a filing lands in history as a tool call.
#:
#: `TextPart` is deliberately absent. `execution.md` claims there is none on the path an
#: `enbanc` participant takes, ever, so one appearing is a claim to re-check rather than an
#: escape to widen.
_ESCAPES = (ToolCallPart, ToolReturnPart, RetryPromptPart)

#: Lines a turn template contributes that the transcript does not hold. They are procedure, not
#: record: `docs/design/prompting.md` owns them and `Transcript.procedure` versions them, which
#: is why the invariant is about the facts around them.
_TURN_SCAFFOLDING = (
    re.compile(r"^## (The case|Round \d+|Addressed to you)$"),
    re.compile(r"^## Filed since you last (filed|deliberated)$"),
    re.compile(r'^Round \d+\. File your argument for ".+", or concede\.$'),
    re.compile(r"^Round \d+\. Answer \S+ and file your response\.$"),
    re.compile(r"^Deliberation \d+ of \d+\. Rule, or issue a continuance\.$"),
)


def _turn(messages: list[ModelMessage]) -> str:
    """The last user prompt: the turn this request is answering."""
    prompts = [
        part.content
        for message in messages
        for part in getattr(message, "parts", ())
        if isinstance(part, UserPromptPart)
    ]
    return str(prompts[-1]) if prompts else ""


def _participant(messages: list[ModelMessage]) -> Any:
    """Whose turn this is — a verdict member, or the string `"judge"`."""
    named = _ADVOCATE_TURN.search(_turn(messages))
    return LoanDecision(named.group("verdict")) if named else "judge"


def _output_tool(info: AgentInfo, kind: str) -> str:
    """The output tool for one filing shape, found by the class name PydanticAI derived it from.

    Matched on a substring rather than spelled out, because the full names are the
    dependency's. `test_agents.py` is where they are pinned as text; everywhere else a bench
    that kept working after a rename is the right behaviour.
    """
    return next(tool.name for tool in info.output_tools or () if kind in tool.name)


@dataclass
class Bench:
    """Every participant in one faked proceeding, scripted and capturing.

    `model` is one `FunctionModel` standing in for the whole bench: it reads the turn to work
    out whose run it is in, which is what lets a single object play four agents. `captured`
    holds every `ModelMessage` list each participant was handed, in order, which is the exact
    context it ran under and the only thing that can settle whether the invariant held.
    """

    concedes: frozenset[Any] = frozenset()
    searches: frozenset[Any] = frozenset()
    cites: frozenset[Any] = frozenset()
    continues: bool = False
    verdict: Any = None
    captured: dict[Any, list[list[ModelMessage]]] = field(default_factory=dict)

    @property
    def model(self) -> FunctionModel:
        return FunctionModel(self._respond)

    def _respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        who = _participant(messages)
        self.captured.setdefault(who, []).append(messages)
        if who == "judge":
            return self._deliberate(info)
        return self._file(who, messages, info)

    def _deliberate(self, info: AgentInfo) -> ModelResponse:
        if self.continues:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        _output_tool(info, "Continuance"),
                        {
                            "interrogatories": [
                                {"to": LoanDecision.DENY.value, "question": "Is that documented?"}
                            ]
                        },
                    )
                ]
            )
        verdict = self.verdict if self.verdict is not None else LoanDecision.DENY
        return ModelResponse(
            parts=[
                ToolCallPart(
                    _output_tool(info, "Ruling"),
                    {
                        "verdict": verdict.value,
                        "reasoning": "Documented income governs; the stated figure is unverified.",
                    },
                )
            ]
        )

    def _file(self, who: Any, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if who in self.concedes:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        _output_tool(info, "Concession"),
                        {
                            "advocate": who.value,
                            "reason": "The ratios are unambiguous; nothing calls for review.",
                        },
                    )
                ]
            )
        if who in self.searches and not self._searched(messages):
            return ModelResponse(parts=[ToolCallPart("psql", {"query": "select wages from w2"})])
        exhibits = [{"source": "s1", "content": "wages: 131,400"}] if who in self.cites else []
        return ModelResponse(
            parts=[
                ToolCallPart(
                    _output_tool(info, "Argument"),
                    {
                        "advocate": who.value,
                        "claim": f"The record supports {who.value}.",
                        "exhibits": exhibits,
                    },
                )
            ]
        )

    @staticmethod
    def _searched(messages: list[ModelMessage]) -> bool:
        return any(
            isinstance(part, ToolReturnPart) and part.tool_name == "psql"
            for message in messages
            for part in getattr(message, "parts", ())
        )


@pytest.fixture
def bench() -> Callable[..., Bench]:
    """A factory for the faked bench above, so each test scripts only what it varies.

        proceeding_bench = bench(searches={deny}, cites={deny}, concedes={refer})
        tribunal = Tribunal(**(outcomes_kwargs() | {"model": proceeding_bench.model}))

    A factory rather than a value because `captured` accumulates: two tests sharing one
    instance would read each other's runs.
    """
    return Bench


@pytest.fixture
def assert_invariant_held() -> Callable[..., None]:
    """*Nothing enters an agent's context that is not also in the transcript*, checked.

    Takes what the capturing bench recorded, the transcript that resulted, and the tribunal's
    own `instructions_for`, and requires every part of every message to be one of:

    * the instructions — asserted equal to `instructions_for(participant)`, so the string a
      caller can preview is the string the agent actually ran under;
    * a user prompt whose every line is either in `render(transcript, ReviewerView())` or is
      turn scaffolding, which is procedure rather than record;
    * one of the four escapes `docs/design/execution.md` enumerates.

    **It cannot be a substring test**, which is why it compares line by line and accepts the
    escapes by type: an advocate emits a bare `_Exhibit` while the transcript holds the stamped
    public `Exhibit` (`0016`), so the record is a *superset* of what the agent wrote and a
    byte-for-byte containment check fails on a proceeding that is perfectly correct.

    An assertion rather than a test: any proceeding-level test can call it, so every future
    test of every other behaviour also happens to check that nothing leaked.
    """

    def check(
        captured: dict[Any, list[list[ModelMessage]]],
        transcript: Transcript[Any],
        instructions_for: Callable[[Any], str],
    ) -> None:
        record = transcript.render()
        for participant, runs in captured.items():
            expected = instructions_for(participant)
            for messages in runs:
                for message in messages:
                    _check_message(message, participant, expected, record)

    def _check_message(
        message: ModelMessage, participant: Any, instructions: str, record: str
    ) -> None:
        if isinstance(message, ModelRequest) and message.instructions is not None:
            assert message.instructions == instructions, (
                f"{participant} ran under instructions that are not the ones "
                f"instructions_for({participant!r}) returns"
            )
        for part in getattr(message, "parts", ()):
            if isinstance(part, UserPromptPart):
                _check_prompt(str(part.content), participant, record)
            else:
                assert isinstance(part, _ESCAPES), (
                    f"{participant}'s context holds a {type(part).__name__}, which is neither "
                    f"derived from the transcript nor one of execution.md's four escapes"
                )

    def _check_prompt(prompt: str, participant: Any, record: str) -> None:
        for line in prompt.splitlines():
            if not line.strip() or any(shape.match(line) for shape in _TURN_SCAFFOLDING):
                continue
            assert line in record, (
                f"{participant} was shown a line the transcript does not hold: {line!r}"
            )

    return check
