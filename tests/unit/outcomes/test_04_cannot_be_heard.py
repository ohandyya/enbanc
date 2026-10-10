"""`docs/design/outcomes.md` § 4 — a participant cannot be heard.

Any of three things — an unreachable provider, a tool that raises, output that will not
validate after retries — ends the proceeding and raises `ProceedingFailed`. `hearing` is never
bound, and the record survives on the exception.

The provider and the database are stand-ins: `ConnectionError` for
`anthropic.APIConnectionError` and `OSError` for `psycopg.OperationalError`. The offline tier
imports neither SDK, and what is under test is *whatever was raised is `__cause__`*, which a
builtin carries as well as either.

**How many entries a cancelled round leaves is never asserted** (`docs/design/testing.md`,
"What must not be asserted") — only which entries a test forced onto the record. The two
judge-side cases are the exception: no round was cancelled, so their count is deterministic.

The doc is mirrored here, never executed. See
`docs/decisions/0032-a-design-doc-is-mirrored-by-tests.md`.
"""

from collections.abc import Callable
from typing import Any

import anyio
import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior

from enbanc import (
    Advocate,
    Argument,
    Case,
    Continuance,
    ProceedingFailed,
    Response,
    Tribunal,
)

Kwargs = Callable[[], dict[str, Any]]

#: Long enough that a missing cancel fails the test rather than passing it slowly; short enough
#: that a hang never stalls the suite.
_HANG = 5


async def test_an_advocates_provider_is_down(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """`APPROVE` files, `DENY`'s provider gives up, and `REFER` is cancelled where it stood.

    The ordering is forced rather than left to the scheduler: `DENY` raises only once the
    consumer has received `APPROVE`'s argument, and `REFER` waits on an event nothing sets, so
    it is demonstrably mid-run when the failure arrives. If the failure did not cancel it,
    this test would time out rather than pass.
    """
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    down = ConnectionError("Connection error.")
    approve_filed = anyio.Event()
    scripted = bench(
        searches={approve},
        cites={approve},
        gates={deny: approve_filed, refer: anyio.Event()},
        raises={deny: down},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(ProceedingFailed) as caught:
        with anyio.fail_after(_HANG):
            async with tribunal.hear_stream(case) as proceeding:
                async for entry in proceeding:
                    if isinstance(entry.filing, Argument) and entry.filing.advocate == approve:
                        approve_filed.set()

    failed = caught.value
    assert failed.participant is deny
    assert failed.round == 1
    assert failed.__cause__ is down
    assert str(failed) == "advocate 'deny' could not be heard in round 1"
    # The judge never deliberated, so nothing was decided.
    assert not any(isinstance(entry.filing, Continuance) for entry in failed.transcript)
    assert any(
        isinstance(entry.filing, Argument) and entry.filing.advocate == approve
        for entry in failed.transcript
    )
    # Everyone dispatched has a key — `REFER` cancelled where it stood, `DENY` died mid-run —
    # and the judge, never dispatched, has none.
    assert set(failed.usage_by_participant) == {approve, deny, refer}
    assert failed.usage.requests >= failed.usage_by_participant[approve].requests >= 2


async def test_the_judges_provider_is_down(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Same failure, one participant later: all three advocates filed, and the deliberation
    that would have closed round 1 never happened."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    down = ConnectionError("Connection error.")
    scripted = bench(
        searches={approve, deny},
        cites={approve, deny},
        concedes={refer},
        raises={("judge", 1): down},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(ProceedingFailed) as caught:
        await tribunal.hear(case)

    failed = caught.value
    assert failed.participant == "judge"
    assert failed.round == 1
    assert failed.__cause__ is down
    assert str(failed) == "the judge could not be heard in round 1"
    assert len(failed.transcript) == 3
    assert not any(isinstance(entry.filing, Continuance) for entry in failed.transcript)
    # All four: the advocates filed, and the judge's row holds what its failed run spent.
    assert set(failed.usage_by_participant) == {approve, deny, refer, "judge"}


async def test_an_advocates_tool_raises(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """Nothing to do with the model — the warehouse is down, and the tool raises in round 2
    while `DENY` answers its interrogatory. Same type, same shape; why is `__cause__`'s
    business."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    refused = OSError("connection refused")

    async def psql_down(query: str) -> str:
        """Query the warehouse."""
        raise refused

    kwargs["advocates"][deny] = Advocate(tools=[*kwargs["advocates"][deny].tools, psql_down])
    scripted = bench(
        searches={approve, deny},
        cites={approve, deny},
        concedes={refer},
        continuances=[
            [
                (approve, "Which income figure does §4.2 require?"),
                (deny, "Does the Schedule C qualify as documented?"),
            ]
        ],
        calls={"r1-q2": [("psql_down", {"query": "select * from schedule_c"})]},
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(ProceedingFailed) as caught:
        with anyio.fail_after(_HANG):
            await tribunal.hear(case)

    failed = caught.value
    assert failed.participant is deny
    # Where it stopped, not how far it got: round 1 completed, and its continuance says so.
    assert failed.round == 2
    assert failed.__cause__ is refused
    continuances = [e.round for e in failed.transcript if isinstance(e.filing, Continuance)]
    assert continuances == [1]
    assert not any(
        isinstance(entry.filing, Response) and entry.filing.advocate == deny
        for entry in failed.transcript
    )
    assert set(failed.usage_by_participant) == {approve, deny, refer, "judge"}


async def test_the_judges_output_will_not_validate(
    outcomes_kwargs: Kwargs, bench: Callable[..., Any], case: Case
) -> None:
    """The one `enbanc` does retry: an empty continuance, refused by `min_length=1`, corrected
    twice against the `output` budget, and emitted the same way each time."""
    kwargs = outcomes_kwargs()
    approve, deny, refer = list(kwargs["verdicts"])
    scripted = bench(
        searches={approve, deny}, cites={approve, deny}, concedes={refer}, continuances=[[]]
    )
    tribunal = Tribunal(**(kwargs | {"model": scripted.model}))

    with pytest.raises(ProceedingFailed) as caught:
        await tribunal.hear(case)

    failed = caught.value
    assert failed.participant == "judge"
    assert failed.round == 1
    assert isinstance(failed.__cause__, UnexpectedModelBehavior)
    assert "Exceeded maximum output retries (2)" in str(failed.__cause__)
    # Nothing the judge emitted reached the clerk, so the record shows a complete round 1 and
    # no deliberation — the same shape a downed judge leaves.
    assert len(failed.transcript) == 3
    assert not any(isinstance(entry.filing, Continuance) for entry in failed.transcript)
    # Three attempts, one run, one row.
    assert len(scripted.captured["judge"]) == 3
    assert failed.usage_by_participant["judge"].requests >= 3
