#!/usr/bin/env bash
# Checks the preconditions for cutting a release, without changing anything.
# Run as `make release-check`, or `make release-check VERSION=X.Y.Z` to also check that
# the version you intend to cut is still free. Every check runs; it exits non-zero if any
# failed. The release process itself is in CONTRIBUTING.md.

set -uo pipefail

version="${1:-}"
failed=0
pass() { printf '  \033[32mok\033[0m    %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; failed=1; }
info() { printf '        %s\n' "$1"; }

echo "Release preconditions"

branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$branch" = "main" ]; then pass "on main"; else fail "on '$branch', not main"; fi

if [ -z "$(git status --porcelain)" ]; then
  pass "working tree is clean"
else
  fail "working tree has uncommitted changes (commit or stash them)"
fi

if gh auth status >/dev/null 2>&1; then
  pass "gh is logged in"
else
  fail "gh is not logged in (run: gh auth login)"
fi

if git fetch --quiet origin main 2>/dev/null; then
  if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
    pass "up to date with origin/main"
  else
    fail "HEAD differs from origin/main (run: git switch main && git pull)"
  fi
else
  fail "could not fetch origin/main"
fi

current="$(uv version --short 2>/dev/null)"
last_tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"
echo
echo "Where things stand"
info "pyproject.toml version: ${current:-unknown}"
info "last tag:               ${last_tag:-none}"
if [ -n "$last_tag" ]; then
  count="$(git rev-list --count "$last_tag"..HEAD)"
  if [ "$count" -gt 0 ]; then
    pass "$count commit(s) since $last_tag"
  else
    fail "no commits since $last_tag: nothing to release"
  fi
fi

if [ -n "$version" ]; then
  echo
  echo "Version $version"
  if git rev-parse -q --verify "refs/tags/v$version" >/dev/null \
     || git ls-remote --exit-code --tags origin "refs/tags/v$version" >/dev/null 2>&1; then
    fail "tag v$version already exists"
  else
    pass "tag v$version is free"
  fi
  status="$(curl -s -o /dev/null -w '%{http_code}' "https://pypi.org/pypi/enbanc/$version/json")"
  case "$status" in
    404) pass "$version is not on PyPI" ;;
    200) fail "$version is already on PyPI, and PyPI never lets a version be reused" ;;
    *)   fail "could not ask PyPI about $version (HTTP $status)" ;;
  esac
fi

echo
if [ "$failed" -eq 0 ]; then
  echo "Ready to release. Next steps: CONTRIBUTING.md, under Releasing."
else
  echo "Not ready: fix the FAIL lines above."
fi
exit "$failed"
