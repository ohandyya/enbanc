"""Round 1 and one deliberation, end to end, with no provider in the loop.

`docs/design/execution.md`'s piece 3 up to the point a continuance would start a second
round: every advocate dispatched at once, each filing entering the record through the clerk,
an argument's exhibits stamped from the ledger, and the judge deliberating on what was filed.

The bench is `outcomes.md`'s, with one key varied — the model — for the reason
`docs/implementations/proceeding-core.md` gives: the tools are real, so the ledger and the
exhibits are what the proceeding actually produced rather than rows a test wrote.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import anyio
import pytest

from enbanc import (
    Argument,
    Case,
    Concession,
    Entry,
    Ruling,
    Transcript,
    Tribunal,
)

Kwargs = Callable[[], dict[str, Any]]


async def test_a_judge_that_rules_in_round_one_produces_a_hearing(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert isinstance(hearing.outcome, Ruling)
    assert hearing.rounds == 1
    assert hearing.outcome is hearing.transcript[-1].filing
    # The three advocates land in whatever order the fan-out finished them in — asserting one
    # is asserting anyio's scheduler — but the ruling is always last, because the judge could
    # not have read a round that had not closed.
    kinds = [entry.filing.kind for entry in hearing.transcript]
    assert sorted(kinds[:-1]) == ["argument", "argument", "concession"]
    assert kinds[-1] == "ruling"


async def test_every_advocate_is_dispatched_and_files_in_round_one(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Round 1 addresses the whole bench, and a concession is a filing like any other."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve}, cites={approve}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    filings = [entry.filing for entry in hearing.transcript]
    filed_by = {f.advocate for f in filings if isinstance(f, Argument | Concession)}
    assert filed_by == {approve, deny, refer}
    assert isinstance(next(f for f in filings if getattr(f, "advocate", None) == refer), Concession)
    assert isinstance(filings[-1], Ruling)


async def test_the_ruling_closes_the_round_it_deliberated_on(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A round is the advocates' filings *plus* the deliberation that closes it, so every entry
    of a one-round proceeding carries `round=1` — including the judge's."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert {entry.round for entry in hearing.transcript} == {1}
    assert hearing.transcript[-1].filing.kind == "ruling"


async def test_every_entry_is_stamped_with_a_filing_time(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`filed_at` is the tribunal's fact, which is why it is on the envelope and not the
    filing. It is timezone-aware, because a naive timestamp in an audit artifact is a
    timestamp nobody can place."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    before = datetime.now(UTC)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    after = datetime.now(UTC)
    for entry in hearing.transcript:
        assert entry.filed_at.tzinfo is not None
        assert before <= entry.filed_at <= after


async def test_an_exhibit_is_stamped_from_the_ledger_the_advocate_wrote(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The advocate emits a bare id and an excerpt; the tribunal fills the rest.

    `content` stays the advocate's — the excerpt is what it claimed mattered — while `tool`,
    `reference` and `label` come from the `Retrieval` its own tool call produced. Reading the
    two contents side by side is how a misquote is caught, so both have to survive.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={deny}, cites={deny}, concedes={approve, refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    argued = next(f for f in (e.filing for e in hearing.transcript) if isinstance(f, Argument))
    exhibit = argued.exhibits[0]
    row = next(r for r in hearing.transcript.ledger if (r.advocate, r.id) == (deny, exhibit.source))
    assert (exhibit.tool, exhibit.reference, exhibit.label) == (row.tool, row.reference, row.label)
    assert exhibit.content == "wages: 131,400"


async def test_the_ledger_is_the_transcripts_own_list(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The rows a `Ledgering` writes have to land in the record, and Pydantic copies a list
    field at construction — so a toolset handed a list that is later passed to
    `Transcript(ledger=...)` writes into an orphan and the record comes back empty."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert {(row.advocate, row.id, row.round) for row in hearing.transcript.ledger} == {
        (approve, "s1", 1),
        (deny, "s1", 1),
    }
    assert refer not in {row.advocate for row in hearing.transcript.ledger}


async def test_ids_are_numbered_within_an_advocate(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Two advocates searching concurrently both get `s1`: the join key is `(advocate, id)`,
    not the id alone."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert sorted(row.id for row in hearing.transcript.ledger) == ["s1", "s1"]


async def test_the_standing_record_is_written_once_at_the_top(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """A transcript is self-contained: the question, the statute, the case, the bench it faced,
    the envelope, who was steered, and the procedure it ran under."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    transcript = (await tribunal.hear(case)).transcript

    assert transcript.question == kwargs["question"]
    assert transcript.statute == kwargs["statute"]
    assert transcript.case == case
    assert transcript.verdicts == list(kwargs["verdicts"])
    assert transcript.max_rounds == 5
    assert transcript.procedure == "p1"


