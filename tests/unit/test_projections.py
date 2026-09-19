"""The viewpoints — where `0026` says the risk moved, and the only place it can still be lost.

`docs/decisions/0026-one-renderer-serves-both-audiences.md` makes the context invariant true
by construction: one renderer, and an agent's view differs from the reviewer's by filter
alone. It is explicit about the cost, too — "a wrong `since`, or a filter that forgets to
drop the ledger, breaks the invariant as thoroughly as a second renderer could. What changes
is that the mistake is in one small, enumerable place." This module is that enumeration.

`docs/design/execution.md` ("`since` and the snapshot, run by run") is the table the
parameterized case below walks. Reproduced here because a list of integers is unreadable
without it:

| Run | Participant | `since` in | Snapshot | Delta rendered |
|---|---|---|---|---|
| 1 | approve | — | — | the case only; round 1 is blind |
| 2 | deny | — | — | the case only |
| 3 | refer | — | — | the case only |
| 4 | judge, deliberation 1 | 0 | entries 1–3 | 1, 2, 3 |
| 5 | approve, `r1-q1` | 0 | entries 1–4 | 1, 2, 3, 4 |
| 6 | deny, `r1-q2` | 0 | entries 1–4 | 1, 2, 3, 4 |
| 7 | deny, `r1-q3` | 1 | entries 1–4 **+ 6** | 6 alone |
| 8 | judge, deliberation 2 | 1 | entries 1–7 | 5, 6, 7 |

Runs 1–3 have neither a `since` nor a snapshot — round 1 is argued blind — so they are
`argument_turn`'s golden in `test_turns.py` rather than a projection case here.
"""

from typing import Any

import pytest

from enbanc import Transcript, Verdict
from enbanc._prompting import AdvocateView, JudgeView, ReviewerView, render

#: Strings the fixture puts only in the ledger or only in the failures, so that their absence
#: from an agent view is assertable by search rather than by reading the code that drops them.
REVIEWER_ONLY = (
    "dti_for",
    "dti: 0.51",
    "— cited",
    "— not cited",
    "the record did not rest on",
    "find_filings",
    "Timed out after 30.0 seconds.",
    "## The ledger",
    "## Failed calls",
    "## The bench",
    "Deliberations allowed",
    "Where the record is ambiguous, deny.",
)


def _views(proceeding: Transcript[Any], since: int) -> list[Any]:
    """Every viewpoint an agent can be given at one `since`: the judge's, and each advocate's.

    The bench comes off `proceeding.verdicts` rather than off an imported enum — a
    `conftest.py` is not a module a test may import from, and the transcript holds the same
    list by design.
    """
    return [JudgeView(since)] + [AdvocateView(v, since) for v in proceeding.verdicts]


def _snapshot_of(proceeding: Transcript[Any], *entries: int) -> Transcript[Any]:
    kept = [proceeding.entries[n - 1] for n in entries]
    return proceeding.model_copy(update={"entries": kept})


@pytest.mark.parametrize("since", [0, 1, 2])
def test_an_agent_view_is_a_subset_of_the_reviewers(
    proceeding: Transcript[Any], since: int
) -> None:
    """Every line an agent emits appears in the reviewer's rendering of the same transcript.

    Line-wise and contiguous rather than a substring test: a rendering that reordered the
    record would still pass a plain `in`, and order is half of what a record is.
    """
    reviewer = render(proceeding, ReviewerView()).split("\n")
    for view in _views(proceeding, since):
        agent = render(proceeding, view).split("\n")
        if not agent:
            continue
        starts = [i for i, line in enumerate(reviewer) if reviewer[i : i + len(agent)] == agent]
        assert starts, f"{view} emitted lines the reviewer view does not contain"


@pytest.mark.parametrize("since", [0, 1])
def test_no_agent_view_carries_the_ledger_the_failures_or_the_bench(
    proceeding: Transcript[Any], since: int
) -> None:
    """Filings only. A retrieval lives in exactly one section and every agent view drops it,
    which is how "never another advocate's retrievals" is satisfied by construction."""
    for view in _views(proceeding, since):
        rendered = render(proceeding, view)
        for forbidden in REVIEWER_ONLY:
            assert forbidden not in rendered, f"{view} leaked {forbidden!r}"


@pytest.mark.parametrize("since", [0, 1, 2])
def test_an_agent_view_adds_no_heading_and_no_instruction(
    proceeding: Transcript[Any], since: int
) -> None:
    """The heading belongs to the turn template, never to the projection.

    `0026` rejected "one renderer with agent-only additions" by name: an addition is exactly
    what the subset property forbids.
    """
    for view in _views(proceeding, since):
        rendered = render(proceeding, view)
        assert not rendered.startswith("#")
        assert "\n#" not in rendered
        assert "File your argument" not in rendered
        assert "Rule, or issue a continuance" not in rendered


