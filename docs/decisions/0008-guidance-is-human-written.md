---
status: accepted
updated: 2026-09-02
---

# 0008. Guidance is human-written

## Context

[`0003`](./0003-models-and-guidance-are-injected.md) named the per-agent steer
`guidance` and settled what it *does*: `enbanc` writes each agent's procedural
prompt and appends the caller's guidance to it, never substituting one for the
other. What it left open is where the string comes from.
[`../design/api.md`](../design/api.md) carried that as an open question — whether
guidance is ever machine-tuned — and answered it "human-written in `0.1.0`",
which is a date rather than a decision.

The same question about the other free-text field a caller writes was answered
in [`0007`](./0007-a-statute-is-opaque-text.md): a statute's `text` is the
author's, and `enbanc` holds no assumption about it. Guidance was left in a
different position for no reason anyone had stated.

Leaving it there is not free. Whether the library may ever generate or rewrite
guidance decides whether guidance needs provenance in the transcript, whether it
has to become an addressable and versioned artifact rather than a constructor
argument, and whether an eval harness, a labeled corpus, and a notion of a
*better* ruling belong inside `enbanc` at all. Those are large commitments to
keep suspended behind a field annotated `str | None`.

## Decision

**`guidance` is written by a human**, in the same sense `Statute.text` is.

It is an optional `str` on `Judge` and on `Advocate`, and it is **opaque to
`enbanc`**: not parsed, validated, templated, scored, or rewritten. The library
appends it to the procedural prompt it owns and does nothing else with it. There
is no optimizer, no tuning loop, no guidance store, and no corpus of labeled
cases anywhere in the library — not in `0.1.0`, and not as a planned extension.

## Consequences

**Rejected: an optimization loop that tunes guidance against labeled cases.** It
needs a metric, and the only metric available is agreement with a verdict
someone has already labeled correct — so `enbanc` would own a training corpus,
an eval harness, and a working definition of ground truth for adjudication. The
last of those is the thing this library exists to *produce a record of*, not to
hold an opinion about. And the artifact would undercut the product: a steer that
nobody wrote is a term in the ruling that no human can account for, sitting in
exactly the place a reviewer would most want to interrogate.

**Rejected: structured guidance** — named fields like `priorities` or
`tie_breakers` in place of prose. This is the `criteria` field
[`0007`](./0007-a-statute-is-opaque-text.md) rejected, in a different costume. It
would put `enbanc` in the business of owning a schema for how someone wants
their agent to behave, and any
schema forces a decomposition on steers that do not decompose that way. The
author can already say it in a sentence, which is what the field takes.

**A caller may still tune it; that is not the library's business.** Guidance is
plain per-agent data, separately addressable and swappable, so an external loop
that generates strings and constructs `Advocate(guidance=...)` works now and
will keep working. What this ADR settles is what `enbanc` builds and what it
claims — not what a caller may pass in. A string produced that way belongs to
the caller, and so does the record of where it came from.

**Guidance stays out of the transcript, and this is what makes that safe.** A
`Transcript` is self-contained over the question, the statute, the case, and the
entries — what a reviewer needs to check the ruling against the rule. Guidance
is not among them because it is an input its author wrote and holds. Had the
library been free to generate it, that would not have held: a ruling shaped by a
string with no author is unauditable unless the record carries the string.

**This withdraws one of `0003`'s rejection rationales without disturbing its
decision.** `0003` rejected a tribunal-level default guidance on two grounds:
that it is incoherent across contradictory roles, and that folding guidance into
one tribunal-wide string would foreclose per-agent machine tuning. The second is
void — there is no machine tuning to foreclose. The first is independently
sufficient and the rejection stands: an advocate is told to argue for one answer
and the judge to weigh all of them, so there is no sentence both should read.
`0003` is immutable and otherwise unchanged; this ADR is where the correction
lives.

**Cost: a user who does not know how to steer an agent gets no help from the
library.** This is the trade [`0007`](./0007-a-statute-is-opaque-text.md) made
for statute text, made again for the same reason: the help would have to know
what a better ruling *is*, which is the author's judgment and not the library's.

**Reversing this needs a new ADR.** No rejected option here would have changed
the field's type — which is precisely why the question could sit open behind the
signature, and why the answer has to be recorded in prose rather than inferred
from it.
