---
status: draft
updated: 2026-09-12
---

# The schemas

**The types everything else stands on.** The first code in the package: the
verdict base, the inputs, the five filings and their private emit-shapes, the
record, the result, and the error hierarchy — laid into the module map
[`packaging.md`](../design/packaging.md#the-modules) fixed before any of it was
written.

## Scope

`_verdicts.py`, `_inputs.py`, `_evidence.py`, `_filings.py`, `_transcript.py`,
`_hearing.py`, and `_errors.py`, plus the `__init__.py` that re-exports what
exists so far. Declarative work: models, generic aliases, and the constraints
that make an invalid record unrepresentable.

**Not in this PR.** `Transcript.render()` — its body is `_prompting.py`, which
lands in [`rendering.md`](./rendering.md). The method and the forced import
cycle arrive with it.

**`__all__` is partial here and stays partial until
[`proceeding-core.md`](./proceeding-core.md).** Four of the twenty-nine names —
`Tribunal`, `Judge`, `Advocate`, `Proceeding` — do not exist yet, so the
twenty-nine-name literal `tests/unit/test_export_surface.py` asserts cannot land
in this PR. The *module* can: "every name in `__all__` resolves" is assertable
over the twenty-five that exist, and it is the half that catches a typo in a
re-export the moment it is made. So the module lands here with that check and
[`proceeding-core.md`](./proceeding-core.md) adds the literal when the list
completes. `tests/unit/test_import_is_inert.py` needs only an importable
package and lands here whole.

## Implements

- [`api.md` § Schemas](../design/api.md#schemas) — every type in it, end to end
- [`api.md` § The judge's output](../design/api.md#the-judges-output) and
  [§ Where ids come from](../design/api.md#where-ids-come-from) — the public
  types and the private emit-pair beside them
- [`api.md` § A note on generic aliases](../design/api.md#a-note-on-generic-aliases)
  — `Filing`, `Deliberation`, and `Outcome` as `TypeAliasType`
- [`evidence.md` § A reference is what makes an exhibit auditable](../design/evidence.md#a-reference-is-what-makes-an-exhibit-auditable)
  — `Source`
- [`packaging.md` § The modules](../design/packaging.md#the-modules),
  [§ Where the errors live](../design/packaging.md#where-the-errors-live),
  [§ What `import enbanc` may do](../design/packaging.md#what-import-enbanc-may-do)

## Depends on

Nothing. This is the first PR.

## Files

**The order they land in is the order they import in.** Runtime imports run down
this list and never back up it
([`packaging.md`](../design/packaging.md#what-imports-what)); the one forced
cycle is `_prompting` ↔ `_transcript`, and neither end of it exists yet, so
every import in this PR is a plain one.

| Module | Public | Private | Imports from the package |
|---|---|---|---|
| `_verdicts.py` | `Verdict`, `VerdictT` | `JUDGE`, `Participant` | — |
| `_inputs.py` | `Statute`, `Case` | — | — |
| `_evidence.py` | `Source`, `Exhibit` | `_Exhibit` | — |
| `_filings.py` | `Argument`, `Concession`, `Interrogatory`, `Response`, `Ruling`, `Continuance`, `Filing`, `Deliberation` | `_Interrogatory`, `_Continuance` | `_verdicts`, `_evidence` |
| `_transcript.py` | `Entry`, `Retrieval`, `ToolFailure`, `Transcript` | — | `_verdicts`, `_inputs`, `_filings` |
| `_hearing.py` | `Undecided`, `Outcome`, `Hearing` | — | `_verdicts`, `_filings`, `_transcript` |
| `_errors.py` | `EnbancError`, `ConfigurationError`, `ProceedingFailed`, `ProceedingUnfinished` | — | `_verdicts`, `_transcript` |
| `__init__.py` | twenty-five of the twenty-nine | — | all seven |

Twenty-five public names: `_evidence` and `_inputs` are not generic and pull in
nothing, `_filings` is where `VerdictT` first reaches a model, and `_errors` sits
at the bottom because `ProceedingFailed` carries the record.

### `_verdicts.py`

```python
class Verdict(StrEnum): ...
VerdictT = TypeVar("VerdictT", bound=Verdict)
JUDGE: Final[Literal["judge"]] = "judge"
Participant = VerdictT | Literal["judge"]
```

`Verdict` declares no members, which is what makes it subclassable
([`0004`](../decisions/0004-verdicts-are-a-strenum.md)).

**`Participant` is a plain alias, not a `TypeAliasType`**, and that is not an
inconsistency with the three aliases below. The collapse
[`api.md`](../design/api.md#a-note-on-generic-aliases) describes happens because
Pydantic's `__class_getitem__` returns the origin class for a parameterized
generic *model*; a union of a bare `TypeVar` and a `Literal` contains no such
model, so `Participant[LoanDecision]` resolves to
`Union[LoanDecision, Literal['judge']]` and works as a Pydantic field annotation
unchanged. Verified on both 3.11 and 3.13.

The models below therefore spell their participant keys `Participant[VerdictT]`
rather than repeating `VerdictT | Literal["judge"]` at four sites. The rendered
annotation is identical to the one `api.md` writes inline — `api.md` spells it
out because the alias is private, not because the code may not use it.

`JUDGE` exists for the value comparisons `_errors.py` makes here and
`_tribunal.py` will make in [`tribunal-construction.md`](./tribunal-construction.md);
the annotations need `Literal["judge"]` regardless.

### `_inputs.py`

`Statute` frozen with `text` and an optional `name`; `Case` frozen, fieldless and
`extra="allow"` ([`0013`](../decisions/0013-a-case-is-a-subclassable-base.md)).
Neither is generic and neither imports anything.

### `_evidence.py`

`Source` (`reference`, `content`, optional `label`), the public `Exhibit` whose
four stamped fields the tribunal fills, and `_Exhibit` — `source` and `content`,
the only two an advocate writes
([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)). None of the
three is generic: an exhibit names no advocate, because the filing around it
already does.

### `_filings.py`

The five filings, `Interrogatory`, the judge's emit-pair, and two of the three
generic aliases:

```python
Deliberation = TypeAliasType(
    "Deliberation",
    Annotated[Ruling[VerdictT] | Continuance[VerdictT], Field(discriminator="kind")],
    type_params=(VerdictT,),
)
```

`Interrogatory.id` is required with no default; `_Interrogatory` has no `id`
field at all, which is what buys the public one that
([`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)).
`min_length=1` sits on `Continuance` *and* `_Continuance`, because they are
checked at different moments
([`0036`](../decisions/0036-a-continuance-carries-at-least-one-interrogatory.md)).

### `_transcript.py`

`Entry`, `Retrieval`, `ToolFailure`, and `Transcript` with `Filing` declared
here beside `Entry`'s use of it. `case` is `SerializeAsAny[Case]`, without which
a subclass's fields leave the artifact silently.

**Three dunders, and two consequences worth writing down.** `__iter__`, `__len__`
and `__getitem__` are [`api.md`](../design/api.md#the-record)'s, and overriding
`BaseModel.__iter__` means `dict(transcript)` raises where it used to yield
field pairs — `model_dump()` is the supported path and is untouched. `__len__`
also makes an entry-less transcript falsy, so `if e.transcript:` on a
`ProceedingFailed` from round 1 reads as "there is no record" when there is one.
That is what `__len__` means on a sized object and it is left alone; the code
says so where the method is defined.

**No `render()`.** The method and the `TYPE_CHECKING` cycle break are
[`rendering.md`](./rendering.md)'s, so nothing here imports `_prompting`.

### `_hearing.py`

`Undecided` — not generic, `reason` required and undefaulted — the `Outcome`
alias, and `Hearing`.

`usage` is a `computed_field` over `usage_by_participant` rather than a stored
field, which is [`api.md`](../design/api.md#per-participant)'s "the breakdown is
the stored fact; `usage` is its sum … there is no second place for the two to
disagree" made structural. It serializes, it appears in the `repr`
[`outcomes.md`](../design/outcomes.md#1-the-judge-rules) prints, and a persisted
hearing round-trips because the dumped key is ignored on the way back in.

This is the one place the implementation asks `api.md` for an edit, and it is
one line: the schema block's `usage: RunUsage` gains the note that it is
computed. `ProceedingFailed.usage` follows the same rule as a plain property.

### `_errors.py`

The base and its three subclasses. `ProceedingFailed` is
`Generic[VerdictT]`, takes its five values keyword-only, and **owns its own
message** — `outcomes.md` prints that text, so the class is the one place it can
be pinned:

```text
advocate 'deny' could not be heard in round 1
the judge could not be heard in round 2
```

The advocate form interpolates `str(participant)`, not the member: `repr()` of a
`StrEnum` member is `<LoanDecision.DENY: 'deny'>`, and leaking a Python
identifier into a message is the same defect
[`0004`](../decisions/0004-verdicts-are-a-strenum.md) rejects for the transcript.

`usage` is a plain property summing `usage_by_participant`, the same rule
`Hearing` follows. The class docstring carries the
[`packaging.md`](../design/packaging.md#where-the-errors-live) warning that
`except ProceedingFailed[LoanDecision]` is a runtime `TypeError`.

`ConfigurationError` and `ProceedingUnfinished` land here as bare subclasses.
Their raisers do not exist yet — `Tribunal(...)` is
[`tribunal-construction.md`](./tribunal-construction.md), `Proceeding.hearing` is
[`proceeding-core.md`](./proceeding-core.md) — and neither carries state.

### `__init__.py`

A module docstring, `from ._module import Name` for twenty-five names, and
`__all__`. No `as` aliasing: pyright treats `__all__` membership as the
re-export declaration. Nothing imports `enbanc.tools`, and nothing at module
level does anything but bind names
([`packaging.md`](../design/packaging.md#what-import-enbanc-may-do)).

### Deleted

`hello()`, and `tests/unit/test_placeholder.py` with it. The placeholder's second
job — proving the `pytest-asyncio` wiring before there was async code — has been
done by `tests/contract/test_output_validation_spends_the_output_budget.py`
since it landed, and that tier runs in `make test`. No async code arrives in
this PR.

### Nothing constrained that `api.md` does not constrain

Three invariants are tempting while writing these models and none of them is
added: `extra="forbid"` on the record types, `ge=1` on `Entry.round` and
`Retrieval.round`, and an aware `filed_at`. Each is real — a newer artifact
silently losing fields in an older reader is a genuine hazard, and a naive
timestamp in a persisted transcript is genuinely ambiguous — and each is a
change to the spec rather than to the code.

This PR is the first test of whether [`api.md`](../design/api.md) implements as
written, and that test is only worth running if it is run honestly. An invariant
worth having is worth arguing in the document that owns the surface and adding
on purpose, not acquiring as a side effect of the first module that could hold
it. The constraints that do land are the ones the design states: `min_length=1`
on both continuances, `Interrogatory.id` required with no default, the three
discriminated unions, and `Undecided.reason` undefaulted.

### Design documents

One line of [`api.md` § The result](../design/api.md#the-result), noting that
`Hearing.usage` is computed — `CLAUDE.md` rule 2, paid in this commit.

Nothing else. Every design document keeps `status: draft` and its *none of this
exists yet* banner: making the documentation stop lying is
[`zero-one-zero.md`](./zero-one-zero.md)'s scope, deliberately, and flipping
`api.md` while `Tribunal` is still absent would only replace one false statement
with another.

## Tests

All in `tests/unit/` — this is `enbanc`'s own behaviour, and every test here is
declarative. **Nothing in this PR needs a model**, faked or otherwise, so the
tier's socket guard has nothing to block and `TestModel` does not appear.

| Module | Pins |
|---|---|
| `test_export_surface.py` | that every name in `__all__` resolves, and that the list is sorted — the twenty-nine-name literal arrives with the last four names ([`proceeding-core.md`](./proceeding-core.md)) |
| `test_import_is_inert.py` | the three invariants in [`packaging.md`](../design/packaging.md#what-import-enbanc-may-do), in a subprocess that `import enbanc` and reads `sys.modules` |
| `test_verdicts.py` | `Verdict` is empty and subclassable; a member interpolates as its value, not as `LoanDecision.APPROVE`; `Participant[V]` admits a member and `"judge"` and nothing else |
| `test_inputs.py` | `Statute` frozen, `name` optional, `text` passed through whole; `Case` frozen, open, subclassable, and a subclass's fields surviving `model_dump` → base-`Case` validate |
| `test_evidence.py` | `Source`'s three fields and optional `label`; `Exhibit`'s five; `_Exhibit` holding only the two an advocate writes |
| `test_filings.py` | each `kind` defaulting and discriminating; `Interrogatory.id` required with no default against `_Interrogatory` having none; `Filing[V]` and `Deliberation[V]` validating every member back from JSON as the right class |
| `test_continuance_is_never_empty.py` | named by [`api.md`](../design/api.md#the-judges-output): `min_length=1` on both shapes, and `minItems: 1` reaching the model in the emitted JSON schema |
| `test_generic_aliases.py` | [`api.md`](../design/api.md#a-note-on-generic-aliases)'s note: `Argument[VerdictT] is Argument`, a plain alias collapsing so that `[V]` raises `TypeError`, and the `TypeAliasType` form not collapsing |
| `test_transcript.py` | the three dunders including a negative index; `SerializeAsAny` keeping a subclass case whole; `guidance` keyed by a member and by `"judge"`; a populated transcript round-tripping with enum members and real filing classes back; the `(advocate, id)` suppression join resolving over a hand-built ledger |
| `test_hearing.py` | both `Outcome` arms round-tripping; `usage` equal to the sum of the breakdown; `Undecided.reason` required; the outcome identical to the terminal filing in memory and merely equal through JSON ([`outcomes.md` § 7](../design/outcomes.md#7-persisting-a-hearing-and-reading-it-back)) |
| `test_errors.py` | the hierarchy catchable on `EnbancError`; `ProceedingFailed`'s five attributes, both message forms, its `usage`, `__cause__` surviving `raise … from`, and `except ProceedingFailed[V]` raising `TypeError` |

**`test_generic_aliases.py` is a unit test, not a contract one.** Its failure
would mean Pydantic moved, which reads like the contract tier's job — but that
tier is scoped to the eight `pydantic-ai` findings in
[`execution.md`](../design/execution.md#what-pydanticai-already-does)
([`0031`](../decisions/0031-tests-are-tiered.md)), and what this module actually
asserts is that `enbanc`'s own aliases parameterize. The collapse is asserted
beside it as the tripwire that explains why the code is written the way it is.

**The suppression join is asserted twice, on purpose, and differently.** Here it
is a claim about the schema — that `Exhibit.source` and `Retrieval.id` join on
`(advocate, id)` over a transcript built by hand. The claim that a *proceeding*
produces a transcript with exactly one buried source is
[`outcomes.md` § 1](../design/outcomes.md#1-the-judge-rules)'s, and lands with
the round loop.

**What is deliberately elsewhere.** `render()`'s output is
[`rendering.md`](./rendering.md)'s golden. The three `ConfigurationError`
*messages* are [`tribunal-construction.md`](./tribunal-construction.md)'s — the
class lands here, its raiser does not, and a message with no raiser is not
assertable.

## Open questions

*None open.* Three were settled before the code was written and each answer is
in the prose above: `Hearing.usage` is a
[`computed_field`](#_hearingpy) and `api.md` gains the line that says so,
`test_export_surface.py`'s [resolve check](#tests) lands now while its literal
waits for PR 7, and [nothing is constrained](#nothing-constrained-that-apimd-does-not-constrain)
that `api.md` does not constrain.
