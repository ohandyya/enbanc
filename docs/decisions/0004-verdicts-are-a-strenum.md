---
status: accepted
updated: 2026-09-02
---

# 0004. Verdicts are a `StrEnum`, and they parameterize the proceeding

## Context

`../design/api.md` had carried the whole schema question as four lines of raw
notes: "The schema for 1. Verdict: StrEnum 2. Statute: Pydantic model 3. ruling:
Pydantic model." Everything else in the `0.1.0` surface was settled around it —
[`0001`](./0001-statute-carries-no-model.md) made the statute inert,
[`0002`](./0002-the-judge-is-a-role.md) named the judge,
[`0003`](./0003-models-and-guidance-are-injected.md) placed the models — and the
types those decisions talk about still had no definitions.

The verdict enum had to be settled first, and could not be settled in isolation.
It is the one type every other shape refers to: an advocate is keyed by it, an
interrogatory is addressed to it, a ruling returns it, and the `advocates`
mapping is validated against it. Choosing its representation late would have
changed every signature in the library at once.

## Decision

**`Verdict` is an empty `StrEnum` that callers subclass.** It declares no
members, which is exactly what makes it extensible — Python permits subclassing
an `Enum` only while it has none.

**`StrEnum`, not `(str, Enum)`.** Verdict values are interpolated into prompts
and written into the transcript. Under `StrEnum`, `f"{LoanDecision.APPROVE}"` is
`"approve"`; under `(str, Enum)` it is `"LoanDecision.APPROVE"`. The support
floor is already 3.11, so `StrEnum` costs nothing.

**A verdict's meaning lives in its value, and there is no description field.**
The member name is the code identity; the value is what the model reads. Where a
bare word would be ambiguous, the value carries the explanation:
`REFER = "refer to a senior underwriter for manual review"`.

**`VerdictT = TypeVar("VerdictT", bound=Verdict)` parameterizes everything.**
`Tribunal(verdicts=LoanDecision)` infers `Tribunal[LoanDecision]`, and the type
flows through `Argument`, `Concession`, `Interrogatory`, `Response`, `Ruling`,
`Continuance`, `Entry`, `Transcript`, and `Hearing`. `hearing.ruling.verdict` is
a `LoanDecision`, not a `str`.

**The `advocates` mapping must be exhaustive.** Every value of the enum must
appear as a key; a missing key and an unknown key are both errors at `Tribunal`
construction.

## Consequences

**Rejected: accepting any `type[StrEnum]` and shipping no base class.** One
fewer import, and `class LoanDecision(StrEnum)` is ordinary Python. Rejected for
the reason [`0001`](./0001-statute-carries-no-model.md) kept `Statute` a type
rather than a `str`: the named base is where per-verdict structure would go if
it is ever needed, and adding a base class later is a breaking change while
adding fields to one is not. It also keeps `verdicts=` narrowly typed, so the
parameter documents what it wants.

**Rejected: `(str, Enum)` for 3.10 compatibility.** `requires-python` is already
`>=3.11`, so there is nothing to buy. The `__str__` behavior is the deciding
difference and it fails in the direction that is hardest to notice — a
transcript full of `LoanDecision.APPROVE` is wrong but not broken.

**Rejected: a `Literal` union of strings instead of an enum.** It would give the
type checker the same closed set with less ceremony. But there is nowhere to
hang an advocate mapping keyed by member, no stable identity to compare against,
and no runtime object to enumerate when the tribunal seats one advocate per
value — which it must do before any model runs.

**Rejected: a separate per-verdict description.** Either a parallel mapping or a
member-metadata scheme. Both add API for something the value already does, and a
description that can drift from the value it describes is worse than no
description.

**Rejected: a partial `advocates` mapping with missing values defaulted.**
Friendlier for wide enums, where only two of five verdicts need tools, and a
bare `Advocate()` is a well-defined baseline rather than a degraded state. It
loses on the failure it permits: adding a member to the verdict enum would
silently seat a new advocate with no tools and no guidance, and the proceeding
would run, produce a plausible ruling, and never mention it.

**Cost: boilerplate on wide enums.** A five-value verdict enum where three
advocates need no configuration still writes three `Advocate()` entries. Paid
deliberately — the noise is visible, and the alternative's failure is not.

**Cost: `Verdict` gives the caller nothing today except a name.** Subclassing it
is currently indistinguishable from subclassing `StrEnum` directly. That is the
price of keeping the extension point, and it is the consequence most likely to
be revisited if per-verdict structure never materializes.
