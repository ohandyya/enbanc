---
status: accepted
updated: 2026-09-04
---

# 0016. An exhibit's reference is stamped from a ledger, not written by the advocate

## Context

`Advocate(tools=[psql, tavily])` appeared in `README.md`, `../design/api.md`,
and `../design/outcomes.md` from the beginning, and nothing anywhere said what a
tool was. There was no statement of what an advocate's tool may return, how a
caller adds one, or what ships by default.

The gap that mattered was on the far end. `Exhibit` — the only place a tool's
output reaches the record — was `source: str` plus `content: str`, where
`source` was a bare tool name. `../design/tribunal.md` sells the library on
**defensibility**: "the answer alone is not the deliverable; you need the
reasoning and the evidence that produced it, in a form a reviewer can audit." A
reviewer holding `Exhibit(source='tavily', content='revenue fell 14%')` can
audit nothing. There is no way back to the document.

So an exhibit needs a **reference**: a string that locates the underlying
evidence — a URL, an object key, a file path, the query that produced a row.
Adding the field is trivial. Deciding **who writes it** is not, and that is what
this ADR settles.

## Decision

**An exhibit's `reference` is stamped by the tribunal from a ledger of what the
advocate's tools actually returned.** The advocate cites; it does not author.

```python
class Exhibit(BaseModel):
    tool: str                 # stamped
    reference: str            # stamped
    content: str              # the advocate's excerpt
    label: str | None = None  # stamped, when the source carried one
```

`source` is renamed `tool`, freeing the word for the pre-filing type below so
`Exhibit.source` and `Source` are not two different things.

**A tool is a plain async function**, passed through to PydanticAI as it is.
`enbanc` defines no tool base class and no tool decorator, which is the promise
`../glossary.md` already made in *"Where the metaphor stops"*. `Advocate` takes
`toolsets` alongside `tools`, mirroring `pydantic_ai.Agent`, so MCP servers need
no `enbanc` concept invented for them.

**`Source` is the opt-in return type that carries a reference.**

```python
class Source(BaseModel):
    reference: str
    content: str
    label: str | None = None
```

`reference` is **opaque to `enbanc`** — the same guarantee
[`0007`](./0007-a-statute-is-opaque-text.md) gives `Statute.text`. Each tool
defines what a locator means for the evidence it returns; the library does not
parse, validate, resolve, or fetch it.

**A return value that is not `Source`-shaped is ledgered as one anonymous source
whose reference is the call itself** — `dti_for(applicant="A. Okonkwo")`. It is
reproducible, and for a database or an internal API it genuinely is the locator.

**The mechanism is a per-advocate ledger.** A toolset `enbanc` owns wraps
everything the advocate was given, intercepts every call, assigns each returned
source an id (`s1`, `s2`, … monotonic across the advocate's whole proceeding, so
a round-3 response can cite a round-1 find), and records id → tool, reference,
label. The advocate's output type carries a private `_Exhibit` — an id and an
excerpt — and the tribunal resolves it when it files.

**This is [`0015`](./0015-interrogatory-ids-are-stamped-on-filing.md) applied
one level down.** That ADR established the principle for interrogatory ids: a
model does not author a value the record's integrity depends on. A fabricated
URL in an audit artifact is indistinguishable from a real one, which is the same
failure with higher stakes.

**Source ids never leave the advocate's context.** The ledger is intra-agent
state, discarded when the proceeding ends. The judge sees resolved exhibits and
the transcript stores resolved exhibits, so
[`0006`](./0006-the-transcript-schema.md) is untouched: the record remains
complete as to the ruling, not as to the search.

**An unresolvable id fails output validation**, retries against the library's
own `Agent(retries=...)` budget, and surfaces as `ProceedingFailed` when spent.
Nothing is silently dropped.

**`enbanc.tools.web_search` ships in `0.1.0`**, written against Tavily's own SDK
as a plain async function returning `list[Source]` — the same mechanism a
caller's tool uses. Tavily is an optional dependency (`enbanc[web]`).

## Consequences

**Rejected: a model-authored `reference` field.** One field, no ledger, no
wrapper toolset, and it works with any tool including provider-executed ones. It
was rejected because it fails at exactly the moment it matters. A reviewer
checking a decision follows the citation; if the citation is invented, they
discover it only by trying, and the transcript gives no signal which ones to
distrust. A library whose product claim is auditability cannot ship citations it
cannot stand behind. This is the alternative most likely to be reached for if
the ledger proves expensive to build, and the reason it is wrong should outlast
that pressure.

**Rejected: model-authored, then verified against the ledger.** The advocate
writes the reference and the tribunal checks it, retrying on mismatch. It costs
the same ledger and the same wrapper, so it buys nothing on implementation, and
the check itself has no good setting: exact string match fails on a trailing
slash or a normalized URL, while fuzzy match is an arbitrary threshold that
either admits fabrications or rejects honest citations. Resolution by id has no
threshold — an id either resolves or it does not.

**Rejected: stamping `content` verbatim too.** It would make an exhibit wholly
tribunal-authored and self-verifying without leaving the artifact. Rejected on
the argument `0006` already made against recording tool traffic: a filed web
page or result set is large, and a transcript whose bulk is raw retrieval is one
nobody reads end to end. It also loses the one thing the advocate knows and the
tribunal does not — which passage mattered.

**Cost, stated plainly: the excerpt can misquote.** `content` is model-authored,
and an advocate can characterize a source unfairly. What the design buys is that
this is now a *findable* defect: the citation resolves, so a reviewer can open
the source and disagree. A fabricated citation is not findable, which is why the
two halves are treated differently.

**Rejected: both an excerpt and a stamped verbatim field.** Self-verifying
inside the artifact and still says what mattered. It roughly doubles transcript
size, and `0006` rejected a middle position of this shape once already — a
per-filing tool-call count — on the grounds that it satisfied neither reading.

**Rejected: refusing to file anything that is not a `Source`.** It would make
`reference` unconditionally meaningful. But it makes every existing PydanticAI
tool and every MCP server second-class and unusable until rewritten, which
contradicts the "you pass PydanticAI tools" promise directly. The anonymous
branch keeps that promise, and the reference it produces is weaker but honest.

**Rejected: wrapping PydanticAI's `pydantic_ai.common_tools.tavily`.** It
already exists and would have been less code. It returns `TypedDict`s, so it
would need an adapter between the tool and the ledger that no caller's tool ever
has — and the default tool would stop being an example of the mechanism and
become an exception to it. `../design/evidence.md` teaches tool authoring by
showing that the shipped tool is built the way yours is; a wrapped built-in
would make that untrue.

**Consequence: provider-executed tools are out of reach.** `enbanc` exposes no
`builtin_tools=`, so PydanticAI's native `WebSearchTool` and its siblings cannot
be given to an `Advocate`. They execute inside the provider and return no
function tool result, so nothing can be ledgered. This is a real capability cost
— provider-side search is cheap and good — and it is accepted because an exhibit
from one would be a citation the library cannot stand behind.

**Consequence: the ledger sharpens `0006`'s open cost.** `0006` names
suppression-invisibility as the consequence most likely to force a successor
ADR. The data needed to record what was searched is now assembled in memory,
which makes that successor a smaller step than it was. Recorded as an open
question in `../design/evidence.md`, not resolved here.

**Constraint on the implementation.** The ledger must be owned by the
proceeding, not by the wrapper toolset instance. PydanticAI's
`WrapperToolset.for_run` and `for_run_step` `replace()` the dataclass, so state
held as a field survives only by the shallow copy sharing a reference to it —
which is true today and is not a documented guarantee.
