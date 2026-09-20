"""One coroutine owns the transcript, so the live view and the record cannot disagree.

`docs/design/execution.md` ("The filing clerk") exists to make one sentence true by
construction: *the entry just received is the last entry of `proceeding.transcript`*
(`docs/decisions/0010-streaming-yields-the-record.md`). If each task appended and then sent, a
sibling could append between the two operations and a consumer would receive entry 5 while
`transcript[-1]` was entry 6.

The clerk is driven directly here — no models, no agents — because what it owns is the seam
between a filing and the record, and that seam is reachable on its own.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import anyio
import pytest

from enbanc import Argument, Case, Concession, Entry, Ruling, Transcript, Verdict
from enbanc._evidence import _Exhibit
from enbanc._filings import _Argument
from enbanc._proceeding import _Filed, _Orchestrator
from enbanc._transcript import Retrieval

Kwargs = Callable[[], dict[str, Any]]


def _orchestrator(kwargs: dict[str, Any], case: Case) -> _Orchestrator[Any]:
    """The orchestrator alone, built from the pieces — no `Tribunal` required.

    This is what `docs/design/packaging.md` means by *`_proceeding.py` takes the pieces*: the
    round loop is constructible from a test without building a tribunal first.
    """
    return _Orchestrator(
        question=kwargs["question"],
        statute=kwargs["statute"],
        case=case,
        verdicts=kwargs["verdicts"],
        judge=kwargs["judge"],
        advocates=kwargs["advocates"],
        model=kwargs["model"],
        max_rounds=kwargs["max_rounds"],
    )


async def _file_through_the_clerk(
    orchestrator: _Orchestrator[Any], *filings: Any
) -> tuple[list[Entry[Any]], list[_Filed[Any]]]:
    """Run the clerk over a handful of filings and collect what it sent and acknowledged."""
    sent: list[Entry[Any]] = []
    receipts: list[_Filed[Any]] = []
    inbox_send, inbox_receive = anyio.create_memory_object_stream[_Filed[Any]](0)
    out_send, out_receive = anyio.create_memory_object_stream[Entry[Any]](0)

    async def consume() -> None:
        async for entry in out_receive:
            # Read inside the loop body, which is the moment `0010` makes a promise about.
            sent.append(entry)
            assert entry is orchestrator.transcript[-1]

    # The clerk runs until its inbox has no senders left, so the send end is closed as soon as
    # the last filing is acknowledged — the same shape `_Orchestrator.run` uses. `out_send` is
    # then closed to end the consumer, which is what `run` does after binding the hearing.
    async with out_send, out_receive, anyio.create_task_group() as tg:
        tg.start_soon(orchestrator._clerk, inbox_receive, out_send)  # noqa: SLF001
        tg.start_soon(consume)
        async with inbox_send:
            for filing in filings:
                filed = _Filed(filing=filing, round=1, done=anyio.Event())
                await inbox_send.send(filed)
                await filed.done.wait()
                receipts.append(filed)
        await out_send.aclose()
    return sent, receipts


@pytest.fixture
def bench_orchestrator(outcomes_kwargs: Kwargs, case: Case) -> _Orchestrator[Any]:
    return _orchestrator(outcomes_kwargs(), case)


async def test_the_entry_sent_is_the_entry_appended(
    bench_orchestrator: _Orchestrator[Any],
) -> None:
    """One object, not two: a consumer holding an entry is holding the record's own row."""
    approve = bench_orchestrator.transcript.verdicts[0]

    sent, _ = await _file_through_the_clerk(
        bench_orchestrator, Concession(advocate=approve, reason="No case.")
    )

    assert len(sent) == 1
    assert sent[0] is bench_orchestrator.transcript[0]


async def test_each_entry_is_the_last_one_at_the_moment_it_is_yielded(
    bench_orchestrator: _Orchestrator[Any],
) -> None:
    """The `0010` promise, over several filings. The assertion itself is inside the consumer in
    the helper above — this is what proves the helper ran it more than once."""
    approve, deny, refer = bench_orchestrator.transcript.verdicts

    sent, _ = await _file_through_the_clerk(
        bench_orchestrator,
        Concession(advocate=approve, reason="No case."),
        Concession(advocate=deny, reason="No case."),
        Concession(advocate=refer, reason="No case."),
    )

    assert len(sent) == 3
    filed = [entry.filing for entry in bench_orchestrator.transcript]
    assert [f.advocate for f in filed if isinstance(f, Concession)] == [approve, deny, refer]


