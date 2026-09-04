---
status: accepted
updated: 2026-09-04
---

# 0019. The ledger is part of the record

## Context

[`0006`](./0006-the-transcript-schema.md) decided that only filed exhibits enter
the transcript and raw tool traffic does not. It named the cost in its own
words:

> **Cost, stated plainly: suppression is invisible.** An advocate that gathered
> damaging evidence and quietly declined to file it leaves no trace. […] This is
> the consequence most likely to force a successor ADR, and a successor would
> have to say what happens to transcript size.

This is that successor. Two things changed after
[`0016`](./0016-exhibits-are-stamped-citations.md).

**The data is already assembled.** `0016` introduced a per-advocate ledger —
every source a tool returned, with the reference stamped onto it — built to
resolve citations. When `0006` was written, recording tool traffic meant
building capture machinery. It now means serializing a structure that exists.

**`0006`'s mitigation does not hold in the configuration `enbanc` recommends.**
`0006` accepted invisible suppression because "the advocate for the opposing
verdict has its own tools and every incentive to find the same thing." That
assumes the opposing advocate *can* find it. `../design/evidence.md` makes tools
strictly per-advocate and calls the asymmetry "a real asymmetry" worth
preserving. Where only one advocate holds the document store, no peer can
surface what it buried, and the mitigation is empty.

## Decision

**`Transcript.ledger` records every source every tool returned, verbatim.**

```python
class Retrieval(BaseModel, Generic[VerdictT]):
    id: str                   # the ledger id; what an Exhibit.source cites
    round: int
    advocate: VerdictT
    tool: str
    reference: str
    content: str              # verbatim, as the tool returned it
    label: str | None = None
```

**The record is now complete as to the search, not only as to the ruling.** That
sentence in `0006` and in `../design/tribunal.md` is reversed.

**It is a sibling field of `entries`, not a sixth filing.** Nobody filed it;
`0006`'s rejection of a sixth `kind` stands unchanged, and an `Entry` remains an
envelope around one of exactly five filings.

**`Exhibit` keeps the ledger id it cited**, as `Exhibit.source`. Suppression is
found by joining — the retrievals no exhibit names — rather than by a flag. The
key is `(advocate, id)`, because ids are numbered within an advocate rather than
across the proceeding. Per-advocate numbering keeps them deterministic: an
advocate's tool calls are sequential, while a single counter shared across
concurrently running advocates would number the same proceeding differently on
every run. This was found by writing `../design/outcomes.md`'s values, where
two advocates' ledgers sat in one list and both began at `s1`.

**There is no `cited: bool` on `Retrieval`.** Whether a round-1 source is ever
cited is unknown until the proceeding ends, so the field would be written on
append and rewritten when a later round cites it. A transcript whose rows change
after they are appended is not append-only, and the join is exact anyway because
both sides carry the same tribunal-stamped id.

**`enbanc` truncates nothing.** A retrieval is stored as the tool returned it.

## Consequences

**Rejected: recording references without content.** Smaller — measured at 12 KB
against 24 KB for a 60-source proceeding — and defensible on the document's own
logic, since following a reference is exactly what a reviewer does for a filed
exhibit. It was rejected on what the common audit costs. A reference-only ledger
says "the approve advocate retrieved `w2-2024.pdf` and cited nothing from it"
and then requires the reviewer to hold credentials for that store, find the
object still present, and trust that it still says what it said. Storing the
content means a reviewer holding only the transcript can see what the advocate
saw. Ease of audit is the product; size is a cost, and this is the trade the
library exists to make. The reference stays on every retrieval, so going to the
primary source remains available to anyone who wants it.

**Rejected: a `Tribunal(record_searches=...)` flag.** It would let each caller
price the trade. An audit guarantee that can be switched off is not a guarantee,
it doubles the transcript shapes every reader must reason about, and it invites
the one configuration nobody should be able to choose — the contested
proceeding run with recording disabled.

**Cost: transcript size is now unbounded and not `enbanc`'s to bound.** Measured
against real Tavily snippets a 60-source proceeding adds ~24 KB, which is
nothing. The ratio is driven entirely by what tools return: at ~600-character
paragraphs the ledger is ~47 KB, and a tool returning scraped pages produces
~480 KB. `../design/evidence.md` says a tool may return "anything at all", so
this is delegated to caller code the library deliberately does not constrain.
Truncation was rejected as the fix — a truncated retrieval can cut the exact
sentence an audit turns on, which is a worse failure than a large file. The
stated lever is tool design: return the snippet the advocate should reason over,
not the document it came from, which is the same discipline that keeps the
advocate's context small.

**Cost: the transcript now carries retrieved content into an artifact that
travels.** Material from systems with their own access controls is reproduced in
a document people forward and archive. Under `0006` the transcript held only
what an advocate chose to quote; it now holds everything its tools returned. A
transcript must be treated as being as sensitive as the most sensitive thing any
advocate's tools can reach. This is the consequence most likely to force a
successor to *this* ADR, and a successor would have to say how a record can be
redacted without ceasing to be one.

**Benefit not claimed: this does not make advocates honest.** It makes
dishonesty findable by someone who looks. A reviewer who reads only the filings
sees exactly what they saw before. What changes is that the question "what was
buried?" now has an answer in the artifact instead of no answer at all.

**Consequence: `../design/tribunal.md`'s invariant is restated.** "The record is
complete as to the ruling, not as to the search" becomes complete as to both.
The narrower invariant `0006` introduced — *nothing reaches an agent from
outside itself that is not also in the transcript* — can go back to the absolute
form [`0002`](./0002-the-judge-is-a-role.md) originally stated, because an
advocate's own tool results are now in the transcript too.

**Consequence: `hear_stream` yields a growing ledger.** Retrievals are appended
as tools return, so a live `proceeding.transcript.ledger` is populated ahead of
the filing that will cite from it. This does not violate
[`0010`](./0010-streaming-yields-the-record.md), which governs what the async
iterator *yields* — still entries, still filings — not what the transcript
behind it contains.
