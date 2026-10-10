"""`docs/design/outcomes.md` § 1 — the judge rules.

Three advocates argue, one concedes, the judge asks two questions and then rules:

    round 1   Argument(advocate=APPROVE, exhibits=[psql, web_search])
              Argument(advocate=DENY,    exhibits=[psql])
              Concession(advocate=REFER)
              Continuance(interrogatories=[r1-q1 -> APPROVE, r1-q2 -> DENY])

    round 2   Response(advocate=APPROVE, answering="r1-q1")
              Response(advocate=DENY,    answering="r1-q2", exhibits=[psql])
              Ruling(verdict=DENY)

The acceptance test for `docs/implementations/round-loop.md`. What makes it worth having is
the record around the entries: `APPROVE` retrieves a verification status it never files — the
suppression join `0019` exists for — and its round-2 searches time out twice, which is why its
response cites nothing and why it is degraded rather than unheard.

The tools are faked here rather than in `conftest.py`, because only this section needs a
warehouse that answers by query and a search that hangs. Every row below is one a proceeding
wrote: nothing in the ledger or the failures is hand-built.

The doc is mirrored here, never executed. See
`docs/decisions/0032-a-design-doc-is-mirrored-by-tests.md`.
"""

from collections.abc import Callable
from typing import Any

import anyio
import pytest
from pydantic_ai import Tool

from enbanc import (
    Advocate,
    Argument,
    Case,
    Concession,
    Continuance,
    Hearing,
    Response,
    Ruling,
    Source,
    Tribunal,
)

Kwargs = Callable[[], dict[str, Any]]

#: What the warehouse holds, by the table a query names.
_TABLES = {
    "schedule_c": "schedule_c_2024: 182000",
    "verification_status": "verification_status: none",
    "w2": "w2_2024: 131400",
}


async def psql(query: str) -> list[Source]:
    """Run one read-only query against the underwriting warehouse."""
    table = next(name for name in _TABLES if name in query)
    return [Source(reference=f'psql(sql="{query}")', content=_TABLES[table])]


async def web_search(query: str) -> list[Source]:
    """Search the web. Round 1's query is answered; round 2's hang until the timeout fires."""
    if "schedule c" not in query:
        await anyio.sleep(30)
    return [
        Source(
            reference="https://www.irs.gov/forms-pubs/about-schedule-c-form-1040",
            content="Net profit from Schedule C is reportable self-employment income.",
            label="About Schedule C (Form 1040)",
        )
    ]


@pytest.fixture
async def hearing_and_bench(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> tuple[Hearing[Any], Any, Tribunal[Any]]:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        concedes={refer},
        calls={
            approve: [
                ("psql", {"query": "SELECT net_profit FROM schedule_c WHERE applicant = ..."}),
                ("psql", {"query": "SELECT verification_status FROM income_docs WHERE ..."}),
                ("web_search", {"query": "schedule c self-employment income"}),
            ],
            deny: [("psql", {"query": "SELECT wages FROM w2 WHERE applicant = ..."})],
            "r1-q1": [
                ("web_search", {"query": "self-employment income verification underwriting"}),
                ("web_search", {"query": "§4.2 filed income"}),
            ],
            "r1-q2": [("psql", {"query": "SELECT verification_status FROM income_docs WHERE ..."})],
        },
        exhibits={approve: ["s1", "s3"], deny: ["s1"], "r1-q2": ["s2"]},
        continuances=[
            [
                (approve, "Which income figure does §4.2 require?"),
                (deny, "Does the Schedule C qualify as documented?"),
            ]
        ],
        verdict=deny,
    )
    advocates = {
        approve: Advocate(tools=[psql, Tool(web_search, timeout=0.05)]),
        deny: Advocate(tools=[psql]),
        refer: Advocate(tools=[psql]),
    }
    tribunal = Tribunal(**(kwargs | {"model": scripted.model, "advocates": advocates}))
    return await tribunal.hear(case), scripted, tribunal


async def test_the_proceeding_outcomes_md_writes_out(
    hearing_and_bench: tuple[Hearing[Any], Any, Tribunal[Any]],
) -> None:
    hearing, _, _ = hearing_and_bench
    approve, deny, refer = hearing.transcript.verdicts

    by_round = [[entry.filing for entry in hearing.transcript if entry.round == n] for n in (1, 2)]
    round_1, round_2 = by_round
    assert {f.advocate for f in round_1 if isinstance(f, Argument)} == {approve, deny}
    assert [f.advocate for f in round_1 if isinstance(f, Concession)] == [refer]
    assert isinstance(round_1[-1], Continuance)
    assert [(i.id, i.to) for i in round_1[-1].interrogatories] == [
        ("r1-q1", approve),
        ("r1-q2", deny),
    ]
    responses = sorted(
        ((f.advocate, f.answering) for f in round_2 if isinstance(f, Response)), key=str
    )
    assert responses == [(approve, "r1-q1"), (deny, "r1-q2")]
    assert isinstance(round_2[-1], Ruling)
    assert round_2[-1].verdict == deny


