---
status: draft
updated: 2026-10-14
---

# Guides that run

**`docs/guides/` stops being an empty directory of pages that were never
written, and becomes a small set of single-file Python scripts a reader can
execute.** A guide here is not a page about `enbanc`; it is the shortest program
that uses `enbanc` to do one real thing, and it is verified by running it.

## Scope

**One use case, one file, no supporting cast.** Each guide is a single `.py`
under `docs/guides/`, runnable as it stands — `uv run docs/guides/<name>.py` —
with no local imports, no CLI arguments, no helper module beside it, and nothing
in it that is not needed to show the use case. The moment a guide grows a second
file it has stopped being an example and become a small application, which is a
thing a reader must understand before they can learn anything from it.

**A guide is a use, and it earns its file by teaching something new.** Each
guide is a different real decision someone would put in front of a tribunal —
a loan, then whatever follows — because a reader looks for the task they have,
not for the feature that serves it. But a second script that runs the same three
calls with a different noun is a file to maintain for nothing, so **every guide
after the first must show at least one part of the surface no earlier guide
did**. The domain is what a reader searches for; the new feature is what keeps
the set from being repetition.

**The first guide is `loan_assessment.py`**: [`api.md` § Shape](../design/api.md#shape)
made executable. That block is written as prose — `psql` is undefined, the
case fields are `...`, the search key is `api_key=...` — so the guide is not a
copy of it but the runnable version of the same example. What it teaches is the
core loop, end to end:

- **A verdict enum, a statute, and a case** — `LoanDecision(Verdict)` with
  `APPROVE` and `DENY`, exactly Shape's two; a `Statute` whose `text` is a short,
  written-out underwriting rule (a debt-to-income ceiling of 0.43, documented
  income over stated income, a minimum credit score), named `underwriting-v3`;
  and a `LoanApplication(Case)` subclass with real fields — applicant, amount
  requested, term, stated annual income, monthly debts, employer.
- **A custom tool, built the way [`evidence.md` § Adding your own tool](../design/evidence.md#adding-your-own-tool)
  says to.** The applicant's file is a dict of documents defined in the script —
  a pay stub, a tax return, a credit report — and a factory,
  `loan_file(documents)`, closes over it and returns an inner
  `async def find_documents(applicant: str) -> list[Source]`, one `Source` per
  document with a `loan-file://…` reference. That is steps 2 and 3 run for real,
  which is why the custom-tool guide the earlier plan floated collapses into this
  one rather than getting a file of its own.
- **An asymmetric toolbox.** Both advocates get `find_documents`; only
  `APPROVE` also gets `web_search`, to look up the employer. That is Shape's
  asymmetry kept on purpose — the two sides of a real decision do not need the
  same evidence sources.
- **A case built to be argued.** Stated income runs above what the tax return
  documents, and the debt-to-income ratio lands just either side of the ceiling
  depending on which income is believed. A clean case teaches nothing about an
  adversarial process; this one gives the `DENY` advocate's guidance —
  *"Weigh documented income over stated income"* — something to bite on.
- **The `Ruling` / `Undecided` `match`, both arms printed**, then
  `hearing.usage` and `hearing.usage_by_participant`.

**The model is a string from the environment, with a default.** The guide
builds its model with `pydantic_ai.models.infer_model` from `ENBANC_MODEL`,
falling back to **`openai:gpt-6-luna`** when it is unset. So a reader with an
`OPENAI_API_KEY` runs it with nothing else to set, and anyone else points it at
their own provider with one variable. That is the caller's code building a
`Model` and handing it over, which is what
[`0003`](../decisions/0003-models-and-guidance-are-injected.md) requires — the
model string never reaches `Tribunal`. Hard-coding a model class, as Shape's
prose does with `AnthropicModel`, would pin the `e2e` tier to one provider,
which the harness refuses to do.

**Credentials are plain `os.environ`, failing in one line.** `TAVILY_API_KEY`
is read directly, and a missing one exits with a message naming the variable
before anything is spent. The provider's own key is PydanticAI's to resolve, as
everywhere else. The guide does not read `.env` and imports no dotenv: a reader
sees exactly what the library needs from them, and nothing about how this
repository's tests happen to supply it.

**The script is `async def main() -> Hearing`**, run by
`if __name__ == "__main__": asyncio.run(main())`. Returning the hearing
rather than only printing it is the one concession the guide makes to being
tested: it is what lets the `e2e` test load the very file a reader runs and
assert on the result, instead of carrying a second copy of the example or
scraping stdout.

**A guide is executed by the `e2e` tier, and every guide runs on every live
run.** A script that nothing runs is a snippet, and it rots on the first
signature change — which is the whole reason [`../../CLAUDE.md`](../../CLAUDE.md)
makes `tests/` the thing that is actually verified. Running only a
representative guide would be a weaker guarantee bought to save money, and the
cheaper way to save it is the rule above: the set stays small because each guide
must teach something new. The tier directory already exists
(`tests/e2e/conftest.py`, plus a placeholder), so this PR adds tests to it rather
than building it.

**`api.md` § Shape stays prose, and is kept in sync by hand.** Its job is to show
the whole surface in one screen, which a runnable script with a real case and a
real tool cannot do. Shape gains one sentence linking to `loan_assessment.py` as
its runnable form, and the two are reconciled by whoever changes either. Making
the design doc quote the script was the alternative; it would trade the compact
version away to remove a drift that a reviewer can see in one diff.

**Three edits ride along, and none of them are optional.**

- [`../guides/README.md`](../guides/README.md) is rewritten. It currently
  promises *"the pages that would seed a documentation site"* and says the
  directory is *"empty until there is something that runs"* — both stop being
  true here. It becomes the index of the scripts, each with the use it shows and
  what it teaches, and the statement of the contract above: one file, runnable,
  executed by `e2e`, and new surface per guide.
- [`packaging.md` § Stability, before 1.0](../design/packaging.md#stability-before-10)
  says `../guides/` *"is still empty"*. It is a design document describing
  behaviour this PR changes, so it is corrected in the same commit
  ([`../../CLAUDE.md`](../../CLAUDE.md) rule 2). *"A guide is the map of a
  task"* survives the edit — that sentence is why this PR exists.
- `pyproject.toml`'s `[tool.pyright]` gains `docs/guides` in `include`, which is
  today `["src", "tests"]`. Ruff needs nothing: `make lint` and `make format`
  already run over `.`, so a guide script is linted and formatted the day it
  lands.

**Not in this PR.**

- **A documentation site.** No mkdocs, no rendered HTML, no navigation config.
  These are files in a repository that a reader can open and run.
- **Prose guides.** Where a guide needs narrative it gets comments in the
  script. A page with no runnable script is not a guide under this document.
- **Shipping guides in the wheel.** `pyproject.toml`'s build-backend section
  stays bare on purpose, and `docs/` is not packaged. A guide is read in the
  repository, not imported from site-packages.
- **`hear_stream`.** `loan_assessment.py` calls `hear()`. Watching a proceeding
  live is a candidate for a later guide; until one exists, the `hear_stream`
  loop stays in [`zero-one-zero.md`](./zero-one-zero.md)'s `e2e` scope, and that
  document says so.
- **The `draft` → `current` sweep, `CHANGELOG.md`, and the version bump** —
  [`zero-one-zero.md`](./zero-one-zero.md).

## Implements

- [`api.md` § Shape](../design/api.md#shape) — as a file a reader runs, which is
  the same claim [`zero-one-zero.md`](./zero-one-zero.md)'s `e2e` test makes
  about it. Landing the guide first is what lets that test run this script
  instead of carrying a second copy of the example.
- [`api.md` § When something goes wrong](../design/api.md#when-something-goes-wrong)
  — the `Ruling` / `Undecided` `match` is in the guide because a caller who
  copies an example that ignores the second arm has copied a bug.
- [`packaging.md` § Stability, before 1.0](../design/packaging.md#stability-before-10)
  — *"a guide is the map of a task"*. This is the first task mapped, and the
  sentence saying the directory is empty is retired by it.
- [`evidence.md` § Adding your own tool](../design/evidence.md#adding-your-own-tool)
  — steps 2 and 3, which exist only as prose, run as `loan_file`.
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  `e2e` row gains its first real occupant.

## Depends on

[`failures.md`](./failures.md) (#29) and [`stream-ordering.md`](./stream-ordering.md)
(#30), both merged. **#29 was the last PR to change the public surface** —
`__all__` completed in [`proceeding-core.md`](./proceeding-core.md), the
endings in [`round-loop.md`](./round-loop.md), and the error types in
`failures.md` — so the guide maps a target that has stopped moving. #30 changed
no surface, but before it `proceeding.transcript[-1]` ran ahead of the stream for
any consumer that `await`s inside its loop, which is the consumer a streaming
guide would show.

## Files

| File | Change |
|---|---|
| `docs/guides/loan_assessment.py` | **New.** The guide, as described under Scope. Module docstring says what it shows and how to run it: `uv run docs/guides/loan_assessment.py`, with `OPENAI_API_KEY` and `TAVILY_API_KEY` set, or `ENBANC_MODEL` and that provider's key instead. |
| `docs/guides/README.md` | **Rewritten.** Index of the guides — one row per script: the use, what it teaches, the variables it reads — and the contract from Scope. |
| `docs/design/packaging.md` | § Stability, before 1.0: *"which is still empty"* replaced with a pointer to the guides. |
| `docs/design/api.md` | § Shape: one sentence linking `loan_assessment.py` as its runnable form. |
| `pyproject.toml` | `[tool.pyright] include` gains `"docs/guides"`. |
| `uv.lock` | `pydantic-ai` 2.36.0 → 2.56.0 and `genai-prices` 0.1.4 → 0.1.12. The guide's default, `openai:gpt-6-luna`, is unknown to 2.36.0 and unpriced by 0.1.4, so its `cost_limit` could not be enforced; both are known and priced at these versions. The `pyproject.toml` floor stays at `>=2.36.0` — the library needs nothing newer, only the guide's default does. |
| `tests/e2e/test_guides.py` | **New.** One test per guide; see Tests. |
| `tests/e2e/test_placeholder.py` | **Deleted.** Its docstring says to replace it once there is an `enbanc` to run, and there now is. The `live_model` skip-or-fail behaviour it exercised is exercised by the new test. |
| `.env.example` | `ENBANC_TEST_MODEL`'s comment gains a sentence: the guides read `ENBANC_MODEL`, and the `e2e` tier sets it from this variable. |
| [`zero-one-zero.md`](./zero-one-zero.md) | Scope and open question rewritten: what remains for it is the `hear_stream` loop. |

## Tests

**`tests/e2e/test_guides.py::test_loan_assessment`** — the only new test, in the
`e2e` tier because it calls a real provider and real Tavily.

- **Setup.** Requests `live_model`, so it skips when `ENBANC_TEST_MODEL` is unset
  and fails when it is set and unusable, like every live test. Skips when
  `TAVILY_API_KEY` is absent from `live_env`. Puts `live_env` into the process
  environment with `monkeypatch.setenv` and sets `ENBANC_MODEL` to
  `ENBANC_TEST_MODEL`'s value — so the test runs the guide against the runner's
  provider, not the guide's default, and the tier stays provider-neutral.
- **Execution.** `runpy.run_path("docs/guides/loan_assessment.py")` loads the
  file without triggering its `__main__` block, and the test awaits the
  `main()` it defines. The file under test is the file a reader runs, byte for
  byte.
- **Assertions — about the shape of the hearing, never its content.** A model is
  free to rule either way, so the verdict is not asserted:
  - `main()` returned a `Hearing` whose outcome is a `Ruling` or an
    `Undecided`.
  - The transcript is coherent: round 1 holds one `Argument` per verdict; entry
    rounds never decrease and none exceeds `hearing.rounds`; every exhibit's
    `source` resolves to an entry in `transcript.ledger`; and on a `Ruling`, the
    last entry is that ruling.
  - `find_documents` was called — at least one ledger source has a
    `loan-file://` reference. That is what proves the custom tool reached the
    model, which is the part of the guide no unit test can.
  - Usage is non-zero: `hearing.usage.requests > 0`, and every participant in
    `usage_by_participant` made at least one request.

Nothing is added to the offline tiers. Everything the guide calls is already
unit-tested; what only this test can catch is the composition failing against a
real model.

## Open questions

Resolved before this PR merges.

- **Which use comes second.** The rule is settled — a different use, teaching at
  least one thing no earlier guide did — and so is what is left to teach:
  watching a proceeding live ([`api.md` § Watching it live](../design/api.md#watching-it-live))
  and reading a persisted hearing back
  ([`outcomes.md` § 7](../design/outcomes.md#7-persisting-a-hearing-and-reading-it-back)).
  Which domain carries each is not decided. Whether it lands in this PR or the
  next is the same question: this PR is complete with `loan_assessment.py` alone.
