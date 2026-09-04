---
status: draft
updated: 2026-09-04
---

# Evidence

How an advocate gathers evidence, and how what it gathers becomes an exhibit a
reviewer can check. The proceeding around this is in
[`tribunal.md`](./tribunal.md); the types are specified in
[`api.md`](./api.md); terms are defined in
[`../glossary.md`](../glossary.md).

> `status: draft` — none of this exists yet. This is the target, not a
> reference.

## Why this document exists

[`tribunal.md`](./tribunal.md#the-premise) sells `enbanc` on **defensibility**:
the answer alone is not the deliverable; you need the reasoning and the evidence
that produced it, in a form a reviewer can audit. A ruling is supposed to be
readable as *"deny, because the applicant's income is unverified, per this
document"* — and the last clause is the one that lets a reviewer disagree.

An exhibit that says only which tool produced it does not support that clause.
`Exhibit(tool="web_search", content="revenue fell 14%")` names no document; a
reviewer who wants to check it has nowhere to go. So an exhibit carries a
**reference**: a string that locates the underlying evidence.

Everything below follows from that one requirement, plus the constraint that the
reference must be trustworthy — see
[How a source becomes an exhibit](#how-a-source-becomes-an-exhibit).

## What a tool is

**A plain async function.** There is nothing to register, decorate, subclass, or
declare. You write a function and pass it to an advocate.

```python
Advocate(tools=[find_filings, dti_for])
```

`enbanc` defines no tool base class and no tool decorator. This is the promise
[`../glossary.md`](../glossary.md#where-the-metaphor-stops) already makes —
*you pass PydanticAI tools* — and it is kept literally: `tools` and `toolsets`
are handed to `pydantic_ai.Agent` as they are.

**The input schema is the function's signature**, derived by PydanticAI from the
annotations and the docstring. `enbanc` holds no assumption about a tool's
parameters, does not require any particular one, and adds none — the same
opaqueness [`0007`](../decisions/0007-a-statute-is-opaque-text.md) gives
`Statute.text`. If PydanticAI can turn your function into a tool, it is a tool.

**`Advocate` takes `toolsets` as well as `tools`**, mirroring
`pydantic_ai.Agent`. MCP servers, `FunctionToolset`, and anything else in
PydanticAI's toolset vocabulary therefore work with no `enbanc` concept invented
for them.

```python
Advocate(
    tools=[web_search(api_key=...), dti_for],
    toolsets=[MCPServerStdio(...)],
)
```

**Tools are per advocate, never shared or inherited.** The advocate for approval
may need different evidence sources than the advocate for denial, and giving
both the same toolbox would flatten a real asymmetry. There is no `tools=` on
`Tribunal`. The judge has none at all, and that is
[load-bearing](./tribunal.md#constraints-that-define-the-design).

## A reference is what makes an exhibit auditable

```python
class Source(BaseModel):
    reference: str            # where a reviewer looks
    content: str              # the retrieved text
    label: str | None = None  # a human-readable name, when there is one
```

A `Source` is one piece of evidence a tool found, together with the locator for
it. It is the pre-filing thing: sources are what tools return, exhibits are what
advocates file, and most sources never become exhibits.

**`reference` is opaque to `enbanc`.** It is a string, and the library does not
parse it, validate its shape, resolve it, or fetch it. Each tool defines what a
locator means for the evidence it returns:

| A tool that searches | Its reference is |
|---|---|
| the web | the result URL |
| a document store | the object key or path |
| a filesystem | the file path, and a line range if it has one |
| a database | the query that produced the row |

This is deliberately the same guarantee
[`0007`](../decisions/0007-a-statute-is-opaque-text.md) gives `Statute.text`. A
schema for references would have to enumerate the kinds of place evidence can
live, and there is no such list. The only contract is the one the annotation
states, and the only test is whether a human holding the string can find the
evidence again.

**`label` is for reading, `reference` is for checking.** A rendered transcript
citing *"Schedule C, 2024"* is legible in a way one citing an S3 key is not, but
the label is a convenience and the reference is the claim. A tool that has no
natural title leaves it `None`.

**A tool does not have to return `Source`.** It may return a string, a dict, a
Pydantic model, an MCP server's payload — anything. What that costs is described
next, and it is small: such a tool is still first-class and still citable, it
just gets a coarser reference.

## How a source becomes an exhibit

**The reference is stamped by the tribunal, not written by the advocate.** This
is the load-bearing decision in this document, and it is
[`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md) applied
one level down: *a model does not author a value the record's integrity depends
on.* A fabricated URL in an audit artifact is indistinguishable from a real one,
and an artifact whose citations cannot be trusted is not an audit artifact. See
[`0016`](../decisions/0016-exhibits-are-stamped-citations.md).

So the advocate never writes a reference. It cites, and the tribunal resolves.

**1. Tool results are ledgered.** A toolset `enbanc` owns wraps everything the
advocate was given and intercepts every call. Each source that comes back is
assigned an id — `s1`, `s2`, … — and recorded in a **ledger**: the id, the tool
that produced it, its reference, and its label.

Ids are numbered **monotonically across the advocate's whole proceeding**, not
restarted per round, so an advocate answering an interrogatory in round 3 can
still cite something it found in round 1. This is the opposite of the
interrogatory scheme, where `r{round}-q{n}` restarts each round because the
round prefix carries uniqueness; here there is no prefix and nothing to restart
against.

**A return value that is not `Source`-shaped is ledgered as one anonymous
source, and its reference is the call itself:**

```python
reference='dti_for(applicant="A. Okonkwo")'
```

That is reproducible — a reviewer re-runs it — and for a database or an internal
API it genuinely is the locator, because there is no URL to point at. This
branch is what keeps every existing PydanticAI tool and every MCP server usable
with no adaptation at all. Returning `Source` is an upgrade, not an entry fee.

**2. The advocate sees the ids.** What reaches the model is the content it would
have seen anyway, with an id attached to each source:

```text
find_filings(applicant="A. Okonkwo") ->
  [s1] Schedule C, 2024 — "net profit: 182,000 …"
  [s2] W-2, 2024        — "wages: 131,400 …"
```

**3. The advocate cites an id.** Its output type carries a **private**
`_Exhibit` — a source id and the excerpt it relies on — exactly as the judge
emits a private `_Interrogatory` with no id on it:

```python
class _Exhibit(BaseModel):   # what the advocate emits
    source: str              # a ledger id, e.g. "s2"
    content: str             # the excerpt it relies on
```

**4. The tribunal stamps and files.** It resolves the id against the ledger and
builds the public `Exhibit`, putting the real reference beside the advocate's
excerpt:

```python
class Exhibit(BaseModel):
    tool: str                 # stamped
    reference: str            # stamped
    content: str              # the advocate's excerpt
    label: str | None = None  # stamped, when the source carried one
```

Three of the four fields are the tribunal's. The one the advocate writes is the
one that says what mattered, and the stamped reference is how a reviewer checks
whether it says it fairly.

### Why `content` is the advocate's excerpt

Stamping the retrieved text verbatim would make an exhibit wholly
tribunal-authored, and it was rejected: a filed web page or result set is large,
and a transcript whose bulk is raw retrieval is one nobody reads end to end —
which is precisely the argument
[`0006`](../decisions/0006-the-transcript-schema.md) used to keep tool traffic
out of the record in the first place.

The excerpt is model-authored and can therefore misquote. That is what the
reference is for. A misquote is a defect a reviewer can *find*, because the
citation resolves; a fabricated citation is one they cannot.

### Source ids never leave the advocate's context

The ledger is intra-agent state. It is created when a proceeding starts, lives
as long as that advocate's run, and is discarded with it. Nothing in the record
holds a source id: the judge sees resolved exhibits, and the transcript stores
resolved exhibits.

This leaves [`0006`](../decisions/0006-the-transcript-schema.md) untouched. The
record is still **complete as to the ruling, not as to the search** — an
advocate that pulled damaging evidence and quietly declined to file it still
leaves no trace, and the ledger does not change that, because the ledger is not
in the record. What it changes is that the evidence which *was* filed can now be
located.

### An unresolvable id is a validation failure

An advocate that cites an id the ledger does not hold has invented a citation,
which is the failure this whole mechanism exists to prevent. The `_Exhibit` is
rejected by an output validator; PydanticAI retries against the library's own
`Agent(retries=...)` budget, and a budget that runs out surfaces as
`ProceedingFailed` — the path
[`api.md`](./api.md#when-something-goes-wrong) already documents for output that
will not validate. Nothing is silently dropped: an exhibit that cannot be
resolved never reaches the transcript, and neither does a ruling that rests on
one.

## Adding your own tool

Three steps, each one optional after the first.

### Step 1 — any async function is already a tool

No `enbanc` import, no `Source`, no change to code you may already have:

```python
async def dti_for(applicant: str) -> str:
    """Look up the applicant's debt-to-income ratio from the warehouse."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT dti FROM applicants WHERE name = $1", applicant
        )
    return f"dti: {row['dti']}"

Advocate(tools=[dti_for])
```

The docstring becomes the tool description and the parameters become the input
schema — PydanticAI reading the signature, not `enbanc` imposing one. The return
value is not `Source`-shaped, so it is ledgered as one anonymous source and what
gets stamped is the call:

```python
Exhibit(
    tool="dti_for",
    reference='dti_for(applicant="A. Okonkwo")',
    content="dti: 0.51",
)
```

### Step 2 — return `Source` when there is a real place to point

The upgrade is the return type and nothing else. It is still a plain async
function, and the call site does not change:

```python
from enbanc import Source

async def find_filings(applicant: str) -> list[Source]:
    """Search the document store for filings belonging to the applicant."""
    hits = await docstore.search(applicant)
    return [
        Source(
            reference=f"s3://underwriting-docs/{hit.key}",
            label=hit.title,
            content=hit.text,
        )
        for hit in hits
    ]

Advocate(tools=[find_filings, dti_for])
```

Now each hit is separately citable, and an exhibit points at the document rather
than at the search that found it:

```python
Exhibit(
    tool="find_filings",
    reference="s3://underwriting-docs/okonkwo/schedule-c-2024.pdf",
    label="Schedule C, 2024",
    content="net profit: 182,000",
)
```

### Step 3 — a factory, when the tool needs configuration

Credentials, clients, and connection pools are closed over. There is no
`deps=` on `Advocate` and no configuration parameter for tools, because a
closure already does it and inventing one would put a second place to configure
the same thing — the division
[`0009`](../decisions/0009-model-settings-live-on-the-model.md) draws for model
settings, applied here.

```python
def docstore_search(client: DocStoreClient, *, limit: int = 5):
    async def find_filings(applicant: str) -> list[Source]:
        """Search the document store for filings belonging to the applicant."""
        hits = await client.search(applicant, limit=limit)
        return [
            Source(reference=..., label=hit.title, content=hit.text)
            for hit in hits
        ]

    return find_filings

Advocate(tools=[docstore_search(client), web_search(api_key=...)])
```

That last line is the point. `web_search` is a factory of exactly this shape, so
**the tool `enbanc` ships and the tool you write are the same kind of object**.
There is no privileged path for built-in tools, and no capability a default tool
has that yours cannot.

## The default tool

```python
from enbanc.tools import web_search

Advocate(tools=[web_search(api_key=...)])
```

`web_search` searches the web through [Tavily](https://tavily.com) and returns
`list[Source]`, one per result:

| Tavily result field | `Source` |
|---|---|
| `url` | `reference` |
| `title` | `label` |
| `content` | `content` |

All three are present on every result and are non-empty strings. The rest of the
response is dropped:

- **`score` and `id`** are always returned and neither is a locator. Tavily's
  `id` is tempting as a ready-made citation handle, and it is the wrong one: it
  is scoped to the request that produced it (`"e5450d-00"`), not to the
  document, so it identifies nothing a reviewer could look up later.
- **`raw_content` and `favicon`** are absent unless asked for, and `web_search`
  does not ask. Raw content is the full page; the ledger holds what the tool
  returned, and filing a page in place of a snippet is the bulk problem
  [`0006`](../decisions/0006-the-transcript-schema.md) already refused.
- **The top-level `answer`** — Tavily's own LLM summary of the results —
  is not requested either, and could not become an exhibit if it were. It is
  synthesized across sources, so there is no single reference behind it. An
  advocate wanting that synthesis can read the results and write it as its
  claim, where a claim belongs.

`web_search` therefore sends `query` and `max_results` and nothing that changes
the response shape.

It is **written against Tavily's own SDK** as a plain async function returning
`Source` — Step 3 above, with nothing added. PydanticAI ships a
`tavily_search_tool` of its own and `enbanc` deliberately does not wrap it: that
one returns `TypedDict`s, so using it would require an adapter layer between the
tool and the ledger that no user's tool ever has. The default tool would then
stop being an example of the mechanism and become an exception to it.

Tavily is an optional dependency, so the core install stays thin:

```bash
pip install "enbanc[web]"
```

**Database query and local file search are not in `0.1.0`.** They are the next
two, and the `reference` contract is what makes them additive rather than
structural: a file-search tool returning `Source(reference="./policy.md#L40-L52")`
needs nothing new from the library.

## What tools may do

**Advocate tools are read-only.** `enbanc` enforces this where it can: it ships
no tool that writes, the judge has no tools at all, and the library itself has
no mutation path. But a tool you pass is your code, and `enbanc` cannot inspect
a function for side effects. **Read-only is a contract you keep, not one
`enbanc` checks.** An adjudication that mutates the world it is reasoning about
produces a record that no longer describes the thing that was decided. See
[`0017`](../decisions/0017-read-only-is-a-contract.md).

**Tools must tolerate concurrency.** Advocates fan out across a round, so
several may call the same tool object at the same time. Share a client; do not
share mutable per-call state.

**Tools must tolerate cancellation.** The first failure in a round cancels the
advocates still in flight
([`0012`](../decisions/0012-a-failure-cancels-the-round.md)), and a tool
awaiting I/O when that happens is cancelled where it stands. Clean up in
`finally`, and do not assume a call that started will finish.

**A tool that raises ends the proceeding.** It is not caught, retried, or
recorded as a concession; it surfaces as `ProceedingFailed` with the original
exception as `__cause__`. An advocate that could not gather evidence has not
been heard, and [`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md)
keeps that distinct from one that chose not to argue. A tool that expects to
come up empty should return an empty result, not raise.

**There is no provider-executed search.** `enbanc` exposes no `builtin_tools=`,
so PydanticAI's native `WebSearchTool` and its siblings are not reachable
through an `Advocate`. They execute inside the provider and return no function
tool result, so nothing can be ledgered and no reference can be stamped — an
exhibit from one would be a citation the library cannot stand behind.

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. A question that is only *sharpened* — its options narrowed, nothing
decided — stays, rewritten in place. See rule 7 in
[`../../CLAUDE.md`](../../CLAUDE.md).

- **Does the ledger ever enter the record?**
  [`0006`](../decisions/0006-the-transcript-schema.md) names
  suppression-invisibility as the consequence most likely to force a successor
  ADR: an advocate that finds damaging evidence and declines to file it leaves
  no trace. A ledger now exists in memory, which makes recording what was
  searched a smaller step than it was when `0006` was written — the data is
  already assembled. What has not changed is `0006`'s reason for refusing: a
  record whose bulk is unfiled retrieval is one nobody reads. Any answer has to
  say what happens to transcript size.

- **Where does tool execution configuration live?** PydanticAI puts
  `tool_timeout` and `max_concurrency` on `Agent`, not on `Model`, so
  [`0009`](../decisions/0009-model-settings-live-on-the-model.md)'s "settings
  ride on the model" does not reach them and they currently have nowhere to go.
  A tool that hangs stalls a round with no bound, which makes this the more
  urgent of the two. It is adjacent to the cost-control question in
  [`tribunal.md`](./tribunal.md#open-questions) and may want the same answer.
