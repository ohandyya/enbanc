---
status: draft
updated: 2026-10-14
---

# Content moderation, watched live

**The second guide, and the last of the `e2e` tier.** A flagged forum post goes
before three advocates, and the reader watches each filing land as it is made.

## Scope

[`guides.md`](./guides.md)'s rule: a guide is a different real decision, and it
teaches surface no earlier guide did. `loan_assessment.py` covered the core loop,
a custom tool, `render()`, the tool-call listing, both outcomes and a budget.
`content_moderation.py` teaches what is left on the streaming side:

- **`hear_stream`.** The loop is the guide's centre: `async with
  tribunal.hear_stream(post) as proceeding`, then `async for entry in
  proceeding`, then `proceeding.hearing` once it ends. The comments carry the
  contract from [`api.md` § Watching it live](../design/api.md#watching-it-live)
  — the stream is the record, it moves at the consumer's pace, breaking out is
  allowed, and `hear()` is this loop consumed.
- **Matching on what was filed.** Each entry's filing is matched on its kind —
  `Argument`, `Concession`, `Continuance`, `Response`, `Ruling` — so the reader
  sees the procedure itself: arguments, the judge's questions, the answers, a
  ruling.
- **Three verdicts, so three advocates.** `ALLOW`, `REMOVE`, and
  `ESCALATE = "escalate to a human moderator"` — the value is what the model
  reads, so a value can carry its meaning. The loop prints member names, the
  code's handle, because the long value makes an unreadable label.

**The case is a genuine gray area, chosen so each side has a real argument.**
A long-standing, trusted member of a home-canning community says they have
water-bath canned heirloom tomatoes for thirty years without added acid, testing
each batch with pH strips, and calls the USDA's "always acidify" rule
conservative and partly about liability. The policy's three rules pull against
each other — remove a false safety claim stated as fact where harm would be
serious; allow experience and criticism of guidance framed as such; escalate when
a post mixes the two — and the moderation file adds a community norm (an
"Untested method" flair the post lacks). `REMOVE` argues from food-safety
guidance (acidify all tomatoes; botulism below pH 4.6), `ALLOW` reads the claim
as conditional and proposes the flair instead, `ESCALATE` argues the mix itself.

**The first case was too easy, and that is the lesson the guide carries.** It
was a weed-killer post with a checkable false claim; `ALLOW` conceded in every
run. With the canning case and a neutral judge — the guidance names what to weigh
and says escalation is a decision, not a default — `ALLOW` still conceded once in
two runs, so all three advocates now share one guidance line: argue the
strongest good-faith reading, concede only if none exists. Across three runs
after that, every advocate argued and the judge questioned one to three of them
before ruling.

All three advocates get the same two tools — a `moderation_file` factory over
the reports, the thread, the author's history and the community rules, and
`web_search` capped at two results — and the same guidance. Asymmetry is the
loan guide's lesson; repeating it would add a line and teach nothing.

**This empties [`zero-one-zero.md`](./zero-one-zero.md)'s `e2e` scope.** That
PR was to run the `hear_stream` loop against a real provider; this guide's test
does, so it becomes the documentation sweep alone, and its open question is
answered.

**Not in this PR.** `render()` and the tool-call listing — the loan guide
teaches both, and printing them here would bury the stream under output a
reader has seen.

## Implements

- [`api.md` § Watching it live](../design/api.md#watching-it-live) — as a file a
  reader runs, linked from that section.
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  `e2e` row's `hear_stream` loop.

## Depends on

[`guides.md`](./guides.md) (#31), merged — the guide contract, the `e2e` harness
(`closed_after`, `closed_models`), and the `ENBANC_MODEL` convention this reuses.

## Files

| File | Change |
|---|---|
| `docs/guides/content_moderation.py` | **New.** The guide. |
| `tests/e2e/test_guides.py` | The loan test's shape checks move into `assert_coherent(hearing, verdicts)` and loading into `run_guide(name, …)`, shared by both tests. **New `test_content_moderation`.** |
| `docs/guides/README.md` | A second row, and its run command. |
| `docs/design/api.md` | § Watching it live links the guide as its runnable form. |
| [`zero-one-zero.md`](./zero-one-zero.md) | Scope becomes the documentation sweep alone; its `hear_stream` item and open question go. |
| [`README.md`](./README.md) | This document as row 13; `zero-one-zero.md` moves to 14. |

## Tests

**`tests/e2e/test_guides.py::test_content_moderation`**, in the `e2e` tier
because it calls a real provider and real Tavily. Same setup as the loan test,
plus `capsys`.

- `assert_coherent` — the checks every guide's hearing meets: an outcome of
  either kind; each advocate heard once in round 1; rounds in order; every
  exhibit resolving to its own advocate's ledger row; the ruling last, on a
  ruling; every row naming its call; non-zero usage.
- **The stream yielded the record.** The guide prints one `[round N]` line per
  entry as it arrives, and the printed sequence must equal the transcript's
  rounds, entry for entry — every entry, in filing order, nothing else.
- The custom tool reached the model: a `mod-file://` reference is in the ledger.

## Open questions

None.
