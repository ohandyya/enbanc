---
name: create-new-release
description: Cut and publish a new release of enbanc to PyPI. Use when the user asks to create a release, cut a release, ship a new version, bump the version, publish to PyPI, or tag a release. Runs the full flow — version decision, release-prep PR, tag, GitHub release, CI watch, PyPI verification.
---

# Create a new release

Publishes a new version of `enbanc` to PyPI by way of a GitHub release.

## How the pipeline works

`.github/workflows/release.yml` fires on `release: published`. It checks out the tagged
commit, asserts `v$(uv version --short)` equals the tag name, then runs `uv build` and
`uv publish --trusted-publishing always` against the `pypi` environment.

Two consequences drive everything below:

- **The tag must point at a commit whose `pyproject.toml` already carries the new version.**
  This is the one real trap. Tag before pulling the merged bump and the job fails.
- **Publishing the GitHub release is the trigger.** Creating the tag alone does nothing;
  deleting a published release does not unpublish from PyPI.

## Preconditions

Verify before touching anything. Stop and report if any fail.

```bash
git rev-parse --abbrev-ref HEAD     # note where the user is
git status --porcelain              # must be empty
gh auth status
uv --version
```

A dirty working tree is a hard stop — ask the user to commit or stash first. If they are on
a branch other than `main`, confirm that `main` is really what they want released.

## Step 1 — Decide the version

```bash
git switch main && git pull
uv version --short                        # current version
git describe --tags --abbrev=0            # last tag
git log "$(git describe --tags --abbrev=0)"..HEAD --oneline
```

Read the commits since the last tag and propose a version. `enbanc` is pre-1.0, where
semver's normal rules are relaxed — `0.x` explicitly means the API may break:

| Situation | Next version |
|---|---|
| Still a placeholder, no real code | `0.0.z` |
| First release with real, usable code | `0.1.0` |
| Breaking change to a released API | bump minor (`0.2.0`) |
| Fixes and additions, nothing broken | bump patch (`0.1.z`) |

If there are **no commits since the last tag**, there is nothing to release — say so and stop.

Ask the user to confirm the number with `AskUserQuestion`, offering your proposal first with
the reasoning behind it. This is the only confirmation gate; once they answer, run the rest
end to end and only come back if something fails.

Throughout the rest of this document, `X.Y.Z` is the confirmed version.

## Step 2 — Release-prep PR

The version bump goes through a PR so the release has a reviewable trail and
`--generate-notes` has a PR title to pick up.

```bash
git switch -c release/X.Y.Z
uv version X.Y.Z                    # explicit; rewrites pyproject.toml and uv.lock
uv version --short                  # confirm it took
```

Prefer the explicit version over `uv version --bump minor` — the user confirmed a specific
number, so set that number.

### Changelog

Update `CHANGELOG.md` in the same commit, [Keep a Changelog](https://keepachangelog.com)
format. If the file does not exist, create it with this header and the new entry only — do
**not** backfill history for past releases unless the user asks:

```markdown
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [X.Y.Z] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

Write the entry from the actual commits since the last tag, in terms of what changed for a
user of the library — not a restatement of commit subjects. Omit any subsection with no
entries. Use today's real date. Newest version goes at the top, directly under the header.

### Open and merge

```bash
git commit -am "Release X.Y.Z"
git push -u origin release/X.Y.Z
gh pr create --title "Release X.Y.Z" --body "Version bump and changelog for X.Y.Z."
gh pr merge --squash --delete-branch
```

PR titles become the generated release notes, so keep every PR title in this repo
descriptive — it pays off here.

If `gh pr merge` reports that checks are still pending or a review is required, retry with
`--auto` and wait for it to land (`gh pr view --json state -q .state` until `MERGED`)
rather than bypassing protection.

## Step 3 — Tag the merge commit

```bash
git switch main && git pull          # ← the step that breaks releases when skipped
test "$(uv version --short)" = "X.Y.Z" || echo "MISMATCH — do not tag"
git tag vX.Y.Z
git push --tags
```

Run that `test` for real and check its output. If `pyproject.toml` on local `main` does not
say `X.Y.Z`, the merge has not arrived — pull again; do not tag.

## Step 4 — Publish

```bash
gh release create vX.Y.Z --generate-notes
```

`--generate-notes` builds the body from PR titles merged since the previous tag. This
publishes immediately, which is what fires the workflow.

## Step 5 — Watch CI

```bash
gh run list --workflow=release.yml --event=release --limit 1 --json databaseId,status -q '.[0]'
gh run watch <databaseId> --exit-status
```

The run may take a few seconds to appear; re-run the `list` command if it returns the
previous release's run or nothing. `gh run watch` blocks until the run finishes and exits
non-zero on failure, so no polling loop is needed.

## Step 6 — Verify on PyPI

```bash
curl -s https://pypi.org/pypi/enbanc/json | jq -r .info.version
```

Should print `X.Y.Z`. The JSON API can lag the upload by up to a minute — if it still shows
the old version right after a green run, re-check once before reporting a problem.

Report to the user: the version, the release URL, the CI conclusion, and the version PyPI
reports.

## Recovery

**Tag landed on the wrong commit** (the classic — tagged before pulling). The "Check tag
matches version" step fails. Harmless; redo it:

```bash
gh release delete vX.Y.Z --yes         # only if the release was already created
git push origin :refs/tags/vX.Y.Z
git tag -d vX.Y.Z
git switch main && git pull
git tag vX.Y.Z && git push --tags
gh release create vX.Y.Z --generate-notes
```

**Version already exists on PyPI.** PyPI refuses to overwrite a version, and deleting a
release does not unpublish it. There is no fixing this in place — bump to the next patch
version and run the whole flow again.

**`uv publish` fails on trusted publishing.** The workflow relies on `environment: pypi`
plus `id-token: write` and a matching trusted publisher configured on PyPI for
`ohandyya/enbanc` / `release.yml`. This is repo/PyPI configuration, not something to fix by
rerunning — report it to the user.

## Rules

- Never force-push a tag. Delete and recreate it.
- Never publish from a dirty working tree or from a branch other than `main`.
- Never skip the `git pull` in step 3.
- Do not run `uv publish` locally. Publishing goes through the workflow's trusted
  publishing; a local publish would need a token and would bypass the tag/version check.
