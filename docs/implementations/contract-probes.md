---
status: draft
updated: 2026-09-13
---

# The contract probes

**The `pydantic-ai` findings `execution.md` rests on, turned from scratch files
into tests.** Seven of the nine probes behind
[what PydanticAI already does](../design/execution.md#what-pydanticai-already-does)
are still throwaway scripts, so a version bump falsifies that document silently.

## Scope

`tests/contract/`, and the design corrections the probes force. This tier is not
about `enbanc` at all
([`testing.md` § The four tiers](../design/testing.md#the-four-tiers)), and a red
test here means the dependency moved.

`execution.md` carries **eleven** findings. Two are derivations rather than probes
and get no module: *Three channels reach a model* summarizes the two above it,
and *What lands in history* is the whitelist the invariant helper encodes, tested
in [`proceeding-core.md`](./proceeding-core.md). Two of the remaining nine are
already pinned — `max_concurrency` at construction, and a failing output schema
spending the `output` budget — so **seven** remain.

**The corrections are in scope because the tier's purpose is to make them.**
[`testing.md`](../design/testing.md#the-four-tiers) says a red contract test
"means the dependency moved, not that `enbanc` broke, and the fix is usually to
change a design document rather than to change code." Writing these seven found
the prose wrong on the first run rather than after a bump, which is the same
finding arriving earlier. Deferring it would leave `execution.md` stating
something the suite next to it contradicts, with nothing saying which wins —
the state [`CLAUDE.md`](../../CLAUDE.md) rule 3 exists to prevent. They are
listed under [Design documents](#design-documents) and they are small.

**Not in this PR.** Anything that imports `enbanc`.

## Implements

- [`execution.md` § What PydanticAI already does](../design/execution.md#what-pydanticai-already-does)
  — the seven unpinned findings
- [`testing.md` § The four tiers](../design/testing.md#the-four-tiers) — the
  finding-to-assertion table is the checklist for this PR, once the row it is
  missing is added to it

## Depends on

Nothing. Independent of every other PR in the plan, and mergeable at any point.

## Files

Seven modules, each named for the finding it pins, as
`test_max_concurrency_is_set_at_construction.py` and
`test_output_validation_spends_the_output_budget.py` already are. No fixture and
no `conftest.py` change: the socket guard is autouse in
`tests/contract/conftest.py` and nothing here wants the network.

| Module | `execution.md` finding |
|---|---|
| `test_a_conversation_is_a_parameter.py` | [Carrying a conversation is a parameter, not a subsystem](../design/execution.md#carrying-a-conversation-is-a-parameter-not-a-subsystem) |
| `test_instructions_are_re_resolved.py` | [Instructions are re-resolved every run and never enter history](../design/execution.md#instructions-are-re-resolved-every-run-and-never-enter-history) |
| `test_a_filing_lands_as_a_tool_call.py` | [A filing lands in history as a tool call, not as text](../design/execution.md#a-filing-lands-in-history-as-a-tool-call-not-as-text) |
| `test_intercepting_a_tool_call_is_one_method.py` | [Intercepting a tool call is one method](../design/execution.md#intercepting-a-tool-call-is-one-method) |
| `test_usage_accumulates_into_the_callers_object.py` | [Usage accumulates into an object the caller owns](../design/execution.md#usage-accumulates-into-an-object-the-caller-owns) |
| `test_two_retry_budgets.py` | [Two retry budgets, not one](../design/execution.md#two-retry-budgets-not-one) |
| `test_a_failing_fan_out_need_not_raise_a_group.py` | [A failing fan-out need not raise an `ExceptionGroup`](../design/execution.md#a-failing-fan-out-need-not-raise-an-exceptiongroup) |

**Every module carries the tier's standing sentence** in its docstring, the one
the two existing modules already carry: *if this fails after a `pydantic-ai`
bump, the dependency moved and `execution.md` is now wrong — fix the document,
then decide whether the design it forced still makes sense.* It is the sentence
that makes a red test here readable by someone who has never seen this tier.

### Design documents

Three corrections, paid in this commit under
[`CLAUDE.md`](../../CLAUDE.md) rule 2.

**[`execution.md`](../design/execution.md) — the fan-out re-raise.** Two
paragraphs, in the finding and in *Piece 3 — the round's task group*, both
saying the same wrong thing: that without the cancelled-exception re-raise,
`REFER`'s cancellation "is caught and recorded as the failure", or that a
cancelled sibling "may win the race to fill `first`". It cannot. The failing task
assigns `first` **before** it calls `tg.cancel_scope.cancel()`, with no `await`
between the two statements, so there is no point at which a sibling runs in
between. Both variants of the doc's own scenario behave identically. What the
re-raise actually protects is named [below](#test_a_failing_fan_out_need_not_raise_a_grouppy);
the conclusion the document draws is untouched, only the scenario it draws it
from.

**[`testing.md`](../design/testing.md) — the checklist table.** It has eight
rows and eleven findings behind it. The row for *A failing output schema spends
the `output` budget* is missing: that finding was added to `execution.md` after
the table was written, together with the test that pins it. The table gains the
row — *Attempts track `output` alone; the constraint reaches the model as
`minItems`* — and "records ten findings" becomes eleven. An incomplete checklist
is the one thing a checklist may not be, and this document calls that table the
checklist for this PR.

**This document's own arithmetic**, corrected above: six of eight of ten became
seven of nine of eleven.

**[`0031`](../decisions/0031-tests-are-tiered.md) also says "ten findings" and
stays as written.** An ADR is immutable and dated — a record of what was true
when the decision was made, not current truth
([`CLAUDE.md`](../../CLAUDE.md) rule 4's principle, one document over). Nothing
it decides changes.

## Tests

The files above are the tests; this section is what each one asserts and why the
assertion discriminates. Every claim below was reproduced against the installed
**`pydantic-ai 2.36.0`** before this document was written.

### `test_a_conversation_is_a_parameter.py`

That `message_history` and `all_messages()` round-trip, which is the whole of the
dict in [History is a dict, written after each run](../design/execution.md#history-is-a-dict-written-after-each-run).

- `run(message_history=None)` is the first-run form and is what round 1 passes.
- Run 2 given run 1's `all_messages()` returns a history whose **prefix is run 1's
  messages unchanged**, with run 2's request appended. Asserted as a prefix rather
  than by length: a length is satisfied by a history that rewrote its own past.
- `message_history` is a parameter of `Agent.run`, not of `Agent.__init__` — the
  mirror image of the `max_concurrency` finding, and the reason a conversation is
  per-call state rather than agent state.

### `test_instructions_are_re_resolved.py`

Two claims, and the second is the one `prompting.md` spends money on.

**Re-resolved, not frozen.** An agent built with a callable `instructions` that
returns `"FIRST"` and then `"SECOND"` is run twice, the second time with the
first run's history:

```text
info.instructions per request: ['FIRST', 'SECOND']
```

`AgentInfo` gained `instructions` and `model_request_parameters` fields, so a
`FunctionModel` reads the *effective* instructions for a request directly. That
is a sharper probe than `execution.md`'s wire capture, which shows two identical
strings and so cannot distinguish re-resolution from freezing.

**Never in `parts`.** No `InstructionPart` appears anywhere in
`result.all_messages()` parts, in either run. **The looser reading of "never
enter history" is worth stating precisely, because a later PR depends on it:**
instructions *are* in history, on the `ModelRequest.instructions` attribute, and
each historical request keeps the string it was sent with. What never enters is a
part. What actually reaches the provider is
`model_request_parameters.instruction_parts`, resolved fresh for each request —
which is why one changed instruction governs the whole conversation even though
the stored records disagree. It is also why `assert_invariant_held`
([`proceeding-core.md`](./proceeding-core.md)) can walk message parts and never
see an instruction: the instructions channel is accounted for separately, through
`tribunal.instructions_for(participant)`, exactly as
[`testing.md`](../design/testing.md#the-transcript-invariant) says.

**The Anthropic hoisting**, the finding's second bullet, pinned here beside it:

```python
model = AnthropicModel("claude-sonnet-4-5", provider=AnthropicProvider(api_key="not-a-real-key"))
system, messages = await model._map_message(msgs, ModelRequestParameters(), {})
# system:     [{'type': 'text', 'text': 'PROCEDURAL\n\nSTATUTE'}]   <- once
# messages:   3                                                     <- not re-emitted per request
```

Given a three-message history whose two requests carry identical instructions,
the instructions appear **once** in the top-level `system` parameter and in none
of the three mapped messages. That is
[`prompting.md`](../design/prompting.md#how-an-agent-is-assembled)'s
shared-cache-prefix claim, which is currently true on the strength of a source
comment nothing checks — and a proceeding's whole cost story rests on it.

Two fragilities, both deliberate: it imports `anthropic`, which arrives
transitively rather than by declaration, and it calls the private `_map_message`.
Either breaking is the tier reporting that the dependency moved, which is the
tier's job. The docstring says so, so the next reader does not "fix" it by
deleting it. No network: constructing a provider with a fake key opens no
connection, and the socket guard is satisfied.

### `test_a_filing_lands_as_a_tool_call.py`

That there is no `TextPart` on the path an `enbanc` participant takes.

- A union `output_type` yields **one output tool per member**, named
  `final_result_<ClassName>` — asserted as the exact names, because the finding's
  point is that renaming a filing class silently changes a string the model reads.
- The filing arrives as a `ToolCallPart` carrying the model's arguments, followed
  by `ToolReturnPart('Final result processed.')`. The receipt string is asserted
  verbatim: [`testing.md`](../design/testing.md#the-transcript-invariant)'s escape
  3 whitelists that exact text, so the invariant helper is wrong the moment it
  changes.
- `all_messages()` contains **no `TextPart`** anywhere.

### `test_intercepting_a_tool_call_is_one_method.py`

The three facts [`evidence.md`](../design/evidence.md#how-a-source-becomes-an-exhibit)
needs, pinned against a `WrapperToolset` subclass standing in for `Ledgering`.

- **The return becomes the `ToolReturnPart` content verbatim.** A wrapper that
  returns `f"REWRITTEN<{result}>"` produces a `ToolReturnPart` whose content is
  exactly that string. This is the finding that makes the ledgering toolset a
  rewrite rather than a decoration.
- **`call_tool` receives the name, the validated arguments, the `RunContext` and
  the resolved tool** — asserted on the four-parameter signature and on what the
  wrapper actually observed.
- **A `Tool`'s timeout surfaces inside the wrapper as `ModelRetry`.**
  `FunctionToolset.call_tool` applies `anyio.fail_after` and converts
  `TimeoutError` into `ModelRetry('Timed out after N seconds.')` itself, with the
  per-tool timeout taking precedence over the toolset's. The wrapper catches it,
  can record it, and re-raises it unchanged. That one `except` clause is the seam
  between a degraded advocate and an unheard one
  ([`0022`](../decisions/0022-tool-failures-are-recorded.md)), and the
  `detail` it stores is PydanticAI's own string.
- **`FunctionToolset(tools=…)` takes bare functions and `Tool` instances alike**,
  so [`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md)'s
  `Tool(fn, timeout=…)` needs no separate path — asserted by registering one of
  each and calling both.

### `test_usage_accumulates_into_the_callers_object.py`

- `run(usage=u)` **mutates `u` in place** across two runs: requests and input
  tokens accumulate rather than reset.
- `result.usage is u` — identity, not equality. It is a property, not a method.
- **A run that dies mid-flight leaves its partial spend.** A tool that raises
  drives the run to `UnexpectedModelBehavior`, and `u` still holds what was spent
  getting there. This is the half that matters: it is what lets
  `usage_by_participant` name every participant that was dispatched even on a
  failure ([`0028`](../decisions/0028-usage-accumulates-per-participant.md)), and
  it is why [`api.md`](../design/api.md#when-something-goes-wrong) can say what it
  says.

**The failure case asserts `>=` and non-zero, never an exact count.**
[`testing.md`](../design/testing.md#what-must-not-be-asserted) forbids exact usage
after a failure, and the rule applies to the probe that establishes the mechanic
as much as to the tests that rely on it. The claim under test is *the partial
spend survives*, not *the partial spend is 400 tokens*.

### `test_two_retry_budgets.py`

Four facts, each with a case built so that consulting the wrong budget gives a
different answer — the same construction the existing output-budget module uses.

| Asserted | How it discriminates |
|---|---|
| Both budgets default to `1` | `retries=None` and two tool timeouts raises *Tool 's' exceeded max retries count of 1* |
| `tools` and `output` are independent | a `tools` budget fully spent by a timeout leaves the `output` retries intact |
| Tool retries key on **tool name** | `alpha` failing once and `beta` failing once both succeed under `retries=1`; a per-run budget would have been spent by `alpha` |
| `Tool(max_retries=…)` overrides | `alpha` failing twice fails under `retries=1` and passes under `Tool(alpha, max_retries=3)` |

**Every case scripts a finite sequence of model responses.** A `FunctionModel`
that calls the tool unconditionally never terminates, hits PydanticAI's inherited
`request_limit` of fifty, and reports `UsageLimitExceeded` — a green-looking
failure that says nothing about retries. Each case emits its tool calls from an
iterator and falls through to a final text response when the iterator is spent.
It is written down because the symptom names the wrong subsystem: the error says
`usage_limits`, and nothing in it suggests the model script is the problem.

The per-tool-name fact is what makes
[`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md)'s "reach for another
tool" a real move, and the override is what
[`execution.md` § Also in scope](../design/execution.md#also-in-scope) hands to
the caller while keeping the `output` budget unreachable.

### `test_a_failing_fan_out_need_not_raise_a_group.py`

Three things, and the third is the reason the module is worth having.

- **The naive shape raises.** An `anyio` task group whose child raises propagates
  an `ExceptionGroup` — the baseline that would put `enbanc` in the position of
  picking one failure out of a set, which
  [`0012`](../decisions/0012-a-failure-cancels-the-round.md) closed by keeping
  `participant` singular.
- **The record-and-cancel shape does not.** A child that records its own failure
  into a single slot and cancels the scope lets the group exit cleanly, with one
  named failure and the peers' partial work intact —
  [`outcomes.md`](../design/outcomes.md#an-advocates-provider-is-down) reproduced.
- **The re-raise, on external cancellation.** This is the correction. Under a
  child failure the re-raise changes nothing, because the failing task fills the
  slot before it cancels:

```text
a child fails (execution.md's scenario):
  reraise=True   clean; first=deny (RuntimeError)    <- correct
  reraise=False  clean; first=deny (RuntimeError)    <- also correct

the proceeding is cancelled from outside (nothing failed):
  reraise=True   clean; first=None                   <- correct
  reraise=False  clean; first=refer ('CANCELLED')    <- names a participant merely stopped
```

Written to the doc's scenario the assertion passes with and without the re-raise,
which is a test that cannot fail. Written to an **outer cancel scope firing while
every child is healthy** it fails the moment the re-raise is dropped, and the
failure is exactly the defect: the first advocate to notice it was cancelled
records *itself* as the failure, and `ProceedingFailed` names a participant that
was merely stopped. That is a live hazard rather than a hypothetical — a caller
cancelling `hear()`, or a timeout around a proceeding, reaches it.

The module asserts the discriminating case, and
[`execution.md`](../design/execution.md) gains the paragraph that describes it.

## Open questions

*None open.* Two were settled before the modules were written and both answers
are in the prose above. The design corrections the probes force
[land in this PR](#design-documents) rather than in a follow-up, because leaving
`execution.md` contradicted by the suite beside it is the state rule 3 forbids.
The Anthropic hoisting is [pinned](#test_instructions_are_re_resolvedpy) inside
the instructions module rather than in one of its own, because it is that
finding's second bullet and the tier's modules map one-to-one onto `execution.md`
headings.
