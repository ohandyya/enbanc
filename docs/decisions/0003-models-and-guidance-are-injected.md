---
status: accepted
updated: 2026-09-01
---

# 0003. Models and guidance are injected per agent

## Context

Every agent in a proceeding needs two things `enbanc` cannot supply: a model to
run on, and whatever role-specific steer the author wants to give it.
[`0001`](./0001-statute-carries-no-model.md) settled where a model does *not*
live — a statute is inert — and explicitly left open "whether the judge and the
advocates can run different models, and whether that is per-advocate."

Naming the judge in [`0002`](./0002-the-judge-is-a-role.md) forced it. A judge
that cannot be given a model cannot run, and once the judge takes one the
question of whether advocates may differ can no longer be deferred.

`../design/api.md` had also drifted. It paraphrased `0001` as "model assignment
has exactly one home, and it is `Tribunal`" — a stronger claim than `0001`
makes. That paraphrase, not the ADR, is what this decision corrects.

## Decision

**The model is injected, never named by a string.** The caller constructs a
`pydantic_ai.models.Model` and hands it over. `enbanc` has no provider concept,
no model-string parser, and no registry — PydanticAI already has all three, and
provider-agnosticism is a property `enbanc` gets by not competing with it.

**`Tribunal(model=...)` is required and is the default every agent inherits.**
`Judge` and `Advocate` each take an optional `model` that overrides it. There is
always at least one agent, so a default is always meaningful; requiring it
avoids an "either the tribunal or every agent" validation rule that would buy
nothing. It is named `model`, matching PydanticAI's `Agent(model=...)`.

A single `Model` instance is safe to share across every agent, and sharing one
is the intended path.

**The steer is called `guidance`, and it augments rather than replaces.**
`enbanc` writes each agent's procedural prompt: the `Ruling | Continuance`
contract, the rule that interrogatories are targeted rather than broadcast, the
judge's prohibition on gathering its own evidence, the advocate's licence to
concede. `guidance` is added to that.

**Guidance is per-agent and never inherited.** There is no tribunal-level
default.

**Nothing beyond `model` and `guidance` in `0.1.0`.** No `ModelSettings`
pass-through for temperature, `max_tokens`, or retries.

## Consequences

**This refines `0001`; it does not supersede it.** `0001` decided a statute
carries no model, and left per-agent assignment open. This answers the question
it left. The correction lands in `../design/api.md`, whose paraphrase overstated
the ADR; `0001` itself is unchanged and remains accurate.

**Rejected: model strings like `"anthropic:claude-sonnet-5"`.** Convenient, and
PydanticAI supports them. But accepting one means `enbanc` owns a provider
concept: a syntax to document, a set of prefixes to keep current, and a failure
mode where an unknown string is `enbanc`'s error message rather than
PydanticAI's. Injection keeps the library ignorant of providers, which is the
only durable form of provider-agnostic.

**Rejected: per-agent models with no tribunal default.** Fully explicit, and it
would make every agent's model visible at the call site. But a `Verdict` enum
with five values means five advocates repeating one argument, and the common
case — one model everywhere — would be the most verbose thing to write.

**Rejected: `instructions` as a full replacement for the system prompt.** It
reads as more control and is less. The output contract would become the
caller's responsibility, and a prompt that omitted it would break schema
validation in a way that presents as a library bug. The word was also wrong:
in PydanticAI `instructions` *is* the system prompt, so keeping it for a value
that gets appended would mislead exactly the reader most likely to assume
otherwise.

**Rejected: a tribunal-level default guidance.** Incoherent across contradictory
roles — an advocate is told to argue for one answer, the judge to weigh all of
them — and anything genuinely shared is already carried by `question` and
`statute`. It would also foreclose per-agent tuning: `../design/api.md` records
an intent to make guidance machine-tunable later, which needs each agent's
guidance separately addressable and swappable. Per-agent optional plain data
satisfies that with nothing built for it now. Folding guidance into one
tribunal-wide string is the only option here that would have closed that door.

**Cost: no temperature or retry control in `0.1.0`** short of configuring the
`Model` you construct. Accepted because a settings pass-through is easy to add
later and awkward to remove, and because the right precedence rule between a
tribunal default and per-agent settings is not obvious enough to guess at now.

**Cost: the caller writes an import and a constructor** before they can run
anything, where a string literal would have done. That is the price of the
library not having opinions about providers.
