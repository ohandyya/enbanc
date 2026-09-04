---
status: accepted
updated: 2026-09-04
---

# 0024. A budget stops the proceeding between rounds

## Context

The last open question in
[`../design/tribunal.md`](../design/tribunal.md). `max_rounds` counts judge
deliberations, which bounds how many times the judge thinks and bounds nothing
about what a round costs: an advocate's run is its own tool loop, and a
twelve-verdict tribunal opens twelve of them at once. The question carried two
governors — what a proceeding may *spend*, and how *wide* its fan-out may be —
the second re-filed here by
[`0020`](./0020-tool-timeouts-ride-on-the-tool.md).

[`0011`](./0011-exhaustion-is-an-outcome-failure-is-an-error.md) fixed where an
answer has to land before there was one: a stop is either a record or an
exception, and the test is whether the tribunal ran its own process. That makes
the landing the substantive half. A budget stop that comes back as a plain
`Undecided` makes *the case was genuinely ambiguous* and *we stopped paying* the
same value in the audit artifact, which is the confusion `0011` exists to
prevent, arriving from a direction it did not consider.

[`0009`](./0009-model-settings-live-on-the-model.md) and `0020` refused a
parameter twice, each time because the setting had a good home on an object the
caller already constructs — `ModelSettings` on the `Model`, `timeout` on the
`Tool`. `0009` also recorded, explicitly, that `UsageLimits` is *untouched* by
that reasoning: it is a run-time argument rather than a `ModelSettings` field,
so it cannot ride on an injected object at all. The same principle therefore
points the other way here.

Three facts about `pydantic-ai` 2.36.0 — the floor `pyproject.toml` pins —
change the question, and two of them were recorded wrongly.

**There is already a governor nobody chose.** `Agent.run` resolves
`usage_limits = usage_limits or UsageLimits()`, and `UsageLimits.request_limit`
defaults to `50`. Every participant run is capped at fifty model requests today,
with `enbanc` passing nothing. `max_rounds` was never the only governor.

**A shared accumulator would erase
[`0014`](./0014-usage-is-broken-down-per-participant.md).** The natural route to
a proceeding-wide budget is one `RunUsage` passed to every `run(usage=...)`,
since limits are checked against it. But `AgentRunResult.usage()` returns
`self._state.usage` — that same object — so every participant would report the
whole proceeding's spend and the per-participant breakdown `0014` makes the
*stored* fact would be gone. `RunUsage` supports subtraction, so deltas are
computable; they are not attributable when *n* advocates mutate one object
concurrently. That concurrency is also why a shared ceiling is soft: every run
in flight can cross it at once.

**`Agent(max_concurrency=<int>)` does not bound the fan-out.** `0020` re-filed
the question saying it governs how many advocates argue at once. It does not.
The limiter is per-`Agent`-instance, each advocate is its own agent running once
per round, so an int hands each of them a private limiter and bounds nothing
across the round. The shareable form is `ConcurrencyLimiter`, which the
docstring describes as being for "sharing limits across multiple agents" — and
a caller cannot reach it, because `enbanc` constructs the agents.

## Decision

**A budget is a proceeding-wide envelope, checked between rounds.**

```python
from pydantic_ai.usage import UsageLimits

tribunal = Tribunal(
    ...,
    max_rounds=5,
    budget=UsageLimits(cost_limit=Decimal("2.00")),
    max_concurrency=4,
)
```

**`Tribunal(budget: UsageLimits | None = None)`.** PydanticAI's type, not one
`enbanc` invents. The default is `None`: no budget, and `max_rounds` alone.

**It is checked at round boundaries against the accumulated total.** `0014`
already makes `enbanc` keep usage per participant and sum it, so the check needs
no new state: before dispatching a round, `enbanc` runs the caller's limits
against that sum using `UsageLimits`' own checkers — `check_before_request`,
`check_tokens`, and `check_before_tool_call` — and treats the
`UsageLimitExceeded` they raise as the stop signal rather than as an error to
propagate.

**The scope widens; the field meanings do not.** Every field consulted is
cumulative in PydanticAI and stays cumulative here — it just accumulates over a
proceeding instead of a run. The two genuinely per-request fields,
`per_request_input_tokens_limit` and `count_tokens_before_request`, have no
meaning at a round boundary and are ignored.

**`enbanc` passes no `usage_limits` into any run.** PydanticAI's inherited
default therefore stands: fifty model requests per participant per round.
Tripping it is a run that could not file, which is `ProceedingFailed` like every
other, and it is named here rather than left to be discovered in production.

**A budget stop is an outcome, and `Undecided` says which envelope ran out.**

```python
class Undecided(BaseModel):
    kind: Literal["undecided"] = "undecided"
    reason: Literal["rounds", "budget"]
```

`reason` is required and undefaulted. `kind` is defaulted because exactly one
value is correct; `reason` has two, and a default would be a guess that reads as
a fact in the record.

**`Tribunal(max_concurrency: AnyConcurrencyLimit = None)`** — PydanticAI's own
`int | ConcurrencyLimit | AbstractConcurrencyLimiter | None`, bounding how many
advocates run at once. The default is `None`: every advocate at once, which is
what the design does today.

**Budget and concurrency are different levers, and this is the answer to the
question asking whether they are one.** A budget bounds money over a proceeding;
concurrency bounds simultaneous provider connections. A twelve-verdict tribunal
hits a rate limit on its first round no matter how much it is allowed to spend.

