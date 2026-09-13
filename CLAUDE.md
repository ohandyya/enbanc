# enbanc

Adversarial multi-agent adjudication, built on PydanticAI. Pre-`0.1.0`: the
public API described in `README.md` and `docs/design/` does not exist yet.

## Asking me questions

I hold every decision. When you are unsure, your job is to make the decision
easy to make well — not to make it fast.

1. **Prose first, `AskUserQuestion` last.** While we are still exploring — plan
   mode, brainstorming, anything where the shape is not yet agreed — ask in the
   message body and wait for a reply. The tool's chips are too small to carry an
   argument. Reach for it only once a decision has narrowed to a few named
   alternatives.
2. **Never open with `AskUserQuestion`.** Every call is preceded by a message
   that says what you found, what actually differs between the options, what
   each one costs later, and which you recommend and why. The options in the
   widget are labels for that text, not a substitute for it.
3. **Recommend, and mark it.** Your pick goes first with `(Recommended)`
   appended. A question with no recommendation is an unfinished analysis. Say
   plainly when you are near-indifferent, and say plainly when an option is a
   mistake.
4. **Show the artifact, don't describe it.** When options differ in something
   concrete — a doc structure, a signature, a directory layout — put it in each
   option's `preview` so I can compare them side by side.
5. **"Other" may be a question, not an answer.** If I type a question back,
   answer it in prose and ask again. Do not read it as a choice, and do not
   start work.
6. **One decision per question.** Never bundle unrelated choices to save a round
   trip. I would rather answer three questions than one compound one.
7. **A question is not a checkpoint to clear.** If `docs/design/`, the code, or
   an obvious default already answers it, decide, and tell me what you assumed.

## Documentation map

Read this before writing code. The directories are not interchangeable — each
one carries a different guarantee about whether its contents are true.

| Path | Guarantee | When to read |
|---|---|---|
| `docs/progress.md` | **Where the work stands.** Status is current; the log is dated. | First, at the start of a session |
| `docs/design/` | **Current truth.** How the system is meant to work. | Always, before implementing |
| `docs/implementations/` | **The build plan.** One doc per PR: scope, files, tests, order. | Before writing a PR's code |
| `docs/decisions/` | Immutable ADRs. Why a path was chosen. | When a decision seems arbitrary |
| `docs/glossary.md` | The domain vocabulary. | Always |
| `docs/guides/` | User-facing how-to. | When changing public behavior |
| `docs/journal/` | **Historical. May be stale.** Records of past work. | Only when explicitly asked |
| `tests/` | **What is actually verified.** Tiered by directory — see below. | Before adding a test |
| `notes/`, `local/` | Human-only. | Never — reads are denied |

## Rules

1. **`docs/design/` is the spec.** It describes the system as it is now, not as
   it once was. Edit it in place; never append "update:" sections.
2. **A change to behavior updates the design doc in the same commit.** If you
   implement something that contradicts `docs/design/`, the design doc is wrong
   and fixing it is part of the change — not a follow-up.
3. **Never treat `docs/journal/` as a spec.** Entries are dated snapshots,
   frozen at write time, and go stale by design. If a journal entry and a design
   doc disagree, the design doc wins.
4. **Superseded designs move to `docs/design/_superseded/`** rather than being
   deleted, and get a `status: superseded` line saying what replaced them.
5. **Write a journal entry only when the diff cannot explain itself.** Git log,
   the diff, and the PR description already cover *what* changed. A journal entry
   earns its place by recording how an episode of work went — a constraint found
   only by building, a shape the implementation was forced into, a dead end worth
   not repeating. Otherwise skip it. A choice that *binds* future work is an ADR
   in `docs/decisions/`, not a journal entry.
6. **`docs/progress.md` is the session checkpoint, not a spec.** The `wrap-up`
   skill maintains it: `Current state` is rewritten in place, `Log` entries are
   prepended and never edited. Reasoning belongs in `docs/journal/`, linked from
   the log entry — not inlined.
7. **Resolving an open question is three moves in one commit.** The answer goes
   into the design doc's prose, where it becomes spec; an ADR in
   `docs/decisions/` records why and what was rejected, indexed in
   `docs/README.md`; only then is the bullet deleted from `## Open questions`.
   Deleting without the first two drops the question without answering it, and
   leaving a struck-through bullet behind is the "update:" section rule 1
   forbids — the ADR is the record, and the index is how it is found. Two cases
   are not resolutions: a question that is merely *sharpened* stays, rewritten
   in place with no ADR, and one that goes *moot* is deleted by whichever ADR
   made it moot, which says so.

8. **`docs/implementations/` is a plan, never a spec.** One document per PR,
   breaking `docs/design/` into the order it gets built: scope, the design
   sections that PR implements, the files and tests it brings, what must merge
   first. Where one disagrees with `docs/design/`, the design doc wins — an
   implementation doc that contradicts it describes a mistake, not a change.
   Once the PR merges the document is history: the code is the truth about the
   code, so never read one to learn how the system currently behaves. A choice
   made while writing a PR that *binds* future work is still an ADR.

## Conventions