async def test_guidance_records_only_who_was_given_some(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Keyed on `guidance is not None`, the same predicate the instruction part is emitted on,
    so the record and the prompt agree about who was steered. `outcomes.md`'s bench steers the
    judge and nobody else."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    transcript = (await tribunal.hear(case)).transcript

    assert transcript.guidance == {"judge": "Where the record is ambiguous, deny."}


async def test_an_advocates_guidance_is_recorded_beside_the_judges(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    advocate = kwargs["advocates"][deny]
    kwargs["advocates"][deny] = type(advocate)(
        tools=advocate.tools, guidance="Weigh documented income over stated income."
    )
    scripted = bench(concedes={approve, deny, refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    transcript = (await tribunal.hear(case)).transcript

    assert transcript.guidance == {
        "judge": "Where the record is ambiguous, deny.",
        deny: "Weigh documented income over stated income.",
    }


async def test_round_one_advocates_read_the_case_and_no_record(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """An advocate arguing blind was shown nothing — `0023` as a missing argument rather than
    as a filter. Its turn is the case, and its first run carries no history."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(concedes={approve, deny, refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    await tribunal.hear(case)

    for verdict in (approve, deny, refer):
        first_run = scripted.captured[verdict][0]
        assert len(first_run) == 1, "an advocate's first run carries no message history"
        prompt = str(first_run[0].parts[-1].content)
        assert prompt.startswith("## The case")
        assert f'File your argument for "{verdict}", or concede.' in prompt
        assert "argued:" not in prompt, "round 1 is blind; no peer filing may appear"


async def test_the_judge_reads_what_round_one_filed(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The judge's snapshot is the transcript as the fan-out left it, rendered at `since=0` —
    so all three round-1 filings are in its delta, and nothing else is."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve}, cites={approve}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    turn = str(scripted.captured["judge"][0][0].parts[-1].content)
    assert turn.startswith("## Round 1")
    assert turn.count("[round 1]") == 3
    assert "Deliberation 1 of 5. Rule, or issue a continuance." in turn
    assert "## The ledger" not in turn, "the ledger is the reviewer's alone"
    assert hearing.transcript[-1].filing.kind == "ruling"


async def test_the_judges_first_run_carries_no_history(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """*The judge has no history in round 1* means `message_history=None`, mechanically."""
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]))
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    await tribunal.hear(case)

    assert len(scripted.captured["judge"][0]) == 1


async def test_a_searching_advocate_carries_its_tool_traffic_into_its_own_filing_run(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """History is a dict written after each run — but within one run PydanticAI already carries
    the conversation, which is what an advocate's second request shows."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={deny}, cites={deny}, concedes={approve, refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    await tribunal.hear(case)

    requests = scripted.captured[deny]
    assert len(requests) == 2, "one request to call the tool, one to file"
    assert "psql(query=" in str(requests[1][-1].parts[0].content)


async def test_the_transcript_invariant_holds_over_the_whole_proceeding(
    outcomes_kwargs: Kwargs,
    bench: Callable[..., Any],
    case: Case,
    assert_invariant_held: Callable[..., None],
) -> None:
    """Nothing entered any participant's context that the transcript does not hold.

    The assertion every proceeding test from here on gets for free — `testing.md` writes it as
    a helper precisely so that tests of other behaviour also happen to check this one.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)

    assert_invariant_held(scripted.captured, hearing.transcript, tribunal.instructions_for)


async def test_a_continuance_is_the_round_loops_and_says_so(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The stated boundary of this PR. A judge that declines to rule needs a round to dispatch
    into, and there is none yet — filing the continuance and reporting
    `Undecided(reason='rounds')` would be a false record for any tribunal whose rounds had not
    actually run out.

    **It arrives inside an `ExceptionGroup`**, because the task group here is the plain one.
    Turning what a proceeding raises into a singular exception is the first-failure slot
    `docs/implementations/failures.md` adds, and asserting the group now is what makes that
    change show up as a diff on this test rather than as a silent widening.
    """
    kwargs = outcomes_kwargs()
    scripted = bench(concedes=set(kwargs["verdicts"]), continues=True)
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.RaisesGroup(
        pytest.RaisesExc(NotImplementedError, match="round-loop.md"), flatten_subgroups=True
    ):
        await tribunal.hear(case)


async def test_a_tribunal_parks_no_state_between_proceedings(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Two hearings from one tribunal, each with its own record. The agents, histories,
    ledgering toolsets and usage accumulators are built inside `hear()` and discarded with it,
    which is what makes this safe — and what would break loudly if any of them were on the
    `Tribunal`, the `Judge` or an `Advocate`."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    first = await tribunal.hear(case)
    second = await tribunal.hear(case)

    assert first.transcript is not second.transcript
    assert len(first.transcript) == len(second.transcript) == 4
    assert len(first.transcript.ledger) == len(second.transcript.ledger) == 2
    assert first.usage.requests == second.usage.requests


async def test_two_proceedings_run_concurrently_keep_their_records_apart(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The same claim, made where it would actually break: one tribunal, two cases at once."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))
    hearings: list[Any] = []

    async def hear_one(applicant: str) -> None:
        # `model_copy` rather than `Case(applicant=...)`: the base is open at runtime, but its
        # fields are the caller's, so a subclass is how a typed one is built.
        hearings.append(await tribunal.hear(case.model_copy(update={"applicant": applicant})))

    async with anyio.create_task_group() as tg:
        tg.start_soon(hear_one, "A. Okonkwo")
        tg.start_soon(hear_one, "B. Marsh")

    assert {h.transcript.case.applicant for h in hearings} == {"A. Okonkwo", "B. Marsh"}
    assert all(len(h.transcript) == 4 for h in hearings)
    assert all(len(h.transcript.ledger) == 2 for h in hearings)


async def test_a_transcript_a_proceeding_produced_round_trips(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Not a proceeding test, but the one thing a proceeding's output owes the reviewer: what
    it wrote validates back. The filings, the envelope and the ledger are checked here against
    a record nothing hand-built."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(searches={approve, deny}, cites={approve, deny}, concedes={refer})
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    hearing = await tribunal.hear(case)
    restored: Transcript[Any] = Transcript[kwargs["verdicts"]].model_validate_json(
        hearing.transcript.model_dump_json()
    )

    assert restored.entries == hearing.transcript.entries
    assert restored.ledger == hearing.transcript.ledger
    assert isinstance(restored[-1], Entry)
    assert isinstance(restored[-1].filing, Ruling)
    assert {type(e.filing).__name__.split("[")[0] for e in restored} == {
        "Argument",
        "Concession",
        "Ruling",
    }
    # The one thing that does not come back as it went: `Transcript.case` is typed `Case`, so a
    # subclass validates back as the open base with its fields as extras. That is the price of
    # `Case` not being a type parameter, and `docs/design/api.md` states it — the artifact
    # survives the round trip even where the static type does not.
    assert restored.case.model_dump() == hearing.transcript.case.model_dump()
