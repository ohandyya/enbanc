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

Publishing a GitHub release starts
[`release.yml`](./.github/workflows/release.yml), which checks that the tag
matches `pyproject.toml`'s version, then builds and publishes to PyPI. Nothing
is ever published from a laptop.

**1. Check you're ready.** Releases are cut from an up-to-date `main` with a
clean working tree and `gh` logged in:

```sh
git switch main && git pull
make release-check VERSION=X.Y.Z
```

It changes nothing. It checks those preconditions, that there are commits to
release, and that `vX.Y.Z` is free both as a tag and on PyPI.

**2. Pick the version.** `enbanc` is pre-1.0: a breaking change to the released
API bumps the minor (`0.2.0`); fixes and additions bump the patch (`0.1.1`).

**3. Open the release PR, and merge it.**

```sh
git switch -c release/X.Y.Z
uv version X.Y.Z            # updates pyproject.toml and uv.lock
# add a dated entry to CHANGELOG.md, written for users of the library
git commit -am "Release X.Y.Z"
git push -u origin release/X.Y.Z
gh pr create --title "Release X.Y.Z" --body "Version bump and changelog for X.Y.Z."
gh pr merge --squash --delete-branch
```

**4. Tag the merge commit.** Pull first. Tagging before the merged bump arrives
is the usual way a release fails.

```sh
git switch main && git pull
uv version --short          # must print X.Y.Z; if not, do not tag
git tag vX.Y.Z && git push --tags
```

**5. Publish, and watch it land.**

```sh
gh release create vX.Y.Z --generate-notes
gh run watch "$(gh run list --workflow=release.yml --limit 1 --json databaseId -q '.[0].databaseId')" --exit-status
curl -s https://pypi.org/pypi/enbanc/json | jq -r .info.version   # X.Y.Z, within a minute
```

**If it goes wrong:**

- **The tag was on the wrong commit.** The version check fails and nothing is
  published. Delete the release and the tag, both on GitHub and locally (never
  force-push a tag), pull, then tag and publish again.
- **The version is already on PyPI.** PyPI never lets a version be reused, and
  deleting the GitHub release does not remove it. Bump to the next patch and
  start over.

In Claude Code, asking to "cut a release" runs these steps through the
[`create-new-release`](./.claude/skills/create-new-release/SKILL.md) skill.