Every doc in `docs/` opens with frontmatter:

```yaml
---
status: current | superseded | draft
updated: YYYY-MM-DD
---
```

- `docs/design/` — named by subject, no numbers: `tribunal.md`, `transcript.md`
- `docs/implementations/` — one per PR, named by subject with no number:
  `package-skeleton.md`. The order lives in that directory's README table, not
  in the filenames, so resequencing the plan is one edit. The GitHub PR number
  is unknowable when the doc is written; it goes in the frontmatter as `pr:`
  once the PR is open. `status` tracks the PR: `draft` while it is planned,
  `current` once a PR is open and expected to merge as it stands, `superseded`
  if the approach was replaced. Both are stamped at the moment the PR opens,
  by [`create-pr-summary`](.claude/skills/create-pr-summary/SKILL.md)
- `docs/decisions/` — numbered and immutable: `0001-short-title.md`
- `docs/journal/` — dated: `YYYY-MM-DD-short-slug.md`

## Development

`make help` lists the available targets. Tooling is uv + ruff + pyright +
pytest, with pre-commit hooks enforced in CI.

### Modules

**`enbanc` and `enbanc.tools` are the only importable namespaces.** Every other
module under `src/enbanc/` is underscore-prefixed. A module named without the
underscore is public the moment anyone imports it, and that cannot be taken back
([`0034`](docs/decisions/0034-the-export-surface-is-the-package.md)).

`__all__` is the contract and its list is `docs/design/api.md`.
`docs/design/packaging.md` is the layout — the module map, the one forced import
cycle, and what `import enbanc` may not do.

### Credentials

**Some work needs a real provider or real Tavily** — the live test tiers, a
scratch script that calls a model, a one-off check that the `web_search` tool
actually searches. The values for that live in `.env`, which is gitignored and
which **you may not read**: it holds live secrets.

**`.env.example` is how you learn what `.env` contains.** It is the committed
template, it names every variable that belongs in `.env`, and it says in prose
what each one is for — `TAVILY_API_KEY`, `ENBANC_TEST_MODEL`, and whatever
credential the chosen provider needs. Read it instead of guessing, and never put
a real value in it.

- **The `make` live targets need nothing from you.** `integration-tests` and
  `e2e-tests` parse `.env` themselves, in `tests/conftest.py`'s `live_env`
  fixture, and skip when what they need is absent.
- **Everything else needs the variables in the shell first.** Source them in the
  same command, because shell state does not survive between calls:

  ```sh
  set -a && source .env && set +a && uv run python scratch.py
  ```

- **Never print a secret.** No `echo "$TAVILY_API_KEY"`, no `env`, no writing one
  into a file, a test fixture, or a commit. If a value looks wrong, say which
  variable is wrong and let me look.

### Tests

**A test's tier is the directory it lives in.** Nothing is marked by hand:
`tests/conftest.py` derives the marker from the path, and the offline guarantee
is an autouse fixture scoped to a directory. Filing a test in the wrong one
silently changes what it is permitted to do.

| Directory | Subject | Third parties | Target |
|---|---|---|---|
| `tests/unit/` | `enbanc`'s own behaviour — the bulk of the suite, and the only tier that tests edge cases | none, enforced | `unit-tests` |
| `tests/contract/` | claims `docs/design/execution.md` makes about `pydantic-ai` | none, enforced | `contract-tests` |
| `tests/integration/` | that the plumbing to a real service works | a provider, Tavily | `integration-tests` |
| `tests/e2e/` | that `docs/design/api.md`'s example works as written | a provider, Tavily | `e2e-tests` |

- **The offline tiers may not reach a third party, and a socket guard enforces
  it.** Fake the model with `TestModel` or `FunctionModel` —
  [`0003`](docs/decisions/0003-models-and-guidance-are-injected.md) makes it
  injected, so a whole proceeding runs with no provider. A test that genuinely
  needs the network belongs in a live tier, not in an exemption.
- **`make test` is the two offline tiers**, and it is what `check-all` and
  `ci.yml` run. The live tiers cost money and never run on their own: locally
  they read `.env`, and in CI they are `live-tests.yml`, fired by hand with the
  `live-tests` label on a PR or a `workflow_dispatch`
  ([`0033`](docs/decisions/0033-live-tiers-run-in-ci-on-demand.md)).
- **A red `contract` test means the dependency moved**, not that `enbanc` broke.
  The fix is usually prose in `docs/design/execution.md`.
- **The harness names no provider.** `ENBANC_TEST_MODEL` holds a model string
  and the credential is that provider's own, resolved by PydanticAI. `enbanc`
  commits to working with any `pydantic_ai.models.Model`, so a tier pinned to
  one provider would test less than the library promises. `TAVILY_API_KEY` is
  the exception, because
  [`0018`](docs/decisions/0018-the-search-client-is-a-core-dependency.md) already
  fixed that provider as the library's.

`docs/design/testing.md` is the strategy — including how the transcript
invariant is checked and how `outcomes.md` is mirrored — and
[`0031`](docs/decisions/0031-tests-are-tiered.md) is why the tiers are shaped
this way.