async def test_the_acknowledgment_carries_the_stamped_entry_back(
    bench_orchestrator: _Orchestrator[Any],
) -> None:
    """The task that filed gets the public entry, not just permission to continue.

    It needs it for its own snapshot extension in round 2, and reading
    `transcript.entries[-1]` after the wait would be a race a concurrent sibling wins. `0027`
    needs the acknowledgment independently of `0010`'s ordering promise.
    """
    approve = bench_orchestrator.transcript.verdicts[0]

    _, receipts = await _file_through_the_clerk(
        bench_orchestrator, Concession(advocate=approve, reason="No case.")
    )

    acknowledged = receipts[0].entry
    assert acknowledged is not None, "the clerk set `done` without stamping an entry"
    assert acknowledged is bench_orchestrator.transcript[0]
    assert acknowledged.round == 1
    assert acknowledged.filed_at.tzinfo is not None


async def test_a_concession_and_a_ruling_pass_through_unconverted(
    bench_orchestrator: _Orchestrator[Any],
) -> None:
    """Neither carries a stamped field, which is why neither has a private counterpart — the
    filing that enters the record is the object the participant emitted."""
    approve = bench_orchestrator.transcript.verdicts[0]
    concession = Concession(advocate=approve, reason="No case.")
    ruling = Ruling(verdict=approve, reasoning="Documented income governs.")

    sent, _ = await _file_through_the_clerk(bench_orchestrator, concession, ruling)

    assert sent[0].filing is concession
    assert sent[1].filing is ruling


async def test_an_argument_is_converted_and_its_exhibits_stamped(
    bench_orchestrator: _Orchestrator[Any],
) -> None:
    """`_Argument` in, `Argument` out, with `tool`, `reference` and `label` filled from the
    ledger row the advocate's own tool call wrote."""
    approve = bench_orchestrator.transcript.verdicts[0]
    bench_orchestrator.transcript.ledger.append(
        Retrieval(
            id="s1",
            round=1,
            advocate=approve,
            tool="psql",
            reference="s3://w2-2024.pdf",
            content="wages: 131,400",
            label="W-2, 2024",
        )
    )

    sent, _ = await _file_through_the_clerk(
        bench_orchestrator,
        _Argument(
            advocate=approve,
            claim="DTI is 0.38.",
            exhibits=[_Exhibit(source="s1", content="wages: 131,400")],
        ),
    )

    filed = sent[0].filing
    assert isinstance(filed, Argument)
    assert filed.claim == "DTI is 0.38."
    assert filed.exhibits[0].model_dump() == {
        "source": "s1",
        "tool": "psql",
        "reference": "s3://w2-2024.pdf",
        "content": "wages: 131,400",
        "label": "W-2, 2024",
    }


async def test_an_exhibit_resolves_against_its_own_advocates_rows(
    bench_orchestrator: _Orchestrator[Any],
) -> None:
    """The join key is `(advocate, id)`: `APPROVE`'s `s1` and `DENY`'s `s1` are different
    retrievals, so the clerk must not stamp one advocate's exhibit from another's row."""
    approve, deny, _refer = bench_orchestrator.transcript.verdicts
    for advocate, reference in ((approve, "s3://schedule-c.pdf"), (deny, "s3://w2.pdf")):
        bench_orchestrator.transcript.ledger.append(
            Retrieval(
                id="s1",
                round=1,
                advocate=advocate,
                tool="psql",
                reference=reference,
                content="figure",
            )
        )

    sent, _ = await _file_through_the_clerk(
        bench_orchestrator,
        _Argument(
            advocate=deny,
            claim="Wages govern.",
            exhibits=[_Exhibit(source="s1", content="figure")],
        ),
    )

    filed = sent[0].filing
    assert isinstance(filed, Argument)
    assert filed.exhibits[0].reference == "s3://w2.pdf"


