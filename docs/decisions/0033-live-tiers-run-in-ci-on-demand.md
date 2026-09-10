---
status: accepted
updated: 2026-09-10
---

# 0033. The live tiers run in CI, but only when asked

## Context

[`0031`](./0031-tests-are-tiered.md) kept the live tiers out of CI entirely and
named the price: "provider drift surfaces only when someone runs the live tiers
… which could be weeks." It accepted that for a library with no users, and said
outright it "is worth revisiting."

This revisits half of it, and the half being revisited is not the cost. It is
the friction. Running `make integration-tests` requires leaving the pull request
under review, switching to a terminal, and having a populated `.env` on the
machine in front of you. The result then lives in that terminal's scrollback
rather than anywhere the pull request can show it. Nothing about that is a
decision anyone made; it is what falls out of having no workflow at all.

The thing `0031` was actually protecting against is *unattended* spend — a
provider billed on every push, on every fork pull request, or nightly forever.
A run that a maintainer explicitly asks for is not that.

One detail of the harness turns out to decide the shape. `tests/conftest.py`
makes a missing credential a **skip**: `live_model` and `tavily_api_key` call
`pytest.skip`, so `make integration-tests` on a fresh clone reports why instead
of erroring, and `../design/testing.md` defends that as correct. In CI the same
behaviour is a trap. A run with no secrets skips every test and reports green —
a live tier that proves nothing, indistinguishable from one that passed.

## Decision

**The live tiers run in CI only when asked.** Two ways to ask, both manual:

- **A `live-tests` label on a pull request.** The run reports as a check on that
  pull request, which is the point — the signal arrives where the change is
  being reviewed.
- **`workflow_dispatch`**, with a tier picker, for any branch from the Actions
  tab.

Nothing fires on `push`, on `pull_request: [opened, synchronize]`, or on a
schedule. Removing the label costs nothing; adding it is the entire gate.

**It is a separate workflow.** `.github/workflows/live-tests.yml` is new;
`ci.yml` is untouched, so its two jobs remain exactly `make check-all` and it
still needs no secrets. `make test` still means the two offline tiers.

**Credentials live in a `live-tests` GitHub environment**, not in repository
secrets: `OPENAI_API_KEY` and `TAVILY_API_KEY` as environment secrets, and
`ENBANC_TEST_MODEL` as an environment *variable*, since a model name is not a
secret and a run log that names the model tested is worth more than one that
hides it. This is the pattern `release.yml` already uses for `pypi`.

**In CI, an unset credential is a failure.** A preflight step fails when any of
the three is empty. The fixtures are not changed — unset still skips on a
laptop, because there it means "this machine is not configured for live runs,"
which is the ordinary state. In CI it means a run was asked for and did not
happen, which is a result.

`../design/testing.md` owns the resulting strategy.

## Consequences

**`0031`'s "CI needs no secrets and no new workflow" no longer holds.** There is
now one workflow that reads two secrets and one variable. The claim survives for
`ci.yml` specifically, which is where it mattered: the gate every change passes
through is still secret-free, and a change that cannot run the live tiers is
still fully reviewable.

**Drift still surfaces only when someone asks.** This buys convenience, not
coverage — the cost `0031` accepted is unchanged, because a label nobody adds
runs nothing. What changes is that asking is one click on the pull request
rather than a context switch, which is the difference between a thing that is
possible and a thing that happens.

**Fork pull requests cannot run the live tiers.** `pull_request` from a fork
gets no secrets, so labelling one fails at the preflight. The failure message
says so. This is a real limitation and it is the correct one: the alternative is
`pull_request_target`, rejected below.

**CI picks a provider, and the harness still does not.** The `live-tests`
environment holds an OpenAI key because something had to, and a workflow cannot
enumerate a credential it does not know the name of. This does not reopen
[`0031`](./0031-tests-are-tiered.md)'s "the harness names no provider": nothing
under `tests/` learns which one was chosen, `live_model` still builds whatever
`ENBANC_TEST_MODEL` names, and moving CI to a different provider is two secrets
and a variable with no change to any test. It is the same choice a populated
`.env` makes on a laptop, made in the same layer.

**The skip/fail rule now depends on where the tests run**, which is one more
thing to know about a harness whose whole appeal is that a test's tier is
visible in its path. It is confined to a single step in one workflow file, and
the step says why.

**Rejected: `pull_request_target` so fork pull requests work.** It runs in the
base repository's context with access to secrets, and the checkout it needs is
the fork's code. Handing an untrusted contributor's code a provider key and a
writable token is the well-documented way to lose both. A maintainer who wants
to run the tiers on a fork's change can push the branch to this repository.

**Rejected: a nightly schedule.** Still deferred, and still for `0031`'s reason
— the library has no users and no release cadence to protect, and a nightly job
spends money whether or not anything changed. Adding one later is now nearly
free: the environment and the workflow exist, and it is a `schedule:` block.

**Rejected: making the fixtures fail rather than skip when a key is absent.** It
would delete the preflight step and put one rule everywhere. Rejected because it
breaks the case `../design/testing.md` explicitly designed for — a fresh clone
running `make integration-tests` and being told why rather than handed a red
suite — and because it would make a Tavily-only machine unable to run the Tavily
test, which is the reason there is no tier-wide gate in the first place.

**Rejected: repository secrets instead of an environment.** Fewer clicks to set
up. Rejected because every workflow in the repository could then read a provider
key, including ones added later for unrelated reasons, and because the
deployments log an environment produces is the only per-run record of when the
library last spent money.
