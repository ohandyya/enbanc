---
status: current
pr: 21
updated: 2026-09-13
---

# The default tool

**`enbanc.tools.web_search`, and the second importable namespace.** The only
tool `0.1.0` ships, written against Tavily's own SDK as a plain async function
returning `list[Source]` — the same kind of object a user's own tool is.

## Scope

`tools/__init__.py` and `tools/_web_search.py`. The factory takes `api_key` and
`max_results`, sends `query` and `max_results` and nothing that changes the
response shape, and maps three Tavily fields onto `Source` while dropping the
rest.

**Not in this PR.** The ledgering that turns what this returns into a citable
exhibit — that is [`ledgering-toolset.md`](./ledgering-toolset.md). This tool
knows nothing about a proceeding.

**The public factory grows no seam for the tests.** `web_search(api_key=...)` is
fixed by the design; the unit tests monkeypatch the Tavily client class in this
module instead.

## Implements

- [`evidence.md` § The default tool](../design/evidence.md#the-default-tool) —
  the field mapping, and what is deliberately dropped
- [`evidence.md` § Step 3 — a factory](../design/evidence.md#step-3--a-factory-when-the-tool-needs-configuration)
  — the shape this tool shares with a user's own
- [`packaging.md` § Two namespaces](../design/packaging.md#two-namespaces-and-nothing-else)
- [`testing.md` § Faking Tavily](../design/testing.md#faking-tavily)

## Depends on

[`schemas.md`](./schemas.md), for `Source`.

## Files

Two modules, both new, and the first code in the package that is not a schema.

| Module | Public | Imports |
|---|---|---|
| `tools/_web_search.py` | `web_search` | `.._evidence`, `tavily` |
| `tools/__init__.py` | `web_search` | `._web_search` |

`tools/` sits at the bottom of
[`packaging.md`](../design/packaging.md#the-modules)'s module list and nothing in
the package imports back up into it, so this PR adds no edge to
[what imports what](../design/packaging.md#what-imports-what) and touches neither
end of the one forced cycle.

### `tools/_web_search.py`

```python
from tavily import AsyncTavilyClient

from .._evidence import Source


def web_search(api_key: str, *, max_results: int = 5) -> Callable[[str], Awaitable[list[Source]]]:
    client = AsyncTavilyClient(api_key=api_key)

    async def web_search(query: str) -> list[Source]:
        """Search the web and return the results, most relevant first."""
        response = await client.search(query, max_results=max_results)
        ...

    return web_search
```

`Source` arrives by relative import from `_evidence`, the way `_filings.py`
reaches `Exhibit`, rather than through `from enbanc import Source`. The public spelling
is what [`evidence.md`](../design/evidence.md#step-2--return-source-when-there-is-a-real-place-to-point)
shows a *user*; inside the package the private module is the path, and the
export surface is for callers.

**`AsyncTavilyClient` is bound at module scope because the tests replace it
there.** [`testing.md`](../design/testing.md#faking-tavily) fixes the seam as
monkeypatching the client class in the module that defines the tool, and that
only works against a module-level name. This is the whole of the accommodation
the tests get: the signature is `evidence.md`'s, unchanged.

**One client per factory call, shared by every call the tool makes.**
[`evidence.md` § What tools may do](../design/evidence.md#what-tools-may-do)
tells users to share a client and not to share mutable per-call state, and the
default tool is an example of that rule rather than an exception to it.
Constructing it in the factory body is safe: `AsyncTavilyClient.__init__` builds
an `httpx.AsyncClient` and performs no I/O, and it does not require a running
event loop, so `web_search(api_key=...)` at module scope in a user's script
opens nothing.

**There is no `close()`.** The factory returns the function and nothing else, so
there is no object a caller could close and no lifecycle to document. The pool
lives as long as the process, which is the right answer in a program.

**It is the wrong answer under pytest, and that was found by running it.** This
document claimed an uncollected client emits no `ResourceWarning`; `httpx` indeed
defines no `__del__`, but asyncio's transport does and so does the socket beneath
it. pytest-asyncio gives each test its own event loop, the client outlives it, and
collecting it later raises two `ResourceWarning`s — which `filterwarnings =
["error"]` turns into a failed session *after* the test has already passed.

The cost is paid in the harness, not in the signature. The integration tier
[closes what the factory built](#testsintegrationtest_web_searchpy) through the
same module-level seam the unit tier fakes. A `close()` on the tool would be
public surface existing for one caller who is not a user, which is exactly the
trade [`testing.md`](../design/testing.md#faking-tavily) refuses — and `evidence.md`
fixes the signature without a lifecycle on it.

#### `max_results` is a factory keyword

`evidence.md` fixes that `web_search` "sends `query` and `max_results`" without
saying where the second one comes from. It is the factory's, defaulted to 5:

```python
Advocate(tools=[web_search(api_key=KEY)])                   # five results
Advocate(tools=[web_search(api_key=KEY, max_results=3)])    # three
```

Three reasons, and none of them is ergonomics.

**It is the shape the design already showed.**
[`evidence.md` § Step 3](../design/evidence.md#step-3--a-factory-when-the-tool-needs-configuration)
writes `docstore_search(client: DocStoreClient, *, limit: int = 5)` and then says
*"`web_search` is a factory of exactly this shape."* A keyword-only count with a
default is that shape, spelled the same way.

**The lever belongs to the caller, not to the model.**
[`api.md` § The record](../design/api.md#the-record) says the
ledger's size is the caller's to control and names this tool's refusal to request
`raw_content` as the example. A `max_results` in front of the model would hand
that back: nothing stops an advocate asking for twenty, and twenty snippets land
in the transcript verbatim. It would also falsify the rendered references
[`outcomes.md`](../design/outcomes.md) prints — `render_call` renders what the
model sent, and `web_search(query="§4.2 filed income")` stops being the only
shape the moment the model can set a second argument.

**Five rather than Tavily's ten.** The server-side default is 10 when the field
is omitted, so "send nothing" is not the neutral option it looks like — it is the
option that puts ten snippets in every ledger entry. Five is the number
`docstore_search` uses in the document this tool is modelled on.

The default keeps `web_search(api_key=...)` valid, so
[`api.md` § Shape](../design/api.md#shape), `README.md`, and every example in
[`outcomes.md`](../design/outcomes.md) stay correct as written.

#### The mapping, and what happens to a row that cannot be mapped

`url` to `reference`, `title` to `label`, `content` to `content`, and `score`,
`id`, `raw_content`, `favicon` and the top-level `answer` dropped — all of it
[`evidence.md` § The default tool](../design/evidence.md#the-default-tool)'s.

**Dropping the last four costs no code.** Every response-shaping parameter on
`AsyncTavilyClient.search` defaults to `None` and is stripped from the request
body before it is sent, so a call passing only `query` and `max_results` already
asks for none of them. The tool suppresses nothing; it declines to ask.

#### What Tavily actually returns

Verified 2026-09-13 against `tavily-python 0.8.1` and the live service, by a
`search(query, max_results=…)` passing nothing else. The unit tests' canned
response mirrors this exactly, because a fake that is tidier than the service is
a fake that hides the mapping's real work:

```text
per result   content  id  raw_content  score  title  url
top level    answer  follow_up_questions  images  query
             request_id  response_time  results
```

**`raw_content` is present with the value `None`; it is not omitted.** `favicon`
is genuinely absent, and so is every other unrequested per-result field. This is
the one place [`evidence.md`](../design/evidence.md#the-default-tool) was wrong —
it had grouped the two as "absent unless asked for" — and the correction this PR
makes is [below](#design-documents). Nothing in the mapping changes: a key whose
value is `None` is dropped by the same code that drops a key that never arrived.

**The three top-level extras are `None`, `None` and `[]`.** `answer` and
`follow_up_questions` come back null and `images` empty, none of them requested.
`evidence.md` says the `answer` is "not requested", which is exactly true and
stays as written — a null is not a summary.

**`id` is returned on every result, and `evidence.md`'s reason for refusing it is
verified rather than merely plausible.** Ids look like `86b3e5-00`, `1175a2-01`,
`db18ee-02` — the shape the design doc quotes as `"e5450d-00"`. The suffix is the
result's position in the response. The prefix is per request: **the same URL, for
the same query, issued twice, came back as `86b3e5-00` and then `d07128-00`.** So
the id is scoped to the request that produced it and not to the document, which
is the design doc's claim word for word, and a citation built on one would be
unresolvable the moment the search was re-run.

**A result missing `url` or `content` is skipped, and the rest of the response is
returned.** `evidence.md` states that all three fields are present and non-empty
on every result, so this path is unreachable against a Tavily that behaves as
documented — but `Source.reference` is required, so a row without a locator
cannot be represented at all, and the behaviour has to be decided rather than
left to a `KeyError`.

Skipping rather than raising, because
[`evidence.md`](../design/evidence.md#what-tools-may-do) says a tool that expects
to come up empty should return an empty result rather than raise, and a raise here
is not proportionate: one malformed row out of five would end the entire
proceeding, discarding four usable sources and every filing already made.

**The cost, stated plainly: a skipped row never reaches the ledger.**
[`evidence.md`](../design/evidence.md#the-ledger-is-part-of-the-record) exists to
answer *what did the advocate see and choose not to show me?*, and a row dropped
inside the tool is invisible to that question. It is accepted because the row had
no reference, which is the one thing an entry in the record is for. A row that
cannot be cited cannot be an exhibit, and a ledger entry that cannot be cited is
not the thing the ledger was built to hold.

`label` needs no such rule: it is `str | None` on `Source` already, so a missing
`title` becomes `None` and the exhibit renders without one.

#### Nothing is caught

Tavily's SDK raises `InvalidAPIKeyError`, `UsageLimitExceededError`,
`BadRequestError`, `ForbiddenError`, and a `TimeoutError` of its own on the
client's 60-second default. None of them is caught, converted, or retried.

This is [`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md) applied to
the tool the library itself ships. The documented bound is the caller's, on the
object the setting rides on:

```python
Tool(web_search(api_key=...), timeout=15.0, max_retries=5)
```

A `web_search` that caught a 429 and returned `ModelRetry` would be a tool with a
capability no user's tool has, and
[`evidence.md`](../design/evidence.md#step-3--a-factory-when-the-tool-needs-configuration)
is explicit that there is no privileged path for built-in tools. It would also
put a second bound beside `Tool(timeout=)` for a caller to discover disagreeing
with the first. So a Tavily error propagates, ends the round, and surfaces as
`ProceedingFailed` with the original exception as `__cause__` — which is what
`evidence.md` already says happens to a tool that raises.

#### The inner function shadows the factory

`def web_search` inside `def web_search` reads as a mistake and is not one.
[`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md) makes it a
constraint: PydanticAI derives the tool name and description from `__name__` and
`__doc__` on the function it is handed, so a factory returning
`async def _inner(...)` would put a tool called `_inner` in front of the model —
and [`outcomes.md`](../design/outcomes.md) prints `tool='web_search'` and
`reference='web_search(query="…")'` throughout.

The name is therefore load-bearing, and `def` is how it is set. The alternative —
defining `_search` and assigning `_search.__name__ = "web_search"` — sets the same
attribute less legibly and leaves `__qualname__` lying. The shadowing is harmless
because the factory body never refers to the outer name after the inner `def`.
A comment at the `def` says all of this in two lines, because the next reader's
instinct will be to rename it.

### `tools/__init__.py`

A module docstring, one `from ._web_search import web_search`, and
`__all__ = ["web_search"]` —
[`packaging.md` § The export surface](../design/packaging.md#the-export-surface)'s
second list, and the whole of it. No `as` aliasing, the same rule the top-level
`__init__.py` follows: pyright treats `__all__` membership as the re-export
declaration.

### `py.typed`

Unchanged. `src/enbanc/py.typed` already covers the subpackage; a second marker
file in `tools/` would be redundant.

### Deleted

`tests/integration/test_placeholder.py`. Its own docstring names its successor —
*"Replace it when the first real integration test lands (`web_search` against real
Tavily, which wants `tavily_api_key` instead)"* — and this is that PR. Its second
job, keeping `make integration-tests` from exiting non-zero on an empty
collection, is done by the test that replaces it.

### Design documents

Three sentences in
[`evidence.md` § The default tool](../design/evidence.md#the-default-tool),
paid in this commit per `CLAUDE.md` rule 2, because each describes behaviour a
reader of that section would otherwise get wrong:

1. That `max_results` is a factory keyword defaulting to 5, beside the sentence
   that already says the tool sends it.
2. That a result missing `url` or `content` is skipped rather than raised on,
   beside the sentence that says all three are always present.
3. That **`raw_content` is returned as a null rather than omitted**. The bullet
   had grouped it with `favicon` as "absent unless asked for"; `favicon` is
   absent, `raw_content` is a key whose value is `None`. The sentence now
   separates the two, and the reasoning around it — that the ledger records
   verbatim what a tool returned, so asking for raw content would put whole
   pages in every transcript — is untouched.

**The `id` bullet is kept, and gains one clause.** It was the open question this
document opened with, and the [live check above](#what-tavily-actually-returns)
confirmed it as written, example value and all. What is added is the way to
re-check it: re-running a query renumbers the same URL. An assertion a reader
can test beats one they must trust, and this document's own history is the
argument for writing it down — the bullet was doubted precisely because nothing
said how to confirm it.

Nothing else. Every design document keeps `status: draft` and its *none of this
exists yet* banner — making the documentation stop lying is
[`zero-one-zero.md`](./zero-one-zero.md)'s scope, and this PR ships two modules
of a package whose central type is still absent.

## Tests

The first PR with tests in two tiers, and the split is
[`testing.md`](../design/testing.md#the-four-tiers)'s exactly: the fake drives
every path, the live one proves the wire.

| Module | Tier | Pins |
|---|---|---|
| `test_web_search.py` | `unit` | the mapping, the drops, the request body, and every path a live Tavily will not produce on demand |
| `test_export_surface.py` | `unit` | one addition — `enbanc.tools.__all__ == ["web_search"]` |
| `test_web_search.py` | `integration` | one happy path against real Tavily |

### `tests/unit/test_web_search.py`

A fake client class with a `search` coroutine that records what it was called
with and returns a canned `dict`, monkeypatched over
`enbanc.tools._web_search.AsyncTavilyClient`. The real factory is driven
throughout — the fake replaces Tavily, never `web_search`.

**The canned response is the shape recorded [above](#what-tavily-actually-returns)**,
down to `raw_content: None` on every result and the three null-or-empty top-level
extras. `testing.md` puts the edge cases in this tier precisely because a live
Tavily cannot be asked for them; that argument only holds while the happy-path
fixture is the response the live service actually sends.

| Asserts | Because |
|---|---|
| `url` → `reference`, `title` → `label`, `content` → `content`, in order, one `Source` per result | the mapping is the tool |
| every returned `Source` dumps to exactly `reference`, `content`, `label` — so `score`, `id`, `raw_content` and the top-level `answer` cannot leak in | [`evidence.md`](../design/evidence.md#the-default-tool) drops five things and says why for each; asserting the surviving set covers all of them at once, and keeps covering them if Tavily adds a sixth |
| `search` was called with exactly `query` and `max_results` | "nothing that changes the response shape" is a claim about the *request*, and this is where it is checked |
| `max_results` defaults to 5 and a factory keyword reaches Tavily | the decision [above](#max_results-is-a-factory-keyword) |
| an empty `results` list returns `[]` and does not raise | a tool that comes up empty returns empty |
| a row missing `url`, and one missing `content`, are skipped while their siblings survive | the decision [above](#the-mapping-and-what-happens-to-a-row-that-cannot-be-mapped); a live service cannot be asked for this |
| a row missing `title` yields `label=None` | `Source.label` is optional, and this is the one missing field that is not an error |
| each Tavily exception propagates unchanged, with its own type | [nothing is caught](#nothing-is-caught), and the type is what a caller's `except` sees |
| the returned function's `__name__` is `"web_search"` and its `__doc__` is non-empty | [`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md)'s constraint, and the only thing standing between the model and a tool called `_inner` |

The non-200 and timeout cases in
[`testing.md` § Faking Tavily](../design/testing.md#faking-tavily) are the
exception row: the SDK turns both into its own exception types before the tool
sees them, so the fake raises `InvalidAPIKeyError`, `UsageLimitExceededError`,
`BadRequestError` and `tavily.errors.TimeoutError` directly rather than
simulating an HTTP status. Faking the status would be testing Tavily's error
mapping, which is Tavily's.

**Nothing here needs a model.** The unit tier's socket guard has nothing to
block, and `TestModel` does not appear: this tool is a function that calls an HTTP
client, and the agent that would call it does not exist yet.

### `tests/unit/test_export_surface.py`

One function added to the module `packaging.md` names. The file currently imports
`enbanc` alone; it gains `import enbanc.tools` and asserts the second list is
`["web_search"]`.

**Importing `enbanc.tools` here does not weaken `test_import_is_inert.py`**,
which asks its question in a subprocess that imports `enbanc` and nothing else.
The two modules are unrelated by construction, which is the reason that test is a
subprocess in the first place.

### `tests/integration/test_web_search.py`

One test, asking for the `tavily_api_key` fixture already in `tests/conftest.py`
and skipping itself when the key is absent. It runs a real query, and asserts the
shape rather than the content: a non-empty `list[Source]`, every `reference` an
`https://` URL, every `content` non-empty, and no more results than
`max_results` asked for.

**The provider is named here and nowhere else in the harness.**
[`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md) fixed Tavily
as the library's choice, which is why this tier may name it while the model tier
may not — `testing.md` draws that line explicitly.

**A module-local fixture closes every client the factory built**, for the reason
[above](#toolsweb_searchpy): the tool has no `close()` by design, and under pytest
the client outlives the loop it was made on. The fixture monkeypatches the same
module-level name the unit tier fakes, but to *track* rather than to fake — the
subclass appends itself to a list and changes nothing else, so the search is a
real search. Whatever the e2e tier ends up running `web_search` inside will need
the same thing, and that is when it earns promotion to a conftest.

It does **not** print the keys of one raw result. This document planned that as
the way its open question about the per-result `id` got answered; the question was
answered before any code was written, so the print would be scaffolding around an
answer — and reaching a raw result means building a second client beside the tool,
which is the one thing the test has no reason to do.

### What is deliberately elsewhere

**That a `Source` becomes a citable exhibit.** The ledger, the stamped reference,
and `as_sources`'s shape-sniff are
[`ledgering-toolset.md`](./ledgering-toolset.md)'s. This PR ends at the return
statement.

**That a `Tool(timeout=)` around `web_search` surfaces as `ModelRetry`.** Already
asserted, and not here: it is one of the claims
`tests/contract/test_intercepting_a_tool_call_is_one_method.py` makes about
PydanticAI ([`contract-probes.md`](./contract-probes.md)). Re-asserting it against
this tool would be testing the dependency a second time, from the wrong tier.

**`test_import_is_inert.py` is untouched, and changes meaning.** Its
`"enbanc.tools" not in imported_modules` and `"tavily" not in imported_modules`
assertions were vacuous while the module did not exist; from this PR they are the
thing keeping `tavily` — and `tiktoken`, which `import tavily` pulls in — off the
`import enbanc` path. The test needed no edit, which is the point of having
written it first.

## Open questions

*None open.* One was recorded while this document was being written and settled
before any code was, and the answer is in the prose above.

**Does a Tavily result carry a per-result `id`?** It does.
[`evidence.md`](../design/evidence.md#the-default-tool) says "`score` and `id`
are always returned" and quotes `"e5450d-00"` as the reason `id` is the wrong
thing to cite, while Tavily's current
[SDK reference](https://docs.tavily.com/sdk/python/reference) lists no such field
and puts a `request_id` at the top level instead. The design document is right
and the reference page is incomplete — settled by
[three live calls](#what-tavily-actually-returns), which also showed the id is
regenerated per request, so the argument is confirmed and not merely the
subject preserved.

**It was settled by asking the service, not by reading about it**, and that is
the transferable part. The question was whether `docs/design/` had gone stale
against a third party — a question only the third party can answer, and the
reason [`0031`](../decisions/0031-tests-are-tiered.md) puts a live tier in the
strategy at all. Reading the vendor's documentation would have produced a
confident, wrong edit to a document whose guarantee is current truth.
