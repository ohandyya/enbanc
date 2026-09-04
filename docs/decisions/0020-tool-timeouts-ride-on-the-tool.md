---
status: accepted
updated: 2026-09-04
---

# 0020. Tool execution settings ride on the tool

## Context

`../design/evidence.md` carried an open question: a tool that hangs stalls a
round with no bound. `max_rounds` does not help — it counts deliberations, and
the deliberation never happens because the round never closes. The only bound
today is whatever a caller built inside their own function.

The question was recorded with two errors, and correcting them is most of the
answer.

**It named `max_concurrency` as tool configuration.** It is not. PydanticAI's
docstring reads: *"Optional limit on concurrent **agent runs** […] additional
calls to `run()` or `iter()` will wait until a slot becomes available."* In
`enbanc` that governs advocate fan-out, which belongs to the cost-control
question in `../design/tribunal.md`, not to this one.

**It said [`0009`](./0009-model-settings-live-on-the-model.md) could not reach
the problem**, because PydanticAI puts `tool_timeout` on `Agent` rather than on
`Model`. That looked at the wrong object. `pydantic_ai.tools.Tool` takes a
`timeout` keyword, so the setting has a home on the thing it configures — which
is what `0009` is actually about.

## Decision

**A tool's execution settings travel inside the `Tool`, and `enbanc` adds
nothing.**

```python
from pydantic_ai import Tool

Advocate(tools=[Tool(dti_for, timeout=10.0)])
```

There is no `tool_timeout` on `Tribunal`, `Judge`, or `Advocate`, in `0.1.0` or
as a planned extension. `enbanc` passes no tool-execution setting of its own and
supplies no default, so what a caller configured is what runs.

**Wrapping is per-tool and opt-in.** A bare async function is still a tool. You
wrap the ones that talk to something you do not control.

**The concurrency half is not resolved here.** It is re-filed as a sharpening of
the cost-control question in `../design/tribunal.md`, per rule 7.

## Consequences

**This is [`0009`](./0009-model-settings-live-on-the-model.md) applied to a
second kind of object, not a new principle.** `0009` refused `settings=` on
`Tribunal`, `Judge`, and `Advocate` because `ModelSettings` had a good home on
an object the caller already constructs and injects. `Tool(timeout=)` is that
same home. Accepting `Advocate(tool_timeout=)` would be adding the parameter
`0009` rejected, under a different name.

**Rejected: `Advocate(tool_timeout=...)` as a pass-through.** It exists and it
works — `Agent(tool_timeout=)` applies to bare functions, so this would have
bounded the ergonomic path in one line. Rejected on the consistency above, and
because it puts a *tool* setting on an *agent* object, which is the coupling
`0009` spent an ADR removing. Recorded explicitly because it was available and
refused, not overlooked.

**Rejected: `Tribunal(tool_timeout=...)` inherited by advocates.** It would
mirror how `model` already flows from tribunal to agent. But `model` is
genuinely a proceeding-wide default that each agent may override, while a
sensible timeout is a property of the system behind one tool — a warehouse query
and an OCR pipeline do not want the same number. The inheritance would carry a
value that is rarely right anywhere.

**Rejected: a non-`None` library default.** A default of, say, 60 seconds would
close the hole unconditionally. It makes `enbanc` the arbiter of how long a
legitimate tool may take, and it will be wrong for somebody's slow warehouse
query — a proceeding failing because the library disagreed about latency is a
worse failure than one that hangs while the caller watches. It also contradicts
`0009` directly: `enbanc` passes none of its own at request time.

**Cost: the ergonomic path stays unbounded.** `Advocate(tools=[dti_for])` has no
timeout, and a hanging tool hangs the proceeding. This is accepted because it is
the position `enbanc` already holds one layer up — HTTP retry, backoff, and
timeout live on the httpx client inside the injected `Model`, and a model call
with no timeout hangs a round exactly the way a tool call does. Bounding tools
and not model calls would be arbitrary.

**What makes the cost tolerable: a timeout is not fatal.** PydanticAI cancels
the call and returns a retry prompt — `Timed out after 10.0 seconds.` — to the
model, counting against `Agent(retries=...)`. The advocate can narrow its query,
try another tool, or file what it has. Only an exhausted budget raises
`UnexpectedModelBehavior`, which `enbanc` surfaces as `ProceedingFailed`. The
failure ladder is timeout → the advocate adapts → retries spent → the proceeding
fails, and only the last rung ends anything. Verified against PydanticAI 2.36.

**Constraint on `web_search` and on any factory tool.** `Tool` derives the tool
name and description from the function's `__name__` and `__doc__`. A factory
returning `async def _inner(...)` would expose a tool called `_inner` to the
model. The returned closure must carry the intended name and a real docstring.

**Consequence: the invariant needed a qualifier.** A retry prompt is
library-authored text that enters an advocate's context and appears in no
filing. That is recorded in
[`0021`](./0021-retry-prompts-are-outside-the-invariant.md).
