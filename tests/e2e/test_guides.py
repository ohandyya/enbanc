"""Every guide in `docs/guides/`, run as the reader runs it.

A guide that nothing executes is a snippet, and it rots on the first signature change. So each
one is loaded from its own path — the file under test is the file a reader opens, byte for
byte — and its `main()` is awaited against the runner's provider rather than the guide's
default, which keeps this tier as provider-neutral as the rest of the harness.

The assertions are about the shape of the hearing, never its content: a model is free to rule
either way, and a test that pinned the verdict would fail for a reason that is not a defect.
See `docs/implementations/guides.md` ("Tests").
"""

import runpy
from collections.abc import Mapping
from pathlib import Path

import pytest
from pydantic_ai.models import Model

from enbanc import Argument, Concession, Hearing, Response, Ruling, Undecided

GUIDES = Path(__file__).parents[2] / "docs" / "guides"


async def test_loan_assessment(
    live_model: Model,
    live_env: Mapping[str, str],
    tavily_api_key: str,
    closed_after: None,
    closed_models: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `live_model` has already put `.env` into the environment and proved the runner's model
    # builds; pointing the guide's own variable at it is what keeps the guide's default out.
    monkeypatch.setenv("ENBANC_MODEL", live_env["ENBANC_TEST_MODEL"])

    # `run_path` executes the module body under a name other than `__main__`, so the guard
    # does not fire and the test drives `main()` itself.
    guide = runpy.run_path(str(GUIDES / "loan_assessment.py"))
    hearing = await guide["main"]()

    assert isinstance(hearing, Hearing)
    assert isinstance(hearing.outcome, (Ruling, Undecided))

    entries = list(hearing.transcript)
    rounds = [entry.round for entry in entries]
    assert rounds == sorted(rounds), "entries were appended out of round order"
    assert rounds[-1] <= hearing.rounds

    # Round 1 hears every advocate exactly once, arguing or conceding.
    opening = [
        e.filing.advocate
        for e in entries
        if e.round == 1 and isinstance(e.filing, Argument | Concession)
    ]
    assert sorted(opening) == sorted(guide["LoanDecision"])

    # Every exhibit resolves to a retrieval its own advocate made — ids are per advocate.
    ledger = {(r.advocate, r.id) for r in hearing.transcript.ledger}
    for entry in entries:
        if isinstance(entry.filing, Argument | Response):
            for exhibit in entry.filing.exhibits:
                assert (entry.filing.advocate, exhibit.source) in ledger

    if isinstance(hearing.outcome, Ruling):
        assert entries[-1].filing == hearing.outcome

    # The custom tool reached the model: nothing else produces a `loan-file://` reference.
    assert any(r.reference.startswith("loan-file://") for r in hearing.transcript.ledger)

    assert hearing.usage.requests > 0
    assert all(usage.requests > 0 for usage in hearing.usage_by_participant.values())