async def test_the_hearing_it_hands_back(
    hearing_and_bench: tuple[Hearing[Any], Any, Tribunal[Any]],
) -> None:
    """The assertion snippets § 1 prints, directly usable as written:

    hearing.outcome.verdict                              # <LoanDecision.DENY: 'deny'>
    hearing.rounds                                       # 2 — not 5, the budget
    len(hearing.transcript)                              # 7
    hearing.outcome is hearing.transcript[-1].filing     # True — a pointer, not a copy
    len(hearing.transcript.ledger)                       # 5 retrieved, 4 filed
    len(hearing.transcript.failures)                     # 2 — both APPROVE, round 2
    """
    hearing, _, _ = hearing_and_bench
    approve, deny, refer = hearing.transcript.verdicts

    assert isinstance(hearing.outcome, Ruling)
    assert hearing.outcome.verdict == deny
    assert hearing.rounds == 2
    assert len(hearing.transcript) == 7
    assert hearing.outcome is hearing.transcript[-1].filing
    assert len(hearing.transcript.ledger) == 5
    assert len(hearing.transcript.failures) == 2
    assert set(hearing.usage_by_participant) == {approve, deny, refer, "judge"}


async def test_the_ledger_shows_what_the_filings_do_not(
    hearing_and_bench: tuple[Hearing[Any], Any, Tribunal[Any]],
) -> None:
    """The suppression join, as § 1 prints it — and it finds exactly one row.

    `APPROVE` queried the verification status, saw `none`, and argued around it. The same
    query is ledgered a second time under `DENY`, which filed it in round 2: retrievals are per
    advocate, so what each one saw is a separate fact, and ids restart per advocate.
    """
    hearing, _, _ = hearing_and_bench
    approve, deny, refer = hearing.transcript.verdicts

    # § 1 spells this with `getattr(e.filing, "exhibits", [])`; narrowed here to the two
    # filings that carry exhibits, which is the same join written so a type checker can see it.
    cited = {
        (e.filing.advocate, x.source)
        for e in hearing.transcript
        if isinstance(e.filing, Argument | Response)
        for x in e.filing.exhibits
    }
    ledger = hearing.transcript.ledger
    buried = [(r.advocate, r.id) for r in ledger if (r.advocate, r.id) not in cited]
    assert buried == [(approve, "s2")]

    # Per advocate, because the advocates run concurrently and their rows interleave in the
    # ledger in whatever order the scheduler chose. Within one advocate the order is fixed:
    # its tool calls are sequential, which is what makes its ids deterministic.
    def rows(advocate: Any) -> list[tuple[str, int, str]]:
        return [(r.id, r.round, r.tool) for r in ledger if r.advocate == advocate]

    assert rows(approve) == [("s1", 1, "psql"), ("s2", 1, "psql"), ("s3", 1, "web_search")]
    assert rows(deny) == [("s1", 1, "psql"), ("s2", 2, "psql")]
    assert rows(refer) == []


async def test_the_empty_response_is_explained_by_the_failures(
    hearing_and_bench: tuple[Hearing[Any], Any, Tribunal[Any]],
) -> None:
    """Two timeouts on one tool, and the advocate is still heard — the `tools` budget is 3."""
    hearing, _, _ = hearing_and_bench
    approve, _, _ = hearing.transcript.verdicts

    failures = [(f.advocate, f.round, f.tool) for f in hearing.transcript.failures]
    assert failures == [(approve, 2, "web_search"), (approve, 2, "web_search")]
    assert all(f.detail.startswith("Timed out after") for f in hearing.transcript.failures)
    response = next(
        e.filing
        for e in hearing.transcript
        if isinstance(e.filing, Response) and e.filing.advocate == approve
    )
    assert response.exhibits == []


async def test_usage_is_the_sum_of_the_breakdown(
    hearing_and_bench: tuple[Hearing[Any], Any, Tribunal[Any]],
) -> None:
    hearing, _, _ = hearing_and_bench

    total = sum((spend.requests for spend in hearing.usage_by_participant.values()), start=0)
    assert hearing.usage.requests == total


async def test_the_transcript_invariant_held(
    hearing_and_bench: tuple[Hearing[Any], Any, Tribunal[Any]],
    assert_invariant_held: Callable[..., None],
) -> None:
    hearing, scripted, tribunal = hearing_and_bench

    assert_invariant_held(scripted.captured, hearing.transcript, tribunal.instructions_for)
