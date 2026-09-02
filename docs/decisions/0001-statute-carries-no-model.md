---
status: accepted
updated: 2026-09-02
---

# 0001. A statute carries no model

> Followed by [`0007`](./0007-a-statute-is-opaque-text.md), which settles what a
> statute *is* — opaque text, with no structure now or planned. That closes the
> open question this ADR made drafting conditional on: `Statute.draft()` is cut
> for good, not deferred. The reasoning below stands as written.

## Context

The drafted public surface constructed a statute like this:

```python
statute = Statute.draft(
    "Approve $500k loans only where DTI < 0.43 and ...",
    model="anthropic:claude-sonnet-4-6",
)
```

A classmethod sits in constructor position, so the `model` read as though it
stuck to the object. Nothing in the example settled whether it did. That left a
question no reader could answer from the API: **is a `Statute` a rule, or a rule
plus the judge that applies it?** `0.1.0` fixes the public surface, so it had to
be settled before any of it was written.

Drafting was justified on the grounds that turning loose policy language into a
testable rule is itself a model call. That argument holds only if "loose policy
language" and "a testable rule" are different kinds of thing — only if a statute
has some structure that prose gets compiled *into*. It has none, and will not in
`0.1.0`: rules are written by hand, and a statute is text that reaches the
judge. So the drafting step had no target representation. It would have rewritten
prose into prose, under a name implying otherwise, while putting a model call on
the authoring path.

## Decision

A `Statute` carries no model. It is the rule and nothing else — inert data, with
no behavior and no inference attached.

`Statute.draft()` is cut from `0.1.0`. Nothing in the statute's construction
touches a model, not as an argument and not as retained metadata.

Model assignment lives solely on `Tribunal`, which remains an open question
there: whether the judge and the advocates can run different models, and whether
that is per-advocate.

`Statute` stays a type rather than becoming a bare `str`. It is the artifact
every ruling is audited against, `question` and `statute` are otherwise two
adjacent strings that can be swapped silently at the call site, and shipping a
`str` would make any later structure a breaking change.

## Consequences

**Rejected: statute as rule + judge.** Letting the statute own the model that
adjudicates against it would give model configuration two owners and require a
precedence rule between them. Worse, it inverts the workflow that motivates this
library: comparing models on a fixed rule is the obvious thing to do with an
auditable adjudicator, and under that design swapping the judge means
re-drafting the statute — the rule and the model moving together, with no way to
attribute a change in outcome to either.

**Rejected: keep drafting, with the model recorded only as provenance.** This
answers the ambiguity without justifying the feature. The model call still sits
on the authoring path for a step that compiles into nothing, and the provenance
field documents a transformation whose value is unestablished.

**Deferred, not rejected: drafting itself.** It becomes coherent the moment a
statute is more than prose. Whether that happens is an open question in
[`../design/api.md`](../design/api.md#open-questions); if it resolves toward
named criteria, drafting can return with a real job and this ADR gets a
successor.

**Cost: users holding loose policy prose get no help turning it into a rule.**
Accepted deliberately. What that help should produce is unspecifiable until we
know what a rule *is*, and shipping a plausible-looking version of it would
commit the API to an answer we have not reached.

**The public surface does not shrink.** Removing the model from `Statute` does
not remove the configuration — it relocates the whole of it to `Tribunal`. That
makes the open model-assignment question in
[`../design/tribunal.md`](../design/tribunal.md#open-questions) harder to defer,
not easier, since it is now the only place the decision can be expressed.