@pytest.mark.parametrize("since", [0, 1, 2])
def test_the_judges_view_and_an_advocates_are_the_same_bytes(
    proceeding: Transcript[Any], since: int
) -> None:
    """They are, today, and that is deliberate rather than an oversight.

    A retrieval appears only in `## The ledger`, which both drop; every *filing* is visible to
    every participant. `AdvocateView.advocate` is therefore carried and not read by the
    filter. This asserts the sameness so that the day a projection grows a per-advocate rule,
    this is the test that says so — see `_prompting.AdvocateView`.
    """
    judge = render(proceeding, JudgeView(since))
    for verdict in proceeding.verdicts:
        assert render(proceeding, AdvocateView(verdict, since)) == judge


@pytest.mark.parametrize(
    ("run", "since", "snapshot_entries", "expected_entries"),
    [
        pytest.param(4, 0, (1, 2, 3), (1, 2, 3), id="run-4-judge-deliberation-1"),
        pytest.param(5, 0, (1, 2, 3, 4), (1, 2, 3, 4), id="run-5-approve-r1-q1"),
        pytest.param(6, 0, (1, 2, 3, 4), (1, 2, 3, 4), id="run-6-deny-r1-q2"),
        pytest.param(7, 1, (1, 2, 3, 4, 6), (6,), id="run-7-deny-r1-q3"),
        pytest.param(8, 1, (1, 2, 3, 4, 5, 6, 7), (5, 6, 7), id="run-8-judge-deliberation-2"),
    ],
)
def test_since_selects_the_delta_run_by_run(
    proceeding: Transcript[Any],
    run: int,
    since: int,
    snapshot_entries: tuple[int, ...],
    expected_entries: tuple[int, ...],
) -> None:
    """`execution.md`'s eight-row table, row by row. Run 7 is the row that constrains all of
    them: its snapshot holds entry 6 and must not hold entry 5."""
    snapshot = _snapshot_of(proceeding, *snapshot_entries)
    assert render(snapshot, JudgeView(since)) == render(
        _snapshot_of(proceeding, *expected_entries), JudgeView(0)
    ), f"run {run} rendered the wrong delta"


def test_run_sevens_exclusion_is_the_snapshots_doing_and_not_sinces(
    proceeding: Transcript[Any], deny: Verdict
) -> None:
    """The sibling case, and the reason the two pieces of state are kept apart.

    `since` selects which rounds; the snapshot decides which filings of those rounds exist to
    select from. Hand run 7's `since` a snapshot that *does* hold entry 5 and it renders both
    — so `since` is not quietly doing the exclusion, and neither piece substitutes for the
    other. `approve` and `deny` run concurrently and either may file first, which is why a
    snapshot can be neither a prefix nor a slice of the live transcript.
    """
    run_seven = render(_snapshot_of(proceeding, 1, 2, 3, 4, 6), AdvocateView(deny, 1))
    assert run_seven == render(_snapshot_of(proceeding, 6), JudgeView(0))
    assert "responded to r1-q1" not in run_seven

    with_the_peer = render(_snapshot_of(proceeding, 1, 2, 3, 4, 5, 6), AdvocateView(deny, 1))
    assert with_the_peer == render(_snapshot_of(proceeding, 5, 6), JudgeView(0))
    assert "responded to r1-q1" in with_the_peer


def test_round_one_does_not_advance_since_so_an_advocate_sees_its_own_filing(
    proceeding: Transcript[Any], deny: Verdict
) -> None:
    """An advocate entering round 2 has `since=0` even though it filed in round 1: it was
    shown nothing there, because it argued blind. Filing and being shown are different events.

    Its own filing is in the delta and is not carved out — what it emitted was a bare id and
    an excerpt, and what entered the record has the tool and the reference stamped beside them.
    """
    delta = render(_snapshot_of(proceeding, 1, 2, 3, 4), AdvocateView(deny, 0))
    assert "[round 1] deny argued:" in delta
    assert "[deny/s1] W-2, 2024" in delta
    assert "s3://underwriting-docs/okonkwo/w2-2024.pdf" in delta


def test_a_since_past_the_last_round_renders_nothing(proceeding: Transcript[Any]) -> None:
    """The filter is a comparison on `Entry.round` and nothing else."""
    assert render(proceeding, JudgeView(2)) == ""
