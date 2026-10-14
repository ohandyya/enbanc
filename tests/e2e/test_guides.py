"""Every guide in `docs/guides/`, run as the reader runs it.

A guide that nothing executes is a snippet, and it rots on the first signature change. So each
one is loaded from its own path — the file under test is the file a reader opens, byte for
byte — and its `main()` is awaited against the runner's provider rather than the guide's
default, which keeps this tier as provider-neutral as the rest of the harness.

The assertions are about the shape of the hearing, never its content: a model is free to rule
either way, and a test that pinned the verdict would fail for a reason that is not a defect.
See `docs/implementations/guides.md` ("Tests").
"""

import re
import runpy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai.models import Model

from enbanc import Argument, Concession, Hearing, Response, Ruling, Undecided, Verdict

GUIDES = Path(__file__).parents[2] / "docs" / "guides"


async def run_guide(
    name: str, live_env: Mapping[str, str], monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], Hearing[Any]]:
    """Load a guide from its own path and await its `main()` against the runner's model.

    `live_model` has already put `.env` into the environment and proved the runner's model
    builds; pointing the guide's own variable at it is what keeps the guide's default out.
    `run_path` executes the module body under a name other than `__main__`, so the guard does
    not fire and the test drives `main()` itself.
    """
    monkeypatch.setenv("ENBANC_MODEL", live_env["ENBANC_TEST_MODEL"])
    guide = runpy.run_path(str(GUIDES / name))
    hearing = await guide["main"]()
    assert isinstance(hearing, Hearing)
    return guide, hearing


def assert_coherent(hearing: Hearing[Any], verdicts: type[Verdict]) -> None:
    """What every guide's hearing must satisfy, whichever way it ruled."""
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
    assert sorted(opening) == sorted(verdicts)

    # Every exhibit resolves to a retrieval its own advocate made — ids are per advocate.
    ledger = {(r.advocate, r.id) for r in hearing.transcript.ledger}
    for entry in entries:
        if isinstance(entry.filing, Argument | Response):
            for exhibit in entry.filing.exhibits:
                assert (entry.filing.advocate, exhibit.source) in ledger

    if isinstance(hearing.outcome, Ruling):
        assert entries[-1].filing == hearing.outcome

    # Every row names the call that produced it.
    assert all(r.call.startswith(f"{r.tool}(") for r in hearing.transcript.ledger)

    assert hearing.usage.requests > 0
    assert all(usage.requests > 0 for usage in hearing.usage_by_participant.values())


async def test_loan_assessment(
    live_model: Model,
    live_env: Mapping[str, str],
    tavily_api_key: str,
    closed_after: None,
    closed_models: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guide, hearing = await run_guide("loan_assessment.py", live_env, monkeypatch)
    assert_coherent(hearing, guide["LoanDecision"])

    # The custom tool reached the model: nothing else produces a `loan-file://` reference.
    assert any(r.reference.startswith("loan-file://") for r in hearing.transcript.ledger)


async def test_content_moderation(
    live_model: Model,
    live_env: Mapping[str, str],
    tavily_api_key: str,
    closed_after: None,
    closed_models: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The `hear_stream` loop, against a real provider.

    The guide prints one `[round N]` line per entry as it arrives, so the printed sequence is
    what the stream yielded. It must be the record: every entry of the transcript, in filing
    order, and nothing else.
    """
    guide, hearing = await run_guide("content_moderation.py", live_env, monkeypatch)
    assert_coherent(hearing, guide["ModerationDecision"])

    printed = [int(n) for n in re.findall(r"^\[round (\d+)\]", capsys.readouterr().out, re.M)]
    assert printed == [entry.round for entry in hearing.transcript]

    assert any(r.reference.startswith("mod-file://") for r in hearing.transcript.ledger)