## Consequences

**The mechanism settles the landing, which is why it was chosen.** A budget
checked mid-run stops with a round half-filed and nothing adjudicated — the
tribunal did not finish its process, and `0011` puts that on the exception side.
A budget checked between rounds stops at exactly the seam `max_rounds` stops at,
with whole rounds behind it and a record that reads like any other undecided
proceeding. Choosing where to check is choosing what the stop *is*.

**A budget is the caller's declared envelope, like `max_rounds`.** Hitting it is
a normal end, not an outage: nothing is broken, every filing in the transcript is
real, and a reviewer can persist it and rerun with more. That is the whole of why
it is a record rather than an exception.

**A field on `Undecided`, not a third `Outcome` member.** Both causes mean the
same thing to control flow — no verdict, rerun with a bigger envelope — so a
second `match` arm would be two arms doing one thing. The difference is
documentary, which is what a field is for. It does not reopen `0011`'s reason for
keeping `Undecided` empty: that was about duplication, and `reason` is the one
fact no other field carries. `Hearing.rounds` cannot stand in for it — a
proceeding can spend its budget on the same round it would have spent its last
deliberation.

**Cost: a caller can ignore a field where a union member forces an arm.** Someone
who logs `Undecided` and moves on still cannot tell the two apart. Accepted,
because the alternative charges every call site an arm to carry information most
of them will not branch on, and the artifact — which is what a reviewer reads —
distinguishes them either way.

**Cost: the budget is coarse.** Nothing stops a runaway *inside* a round, so the
guarantee is that a proceeding stops within one round of its budget, not that it
never exceeds it. The bound on the overshoot is one round's spend, and underneath
it sit PydanticAI's inherited per-run request limit and, for a caller who wants
one, `tool_calls_limit`. This is the shape of cost `0020` already accepted for an
unbounded tool.

**Cost: two budgets means two tribunals.** `budget` is not an argument to
`hear()`, so varying it per case means constructing a second `Tribunal`. This is
`0009`'s per-run-override reasoning applied unchanged: a proceeding configured
differently is better expressed as a different tribunal than as a keyword that
leaves no trace in the record.

**Constraint on the implementation: normalize the concurrency limit once and
share the object.** `normalize_to_limiter` returns an `AbstractConcurrencyLimiter`
unchanged but builds a *new* limiter from an `int` or a `ConcurrencyLimit`. So
`enbanc` must normalize the caller's value once per proceeding and hand the same
limiter to every advocate agent; forwarding the raw value to each
`Agent(max_concurrency=...)` would give each advocate a private limiter and bound
nothing. The judge is not given one: it runs alone, and the fan-out is the only
place concurrency exists in a proceeding. Recorded here because it binds the
implementation rather than the surface.

**Rejected: `max_rounds` is the only governor.** The smallest surface, and it was
the status quo. It leaves a caller no way to cap tokens or dollars at all —
`0009` closed the `Model` route by putting settings on the injected object, and
`UsageLimits` is not one of them — so "bound your spend" would mean "choose fewer
rounds and hope". It is also no longer honest: the inherited fifty-request
default means the library already has a governor it did not choose, and a design
doc claiming otherwise would be a claim known to be false.

**Rejected: a per-run pass-through**, handing the caller's `UsageLimits` to each
participant run. One line, keeps `0014` intact, and PydanticAI enforces it
precisely rather than a round late. But it caps a participant, not a proceeding:
the real ceiling becomes advocates × rounds × the limit, which is not the number
anyone sets a budget to. A caller who wants this can still have it per tool
(`tool_calls_limit`) or per model, and what they cannot otherwise get is the
proceeding-wide number.

**Rejected: a proceeding-wide budget via a shared `RunUsage`.** The only option
that stops the instant the budget is crossed. It costs `0014`'s breakdown, as
above; it is soft under a concurrent fan-out anyway, so the precision it buys is
partly illusory; and every stop lands mid-round, which forces the exception
reading and leaves a partial round in the record for a stop the caller asked for.

**Rejected: an `enbanc` budget type.** A `Budget` model with `max_cost`,
`max_tokens`, and friends would let `enbanc` name only the fields that apply at a
round boundary, instead of accepting a type with two that do not. It was rejected
for the reason `enbanc` takes `RunUsage` rather than defining a usage type:
PydanticAI already has one that works, callers already know it, and duplicating
six fields — including the `cost_limit` that does the real work — to avoid
documenting two exclusions is a bad trade. The ignored fields are stated in
`../design/api.md` rather than hidden.

**Rejected: a `detail: str` on `Undecided`** carrying `UsageLimitExceeded`'s
message. It would say which limit tripped and by how much. But which limit
tripped is recoverable by comparing `hearing.usage` against the `budget` the
caller set, and a provider-adjacent free-text string copied into an audit record
is a field nothing can validate and everything must keep true.

**Rejected: raising a `BudgetExhausted`.** The loud path, and it makes it
impossible to file "we ran out of money" as an adjudication. `ProceedingFailed`
could not carry it — its `participant` field asserts someone could not be heard,
and here everyone was heard fine — so it would mean a fifth exception type for a
stop that is not a failure. `0011` rejected raising on exhaustion because the
outcome a reviewer most needs to examine is the one that would not serialize, and
that argument does not weaken when the envelope is denominated in dollars rather
than rounds.

**This closes the last open question.** `../design/tribunal.md` and
`../design/api.md` now carry none, and `docs/design/` describes a complete
system.
