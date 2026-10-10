"""Round 2 and after: what a continuance starts, end to end, with no provider in the loop.

`docs/design/execution.md`'s round loop over the bench `outcomes.md` uses. Every test here is a
claim about the sequence that document writes out run by run — ids stamped at the clerk, one
task per addressed advocate, an advocate's own questions answered in order, `since` advanced
per run, and run 7's snapshot, which holds the advocate's own response and not its peer's.

The worked proceeding is `APPROVE` asked `r1-q1` and `DENY` asked `r1-q2` and `r1-q3`, so most
tests script that continuance and read what each run was handed.
"""

from collections.abc import Callable
from typing import Any

import anyio

from enbanc import (
    Case,
    Concession,
    Continuance,
    Response,
    Ruling,
    Tribunal,
)

Kwargs = Callable[[], dict[str, Any]]

#: The worked proceeding's first continuance, in emission order.
Q1 = "Does the W-2 reconcile with the Schedule C figure?"
Q2 = "Is stated income disqualifying when documented income is on file?"
Q3 = "Would a verified 2024 return change your answer?"


def _worked(verdicts: Any) -> list[list[tuple[Any, str]]]:
    approve, deny, _ = list(verdicts)
    return [[(approve, Q1), (deny, Q2), (deny, Q3)]]


def _turns(captured: dict[Any, list[list[Any]]], who: Any) -> list[str]:
    """Each distinct turn one participant was handed, in order — one per run.

    A run that calls a tool makes several model requests over the same turn, so consecutive
    duplicates are one run.
    """
    turns: list[str] = []
    for messages in captured.get(who, []):
        prompts = [
            str(part.content)
            for message in messages
            for part in getattr(message, "parts", ())
            if type(part).__name__ == "UserPromptPart"
        ]
        if prompts and (not turns or turns[-1] != prompts[-1]):
            turns.append(prompts[-1])
    return turns


def _answering(turns: list[str], interrogatory_id: str) -> str:
    return next(turn for turn in turns if f"Answer {interrogatory_id} and" in turn)