async def test_an_unresolvable_id_reaching_the_clerk_is_a_bug_in_enbanc(
    bench_orchestrator: _Orchestrator[Any],
) -> None:
    """By the time a filing reaches the clerk, the output function has already rejected every
    id this advocate was not issued — so a miss here is not a model behaving badly and must not
    be reported as one.

    It is an `AssertionError` rather than a `ModelRetry` for that reason: there is nobody left
    to correct.
    """
    approve = bench_orchestrator.transcript.verdicts[0]

    with pytest.raises(BaseExceptionGroup) as caught:
        await _file_through_the_clerk(
            bench_orchestrator,
            _Argument(
                advocate=approve,
                claim="DTI is 0.38.",
                exhibits=[_Exhibit(source="s7", content="invented")],
            ),
        )

    assert any(isinstance(exc, AssertionError) for exc in caught.value.exceptions)
    assert "'s7'" in str(caught.value.exceptions[0])


def test_the_orchestrator_builds_the_transcript_before_the_toolsets(
    outcomes_kwargs: Kwargs, case: Case
) -> None:
    """Pydantic copies a list field at construction, so a `Ledgering` given a list that was
    later passed to `Transcript(ledger=...)` would write into an orphan — silently.

    Asserted as identity, because that is the whole of the claim: the toolset's list *is* the
    record's list (`0016`'s ownership constraint).
    """
    orchestrator = _orchestrator(outcomes_kwargs(), case)

    for ledgering in orchestrator.ledgerings.values():
        assert ledgering.ledger is orchestrator.transcript.ledger
        assert ledgering.failures is orchestrator.transcript.failures


def test_one_ledgering_per_advocate_carries_that_advocates_name(
    outcomes_kwargs: Kwargs, case: Case
) -> None:
    """Ids are numbered within an advocate, so the counter has to be per advocate — and it
    lives the whole proceeding, because a round-3 response may cite a round-1 find."""
    orchestrator = _orchestrator(outcomes_kwargs(), case)

    assert {verdict: led.advocate for verdict, led in orchestrator.ledgerings.items()} == {
        verdict: verdict for verdict in orchestrator.advocates
    }


def test_a_snapshot_is_a_transcript_that_stops_growing(outcomes_kwargs: Kwargs, case: Case) -> None:
    """A snapshot is constructed, not sliced: it is a `Transcript` — the one type the renderer
    takes — whose entries are fixed at the moment it was taken.

    `since` selects which rounds render; the snapshot decides which filings of those rounds
    exist to select from. Here only the second half is exercised, because round 1 is the only
    round this PR dispatches.
    """
    orchestrator = _orchestrator(outcomes_kwargs(), case)
    approve = orchestrator.transcript.verdicts[0]
    filed_at = datetime.now(UTC)
    orchestrator.transcript.entries.append(
        Entry(
            round=1,
            filed_at=filed_at,
            filing=Concession(advocate=approve, reason="No case."),
        )
    )

    snapshot = orchestrator._snapshot()  # noqa: SLF001
    orchestrator.transcript.entries.append(
        Entry(
            round=1,
            filed_at=filed_at,
            filing=Concession(advocate=approve, reason="Filed after the snapshot."),
        )
    )

    assert isinstance(snapshot, Transcript)
    assert len(snapshot) == 1
    assert len(orchestrator.transcript) == 2
    assert snapshot.question == orchestrator.transcript.question


def test_the_orchestrator_needs_no_tribunal(outcomes_kwargs: Kwargs, case: Case) -> None:
    """Stated as a test because it is a packaging rule: `_tribunal` imports `_proceeding` and
    never the reverse, and a round loop that could only be built through a `Tribunal` would
    make that rule untestable rather than merely unfollowed."""
    orchestrator = _orchestrator(outcomes_kwargs(), case)

    assert isinstance(orchestrator.transcript, Transcript)
    assert isinstance(orchestrator.transcript.verdicts[0], Verdict)
    assert orchestrator.hearing is None
