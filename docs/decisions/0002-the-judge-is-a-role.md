---
status: accepted
updated: 2026-09-01
---

# 0002. The judge is a role, and the set of judges is closed

## Context

The judge is the centre of the design.
[`../design/tribunal.md`](../design/tribunal.md) builds its premise on
splitting advocacy from adjudication, and "the judge has no tools" is the
constraint that makes the transcript a complete explanation of a ruling. The
glossary named advocates, arguments, rulings and continuances.

The public surface named none of it. `api.md` imported `Tribunal`, `Advocate`,
`Statute`, `Case` and `Verdict` and stopped, so the one agent the whole premise
rests on had nowhere to live and no way to be configured. Deferring got harder
when [`0001`](./0001-statute-carries-no-model.md) moved all model configuration
to `Tribunal`: the judge became the only place that decision could be expressed.

`0.1.0` fixes the public surface, so this had to be settled before any of it was
written.

## Decision

**The set of judge implementations is closed, and `enbanc` owns all of them.**
This is the load-bearing part; the rest follows from it.

The product claim is that a transcript is a complete and auditable account of a
ruling. That claim rests on constraints `enbanc` enforces — the judge has no
tools, and nothing enters an agent's context that is not in the record. Both are
enforceable only while `enbanc` constructs every judge. Hand judge construction
to callers through a protocol and both demote from guarantees to conventions: a
user-supplied judge that queries an API mid-deliberation still produces a
transcript, just not one that explains the ruling. The library would be making a
promise it had given away the ability to keep.

From that:

**`Judge` is a concrete class, not a protocol or an ABC.** It is constructed by
the caller and passed to `Tribunal`, symmetric with `Advocate` and matching the
glossary's framing of the two as peer roles. It takes an optional `model`
overriding the tribunal's default, and optional `guidance`. It takes no tools —
not as an empty default, but as an absence — and no output type, which the
library derives from the `Verdict` enum.

**`Judge` owns behavior.** `Tribunal` calls a method on it rather than reading
its fields and running the loop itself.

**Per-proceeding state lives in a sitting, not on the injected object.** Agents
carry their conversation across rounds: the judge deliberates repeatedly, and an
advocate answers interrogatories with its own earlier argument in view. That
history belongs to one proceeding. `Judge` and `Advocate` are durable
descriptions; `hear()` mints a short-lived sitting per agent per proceeding and
discards it when the proceeding ends.

**This applies to `Advocate` identically.** It is a property of agents that
accumulate history, not of the judge specifically. An asymmetry here would be a
bug waiting for whoever first reuses an advocate.

**The sitting is internal.** Not exported, not in the glossary, never on the
result.

**Invariant: nothing enters an agent's context that is not also in the
transcript.** Message history is a representation of the transcript — shaped for
the provider, cheap to cache — never a second channel.

**`hear()` reports aggregate usage.** `pydantic_ai.usage.RunUsage`, summed
across the judge and every advocate.

## Consequences

**Rejected: `judge_model=` and `judge_instructions=` kwargs on `Tribunal`.** The
smallest possible surface, and honest that there is exactly one judge. But it
contradicts a glossary that presents Judge and Advocate as peer roles — one
would be a class you construct, the other a pair of prefixed keywords — and it
leaves a bench nowhere to go.

**Rejected: `Judge` as a protocol with a shipped `LLMJudge`.** Two public names
for one `0.1.0` concept, and the courtroom vocabulary fights it: the thing you
construct would not be called a judge. The deciding reason is the one above —
an open protocol trades the audit guarantee for an extension point nobody has
asked for.

**Rejected: history on the injected `Judge` or `Advocate`.** It makes a
constructed object single-use. A second `hear()` would deliberate case B with
case A still in context — silently, producing a plausible ruling — and
concurrent calls would interleave writes into one message list.

**Rejected: exposing the sitting on the result.** Given the invariant it holds
no fact the transcript lacks, only a provider-shaped rendering of the same
record. Two competing views would undercut the transcript's standing as *the*
audit artifact. Usage is surfaced instead precisely because it is the one thing
a proceeding produces that the transcript does not contain.

**Constraint on the implementation.** `Tribunal` calls the judge's sitting
method and nothing else: no `isinstance` checks against `Judge`, no reaching
past the boundary into its agent or its history. This is what would keep a later
`judge: Judge | Bench` a non-breaking widening rather than a rewrite. It binds
the implementation, which is why it is recorded here rather than in a design doc.

**Deferred: the bench.** *En banc* names a full bench, and `0.1.0` seats one
judge. If a bench ever sits it joins `judge=` as a union member; an interface
gets extracted only if a third member appears, and it would still be
`enbanc`-owned. Not an extension point.

**Cost: a class for what is currently two fields**, plus a config-versus-runtime
split that nothing yet forces. Both are paid to keep `hear()` reusable and the
bench reachable.

**Cost: no supported path for a custom judge.** A caller who wants different
adjudication logic has to fork or wait. This is the deliberate price of the
guarantee, and it is the consequence most likely to be revisited — if it is, the
successor ADR has to say what happens to the audit claim.