async def test_a_continuance_starts_a_round_and_the_judge_then_rules(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={refer}, continuances=_worked(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert isinstance(hearing.outcome, Ruling)
    assert hearing.rounds == 2
    assert hearing.outcome is hearing.transcript[-1].filing
    assert [entry.round for entry in hearing.transcript] == [1, 1, 1, 1, 2, 2, 2, 2]
    assert isinstance(hearing.transcript[3].filing, Continuance)
    responses = [entry.filing for entry in hearing.transcript if entry.round == 2][:-1]
    assert all(isinstance(response, Response) for response in responses)


async def test_ids_are_stamped_in_emission_order_and_restart_each_round(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`r{round}-q{n}`, `n` from 1 within the continuance — and nothing the judge wrote moves.

    The second continuance is numbered `r2-q1`, not `r1-q4`: the round prefix carries
    uniqueness, so the counter restarts
    (`docs/decisions/0015-interrogatory-ids-are-stamped-on-filing.md`).
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    script = [*_worked(kwargs["verdicts"]), [(approve, "Can you produce an audited return?")]]
    scripted = bench(concedes={refer}, continuances=script)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    continuances = [entry for entry in hearing.transcript if isinstance(entry.filing, Continuance)]
    assert [entry.round for entry in continuances] == [1, 2]
    stamped = [
        [(i.id, i.to, i.question) for i in entry.filing.interrogatories]  # type: ignore[union-attr]
        for entry in continuances
    ]
    assert stamped == [
        [("r1-q1", approve, Q1), ("r1-q2", deny, Q2), ("r1-q3", deny, Q3)],
        [("r2-q1", approve, "Can you produce an audited return?")],
    ]
    assert hearing.rounds == 3


async def test_answering_is_the_dispatched_id_and_the_advocate_is_the_one_asked(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Neither end of the link is model-authored. The bench's model is never asked for either
    field — the response tool's schema is `answer` and `exhibits` alone — so whatever lands in
    the record came from the dispatch."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={refer}, continuances=_worked(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    responses = [entry.filing for entry in hearing.transcript if isinstance(entry.filing, Response)]
    assert sorted((r.answering, r.advocate) for r in responses) == [
        ("r1-q1", approve),
        ("r1-q2", deny),
        ("r1-q3", deny),
    ]
    # The bench writes `"<verdict> answers <id>."` from what its turn asked, so a response
    # filed under the wrong id would show the mismatch here.
    assert all(r.answer == f"{r.advocate.value} answers {r.answering}." for r in responses)


async def test_only_the_advocates_a_continuance_names_are_dispatched(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(continuances=[[(deny, Q2)]])
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert len(_turns(scripted.captured, approve)) == 1
    assert len(_turns(scripted.captured, refer)) == 1
    assert len(_turns(scripted.captured, deny)) == 2
    # An advocate that was not asked spends nothing in round 2: its accumulator is round 1's.
    assert hearing.usage_by_participant[approve].requests == 1
    assert hearing.usage_by_participant[deny].requests == 2


async def test_a_conceded_advocate_is_still_addressable(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`docs/decisions/0037-a-conceded-advocate-stays-addressable.md`: nothing filters a
    conceded advocate out of the dispatch, and it answers like any other."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={refer}, continuances=[[(refer, "Why concede?")]])
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    filings = [entry.filing for entry in hearing.transcript]
    assert any(isinstance(f, Concession) and f.advocate == refer for f in filings)
    assert any(
        isinstance(f, Response) and f.advocate == refer and f.answering == "r1-q1" for f in filings
    )


async def test_one_advocates_questions_are_filed_in_id_order(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`docs/decisions/0027-an-advocate-answers-its-interrogatories-in-order.md` — the one
    ordering within a round the design guarantees. Run it a few times: a scheduler that could
    reorder them would get the chance."""
    kwargs = outcomes_kwargs()
    for _ in range(5):
        scripted = bench(continuances=_worked(kwargs["verdicts"]))
        tribunal = Tribunal(**(outcomes_kwargs() | {"model": scripted.model}))

        hearing = await tribunal.hear(case)

        deny_answered = [
            entry.filing.answering
            for entry in hearing.transcript
            if isinstance(entry.filing, Response) and entry.filing.advocate.value == "deny"
        ]
        assert deny_answered == ["r1-q2", "r1-q3"]


async def test_since_and_the_snapshot_match_the_worked_proceeding(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Rows 5–8 of `execution.md`'s run-by-run table, read off what each run was handed.

    Runs 5 and 6 see all four round-1 entries: `since=0`, base snapshot. Run 7 sees only
    `DENY`'s own stamped `r1-q2` response: `since=1`, and a snapshot extended by that one
    entry. Deliberation 2 sees the three responses and none of round 1.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={refer}, continuances=_worked(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    await tribunal.hear(case)

    round_one = ["approve argued:", "deny argued:", "conceded:", "the judge issued a continuance:"]
    run_5 = _answering(_turns(scripted.captured, approve), "r1-q1")
    run_6 = _answering(_turns(scripted.captured, deny), "r1-q2")
    run_7 = _answering(_turns(scripted.captured, deny), "r1-q3")
    deliberation_2 = _turns(scripted.captured, "judge")[1]

    for turn in (run_5, run_6):
        assert all(marker in turn for marker in round_one)
        assert "[round 2]" not in turn
    assert "[round 2] deny responded to r1-q2:" in run_7
    assert "[round 1]" not in run_7
    assert "approve responded" not in run_7
    for interrogatory_id in ("r1-q1", "r1-q2", "r1-q3"):
        assert f"responded to {interrogatory_id}:" in deliberation_2
    assert "[round 1]" not in deliberation_2


async def test_a_third_round_is_shown_everything_the_second_filed(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`since` is the last round a participant was *shown*, not the last round it *ran*.

    `APPROVE` answers once in round 2, having been shown round 1 alone — so its `since` is 1,
    and its round-3 turn renders every round-2 filing: its own stamped response, `DENY`'s, and
    the continuance that asks it again. A `since` advanced to the round being run would render
    it none of them.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    script = [[(approve, Q1), (deny, Q2)], [(approve, "Can you produce an audited return?")]]
    scripted = bench(concedes={refer}, continuances=script)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    await tribunal.hear(case)

    round_3 = _answering(_turns(scripted.captured, approve), "r2-q1")
    assert "[round 2] approve responded to r1-q1:" in round_3
    assert "[round 2] deny responded to r1-q2:" in round_3
    assert "[round 2] the judge issued a continuance:" in round_3
    assert "[round 1]" not in round_3


async def test_run_seven_is_not_shown_a_peers_response_that_landed_first(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The adversarial version of run 7, forced rather than left to the scheduler.

    `DENY`'s first response waits until the stream has yielded `APPROVE`'s. The stream is a
    rendezvous, so receiving that entry means it is already in `transcript.entries` — entry 5
    has demonstrably landed before entry 6. `DENY`'s second run must still not be shown it:
    its snapshot is the round's base plus its own filings, never the live record.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    approve_filed = anyio.Event()
    scripted = bench(
        concedes={refer},
        continuances=_worked(kwargs["verdicts"]),
        gates={"r1-q2": approve_filed},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    async with tribunal.hear_stream(case) as proceeding:
        async for entry in proceeding:
            if isinstance(entry.filing, Response) and entry.filing.advocate == approve:
                approve_filed.set()
    hearing = proceeding.hearing

    answered = [e.filing.answering for e in hearing.transcript if isinstance(e.filing, Response)]
    assert answered == ["r1-q1", "r1-q2", "r1-q3"]  # entry 5 really did land first
    run_7 = _answering(_turns(scripted.captured, deny), "r1-q3")
    assert "[round 2] deny responded to r1-q2:" in run_7
    assert "approve responded" not in run_7


async def test_a_round_two_response_may_cite_a_round_one_find(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The ledgering toolset outlives every round, so `DENY`'s `s1` is still its to cite."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={deny}, continuances=[[(deny, Q2)]], exhibits={"r1-q1": ["s1"]})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    response = next(e.filing for e in hearing.transcript if isinstance(e.filing, Response))
    assert [(x.source, x.tool) for x in response.exhibits] == [("s1", "psql")]


async def test_ids_keep_counting_across_rounds(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`DENY`'s round-2 find is `s2` with `round=2` — not a second `s1`, because the id is
    counted out of the shared ledger rather than out of a per-run copy."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={deny},
        cites={deny},
        continuances=[[(deny, Q2)]],
        calls={"r1-q1": [("psql", {"query": "select verification_status"})]},
        exhibits={"r1-q1": ["s2"]},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    rows = [(r.id, r.round) for r in hearing.transcript.ledger if r.advocate == deny]
    assert rows == [("s1", 1), ("s2", 2)]
    response = next(e.filing for e in hearing.transcript if isinstance(e.filing, Response))
    assert [x.source for x in response.exhibits] == ["s2"]


async def test_the_transcript_invariant_held_across_two_rounds(
    outcomes_kwargs: Kwargs,
    bench: Callable[..., Any],
    case: Case,
    assert_invariant_held: Callable[..., None],
) -> None:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny},
        cites={approve, deny},
        concedes={refer},
        continuances=_worked(kwargs["verdicts"]),
        calls={"r1-q2": [("psql", {"query": "select verification_status"})]},
        exhibits={"r1-q2": ["s2"]},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert hearing.rounds == 2
    assert_invariant_held(scripted.captured, hearing.transcript, tribunal.instructions_for)
