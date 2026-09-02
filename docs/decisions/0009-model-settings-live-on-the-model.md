---
status: accepted
updated: 2026-09-02
---

# 0009. Model settings live on the injected model

## Context

[`0003`](./0003-models-and-guidance-are-injected.md) settled that the model is
injected and that `Tribunal(model=...)` is the default every agent inherits, and
closed with "nothing beyond `model` and `guidance` in `0.1.0` — no
`ModelSettings` pass-through." It recorded that as a deferral rather than an
answer: the gap was accepted "because a settings pass-through is easy to add
later and awkward to remove, and because the right precedence rule between a
tribunal default and per-agent settings is not obvious enough to guess at now."
[`../design/api.md`](../design/api.md) carried the matching open question.

What ends the deferral is a fact about PydanticAI rather than a preference. In
`pydantic-ai` 2.36.0 — the floor `pyproject.toml` pins — `Model.__init__` takes
`settings: ModelSettings | None`, and the model merges them into every request it
makes. Temperature, `max_tokens`, `timeout`, `stop_sequences`, `extra_headers`,
thinking configuration, and every provider-specific setting already have a home
in the object the caller constructs and hands over.

That also makes the question smaller than the way it was written. "Temperature,
`max_tokens`, retries" is three things with three different homes, and only one
of them was ever a candidate for a per-agent argument.

## Decision

**Model settings are the caller's, and they travel inside the `Model`.**
`enbanc` takes no `settings` or `model_settings` argument on `Tribunal`, `Judge`,
or `Advocate` — not in `0.1.0` and not as a planned extension. You configure a
`pydantic_ai.models.Model` and hand it over; what you configured is what that
agent runs with.

**`enbanc` supplies no per-request model settings of its own.** PydanticAI
merges a model's own settings with the settings passed at request time, and the
request-time ones win. Anything the library passed would therefore silently
override what a caller baked in, at a precedence the caller cannot see. It
passes none, so the model's settings are the last word.

**Per-agent settings are per-agent models.** The override `0003` already
provides is the whole mechanism — a second `Model`, constructed over the same
provider so both share one HTTP client:

```python
provider = AnthropicProvider(api_key=...)
careful = AnthropicModel(
    "claude-opus-5", provider=provider, settings=ModelSettings(temperature=0.0)
)
cheap = AnthropicModel("claude-sonnet-5", provider=provider)

Tribunal(model=cheap, judge=Judge(model=careful), ...)
```

**Retries are not one thing, and neither half is a model setting.** HTTP-level
retry and backoff belong to the httpx client inside the provider inside the
`Model` — `pydantic_ai.retries` ships tenacity-backed transports for exactly
this — so they are already the caller's, by the same route as everything else
here. Tool-call and output-validation retries are `Agent(retries=...)`, and
`enbanc` constructs every agent: those budgets guard the `Ruling | Continuance`
contract the library owns, and they stay internal.

## Consequences

**Rejected: `settings=` on `Tribunal`, `Judge`, and `Advocate`.** It would
recreate the precedence problem `0003` declined to guess at, and make it worse
than the two-layer one PydanticAI already resolves: a tribunal default, a
per-agent override, and the model's own baked settings are three layers, and the
rule joining them would be `enbanc`'s invention — documented by `enbanc`, and
debugged by whoever finds temperature is not what they set it to. Injection means
the object you hand over *is* the configuration. A parallel channel that
partially overrides it makes the injected object no longer authoritative, which
is the property that made injection worth choosing.

**Rejected: a pass-through on `Tribunal` only.** The cheap version — one layer,
no per-agent rule to write. But it buys nothing a `Model` does not already
carry, and it lands on the wrong side of the merge: a tribunal-level setting
reaches the request, and the request wins, so the one thing this option adds is
a way to silently beat the settings a caller put on their own model.

**The caller can now configure things `enbanc` would rather they did not.**
`ModelSettings` includes `tool_choice` and `parallel_tool_calls`; a model built
with `tool_choice='none'` and handed to an advocate takes that advocate's tools
away, and the proceeding comes out thin rather than broken. `enbanc` does not
police this, for the reason [`0007`](./0007-a-statute-is-opaque-text.md) does not
inspect statute text: the injected object is the caller's. The record still shows
what happened — an advocate arguing with no exhibits is visible in the
transcript.

**Cost: changing temperature is a constructor, not a keyword.** Running a
proceeding at temperature 0 means building a `Model` with settings rather than
passing `temperature=0` to `hear()`. Accepted: it is one object the caller
already builds, and it keeps every knob PydanticAI grows — new sampling
parameters, provider-specific settings — reachable the day it ships, without
`enbanc` widening its own surface to match.

**Cost: no per-run override.** `hear()` takes a case and nothing else, so two
runs of one tribunal at different temperatures means two models. Accepted,
because the alternative is a hidden argument: nothing in the record distinguishes
the two runs, and a proceeding configured differently is better expressed as a
different tribunal than as a keyword that leaves no trace.

**This closes `0003`'s deferral rather than reversing it.** `0003` predicted a
pass-through would be easy to add and awkward to remove, and declined to guess a
precedence rule. The answer is that no precedence rule is needed, because there
is no second place to set them.

**Untouched: `UsageLimits`.** The cost-control question in
[`../design/tribunal.md`](../design/tribunal.md#open-questions) asks whether a
budget can halt a proceeding mid-round. `UsageLimits` is a run-time argument, not
a `ModelSettings` field, and it is not baked into a `Model` — so that question
stays open, and nothing here decides it in either direction.

**Reversing this needs a new ADR.** The absence of a `settings` argument is not
an oversight to be filled in when someone asks for it; it is the shape injection
was chosen for.
