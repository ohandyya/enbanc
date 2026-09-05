---
status: accepted
updated: 2026-09-05
---

# 0030. The retry budgets, and a tool's retries ride on the `Tool`

## Context

Three documents refer to "the library's own `Agent(retries=...)` budget" and none
of them names a number.

[`0009`](./0009-model-settings-live-on-the-model.md) put HTTP retry and backoff on
the caller's httpx client and kept tool and output-validation retries internal,
"because those budgets guard the `Ruling | Continuance` contract the library
owns". [`0016`](./0016-exhibits-are-stamped-citations.md) spends it on an
unresolvable `_Exhibit.source`. [`0020`](./0020-tool-timeouts-ride-on-the-tool.md)
spends it on a timed-out tool, and builds a ladder on it — *timeout → the advocate
adapts → retries spent → the proceeding fails* — in which only the last rung ends
anything.

Read together those describe **one** budget that a flaky tool and a miscited
exhibit compete for. Writing `../design/execution.md` established that
`pydantic-ai 2.36.0` has two, and that the default breaks a specified example.

**`retries` is `int | AgentRetries`**, where `AgentRetries` is
`{'tools': int, 'output': int}` and a bare `int` sets both
(`agent/__init__.py:379-389`). **Both default to `1`**, and they are independent:

```text
same tool timing out N times:
  timeouts=1  retries=None          -> OK
  timeouts=2  retries=None          -> UnexpectedModelBehavior: Tool 'slow' exceeded
                                       max retries count of 1
  timeouts=2  retries={'tools': 3}  -> OK

tools=1 fully spent by a timeout, then two output-validation retries still available
  -> OK
```

**Tool retries are counted per tool name** (`tool_manager.py:262`, keyed on
`name`), not per run.

**`../design/outcomes.md` §1 is unreachable at the default.** It shows `APPROVE`
timing out **twice on `web_search`** in round 2 and the proceeding going on to
rule — two `ToolFailure` rows explaining an empty `exhibits` list, which is
[`0022`](./0022-tool-failures-are-recorded.md)'s worked example. At `tools: 1` the
second timeout raises and the proceeding fails instead. A specified behaviour and
an inherited default disagree, and the default wins until someone picks a number.

**`Tool` already carries `max_retries`**, resolving `tool → toolset → ctx`
(`agent/__init__.py:699`) — the same object `0020` put `timeout` on.

## Decision

**`enbanc` builds every agent with `retries={'tools': 3, 'output': 2}`.**

**They are two budgets and the design says so.** A timed-out tool spends `tools`;
an `_Exhibit` citing an id the advocate was never issued spends `output`. Neither
can exhaust the other.

**`tools` is 3.** Three failures of the *same* tool before an advocate is treated
as one that could not be heard. `outcomes.md` §1's two timeouts fit with a rung to
spare, and because counting is per tool name, reaching for a different tool costs
nothing from this budget at all — which is what makes `0020`'s "the advocate
adapts" a move rather than a phrase.

**`output` is 2.** One correction usually fixes a miscited id; two covers a
stubborn model without paying indefinitely for a broken one.

**Neither number is configurable through `enbanc`**, per `0009`.

**The `tools` half is overridable per tool, where it belongs.**
`Tool(fn, timeout=..., max_retries=...)` overrides the agent-level default for
that tool, and `../design/evidence.md` documents it beside the timeout:

```python
Advocate(
    tools=[
        Tool(web_search(api_key=...), timeout=15.0, max_retries=5),
        Tool(dti_for, timeout=5.0),
        parse_statute_dates,
    ],
)
```

**The `output` half stays unreachable**, and will stay unreachable. It guards the
`Ruling | Continuance` contract and the citation integrity
[`0016`](./0016-exhibits-are-stamped-citations.md) rests on, which is exactly what
`0009` says is the library's.

## Consequences

**`../design/evidence.md` and `../design/api.md` are corrected in the same
commit**, under rule 2. Both spoke of one budget. `api.md`'s "the library's own
budget — `Agent(retries=...)`, guarding the `Ruling | Continuance` contract" is
the `output` half alone.

**`0020`'s ladder now has a number under it**, and it is the number that makes
`outcomes.md` §1 true rather than aspirational. A degraded advocate and an unheard
one were distinguished in prose by `0022`; they are distinguished in behaviour by
this.

**`0020` is extended by one field, not reopened.** Its decision was that a tool's
*execution settings* travel inside the `Tool` because the right value belongs to
the system behind the tool. A warehouse query and a third-party search API do not
want the same tolerance for repeated failure any more than they want the same
timeout, and the answer is the same object. `0020`'s "`enbanc` supplies no default"
does not extend here: `enbanc` must supply an agent-level default because
PydanticAI supplies one either way, and 1 is the wrong one.

**Rejected: inherit PydanticAI's `1`.** Consistent with "`enbanc` retries nothing
of its own", and the smallest possible surface. It makes a *single* tool timeout
followed by a second one fatal, which contradicts `0020`'s "a timeout is not
fatal" and forces `outcomes.md` §1 to be rewritten so that a flaky search API ends
a proceeding. The consistency is superficial anyway: "retries nothing of its own"
is about HTTP-level retry, which `0009` gave to the caller's transport, not about
the budgets `0009` explicitly kept.

**Rejected: `tools: 2`.** The minimum that makes `outcomes.md` §1 reachable and
nothing more, on the argument that an advocate which cannot get a tool to answer
twice has genuinely lost that evidence. It was close. Three wins because the
example being *exactly* at the limit is a bad property for a specified behaviour —
one more retry in a worked example would silently change the outcome — and because
the cost of the third rung is bounded by the tool's own timeout, which `0020`
already makes the caller's to set.

**Rejected: a large `tools` budget, five or more.** A proceeding is minutes long
and expensive to lose, and a third-party API failing three times is ordinary.
Rejected because each attempt waits out the full timeout before failing, so a
genuinely dead tool costs `max_retries × timeout` of round latency with nothing to
show for it — and the caller who knows their API is flaky can now say so on the
`Tool`.

**Rejected: exposing `output` as well.** Symmetry with the `tools` half, and a
caller running a weaker model might reasonably want more attempts at a valid
citation. It is refused for `0009`'s stated reason: a caller who sets it to zero
turns a fabricated citation into a `ProceedingFailed` with no chance to correct,
and one who sets it high pays repeatedly for a model that cannot cite. Neither is
a knob whose good setting the library could document.

**Cost: a proceeding can now spend three timeouts' worth of latency per tool per
run before failing.** With an unbounded tool that is unbounded time, which is
`0020`'s accepted cost multiplied by three. The lever is unchanged and is named in
the same place: bound any tool that talks to something you do not control.

**Cost: two numbers that are `enbanc`'s and appear in no public type.** They are
in `../design/execution.md` and here, and nowhere a caller can read them from the
library. That is what `0009` chose; this ADR is the reason there is somewhere to
look them up.
