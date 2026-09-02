---
status: accepted
updated: 2026-09-02
---

# 0007. A statute is opaque text

## Context

[`0001`](./0001-statute-carries-no-model.md) settled what a statute does *not*
carry — a model — but left what it *is* open. The shape that shipped into
[`../design/api.md`](../design/api.md) was `text: str` plus an optional `name`,
described there as a deferral rather than an answer: the alternative on the
table was a set of named criteria the judge would rule on one at a time, with a
`criteria` field held out as an additive change that the prose deliberately did
not foreclose.

Deferring it has a cost that lands on everything downstream. The judge's system
prompt, the advocates' framing, `Transcript.render()`, and `0001`'s deferred
`Statute.draft()` all have to be written without knowing whether `text` is the
rule itself or a rendering of some structure that is the real rule. Writing them
against a maybe means writing them twice, and it means the first version of each
quietly commits to an answer nobody has stated.

## Decision

A `Statute` is `text` and an optional `name`. Nothing else, now or as a planned
extension.

The `text` is written by a human, and its format and content are entirely the
author's business — a paragraph, numbered clauses, Markdown, a pasted policy
document, a table. **`enbanc` holds no assumption about it.** It does not parse
it, validate its shape, split it into parts, or require any structure. The
statute reaches the judge and the advocates whole, and the transcript reproduces
it verbatim. The only constraint is the one the type states: it is a `str`.

`name` stays, and its job is unchanged: it is what a transcript cites when a
reviewer asks which version of a policy produced a decision. It is a label on
the text, not a claim about the text.

## Consequences

**Rejected: a `criteria` field of named, individually-ruled clauses.** It would
put `enbanc` in the business of owning a schema for other people's policies —
deciding what a criterion is, whether criteria nest, whether they are
conjunctive, what happens when one is unmet but the whole still passes. Every
answer there is a policy judgment belonging to the person who wrote the rule,
and any schema we picked would force a decomposition on rules that do not
decompose that way. Worse, the user has already written the rule down; a
criteria list is a lossy re-encoding of a document that was fine as it was.

**Rejected: the transcript argument for structure.** Named criteria were
motivated by wanting the transcript to show *which* criterion decided the case.
That is a fact about the judge's reasoning, not about the statute — the judge
can cite the clause it relied on in `Ruling.reasoning`, in the author's own
words, without `enbanc` having assigned that clause an identifier first. A
structured statute would buy a field that is machine-readable at the price of
making the record disagree with the document it is auditing against.

**Rejected: inspecting the text at construction.** Sniffing for structure,
linting for emptiness, or normalizing whitespace are all small versions of
holding an assumption. A statute that looks wrong to `enbanc` is not
necessarily wrong, and a library that quietly reshapes the rule it is asked to
apply breaks the one thing the transcript is for.

**Moot, not deferred: `Statute.draft()`.** `0001` deferred drafting on the
grounds that it becomes coherent the moment a statute is more than prose, and
made this question the condition. The condition will not be met: there is no
target representation to compile into, so there is nothing for a drafting step
to produce that the author has not already written. Drafting is cut, and the
open question in [`../design/api.md`](../design/api.md#open-questions) that
`0001` pointed at is answered by this ADR rather than left standing.

**Cost: users holding loose policy prose still get no help turning it into a
rule.** `0001` accepted this as temporary, pending an answer here. It is now
permanent, and correctly so — the help would have to know what a rule *is*,
which is exactly the thing this ADR declines to decide on the author's behalf.

**Cost: the library cannot report per-criterion outcomes.** No structured
"clause 3 failed" field exists or will. What the record shows is the judge's
reasoning in prose, which is what a human reviewer reads anyway.

**Reversing this needs a new ADR.** The shape is still additive-friendly by
accident — a field could be appended without breaking a caller — but
`../design/api.md` no longer holds room for one as a stated intent, and no part
of `0.1.0` should be written in anticipation of it.
