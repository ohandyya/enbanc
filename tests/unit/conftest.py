"""The unit tier: `enbanc`'s own behaviour, offline and enforced.

This is the bulk of the suite and the only tier that tests edge cases. A complete
multi-round proceeding belongs here, not in `e2e`: ADR 0003 makes the model injected, so a
whole proceeding runs with no provider in the loop.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
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

    Never called in this tier yet — a tribunal holds its tools and nothing runs them until
    there is a proceeding — but it has to be a real async function with a docstring, because
    that is what PydanticAI derives a tool schema from and what an `Advocate` is annotated to
    take.
    """
    return []


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
