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

There is a second question a reviewer asks, and it is not answered by any
exhibit: *what did the advocate see and choose not to show me?* The record
answers that too, because what an advocate's tools returned is recorded whole —
see [The ledger is part of the record](#the-ledger-is-part-of-the-record).

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
    source: str               # the ledger id it cited
    tool: str                 # stamped
    reference: str            # stamped
    content: str              # the advocate's excerpt
    label: str | None = None  # stamped, when the source carried one
```

Four of the five fields are the tribunal's. The one the advocate writes is the
one that says what mattered, and the stamped reference is how a reviewer checks
whether it says it fairly. `source` is kept rather than consumed, because the
ledger is [part of the record](#the-ledger-is-part-of-the-record) and the id is
what joins an exhibit to the retrieval behind it.

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

### The ledger is part of the record

The ledger is not discarded when the proceeding ends. It is recorded on the
transcript, verbatim, as `Transcript.ledger`:

```python
class Retrieval(BaseModel, Generic[VerdictT]):
    id: str                   # the ledger id; what an Exhibit.source cites
    round: int
    advocate: VerdictT        # whose tool call produced it
    tool: str
    reference: str
    content: str              # verbatim, as the tool returned it
    label: str | None = None
```

**This is what makes the record complete as to the search, not only as to the
ruling.** An advocate that pulls damaging evidence and quietly declines to file
it now leaves a trace: the retrieval is in the ledger and no exhibit cites it.
That reverses the cost
[`0006`](../decisions/0006-the-transcript-schema.md) accepted and named as the
consequence most likely to force a successor. See
[`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md).

**Suppression is found by joining, not by a flag.** The retrievals nothing rests
on are the ledger ids no `Exhibit.source` names:

```python
cited = {(entry.filing.advocate, e.source)
         for entry in transcript
         for e in exhibits_of(entry.filing)}
buried = [r for r in transcript.ledger if (r.advocate, r.id) not in cited]
```

**The join key is `(advocate, id)`, not `id`.** Ids are numbered within an
advocate — [step 1](#how-a-source-becomes-an-exhibit) — so `APPROVE`'s `s1` and
`DENY`'s `s1` are different retrievals. Keeping the counter per advocate is what
makes ids deterministic: an advocate's tool calls are sequential, while one
counter shared across advocates running concurrently would number the same
proceeding differently on every run.

There is no `cited: bool` on `Retrieval` on purpose. Whether a round-1 source is
ever cited is unknown until the proceeding ends, so the field would be written
on append and rewritten when a later round cites it — and a transcript whose
rows change after they are appended is not append-only. The join is exact,
because both sides carry the same tribunal-stamped id.

**Why the content and not just the reference.** A reference alone would be
smaller, and it would be enough in principle — following it is what a reviewer
does for a filed exhibit. It was rejected because it makes the common audit
require what the artifact was supposed to remove: credentials for the systems
the tools queried, a source that still exists and still says what it said, and a
second tool to go look. Storing the content means a reviewer holding only the
transcript can see what the advocate saw and decide whether burying it was fair.
Ease of audit is the product; size is a cost. Following the reference stays
available for anyone who wants the primary source.

**What this costs, plainly: the transcript is larger, and by an amount `enbanc`
does not control.** A tool that returns whole pages puts whole pages in the
record. `enbanc` stores what a tool returned and truncates nothing — a truncated
retrieval could cut the exact sentence an audit turns on. The lever is the tool:
return the snippet you want the advocate to reason over, not the document it
came from. That is the same discipline that keeps an advocate's context small.

**And it carries what the tools returned into an artifact that travels.**
Content from systems with their own access controls is now reproduced in a
document people forward. Under a reference-only record the source system would
still govern who can read it; here the transcript does. Treat a transcript as
being as sensitive as the most sensitive thing an advocate's tools can reach.

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
    source="s1",
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
    source="s1",
    tool="find_filings",
    reference="s3://underwriting-docs/okonkwo/schedule-c-2024.pdf",
    label="Schedule C, 2024",
    content="net profit: 182,000",
)
```

And `s2`, the W-2 it did not cite, is in `transcript.ledger` with its text
intact, where a reviewer will find it.

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

**Name the inner function what you want the model to call**, and give it a real
docstring. PydanticAI reads `__name__` and `__doc__` off the function it is
handed, so a factory that returns `async def _inner(...)` puts a tool called
`_inner` in front of the model. The closure above is named `find_filings` for
that reason, not for style.

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
  does not ask. Raw content is the full page, and the ledger records verbatim
  what a tool returned — so requesting it would put whole pages in every
  transcript. The snippet is what the advocate reasons over and what a reviewer
  needs; the page is a click away through the reference.
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

`tavily-python` is a core dependency, so `web_search` imports on a plain
install. It is the only tool `0.1.0` ships and it appears in the first example a
reader copies; a default that a default install cannot import is not a default.
See [`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md).

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

**Bound any tool that talks to something you do not control.** A tool that hangs
stalls the round, and `max_rounds` does not help — it counts deliberations, and
the deliberation never happens. `enbanc` supplies no default and adds no
parameter for this: the setting rides on the tool, which is
[`0009`](../decisions/0009-model-settings-live-on-the-model.md) applied to a
second kind of object. Wrap with PydanticAI's `Tool`:

```python
from pydantic_ai import Tool

Advocate(
    tools=[
        Tool(web_search(api_key=...), timeout=15.0),   # third-party HTTP
        Tool(find_filings, timeout=30.0),              # S3 plus OCR, legitimately slow
        Tool(dti_for, timeout=5.0),                    # a local warehouse
        parse_statute_dates,                           # pure CPU; nothing to bound
    ],
)
```

Wrapping is per tool and opt-in — the last entry is still a tool — and the
number belongs to the system behind it, which is why there is no tribunal-wide
or per-advocate default to inherit. A warehouse query and an OCR pipeline do not
want the same bound.

**A timeout is not fatal.** PydanticAI cancels the call and tells the model
`Timed out after 15.0 seconds.`, counting against the library's
`Agent(retries=...)` budget. The advocate can narrow the query, reach for
another tool, or file what it has. Only an exhausted budget raises, and that
surfaces as `ProceedingFailed`. The ladder is **timeout → the advocate adapts →
retries spent → the proceeding fails**, and only the last rung ends anything.
See [`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md).

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

- **Should the record show that a tool failed?** A retry prompt is
  library-authored text an agent sees and no transcript holds, which
  [`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md) accepts
  as an exception to the invariant. The cost it accepts is that an advocate
  whose searches timed out three times and then filed a thin argument reads, in
  the record, as an advocate that argued thinly. The ledger records what came
  back, not what failed to come back, so a weak case and a degraded one are
  indistinguishable. An answer would have to close that without recording every
  prompt — an `outcome` on `Retrieval`, or a failures list beside the ledger,
  are the two shapes that seem plausible. Any answer inherits
  [`0006`](../decisions/0006-the-transcript-schema.md)'s constraint: intra-agent
  churn does not belong in an artifact someone has to read.
