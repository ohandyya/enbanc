---
status: accepted
updated: 2026-09-02
---

# 0013. A case is a subclassable base, not a type parameter

## Context

`Case` appeared in every example in [`../design/api.md`](../design/api.md) and
[`../design/outcomes.md`](../design/outcomes.md) — `Case(applicant=...,
income=182000)` — and in the signature of both `hear()` and `Transcript`, but
the `## Schemas` section that spells out every other public type never defined
it. The examples were constructing something with no shape.

Two things made that more than a gap in the documentation.

**It is a field of the audit artifact.** `Transcript.case` sits beside the
question and the statute in the record that
[`0006`](./0006-the-transcript-schema.md) requires to be self-contained. Whatever
`Case` is has to serialize completely and survive being read back, or the
artifact quietly loses the facts it claims to have adjudicated.

**It sits inside generics.** Everything in the library is keyed on the verdict
enum. If the case's type must flow the same way, `Transcript`, `Hearing`,
`Proceeding`, and `ProceedingFailed` each gain a second type parameter — on top
of the `TypeAliasType` plumbing that generic aliases already force on this
codebase, and with no natural place to bind it, since a `Tribunal` is
constructed before any case exists.

## Decision

**`Case` is a `BaseModel` base class with no fields, `frozen=True` and
`extra="allow"`.** Users subclass it to give their facts a schema:

```python
class LoanApplication(Case):
    applicant: str
    income: int
    dti: float
```

and the open base stays directly constructible for one-offs.

**Nothing gains a type parameter.** `Transcript.case` is annotated `Case`, and
`hear()` takes a `Case`. A caller wanting its own type back out of a persisted
transcript writes `LoanApplication.model_validate(t.case.model_dump())`.

**`Transcript.case` is `SerializeAsAny[Case]`.** Pydantic v2 serializes by the
declared type, so without it a subclass's fields never reach the JSON.

## Consequences

**Rejected: generic in the case type.** Either `Case[FactsT]` wrapping a
payload, or dropping the class entirely and typing `case: CaseT` bound to
`BaseModel`. It is the option with the real argument behind it — the case comes
back precisely typed — and it loses on where that type is actually worth
anything.

`enbanc` reads no field of a case; it renders it into the prompt and records it.
So the type buys nothing inside the library, and at the call site nothing either,
because the caller is holding the object it just passed to `hear()`. The single
place it would pay is reading a transcript back from JSON — and there it does not
save the caller from naming the concrete class:
`Transcript[LoanDecision, LoanApplication].model_validate_json(...)` and
`LoanApplication.model_validate(t.case.model_dump())` demand the same knowledge
in the same one place. Paying a second parameter on four public types, and a
second axis of alias machinery, to relocate that one mention is a bad trade.

It has no clean binding site either. A tribunal is built before any case exists,
so `CaseT` could only be a method-level variable on `hear()` — a parameter that
appears on the way out (`Hearing[LoanDecision, LoanApplication]`) which no
constructor ever mentions.

**Rejected: an opaque `text: str`,** the strict analogue of
[`0007`](./0007-a-statute-is-opaque-text.md). The symmetry is superficial and the
two are not alike. A statute is a document a human already wrote as prose, and
`0007` refuses to re-encode it. A case is structured data the caller is holding
as objects — an application row, a record fetched from a database — and
flattening it to a string at the boundary would push the rendering onto the
caller and leave the transcript recording a rendering rather than the facts.
Rendering a case for the prompt is the library's job, exactly as it is for a
statute; the difference is only that here there is a structure to render from.

**Rejected: a bare `dict[str, Any]`.** It gives up validation and the name. A
case is a noun in the glossary and a labelled field in the record, and being a
type is what lets it be one — the same reason
[`0001`](./0001-statute-carries-no-model.md) kept `Statute` a type rather than a
`str`.

**Rejected: `extra="forbid"` on the base.** It would make `Case(applicant=...)`,
written in the README and in every worked example in
[`../design/outcomes.md`](../design/outcomes.md), an error. Worse, it would make
the round trip lossy in the strictest possible way: a subclass's fields,
validated back against the declared base type, would be rejected outright rather
than kept. Permissiveness on the base is what keeps the artifact readable back by
anyone who does not have the caller's subclass in hand.

**Cost: two ways to spell a case.** A reader of `Transcript.case` cannot tell
whether the author had a schema or threw keyword arguments at the base. Accepted:
the open base is the prototyping path and the round-trip path, and the design doc
points at subclassing for anything that runs twice.

**Cost: `hearing.transcript.case` is statically `Case`.** Attribute access on
facts pulled out of a transcript is unchecked. This is precisely the thing the
rejected option would have fixed, and the assessment above is why it is not worth
its price.

**`SerializeAsAny` is a defect this decision creates, and closes.** Annotating
the field as the base type is what allows a subclass instance in the first place,
and it is also what silently drops that subclass's fields on `model_dump()`.
[`../design/api.md`](../design/api.md#the-record) states the requirement where
the schema is given, next to the generic-alias note, because both are constraints
that a type checker will not catch and only running the code reveals.

**Frozen, following [`0001`](./0001-statute-carries-no-model.md) and
[`0007`](./0007-a-statute-is-opaque-text.md).** A statute is frozen partly
because it is shared across proceedings; a case is not, and is frozen for the
other half of that reasoning alone — a record of the facts that could be edited
mid-hearing makes the transcript's account of what was decided unfalsifiable.

**Nothing about the proceeding changes.** No round, filing, or deliberation
depends on the shape of a case, which is the same fact that decided the question.
