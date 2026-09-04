---
status: current
updated: 2026-09-04
---

# Writing the prompt found what reviewing the invariant did not

The session designed [`prompting.md`](../design/prompting.md) — the two
procedural prompts, how an agent's instructions are assembled, the turn
templates, and `Transcript.render()`. What was decided, and what lost, is in
[`0025`](../decisions/0025-the-record-includes-what-steered-it.md),
[`0026`](../decisions/0026-one-renderer-serves-both-audiences.md) and
[`0027`](../decisions/0027-an-advocate-answers-its-interrogatories-in-order.md).
This entry is about *when* three of the findings in them arrived, because the
pattern is now the second instance of one this repo has already recorded once —
see [`2026-09-02-values-before-schemas.md`](./2026-09-02-values-before-schemas.md).

All three arrived while writing the concrete artifact, and none of them arrived
while reading the documents that were supposed to guarantee them.

## What building the artifact caught

**Two unnamed exceptions to the invariant, sitting in plain sight.**
`tribunal.md` claims *nothing enters an agent's context that is not also in the
transcript*, and [`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md)
had already been written specifically to name the one exception and to forbid
adding a second. There were already three. `guidance` reached every agent and no
transcript held it; so did `enbanc`'s own procedural prompt. Nothing found this
in four documents and twenty-four ADRs, including the ADR whose entire subject
was auditing that sentence.

What found it was building the traceability table — one row per element of an
agent's context, one column for the transcript field holding it. That is a
mechanical exercise and it cannot be completed dishonestly: a row with an empty
right-hand column is a hole. Reading the invariant asks *is this true?*, which
the mind answers from the two or three cases it happens to hold. Writing the
table asks *what is the complete list?*, which it cannot.

**A definition that contradicted itself one sentence later.** The `since`
parameter was first written as "the last round the participant was shown", then
glossed in the next sentence as "for an advocate, the last round in which it
filed". Those disagree for an advocate entering round 2 — shown nothing, filed
in round 1 — and the worked example beside them used the wrong one. Both
sentences read fine; the pair does not. It surfaced only when a *second* worked
example had to be written, for the second run of a twice-questioned advocate,
and the two definitions produced different deltas.

**A premise that a new decision would have quietly falsified.** `evidence.md`
justifies per-advocate ledger ids with a stated premise: *an advocate's tool
calls are sequential*. Dispatching two interrogatories to one advocate
concurrently — which `0015` permits and nothing forbade — makes that false from
the inside, and with it the determinism the ids rest on. Nothing connects those
two documents; what connected them was taking a justification literally enough to
ask what could break it.

## Why the artifact finds what the rule does not

An invariant is a claim about a set nobody ever enumerates. It stays true in
review because review samples the set, and it samples the cases the author was
thinking about when they wrote it. The concrete artifact enumerates: a prompt has
to contain everything the agent will read, a table has to have a row per element,
a worked example has to commit to one delta rather than a definition compatible
with two.

This is the same finding as `2026-09-02`, one level up. There it was schemas
versus values: a schema says what is *representable*, a value has to commit. Here
it is invariants versus artifacts: an invariant says what is *forbidden*, an
artifact has to exhibit everything present. Both times the abstraction survived
its own review, an ADR, and prose written to justify it — and fell to the first
concrete instance.

## What to do with this

[`execution.md`](../design/execution.md) is next, and it carries the same risk in
sharper form: it owns the sentence *message history is a representation of the
transcript — never a second channel*, which is an invariant of exactly the shape
that just failed twice.

Write the literal message sequence first. Two rounds, three advocates, one
twice-questioned — every `ModelRequest` and `ModelResponse` in order, for one
advocate and for the judge, before writing a paragraph about how history works.
If a message in that sequence has no transcript field behind it, that is the
finding, and it will not show up in prose that describes the mechanism instead of
exhibiting it.

Second, smaller: when a design doc justifies a choice with a premise about
behaviour — "tool calls are sequential", "advocates fan out concurrently" — treat
the premise as a thing that can be falsified elsewhere in the system, not as
background. `evidence.md` now says so about its own, in the paragraph that
protects it.
