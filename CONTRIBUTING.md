# Contributing

## Setup

```sh
uv sync
make hooks       # install the pre-commit hook, once per clone
make help        # list every target
```

Tooling is uv, ruff, pyright and pytest. Python 3.11 or later.

## Before you open a PR

```sh
make check-all   # ruff lint, ruff format, pyright, and the offline tests
```

That is what CI runs. It needs no API keys.

**Tests are tiered by directory.** Where a test lives decides what it may do:

| Directory | Tests | Network | Target |
|---|---|---|---|
| `tests/unit/` | `enbanc`'s own behaviour | none, enforced | `make unit-tests` |
| `tests/contract/` | what the design assumes about pydantic-ai | none, enforced | `make contract-tests` |
| `tests/integration/` | the plumbing to a real provider and Tavily | yes, costs money | `make integration-tests` |
| `tests/e2e/` | the documented example and every guide | yes, costs money | `make e2e-tests` |

The live tiers read keys from `.env`. Copy `.env.example`, which says what each
variable is for. In CI they run only when asked for: add the `live-tests` label
to a PR. [`docs/design/testing.md`](./docs/design/testing.md) has the whole
strategy.

## Changing behaviour

[`docs/design/`](./docs/design/) is the spec. A change to behaviour updates the
design doc in the same PR. A decision that binds future work gets an ADR in
[`docs/decisions/`](./docs/decisions/). A change to what the models are told is
a new procedure version
([`docs/design/prompting.md`](./docs/design/prompting.md)).
[`docs/README.md`](./docs/README.md) explains what each docs folder is for.

## Releasing

**1. Check you're ready.** Releases are cut from an up-to-date `main` with a
clean working tree and `gh` logged in:

```sh
git switch main && git pull
make release-check
```

It changes nothing. It checks those preconditions and that there are commits to
release.

**2. Run the release.** In Claude Code, run
[`/create-new-release`](./.claude/skills/create-new-release/SKILL.md). It
proposes the version and asks you to confirm it, then opens and merges the
release PR with the changelog, tags the merge, publishes the GitHub release,
watches [`release.yml`](./.github/workflows/release.yml) publish to PyPI, and
checks that PyPI has the new version. It also knows how to recover if a step
fails. Nothing is ever published from a laptop.
