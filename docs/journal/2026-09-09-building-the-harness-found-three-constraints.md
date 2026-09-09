---
status: current
updated: 2026-09-09
---

# Building the harness found three constraints designing it had not

The fourth instance of a pattern the last three entries record
([`2026-09-02`](./2026-09-02-values-before-schemas.md),
[`2026-09-04`](./2026-09-04-writing-the-prompt-found-the-holes.md),
[`2026-09-05`](./2026-09-05-the-probe-found-the-holes.md)), and the first where
the artifact under construction was the thing that checks the other artifacts.

`design/testing.md` was settled in conversation before any of it was built: four
tiers, directory-as-tier, an enforced offline guarantee, `outcomes.md` mirrored
rather than executed. Those decisions survived contact and are recorded in
[`0031`](../decisions/0031-tests-are-tiered.md) and
[`0032`](../decisions/0032-a-design-doc-is-mirrored-by-tests.md). What did not
survive was three things the design had been quiet about, each found by running
the harness rather than by reading it.

## The tier layout dictates the import mode

Four tier directories, three of them seeded with a file called
`test_placeholder.py`. Each tier passed on its own. `pytest tests/` failed to
collect at all:

```text
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your
test file modules
```

Under pytest's default `prepend` import mode, and with `tests/` not a package,
two files sharing a basename resolve to one top-level module name and collection
aborts.

The reflex is to rename the files. That is the wrong fix, and seeing why is the
finding: **duplicate basenames are not incidental to this layout, they are its
normal case.** A tier is a directory, and the same subject gets tested from more
than one tier — `test_web_search.py` belongs in `tests/unit/` for the mapping
edge cases *and* in `tests/integration/` for the live call. The scheme
[`0031`](../decisions/0031-tests-are-tiered.md) chose generates this collision
continuously. Renaming three files would have deferred it to whoever wrote the
fourth.

`--import-mode=importlib` names each module from its full path and the class of
problem disappears. It is now in `pyproject.toml` with the reasoning attached,
because it reads like a style preference and is not one.

Worth noting what hid it: every per-tier `make` target passed, and so did
`make test`, because that runs `tests/unit tests/contract` and the collision was
between `unit` and `integration`. Only the bare `pytest` — the form nobody in the
Makefile uses — reproduced it.

## The socket guard is a tripwire, not a sandbox

The design said the offline tiers "enforce" being offline. Building it meant
choosing what to patch, and probing what that actually covers turned a slogan
into a bounded claim.

`socket.socket.connect` turns out not to be defined on `socket.socket` at all —
it is inherited from the C base `_socket.socket`, so patching it installs a
shadowing attribute on the Python subclass. That is fine (`monkeypatch` deletes
it on undo rather than re-setting it, verified), but it says exactly where the
guard's edge is. Four probes, all run:

| | |
|---|---|
| `asyncio.open_connection` | **blocked** |
| `socket.getaddrinfo` | resolves — DNS is untouched |
| `_socket.socket().connect` | bypasses — the C base is not patched |
| a subprocess | bypasses — `monkeypatch` is process-local |

The first row is the one that matters and is why the choke point is `connect`
rather than socket construction or name resolution: every HTTP client this
library will use is async, so httpx, the provider SDKs, and `tavily-python` all
land there without the guard naming any of them. The other three are why
`testing.md` now says the guard catches accidents rather than claiming it cannot
be escaped. The realistic gap is none of the probed ones: it is a client
constructed at **import time**, which connects before any fixture has run.

An enforcement mechanism whose reach is undocumented is worse than one with a
stated edge, because the undocumented one gets trusted for things it does not do.

## Provider-agnosticism reaches the harness

The first version of the live tiers required `ANTHROPIC_API_KEY`. This was
caught in review, not by running, and it is the sharpest of the three because
nothing would have failed: the tests would have passed on a machine with an
Anthropic key and skipped everywhere else, quietly encoding a provider the
library does not have.

[`api.md`](../design/api.md#design-commitments) commits to working with any
`pydantic_ai.models.Model` the caller constructs. A live tier that can only run
against one provider tests less than that. So `ENBANC_TEST_MODEL` holds a model
string, `infer_model` builds it, and the credential is the provider's own under
the provider's own variable name — resolved by PydanticAI, never enumerated by
the harness. `TAVILY_API_KEY` stays, because
[`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md) already
fixed that provider as the library's choice rather than the runner's.

Then running it produced the second finding. `infer_model` fails three different
ways across two exception types:

```text
ENBANC_TEST_MODEL=nonsuch:whatever    UserError:   Unknown model
ENBANC_TEST_MODEL=cohere:command-r    ImportError: install the `cohere` package
credential absent                     UserError:   Set the …_API_KEY variable
```

The first implementation caught `UserError` and skipped. That is wrong twice
over: it lets a typo pass as "not configured", and it does not catch the
`ImportError` at all. The rule the failures forced is **unset skips,
set-but-unusable fails** — an absent variable means the machine is not set up for
live runs, while a variable that is set and cannot be built means a live run was
asked for and did not happen. Skipping would hide a typo, a missing SDK, and a
missing key behind one green dot.

## Dead ends

**`from conftest import REQUIRED_KEYS` in a test module.** Written, then removed
before it ran. A conftest is not on the import path for the modules it serves,
and under the `importlib` mode adopted above it is not importable by that name at
all. Two lines of duplication in each live tier beat a `sys.path` trick.

**A blanket autouse skip on each live tier.** The first cut gated the whole tier
on both keys being present. Replaced by per-fixture skips — `live_model`,
`tavily_api_key` — so a Tavily test still runs on a machine with no model
configured. A tier-wide gate makes the coarsest possible claim about why nothing
ran.

## What to do with this

Same as the previous three entries: the artifact that gets built finds things the
artifact that gets read does not. The new part is that this held for a piece of
*infrastructure* whose whole purpose is to catch mistakes — the enforcement
mechanism had an undocumented edge, and only probing it produced the bounded
claim now in `testing.md`.

Concretely, for the next session: the import mode and the skip-vs-fail rule are
settled and recorded. The socket guard's edge is not a to-do, but the
import-time-client gap is worth remembering when the first real module lands,
because that is the shape that would slip past it.
