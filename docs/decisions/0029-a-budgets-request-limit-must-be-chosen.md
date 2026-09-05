---
status: accepted
updated: 2026-09-05
---

# 0029. A budget's `request_limit` must be chosen, not inherited

## Context

[`0024`](./0024-a-budget-stops-the-proceeding-between-rounds.md) made `budget` a
proceeding-wide envelope of PydanticAI's own `UsageLimits`, checked at round
boundaries against the accumulated total using that type's own checkers —
`check_before_request`, `check_tokens`, and `check_before_tool_call`. It named
the two fields that have no meaning at a round boundary,
`per_request_input_tokens_limit` and `count_tokens_before_request`, and said they
are ignored.

Writing `../design/execution.md` found a third field that needs handling, for a
reason none of the others have.

**`UsageLimits.request_limit` defaults to `50`** (`usage.py:449`). It is a
dataclass field, so a caller who writes

```python
budget=UsageLimits(cost_limit=Decimal("2.00"))
```

hands `enbanc` an object carrying `request_limit=50` that they never wrote.
`check_before_request` is exactly the checker that enforces it
(`usage.py:516-522`), so under `0024` as written, a $2.00 ceiling is *also* a
fifty-request cap on the entire proceeding.

`../design/outcomes.md` §1 reports `requests=11` across two rounds. Five rounds
trips fifty, and the hearing comes back `Undecided(reason='budget')` having spent
around $0.30 of the $2.00 it was allowed — an audit artifact stating that the
money ran out when it did not. That is precisely the confusion `0024` exists to
prevent, arriving from inside its own mechanism.

**`0024`'s mechanism is not wrong.** The checkers are the right ones and the
round boundary is the right seam. What it did not see is that the field arrives
pre-filled, so what was missing was a guard, not a different checker.

The fifty here is also not the fifty in `../design/api.md`'s "each participant
gets fifty model requests per round". That one is PydanticAI's per-run default
applying in its own scope, because `enbanc` passes no `usage_limits` into a run.
The two numbers are equal, unrelated, and easy to mistake for each other.

## Decision

**A budget keeps every cumulative field, `request_limit` included.** The
round-boundary check is `0024`'s, unchanged.

**`Tribunal(...)` raises `ConfigurationError` when `budget` is passed with
`request_limit` still equal to `UsageLimits`' own default of `50`.**

```text
enbanc.ConfigurationError: budget.request_limit is 50, which is UsageLimits' own
per-run default rather than a proceeding-wide figure you chose. Pass
request_limit=None for no cap, or an explicit number.
```

```python
budget=UsageLimits(cost_limit=Decimal("2.00"), request_limit=None)   # ok
budget=UsageLimits(request_limit=400)                                # ok
budget=None                                                          # ok
```

**The check applies only when `budget` is given.** A tribunal with no budget
reaches no `UsageLimits` object and is unaffected.

**The ignored list stays at two.** `per_request_input_tokens_limit` and
`count_tokens_before_request` remain the only fields a budget carries that
`enbanc` does not consult.

## Consequences

**This is additive to `0024`, not a correction of it.** Its decision section
stands word for word: the same three checkers, the same seam, the same
`Undecided(reason='budget')`. What is added is a construction-time precondition
on the object handed in. A reader comparing the two should not read a reversal
into this.

**The global budget stays whole**, which is the point. `cost_limit`, all three
cumulative token limits, `tool_calls_limit`, and `request_limit` all govern a
proceeding.

**`request_limit` is worth the trouble because `cost_limit` can silently do
nothing.** `check_cost` raises only when `usage.cost is not None`, and
`../design/api.md` already warns that `cost is None` means *unpriceable*, not
free. For a self-hosted or unpriced model a cost ceiling therefore enforces
nothing at all, and a request or token cap is the only working governor. Dropping
`request_limit` would have removed one of the two levers that still work in
exactly the case where the headline lever does not. The
`CostNotFoundWarning` `enbanc` surfaces once per proceeding
(`../design/execution.md`, *The budget check*) is what tells a caller they are in
that case.

**This is the fourth `ConfigurationError` case, and the second of its kind.**
[`0014`](./0014-usage-is-broken-down-per-participant.md) made a verdict valued
`"judge"` a construction error rather than a silent collapse of two participants
into one usage entry. This is the same move: a configuration that looks ordinary,
means something the caller did not write, and produces a record that misstates
what happened. Both are two-line checks that replace an unbounded amount of
documentation nobody reads at the moment it would help.

**Rejected: ignore `request_limit`, as the two per-request fields are ignored.**
The smallest change, no new failure mode, no friction on the README example. It
loses on two counts. A caller who *deliberately* writes `request_limit=200` would
have it silently discarded — the library ignoring an instruction rather than
refusing it, which is worse than either honouring or rejecting it. And it removes
the governor that still functions when a model cannot be priced, which is not a
rare configuration.

**Rejected: honour it and document the hazard.** One paragraph in
`../design/api.md` saying a budget needs `request_limit=None`. Cheapest to build,
and it fails exactly as `0014`'s rejected alternative would have: the failure
stays silent for everyone who has not read the paragraph, and it presents as a
budget that stopped a cheap proceeding for no visible reason. Documentation does
not fix a default.

**Rejected: honour it only when another field was also set**, so that
`UsageLimits(request_limit=50)` alone is read as deliberate. It narrows the blast
radius and it is a rule with an `and` in it that every reader of `api.md` would
have to hold. The explicit error costs one keyword and needs no rule.

**Cost: `request_limit=None` is boilerplate on the common path.** Every caller
who wants a cost ceiling writes one extra keyword, and it appears in
`../design/api.md`'s and `README.md`'s first examples, where a reader is forming
their idea of how much ceremony this library asks for. Accepted, because the
keyword is *explicit about a limit that governs their proceeding* — which is what
a budget is for — and because the alternative is a silent stop that reads in the
audit artifact as a financial fact.

**Cost: an upstream change to that default would change what `enbanc` rejects.**
The check compares against `UsageLimits`' own default rather than a literal, so
it tracks the dependency rather than drifting from it; but if PydanticAI ever
makes `request_limit` default to `None`, the check becomes dead code that should
be removed rather than a check that quietly stops firing. It is named here so a
version bump has somewhere to look.
