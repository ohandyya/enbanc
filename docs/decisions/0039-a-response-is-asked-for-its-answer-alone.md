---
status: accepted
updated: 2026-10-10
---

# 0039. A response is asked for its answer alone

## Context

[`0015`](./0015-interrogatory-ids-are-stamped-on-filing.md) fixed that no
participant authors an id in either direction: the tribunal stamps
`Interrogatory.id`, and it fills `Response.answering` *from the dispatch rather
than from the model's output*, because it dispatches one advocate run per
interrogatory and so knows which question each run answers.
[`api.md`](../design/api.md#where-ids-come-from) states the consequence — *a
response citing a question nobody asked is not a state the library can reach.*

Neither document said how, and the question was deferred twice.
[`ledgering-toolset.md`](../implementations/ledgering-toolset.md) put
`advocate` and `answering` on the private `_Response` so the clerk's conversion
would be a field copy, and left *whether the orchestrator overwrites them from
the dispatch or omits them from the output schema* to
[`proceeding-core.md`](../implementations/proceeding-core.md) — which had no
round 2 and did not decide.

Left as it stood, it would have been neither. Handing `_Response[V]` to the
agent as its round-2 output type puts `answering` in the JSON schema as a
**required** field, and whatever the model writes there is what the record
keeps. Verified against `pydantic-ai 2.36.0`:

```text
sole output type _Response[LD]:
  tool:     final_result
  required: ['advocate', 'answering', 'answer']
  model wrote answering='WRONG'  ->  output.answering == 'WRONG'
```

So the unreachable state was reachable, and the round loop
([`round-loop.md`](../implementations/round-loop.md)) could not be built without
choosing.

## Decision

**An advocate's response is asked for `answer` and `exhibits`, and nothing
else.** Its round-2+ output type is an output function whose *parameters* are
those two fields; `advocate` and `answering` are filled from the dispatch inside
it, and the citation check runs on the response it builds:

```python
def respond(answer: str, exhibits: Sequence[_Exhibit] = ()) -> _Response[V]:
    response = _Response[V](advocate=verdict, answering=interrogatory.id,
                            answer=answer, exhibits=list(exhibits))
    check_citations(response)
    return response
```

PydanticAI shapes an output function's tool from its parameters, so this is the
whole schema the model sees — `final_result`, with `answer` required and
`exhibits` optional. It carries no docstring, for the reason
[`0038`](./0038-the-citation-check-rides-on-the-output-type.md) records: one
would reach the model as the tool's description.

Two properties of the dependency make this safe, and both are pinned in
`tests/contract/test_an_output_validator_forbids_a_run_output_type.py`: a
function of several parameters is offered as an object of exactly those
parameters, and a `ModelRetry` raised inside it spends the **`output`** budget
exactly as the single-parameter form's does — so a miscited response is
governed the same way a miscited argument is
([`0030`](./0030-the-retry-budgets.md)).

## Consequences

**The link is the tribunal's in the literal sense `api.md` claims.** The model is
never asked for `answering`, so it cannot get it wrong, and there is no
validation to run and no retry to spend on bookkeeping. `0015`'s *every
`answering` resolves, by construction rather than by validation* holds as
written.

**The advocate's own history holds nothing that contradicts the record.** What it
emitted — an answer and bare exhibit ids — is the fourth escape
[`execution.md`](../design/execution.md#what-lands-in-history-that-no-rendered-turn-contains)
already enumerates: a subset of what entered the record, never a different
version of it.

**Cost: the wire shape is a function signature, not `_Response`.** A field added
to `_Response` reaches the model only if it is also added to `respond`. That is
the *two shapes that must move together* cost `0015` already accepted for
`_Continuance`, paid at the same single seam in `_proceeding.py`.

**Cost: round 2 is no longer in step with round 1.** `_Argument` and the public
`Concession` still ask the model for `advocate`. That asymmetry is out of this
decision's scope — it concerns which verdict a filing is recorded under, not the
interrogatory link — and is noted in `round-loop.md` as a separate question.

**Rejected: ask for both and overwrite them.** Keep `_Response[V]` as the
function's parameter, and `model_copy(update={"advocate": verdict, "answering":
interrogatory.id})` before the check. The smallest change, and it keeps round 2's
wire in step with round 1's. It loses on what it leaves behind: a model that
writes `answering="r1-q1"` while answering `r1-q3` carries that wrong link in its
own conversation for every later round, while the record says otherwise. That
stretches the fourth escape from *a superset of the same fact* to *a
contradiction of it*, and asking a model for a value in order to discard it is
the move `0015` and [`0016`](./0016-exhibits-are-stamped-citations.md) were both
written against.
