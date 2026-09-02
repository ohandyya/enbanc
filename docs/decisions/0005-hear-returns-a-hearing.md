---
status: accepted
updated: 2026-09-02
---

# 0005. `hear()` returns a hearing, not a widened ruling

## Context

`../design/api.md` sketched the result as a flat object — `ruling.verdict`,
`ruling.reasoning`, `ruling.transcript`, `ruling.usage` — while explicitly
recording that it had not committed to a shape: "Whether the caller gets a
widened `Ruling` carrying both, or a distinct result type that wraps the judge's
`Ruling`, is unsettled; the sample above writes `ruling.transcript` without
committing to either."

Two things forced it. [`0002`](./0002-the-judge-is-a-role.md) established that
the judge is `enbanc`-owned precisely so that its inputs and outputs can be
constrained, which makes "what may appear on the judge's output type" a
guarantee rather than a style question. And the round-limit exhaustion question
in `../design/tribunal.md` needs somewhere for its answer to live; the shape of
the result determines what answers are even available.

## Decision

**`hear()` returns a `Hearing`**, a distinct type that wraps the judge's ruling
rather than widening it:

```python
class Hearing(BaseModel, Generic[VerdictT]):
    ruling: Ruling[VerdictT] | None
    transcript: Transcript[VerdictT]
    usage: RunUsage
    rounds: int
```

**`Ruling` carries a verdict and reasoning and nothing else.** Everything else a
caller wants is a fact about the proceeding, not about the decision: the
transcript and the usage are the tribunal's, and the round an entry belongs to
is the tribunal's too.

**`Hearing.ruling` is the final entry's filing, not a copy.** The transcript is
complete on its own; the field exists so callers do not walk the record
backwards to find the terminal ruling.

**No forwarding properties.** `Hearing` does not re-export `.verdict` or
`.reasoning`.

**Exhaustion is not decided here.** `Hearing` accommodates either answer — a
`None` ruling, or `hear()` raising an exception that carries the `Hearing` — and
the question stays open in `../design/tribunal.md`.

## Consequences

**Rejected: a widened `Ruling` carrying transcript and usage.** This is what the
sample read like, and it is the nicest thing to type. It fails on both counts
that forced the decision. The judge's output type would carry fields the judge
cannot produce, so the schema handed to the model and the type handed to the
caller could no longer be the same object. And exhaustion could only be
expressed as `verdict: V | None` — a ruling with no verdict — re-admitting
exactly the invalid state the `Ruling | Continuance` union exists to make
unrepresentable. The union would be enforcing a guarantee at one end that the
result type breaks at the other.

**Rejected: a wrapper that forwards `.verdict` and `.reasoning`.** It keeps the
original sample compiling and reads better than `hearing.ruling.verdict`. But a
forwarded `.verdict` has to do something when there is no ruling, and every
option is bad: return `None` and the caller cannot distinguish "denied" from
"never decided" without checking anyway; raise, and an attribute access becomes
a control-flow branch. The wrapper was chosen to make the absent ruling
explicit, and forwarding is the one addition that would hide it again.

**The `hear()` sample got worse, and that is information.** Every call site now
reads `if hearing.ruling is not None:` before touching a verdict. That check is
the visible cost of leaving exhaustion open, and it is the strongest argument on
record for resolving that question toward an exception — at which point `ruling`
stops being optional and the check disappears. Writing the honest sample is what
surfaced this.

**Consistency: the same reasoning shapes `Entry`.** `round` and `filed_at` wrap
a filing rather than being fields on it, because they are the tribunal's facts
and not the filer's. `Hearing` wrapping `Ruling` and `Entry` wrapping a filing
are one principle applied twice; see
[`0006`](./0006-the-transcript-schema.md).

**Cost: one more exported name, and one more hop at the call site.**
`hearing.ruling.verdict` where `ruling.verdict` would have done. Accepted as the
price of the judge's output type meaning exactly one thing.
