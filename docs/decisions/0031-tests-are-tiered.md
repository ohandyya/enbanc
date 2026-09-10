---
status: accepted
updated: 2026-09-09
---

# 0031. Tests are tiered, and the offline tier is enforced

## Context

`../design/testing.md` was a placeholder until now, and the suite is two
placeholder tests. That is the moment to decide this: a tiering scheme is cheap
to adopt and expensive to reverse, because reversing it means rewriting every
test written under the old one.

Three facts about this library shape the answer.

**Almost everything is assertable offline.**
[`0003`](./0003-models-and-guidance-are-injected.md) makes the model an injected
dependency, so `TestModel` and `FunctionModel` run a complete multi-round
proceeding with no provider. The expensive tier is small by construction.

**Some tests are about the dependency, not about `enbanc`.**
`../design/execution.md` records ten findings about `pydantic-ai 2.36.0` and says
they "are worth re-checking when the pin moves." `../progress.md` is more
pointed: they "belong in `tests/` the moment it holds anything real, or a version
bump falsifies the document silently." They need no network, so they are
mechanically offline, but a failure means something entirely different from a
failure in `enbanc`'s own tests.

**A rule about network access is worthless unless something checks it.** A unit
test that quietly acquired a live provider call still passes. It is slower,
flakier, nondeterministic, and billed, and nothing about the green run says so.

## Decision

**Four tiers: `unit`, `contract`, `integration`, `e2e`.** `unit` is `enbanc`'s
own behaviour and carries the edge cases. `contract` holds the probes behind
`execution.md`'s findings. `integration` proves one happy path per external seam.
`e2e` runs `../design/api.md`'s example against real providers.

`contract` is separate from `unit` despite being equally offline, because its
failures are read differently: red there means the pin moved and a design
document is now wrong, and the fix is usually prose rather than code.

**A test's tier is its directory.** `tests/unit/`, `tests/contract/`,
`tests/integration/`, `tests/e2e/`. The Make targets select by path;
`tests/conftest.py` applies the matching marker during collection so `-m` also
works. No test is decorated by hand.

**The offline tiers enforce it.** An autouse fixture in the `unit` and `contract`
conftests replaces `socket.socket` with a raising stub. Loopback stays allowed;
reaching a third party is an error naming the test that did it.

**The live tiers do not run in CI.** They read keys from `.env` and are run by
hand through `make integration-tests` and `make e2e-tests`. `make test` stays an
alias for the offline tiers, so `check-all` and `.github/workflows/ci.yml` keep
the composition they already have.

*Revised by [`0033`](./0033-live-tiers-run-in-ci-on-demand.md): the live tiers
now run in CI when a maintainer asks for them, in a workflow of their own.
Everything else here stands.*

`../design/testing.md` owns the resulting strategy.

## Consequences

**The offline guarantee becomes a property of the suite rather than a habit.** It
holds for tests nobody has written yet, by authors who have not read this. That
is the difference between a decision and a preference.

**Directory placement is the only thing an author has to get right**, and it is
the thing they cannot avoid doing. A misfiled test is visible in the tree; a
missing marker is visible nowhere.

**CI needs no secrets and no new workflow.** Fork pull requests keep working,
nothing spends money unattended, and the existing `ci.yml` contract — that the
two jobs are exactly `make check-all` — survives untouched.

**Cost: provider drift surfaces only when someone runs the live tiers.** If
Tavily changes a response shape or a provider changes an error class, `enbanc`
learns about it at the next manual run, which could be weeks. This is the real
price of the CI decision and it is accepted for now because the library has no
users and no release cadence to protect. It is worth revisiting when it does; a
scheduled job against a repository environment holding the live tiers'
credentials is the obvious move, and nothing here makes that harder.

**Cost: four directories for a suite that does not exist yet.** Three of them
start close to empty. Accepted because the alternative is discovering the shape
later, with tests already written against the old one.

**Rejected: separation by marker alone, in one flat tree.** Fewer directories,
and the tier of a test is stated where the test is. Rejected on the enforcement
point: an autouse fixture cannot key off a marker that a test may or may not
carry, and an author who forgets one silently lands a live-calling test in the
default tier. Directory placement cannot be forgotten because the file has to go
somewhere.

**Rejected: `e2e` as a standalone script.** It would read the way a user's own
code reads and would double as documentation. Rejected because
`../design/api.md`'s entry points are async, so the script hand-rolls an event
loop, and it gives up fixtures, parametrization, skip-on-missing-key, and any
failure report richer than an exit code — all to avoid a directory. The
documentation argument is real and is better served by `api.md`'s example, which
already exists and which the `e2e` test runs.

**Rejected: live tiers on every pull request.** Full signal on every change.
Rejected because it bills a provider per push and breaks outright on fork pull
requests, which cannot read secrets.

**Rejected: a nightly live workflow.** Drift would surface within a day, which is
the cost named above. Rejected *for now* rather than on principle: it means
managing two secrets and an environment for a library with no users, and it can
be added later without touching anything this ADR decides.
