---
status: draft
updated: 2026-09-20
---

# The ledgering toolset

**`execution.md`'s piece 2.** One `WrapperToolset` over one `CombinedToolset`,
intercepting every tool call an advocate makes, so that every source it saw is
recorded and every citation it files can be stamped.

## Scope

`_ledgering.py`: `Ledgering` with `call_tool` overridden, `as_sources`'s
shape-sniff, the "returned *N* sources" header line composed around
`_prompting.render_source` — already built in
[`rendering.md`](./rendering.md#one-three-line-source-shape-in-three-dressings),
which is where each source's own three-line shape lives — in
[`prompting.md`](../design/prompting.md#how-ledger-ids-reach-the-model)'s
format, the per-advocate id counter that survives the whole proceeding, and the
output validator that rejects an `_Exhibit` citing an id the ledger does not
hold.

A `ModelRetry` — which is what a `Tool` timeout becomes — is recorded on
`failures` and re-raised untouched. Anything else propagates: the difference
between a degraded advocate and an unheard one is that one `except` clause.

`_filings.py` gains `_Argument` and `_Response`, the advocate's emit-shapes, for
the reason [below](#the-validator-and-the-two-filings-it-validates): `_Exhibit`
has been in the package since [`schemas.md`](./schemas.md) and nothing carries
it, so the validator has nothing to validate until something does.

**Not in this PR.** Wiring the toolset into an agent, and setting `round` on it
before each dispatch. Both are the orchestrator's, in
[`proceeding-core.md`](./proceeding-core.md). This PR constructs and calls the
toolset directly, which is what
[`packaging.md`](../design/packaging.md#the-modules) means by the internals being
laid out because tests import them.

## Implements

- [`execution.md` § Piece 2 — the ledgering toolset](../design/execution.md#piece-2--the-ledgering-toolset)
- [`evidence.md` § How a source becomes an exhibit](../design/evidence.md#how-a-source-becomes-an-exhibit)
- [`evidence.md` § The ledger is part of the record](../design/evidence.md#the-ledger-is-part-of-the-record)
- [`evidence.md` § A call that returned nothing is recorded too](../design/evidence.md#a-call-that-returned-nothing-is-recorded-too)
- [`evidence.md` § An unresolvable id is a validation failure](../design/evidence.md#an-unresolvable-id-is-a-validation-failure)
- [`prompting.md` § How ledger ids reach the model](../design/prompting.md#how-ledger-ids-reach-the-model)
- [`api.md` § Where ids come from](../design/api.md#where-ids-come-from) — the
  advocate's half of it, which is the pair `_Exhibit` has been waiting for

## Depends on

[`schemas.md`](./schemas.md), [`rendering.md`](./rendering.md).

## Files

One new module, one pair of models added to an existing one, and three design
documents corrected. The module map
([`packaging.md`](../design/packaging.md#the-modules)) puts `_ledgering.py`
ninth, between `_errors.py` and `_tribunal.py`, so every import it makes runs
downhill.

| Module | Holds | Imports from the package |
|---|---|---|
| `_ledgering.py` | `Ledgering`, `as_sources`, `render_call`, `render_results` | `_verdicts`, `_evidence`, `_filings`, `_prompting`, `_transcript` |
| `_filings.py` | gains `_Argument` and `_Response` | unchanged |

**No new public names.** `Ledgering` is internal — nothing in
[`api.md`](../design/api.md) names it, a caller never constructs one, and the
twenty-nine-name `__all__` is untouched, so `tests/unit/test_export_surface.py`
does not move. `_Argument` and `_Response` carry the leading underscore for the
reason `_Exhibit` does: they sit beside a public counterpart and could be
mistaken for it.

### The wrapper is rebuilt for every run

The load-bearing fact about this module, and it is not guessable from the
design. [`0016`](../decisions/0016-exhibits-are-stamped-citations.md) ends on it
as a constraint — *"the ledger must be owned by the proceeding, not by the
wrapper toolset instance"* — and this PR is where it becomes code. Verified
against `pydantic-ai 2.36.0` by running it:

- `CombinedToolset.for_run` **always** returns `replace(self, toolsets=…)`. It
  has no identity guard, unlike its own `for_run_step`, which returns `self`
  when every child is unchanged.
- `WrapperToolset.for_run` therefore always sees a new `wrapped` and always
  returns `replace(self, wrapped=new_wrapped)`.
- `dataclasses.replace` **re-constructs the instance from its fields**. The
  copy's field values are the *original's*, read at run start.

So the `Ledgering` the orchestrator holds is not the one `call_tool` runs on.
Three rules follow, and all three are load-bearing:

1. **Every piece of state is a dataclass field.** A subclass that sets
   attributes in a hand-written `__init__` — which is how
   `tests/contract/test_intercepting_a_tool_call_is_one_method.py` writes its
   stand-in — loses them on the first `replace()`, because `replace()` calls
   `__init__` with the field values and nothing else. That stand-in survives
   only because it wraps a bare `FunctionToolset`, which returns `self` from
   `for_run`; wrap it in the `CombinedToolset` the design prescribes and it
   stops accumulating.
2. **State that has to accumulate lives in a mutable container, shared by
   reference.** `replace()` is shallow, so a `list` field is the *same list* in
   the copy. An `int` field is not: `self.next_id += 1` mutates the copy, the
   original never sees it, and the next run's copy starts from the stale value.
   A counter would silently renumber `s1` at the top of every round — the
   failure `0019`'s join key exists to make impossible.
3. **`round` is safe as a plain field because it flows one way.** The
   orchestrator sets it on the original *before* dispatch and `for_run` copies
   it into the run; nothing inside the run writes it back. That is exactly the
   *"mutable attribute is the seam between the two lifetimes"*
   [`execution.md`](../design/execution.md#what-call_tool-does) describes, and
   it is safe for the reason that section gives: an advocate's runs are
   sequential.

**Rejected: overriding `for_run` to return `self`.** It removes the problem in
one line and it is wrong. `WrapperToolset.for_run` exists to hand the *wrapped*
toolset its per-run preparation, and an MCP server is the thing that needs it —
so pinning identity would buy deterministic ids by breaking the toolsets
`evidence.md` promises work unchanged. PydanticAI documents the hook as *"return
a fresh instance for per-run state isolation"*; the shared list costs nothing and
does not fight it.

### The fields, and who owns the lists

```python
@dataclass(kw_only=True)
class Ledgering(WrapperToolset[None], Generic[VerdictT]):
    advocate: VerdictT
    ledger: list[Retrieval[VerdictT]]
    failures: list[ToolFailure[VerdictT]]
    round: int = 1
```

`wrapped` is inherited from `WrapperToolset` and stays positional; `kw_only=True`
governs only the fields declared here, which keeps `round`'s default legal after
three fields that have none. Deps are fixed at `None` because `Advocate` has no
`deps=` ([`0009`](../decisions/0009-model-settings-live-on-the-model.md)), and
`Generic[VerdictT]` is what makes `Retrieval[VerdictT]` and `ToolFailure[VerdictT]`
the rows this instance writes rather than rows of some other bench.

**The two lists are the transcript's own.** The orchestrator passes
`transcript.ledger` and `transcript.failures`, so a row is in the record the
instant it is written and a `ProceedingFailed` carries a ledger that is complete
as far as the proceeding got. That is `0016`'s ownership constraint satisfied
literally, and it is what makes rule 2 above work: the lists outlive every
`replace()` because the proceeding, not the toolset, is holding them.

**This does not go through the filing clerk, and does not need to.** The clerk
exists for [`0010`](../decisions/0010-streaming-yields-the-record.md)'s ordering
promise about `entries` — *the entry just received is the last entry* — and
nothing streams the ledger.
[`execution.md`](../design/execution.md#what-call_tool-does) already writes
`self.ledger.extend(rows)` inside `call_tool` for that reason. Concurrent
advocates appending to one list is safe because there is no `await` between the
count and the `extend` ([below](#ids-are-counted-out-of-the-ledger-not-into-a-counter)),
so no task interleaves between them.

**`round` defaults to `1`** so a test that never sets it gets round 1, which is
the round a toolset constructed and immediately used is in. The orchestrator
sets it explicitly from round 2 on.

### Ids are counted out of the ledger, not into a counter

```python
base = sum(1 for row in self.ledger if row.advocate == self.advocate)
rows = [
    Retrieval[VerdictT](id=f"s{base + n}", …)
    for n, source in enumerate(sources, start=1)
]
self.ledger.extend(rows)
```

Three things this shape is buying, each of which the obvious spelling gets wrong:

- **The count is derived, so there is no second state to go stale.** Rule 2
  above rules out a counter field. A `list[int]` box would survive, and it would
  be a second place that can disagree with the rows it is supposed to describe —
  the objection this library already makes to `cited` on a `Retrieval` and
  `position` on an `Argument`.
- **`base` is read once, before any row is built.** Calling a `next_id()` that
  counts the list inside the comprehension gives every source of a two-source
  call the same id, because nothing is appended until the `extend`. This is the
  one bug in this module that a single-source test cannot see.
- **The filter is `row.advocate == self.advocate`.** The list is transcript-wide
  and holds every advocate's rows, and ids are numbered *within* an advocate —
  so `APPROVE`'s `s1` and `DENY`'s `s1` are different retrievals, joined on
  `(advocate, id)` ([`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md)).
  Counting the whole list would number one bench-wide sequence and break the
  join's premise.

Nothing else writes rows for this advocate, so the count *is* the number of ids
issued, and it is exact rather than approximately right.

### `call_tool`, end to end

```python
async def call_tool(
    self,
    name: str,
    tool_args: dict[str, Any],
    ctx: RunContext[None],
    tool: ToolsetTool[None],
) -> Any:
    call = render_call(name, tool_args)
    try:
        result = await super().call_tool(name, tool_args, ctx, tool)
    except ModelRetry as e:
        self.failures.append(
            ToolFailure[VerdictT](
                round=self.round,
                advocate=self.advocate,
                tool=name,
                reference=call,
                detail=str(e),
            )
        )
        raise
    base = sum(1 for row in self.ledger if row.advocate == self.advocate)
    rows = [
        Retrieval[VerdictT](
            id=f"s{base + n}",
            round=self.round,
            advocate=self.advocate,
            tool=name,
            reference=source.reference,
            content=source.content,
            label=source.label,
        )
        for n, source in enumerate(as_sources(result, fallback_reference=call), start=1)
    ]
    self.ledger.extend(rows)
    return render_results(call, rows)
```

`call` is rendered before the `try`, because both arms need it: it is the failed
call's `reference` and it is the anonymous source's `reference` and the tool
result's header line. One string, three uses, and a reviewer reading a failure
beside a retrieval sees the same call spelled the same way.

**`except ModelRetry` and nothing wider.** A timeout arrives here as a
`ModelRetry` because `FunctionToolset.call_tool` converted it
(`tests/contract/test_intercepting_a_tool_call_is_one_method.py` pins that), and
a tool may also raise one deliberately — both are calls that returned nothing,
and both belong on `failures`. `detail` is `str(e)`, PydanticAI's own string
rather than one `enbanc` composes
([`0022`](../decisions/0022-tool-failures-are-recorded.md)). The re-raise is bare
`raise`, so the traceback and the instance are untouched and PydanticAI still
turns it into the `RetryPromptPart` the advocate is corrected by. Anything else
propagates: it ends the round and surfaces as `ProceedingFailed`, and the one
`except` clause is the whole distinction between a degraded advocate and an
unheard one.

**`get_tools` is not overridden.** The wrapper changes nothing about which tools
the model is offered or what their schemas say — only what comes back. That is
what makes the interception invisible to a tool author.

### `render_call`, and what a reference is made of

```python
def render_call(name: str, tool_args: dict[str, Any]) -> str:
    args = ", ".join(
        f"{key}={json.dumps(value, ensure_ascii=False, default=repr)}"
        for key, value in tool_args.items()
    )
    return f"{name}({args})"
```

Four decisions, and the worked example
[`evidence.md`](../design/evidence.md#how-a-source-becomes-an-exhibit) fixes —
`dti_for(applicant="A. Okonkwo")` — settles the first two:

- **`json.dumps`, not `repr`.** The spec spells a string argument in double
  quotes and an integer bare; `repr` gives `'A. Okonkwo'`, and a reference that
  does not match the format the design wrote down is a reference nobody can
  grep for.
- **`ensure_ascii=False`**, so a non-ASCII locator stays legible instead of
  becoming `é` in an audit artifact.
- **`default=repr`**, so a validated `datetime`, `Decimal` or model — which
  `json.dumps` cannot serialize — degrades to something readable instead of
  raising inside the ledger. A tool call must never fail because `enbanc` could
  not print it.
- **Insertion order, never sorted.** The order is the one PydanticAI handed over,
  and re-ordering it would make the reference say something the call did not.

No arguments renders as `slow()`, which is the shape a failure row takes for a
zero-argument tool.

**The arguments are the validated ones, so a defaulted parameter appears even
when the model omitted it.** Verified: a tool declared
`find_filings(applicant: str, year: int = 2024)` called by the model with
`applicant` alone reaches `call_tool` as `{"applicant": …, "year": 2024}` and
renders with both. That is the right side of the trade — the reference is then
the call as it actually ran, which is what *reproducible* means in
[`evidence.md`](../design/evidence.md#how-a-source-becomes-an-exhibit) — but it
is not what [`execution.md`](../design/execution.md#denys-history--three-runs-thirteen-messages)'s
worked trace shows, where the same tool renders with and without `year`
([below](#design-documents)).

**Rejected: stripping arguments that equal the tool's declared default.** It
would keep the trace as written and it would mean reading defaults back out of
`tool.tool_def.parameters_json_schema` — reaching into a dependency's schema to
make a reference prettier, and dropping a value the model *did* choose to send
whenever it happened to match. The reference is a locator, not a transcript of
the model's keystrokes.

### `as_sources` is the shape test

```python
def as_sources(result: Any, *, fallback_reference: str) -> list[Source]:
```

| What a tool returned | What is ledgered |
|---|---|
| a `Source` | that one source, as written |
| a sequence whose every item is a `Source` | those sources, in order, as written |
| an empty sequence | nothing — no row, no failure |
| anything else | one anonymous `Source(reference=fallback_reference, content=str(result))` |

- **`isinstance`, not duck typing.** `evidence.md` says *a `Source`, or a
  sequence of them*, and `Source` is a class the caller imports from `enbanc`. A
  subclass passes; an object that merely has `.reference` and `.content` does
  not, and is ledgered anonymously with its `str()` intact — nothing is lost,
  it just gets the coarser reference.
- **`str` and `bytes` are excluded from the sequence branch explicitly.** A
  string is a `Sequence`, and `all(isinstance(c, Source) for c in "")` is
  vacuously true, so the ordinary spelling ledgers `""` as zero sources.
- **A mixed sequence is anonymous as a whole.** Ledgering the `Source`s in it
  and dropping the rest would put half a tool result in the record under its own
  ids and the other half nowhere, which is the one thing
  [`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md) does not
  tolerate. All or nothing, and the anonymous branch keeps the whole value.
- **`str(result)`, not `repr` and not a JSON dump.** One rule for every
  non-`Source` return, so the sniff does not grow a ladder of prettifiers for
  dicts and models. A dict lands as `{'dti': 0.51}`. What a retrieval's content
  looks like is the tool author's lever
  ([`evidence.md`](../design/evidence.md#the-ledger-is-part-of-the-record)), not
  the renderer's.
- **An empty return produces no row and no failure**, which is the honest
  reading of both design sentences: *a tool that expects to come up empty
  returns an empty result*, and a `Retrieval` exists per source. The model is
  told `returned 0 sources.` and the record says the advocate called the tool
  only in the sense that nothing came of it — a gap named in `evidence.md` in
  this commit ([below](#design-documents)), because a tool author who wants the
  empty search *in* the ledger has a one-line move available: return a `Source`
  that says so.

### `render_results` — the tool-result format

```python
def render_results(call: str, rows: Sequence[Retrieval[Any]]) -> str:
```

The header line, a blank line, then one `render_source` block per row separated
by blank lines. `render_source` is
[`rendering.md`](./rendering.md#one-three-line-source-shape-in-three-dressings)'s,
called with a **bare** `id` and no `note` — the two things that distinguish a
tool result from a ledger row and an exhibit — and its output is used
unindented, at column 0.

```text
find_filings(applicant="A. Okonkwo") returned 2 sources.

[s1] Schedule C, 2024
  s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
  net profit: 182,000

[s2] W-2, 2024
  s3://underwriting-docs/okonkwo/w2-2024.pdf
  wages: 131,400
```

```text
dti_for(applicant="A. Okonkwo") returned 1 source.

[s3] dti_for(applicant="A. Okonkwo")
  dti: 0.51
```

**`source` is singular at one and plural everywhere else**, including zero —
`returned 0 sources.`, and with no rows to follow it that header is the entire
return value, one line with no trailing newline.

**The rows are rendered from the `Retrieval`s, never from the `Source`s.** They
hold the same values, and rendering the persisted row is what makes *what the
model read* and *what the record holds* the same bytes by construction rather
than by review — the same move
[`0026`](../decisions/0026-one-renderer-serves-both-audiences.md) makes one level
up.

**This text is `p1`.** [`prompting.md`](../design/prompting.md#procedure-versions)
scopes `PROCEDURE` to both procedural prompts, all four turn templates, **the
tool-result format**, and the render format, so this function is the last piece
of that surface to be written and it gets a golden like the rest
([below](#tests)). No bump is owed: the format is transcribed from
`prompting.md` as written, and nothing has stamped a transcript with `p1` yet.

### The validator, and the two filings it validates

`_filings.py` gains the advocate's emit-pair, beside the public shapes they
convert into, exactly as `_Interrogatory` and `_Continuance` sit beside theirs:

```python
class _Argument(BaseModel, Generic[VerdictT]):
    kind: Literal["argument"] = "argument"
    advocate: VerdictT
    claim: str
    exhibits: list[_Exhibit] = []

class _Response(BaseModel, Generic[VerdictT]):
    kind: Literal["response"] = "response"
    advocate: VerdictT
    answering: str
    answer: str
    exhibits: list[_Exhibit] = []
```

**They land here because this is the PR that needs them.**
[`api.md`](../design/api.md#where-ids-come-from) has said since
[`schemas.md`](./schemas.md) that *an advocate's output type carries a private
`_Exhibit`*, and `_Exhibit` has existed since then with nothing carrying it: the
public `Argument.exhibits` is `list[Exhibit]`, four of whose five fields only the
tribunal can fill. A validator over an output type that does not exist is a guess
about its own signature, so the type comes first.

`advocate` and `answering` are the tribunal's to fill at dispatch, not the
model's — [`api.md`](../design/api.md#where-ids-come-from) is explicit that
*neither end of that link is model-authored*. They are on the emit-shapes anyway
because the public filings carry them and the clerk's conversion is then a field
copy rather than a merge of two sources; whether the orchestrator overwrites them
from the dispatch or omits them from the output schema is
[`proceeding-core.md`](./proceeding-core.md)'s call, made where the agent is
built.

The validator itself is a method, because the ledger it resolves against is the
instance's:

```python
def check_citations(self, filing: _Argument[VerdictT] | _Response[VerdictT]) -> None:
    ...   # raises ModelRetry for an id this advocate was never issued
```

- **It is registered by [`proceeding-core.md`](./proceeding-core.md)**, as the
  agent's output validator, which is the wiring this PR does not do. It is called
  directly by this PR's tests.
- **It sees the rows the run just wrote**, because the validator closes over the
  orchestrator's `Ledgering` while `call_tool` ran on a `replace()` copy — and
  the two share the list. That is rule 2 [above](#the-wrapper-is-rebuilt-for-every-run)
  paying for itself a second time.
- **It spends the `output` budget**, because that is the budget an output
  validator spends
  ([`0030`](../decisions/0030-the-retry-budgets.md),
  `tests/contract/test_output_validation_spends_the_output_budget.py`). Nothing
  in this module names a number; `enbanc`'s `retries={'tools': 3, 'output': 2}`
  is set where agents are built.
- **A `Concession` is not validated**, because it carries no exhibits. The
  advocate's actual `output_type` per round is the orchestrator's.

The message names the id, says what is available, and uses the procedural
prompt's own vocabulary — *issued to you*, which the advocate has already read:

```text
[s7] was not issued to you. The ids you may cite are: s1, s2, s3.
```

Two cases worth their own words:

- **An empty ledger.** `The ids you may cite are: (none) — your tools have
  returned no sources.` A model told to pick from an empty list picks again;
  told there are none, it files without exhibits.
- **A qualified id**, one holding `/`. The advocate reads `[deny/s2]` in the
  rendered record and may copy it, and the procedural prompt already warns that
  *those are not yours to cite*. The message says which half went wrong rather
  than listing ids that all look different from what it wrote.

**Not covered by `p1`.** A retry prompt is outside the invariant
([`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md)) and is
not in `prompting.md`'s list of what `PROCEDURE` versions, so this text may be
improved without a bump. It is still pinned by a test, because it is text a model
acts on.

### What this PR does not construct

```python
Ledgering(
    wrapped=CombinedToolset([
        FunctionToolset(tools=advocate.tools),
        *advocate.toolsets,
    ]),
    …
)
```

That is [`execution.md`](../design/execution.md#one-wrapper-over-one-combined-toolset)'s
construction and it belongs to the orchestrator, which is the only thing holding
an `Advocate` and a transcript at the same time. **No factory is added here** —
it would have no caller in this PR and would be a guess about its own signature,
the same reason [`tribunal-construction.md`](./tribunal-construction.md) left the
guidance mapping alone. The tests build the toolset inline, in exactly the shape
above, so the shape is exercised even though the wiring is not written.

**No new lint ignores.** The goldens in this PR are tool results, whose longest
line is a reference at well under 100 columns, and the snapshot comparisons are
calls rather than upper-case constants, so neither `E501` nor `SIM300` is
implicated.

### Design documents

Five edits, all of them `CLAUDE.md` rule 2 paid in this commit.

[`execution.md` § What PydanticAI already does](../design/execution.md#what-pydanticai-already-does)
gains a twelfth finding, **A wrapper toolset is rebuilt for every run**, with the
`CombinedToolset.for_run` / `replace()` chain and the three rules it forces. The
count in that section's prose and
[`testing.md`](../design/testing.md#the-four-tiers) — *"records eleven findings"*,
*"Two of the eleven findings are derivations"* — moves to twelve, and
`testing.md`'s findings table gains the matching row.

[`execution.md` § What `call_tool` does](../design/execution.md#what-call_tool-does)
— the sketch's `self.next_id()` becomes the derived count, because a counter is
the one spelling the finding above rules out, and a design document that shows it
is a document that will be copied.

[`execution.md` § `DENY`'s history](../design/execution.md#denys-history--three-runs-thirteen-messages)
— `find_filings(applicant="A. Okonkwo", year=2024)` loses its `year`, in the
`ToolCallPart` and in the rendered result under it. With validated arguments a
defaulted parameter is present in every call or in none, so one tool cannot
render both ways in one proceeding; the worked trace showed it doing exactly
that. What the two lines were illustrating — that `DENY` narrowed its query — is
carried by the round-2 call existing at all.

[`execution.md` § The proceeding, as messages](../design/execution.md#the-proceeding-as-messages)
— five lines in the worked traces gain a second underscore:
`final_result_ArgumentLoanDecision` becomes `final_result__ArgumentLoanDecision`
and `final_result_ResponseLoanDecision` becomes
`final_result__ResponseLoanDecision`, because PydanticAI derives an output tool's
name from the class and the advocate now emits `_Argument` and `_Response`. That
is the judge's `final_result__ContinuanceLoanDecision` reproduced one advocate
down, for the same reason. `ConcessionLoanDecision` and `RulingLoanDecision` do
not move — those two filings are emitted public — and neither does the probe
example in
[§ A filing lands in history as a tool call](../design/execution.md#a-filing-lands-in-history-as-a-tool-call),
which is the contract test's own classes. No `PROCEDURE` bump: that section says
outright that the tool names are PydanticAI's and are not covered by
`Transcript.procedure`.

[`evidence.md` § A call that returned nothing is recorded too](../design/evidence.md#a-call-that-returned-nothing-is-recorded-too)
— one paragraph on the empty return: a tool that comes up empty produces no
`Retrieval` and no `ToolFailure`, because it neither found anything nor failed,
and a tool author who wants that fact in the record returns a `Source` saying so.
The section already covers the failed call; the successful-but-empty one fell
between it and the ledger.

**No `PROCEDURE` bump.** `p1` stands, for the reason
[above](#render_results--the-tool-result-format).

Every design document keeps `status: draft` and its *none of this exists yet*
banner; making the documentation stop lying is
[`zero-one-zero.md`](./zero-one-zero.md)'s scope.

## Tests

All in `tests/unit/` except one, which is the point of the tier split: the
claim about `enbanc` goes to `unit`, and the claim about `pydantic-ai` goes to
`contract` so that a version bump reports as a moved dependency rather than as a
broken library.

| Module | Tier | Pins |
|---|---|---|
| `test_ledgering.py` | unit | the toolset driven through a real `Agent`: ids monotonic within a run and across rounds; `round` stamped from the attribute the orchestrator sets; two advocates numbering independently over one shared list; a `ModelRetry` recorded and re-raised; a tool that raises anything else propagating with no row and no failure written; the rewritten result reaching the model as the `ToolReturnPart` |
| `test_as_sources.py` | unit | the four-row table [above](#as_sources-is-the-shape-test), parameterized: a `Source`, a list, a tuple, a subclass, an empty list, a `str`, a `dict`, a `BaseModel`, `None`, and a mixed list |
| `test_tool_results.py` | unit | the tool-result format as `inline-snapshot` goldens with `PROCEDURE == "p1"` asserted: two labelled sources, one anonymous source, and the zero-source header; `render_call` over a string, an int, a bool, a non-ASCII value, and no arguments at all |
| `test_citation_validation.py` | unit | an unissued id raising `ModelRetry`; an issued one passing; another advocate's id rejected although the row is in the same list; the empty-ledger message; the qualified-id message; a `Concession`-shaped filing needing no validation |
| `test_filings.py` | unit | gains `_Argument` and `_Response`: `exhibits` typed `list[_Exhibit]` against the public pair's `list[Exhibit]`, and the `kind` tags matching their public counterparts |
| `test_a_wrapper_toolset_is_rebuilt_per_run.py` | contract | the finding: `CombinedToolset.for_run` returning a new object unconditionally; a `WrapperToolset` over one being `replace()`d per run; a scalar field's mutation not reaching the original; a list field's doing so; a field written on the original between runs reaching the next run's copy |

### Every test drives a real `Agent`

Calling `ledgering.call_tool(...)` directly is the obvious way to test this
module and it would pass on an implementation that is broken in the one way that
matters. `replace()` happens inside `Agent.run`, so a direct call runs on the
original instance, where a counter field and a shared list behave identically.
The id-continuity tests therefore go through `Agent(…, toolsets=[ledgering])`
with a scripted `FunctionModel` — the shape
`tests/contract/test_intercepting_a_tool_call_is_one_method.py` already uses,
including its finite-by-construction note: a `FunctionModel` that calls
unconditionally runs into PydanticAI's inherited `request_limit` of fifty and
reports `UsageLimitExceeded`, which names the wrong subsystem entirely.

**The `CombinedToolset` is not optional in those tests.** Wrapping a bare
`FunctionToolset` skips the `replace()` path, and a test written that way is
green against every implementation this module could have had.

Nothing here needs a provider: `FunctionModel`, an async function, and
`Tool(fn, timeout=…)` for the timeout case, all offline, all inside the tier's
socket guard.

### The fixtures are the worked proceeding's

`tests/unit/conftest.py` already holds `deny` and the eight-entry `proceeding`
whose ledger carries `approve/s1`, `approve/s2`, the anonymous `approve/s3`, and
`deny`'s two — the rows this module produces, hand-written
([`rendering.md`](./rendering.md#the-fixture-is-the-worked-proceeding-and-it-is-shared)).
The goldens here render the same sources, so a tool result and the ledger row it
became are the same bytes in two test modules, and
[`prompting.md`](../design/prompting.md#how-ledger-ids-reach-the-model)'s two
worked examples are reproduced rather than paraphrased.

No new fixture is added. What this module needs beyond those is a tool, a model
that calls it, and a list — all local to the test that wants them.

### What is deliberately not asserted

**That the advocate's agent is built with this toolset.** There is no agent
until [`proceeding-core.md`](./proceeding-core.md), and the construction snippet
[above](#what-this-pr-does-not-construct) is that PR's to make true.

**That `Transcript.ledger` ends up holding what a proceeding retrieved.** This
PR writes into a list the caller owns; that the list is the transcript's, and
that `outcomes.md` § 1's suppression join finds exactly one buried source, is
the round loop's claim and lands with it.

**That an exhausted `output` budget raises `ProceedingFailed`.** The validator
raises `ModelRetry` and the budget is PydanticAI's;
`tests/contract/test_output_validation_spends_the_output_budget.py` already pins
which budget that spends, and the `ProceedingFailed` at the end of it needs a
proceeding.

**That a reference resolves.** `reference` is opaque to `enbanc`
([`0007`](../decisions/0007-a-statute-is-opaque-text.md) applied one level down):
the tests assert the string that was recorded, never that it points anywhere.

## Open questions

*None open.* Three were settled while the module was written, and each answer is
in the prose above with the reasoning that chose it: state lives in
[shared mutable containers](#the-wrapper-is-rebuilt-for-every-run) because the
wrapper is rebuilt per run, a reference renders the
[validated arguments](#render_call-and-what-a-reference-is-made-of) including
defaults, and an [empty return](#as_sources-is-the-shape-test) is zero rows
rather than one anonymous row. The last two are edits to `execution.md` and
`evidence.md` in this commit rather than facts that live only here.
