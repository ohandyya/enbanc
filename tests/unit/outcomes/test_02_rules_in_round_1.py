"""`docs/design/outcomes.md` § 2 — the judge rules in round 1.

The cheapest proceeding there is: three advocates file, the record is clear enough that no
interrogatory is needed, and the judge rules. Four entries, one round, a `Hearing`.

This is the acceptance test for `docs/implementations/proceeding-core.md`, and it is the one
ending reachable without a round loop — which is why the spine starts here rather than at § 1.
Every other section of that document arrives with the PR that makes its ending possible.

The doc is mirrored here, never executed: `CLAUDE.md` rule 2 is what keeps the two in step,
and a change to behaviour is exactly what breaks this module. See
`docs/decisions/0032-a-design-doc-is-mirrored-by-tests.md`.
"""

from collections.abc import Callable
from typing import Any

from enbanc import Argument, Case, Concession, Continuance, Ruling, Tribunal

Kwargs = Callable[[], dict[str, Any]]


async def test_the_proceeding_outcomes_md_writes_out(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """§ 2's four entries, in the shape the document prints them:

    round 1   Argument(advocate=APPROVE, exhibits=[psql])
              Argument(advocate=DENY,    exhibits=[psql, web_search])
              Concession(advocate=REFER)
              Ruling(verdict=APPROVE)
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny}, cites={approve, deny}, concedes={refer}, verdict=approve
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    filings = [entry.filing for entry in hearing.transcript]
    assert len(filings) == 4
    assert {f.advocate for f in filings if isinstance(f, Argument)} == {approve, deny}
    assert [f.advocate for f in filings if isinstance(f, Concession)] == [refer]
    assert isinstance(filings[-1], Ruling)
    assert filings[-1].verdict == approve


async def test_the_hearing_it_hands_back(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The assertion snippets § 2 prints, directly usable as written:

    hearing.rounds                                    # 1
    len(hearing.transcript)                           # 4 entries
    hearing.usage_by_participant                      # 3 advocates + 'judge'
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny}, cites={approve, deny}, concedes={refer}, verdict=approve
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert hearing.rounds == 1
    assert len(hearing.transcript) == 4
    assert set(hearing.usage_by_participant) == {approve, deny, refer, "judge"}
    assert hearing.usage.requests > 0


async def test_a_continuance_never_appears(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """*`max_rounds=5` is a ceiling, not a target.* The judge ruled on round 1's record, so
    nothing in the transcript is a continuance and no second round was dispatched."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve}, cites={approve}, concedes={refer}, verdict=approve)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert not any(isinstance(entry.filing, Continuance) for entry in hearing.transcript)
    assert hearing.transcript.max_rounds == 5
    assert hearing.rounds == 1


async def test_the_outcome_is_the_final_entrys_filing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A pointer, not a copy — the one assertion § 1 and § 2 share, and the one that would
    break silently if the clerk filed a converted copy of the judge's ruling."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={approve, deny, refer}, verdict=approve)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert hearing.outcome is hearing.transcript[-1].filing


async def test_the_suppression_join_finds_what_was_retrieved_and_not_filed(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`entries` says what the ruling rests on; `ledger` says what was available to rest on.

    Here `DENY` searched and filed nothing from it, so its retrieval is in the record with no
    exhibit naming it — the join `0019` exists for, over a proceeding built to have exactly
    one. The join key is `(advocate, id)`, because ids are numbered within an advocate.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve}, concedes={refer}, verdict=approve)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    cited = {
        (entry.filing.advocate, exhibit.source)
        for entry in hearing.transcript
        if isinstance(entry.filing, Argument)
        for exhibit in entry.filing.exhibits
    }
    buried = [row for row in hearing.transcript.ledger if (row.advocate, row.id) not in cited]
    assert [(row.advocate, row.id) for row in buried] == [(deny, "s1")]
    assert buried[0].content == "wages: 131,400"


async def test_the_transcript_invariant_held(
    outcomes_kwargs: Kwargs,
    bench: Callable[..., Any],
    case: Case,
    assert_invariant_held: Callable[..., None],
) -> None:
    """Every proceeding test in the spine calls it, which is the point of writing it as a
    helper rather than as one dedicated test."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny}, cites={approve, deny}, concedes={refer}, verdict=approve
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert_invariant_held(scripted.captured, hearing.transcript, tribunal.instructions_for)


async def test_the_rendered_record_reads_as_a_proceeding(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The reviewer's viewpoint over a record nothing hand-built.

    `test_transcript_render.py` pins the format against a fixture; what this adds is that a
    transcript a *proceeding* produced renders through the same path — the ledger rows it
    wrote included, with `cited` computed at render time rather than stored.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve}, concedes={refer}, verdict=approve)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    rendered = (await tribunal.hear(case)).transcript.render()

    assert rendered.startswith("# Proceeding")
    assert "## The statute — underwriting-v3" in rendered
    assert f"[round 1] the judge ruled — {approve}:" in rendered
    assert f"[{approve}/s1] W-2, 2024 — cited" in rendered
    assert f"[{deny}/s1] W-2, 2024 — not cited" in rendered
