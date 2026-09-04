---
status: draft
updated: 2026-09-04
---

# Public API

The surface being designed toward `0.1.0`. Mechanics behind it are in
[`tribunal.md`](./tribunal.md) and [`evidence.md`](./evidence.md); terms are
defined in [`../glossary.md`](../glossary.md). This document specifies the
types — [`outcomes.md`](./outcomes.md) shows every way a proceeding can end,
with values in them.

> `status: draft` — none of this exists yet, and it will change. This is the
> target, not a reference.

## Shape

```python
from pydantic_ai.models.anthropic import AnthropicModel

from enbanc import (
    Tribunal, Judge, Advocate, Statute, Case, Verdict, Ruling, Undecided,
)
from enbanc.tools import web_search

class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"

statute = Statute(
    text="Approve $500k loans only where DTI < 0.43 and ...",
    name="underwriting-v3",
)

tribunal = Tribunal(
    question="Shall the bank loan this applicant $500k?",
    verdicts=LoanDecision,
    statute=statute,
    model=AnthropicModel("claude-sonnet-5"),
    judge=Judge(guidance="Where the record is ambiguous, deny."),
    advocates={
        LoanDecision.APPROVE: Advocate(tools=[psql, web_search(api_key=...)]),
        LoanDecision.DENY: Advocate(
            tools=[psql],
            guidance="Weigh documented income over stated income.",
        ),
    },
    max_rounds=5,
)

hearing = await tribunal.hear(Case(applicant=..., income=...))

match hearing.outcome:
    case Ruling(verdict=verdict, reasoning=reasoning):
        verdict                     # LoanDecision.DENY
    case Undecided():               # max_rounds spent, the judge never ruled
        ...

hearing.transcript                  # every filing, in order
hearing.usage                       # tokens and cost, judge plus advocates
hearing.usage_by_participant        # the same spend, split by who incurred it
```

That `match` is not decoration. A proceeding either produces a ruling or spends
`max_rounds` deliberations without reaching one, and `Outcome` is a
discriminated union rather than an optional so the second arm cannot be read
past — a type checker will not let you touch `.verdict` until you have narrowed.

What is *not* in that union is **failure**. If a provider is unreachable, an
advocate's tool raises, or a model's output cannot be validated, `hear()` raises
and there is no `Hearing` at all. See
[When something goes wrong](#when-something-goes-wrong) and
[`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md).

## What each piece carries

**`Verdict`** — you subclass it to enumerate the allowed answers. The set of
values determines how many advocates exist; there is exactly one advocate per
value, and no way to end up with an advocate arguing for an answer outside the
enum. It is also the type parameter every other generic here is keyed on:
`verdicts=LoanDecision` is what makes a ruling's `verdict` a `LoanDecision`
rather than a `str`.

**`Statute`** — the rule being judged against, and nothing else. You author it;
it carries no model and does nothing on its own. Its `text` is yours: whatever
format and content you write, `enbanc` holds no assumption about it and passes
it through whole. Frozen, because it is shared across tribunals and across
concurrent proceedings, and because a rule that could be edited mid-hearing
would make the transcript's account of what was applied unfalsifiable. See
[`0001`](../decisions/0001-statute-carries-no-model.md) and
[`0007`](../decisions/0007-a-statute-is-opaque-text.md).

**`Case`** — the facts of a single decision. A base class you subclass to give
those facts a schema, and open enough to use as it is when they do not need one.
Like `Statute`, it is a noun in the record — supplied by you, never an agent —
and frozen, so what the transcript says was decided on cannot change under it. It
is not a type parameter: `enbanc` renders a case and records it, and reads no
field of it. See
[`0013`](../decisions/0013-a-case-is-a-subclassable-base.md).

**`Advocate`** — assigned one verdict value, given its own read-only `tools` and
`toolsets`. Both are PydanticAI's, passed through as they are: a tool is a plain
async function, and `enbanc` defines no tool base class and no tool decorator.
They are per-advocate on purpose — the advocate for approval may need different
evidence sources than the advocate for denial, and giving both the same toolbox
would flatten a real asymmetry. Takes an optional `model`, overriding the
tribunal's, and optional `guidance` — prose you write, which `enbanc` appends to
the procedural prompt it owns and does not otherwise touch. What a tool may
return, and how its output becomes a citable exhibit, is
[`evidence.md`](./evidence.md).

**`Judge`** — exactly one, and it has no tools. It reasons only over what
advocates put into the record, which is what keeps the transcript a complete
explanation of the ruling. Its output type belongs to the library and is derived
from your `Verdict` enum — a `Ruling` or a `Continuance`, never free text — so
there is nothing to configure there. Like an advocate, it takes an optional
`model` and optional `guidance`.

**`Tribunal`** — holds the question, statute, judge, advocates, default model,
and round limit. Async, because every round fans out across advocates. The
`advocates` mapping must cover every value of the verdict enum: a missing key
and an unknown key each raise `ConfigurationError` at construction, so adding an
enum member fails loudly instead of quietly seating a tool-less advocate nobody
meant to create.

**`Transcript`** — the append-only record of every filing, and the audit
artifact. Self-contained: it carries the question, the statute, and the case
alongside the entries, so a transcript dumped to JSON is a complete account on
its own rather than a fragment that needs the `Hearing` to be legible. Beside
the entries it carries the `ledger` — every source every advocate's tools
returned, filed or not — so the record answers *what was left out?* as well as
*what was this decided on?*

**`Hearing`** — what `hear()` returns: the outcome, the transcript, what the
proceeding spent — in total and per participant — and how many rounds ran. A
`Hearing` exists only when the tribunal ran to the end of its own process; when
it could not, `hear()` raises instead.

**`Outcome`** — how the proceeding ended, as a discriminated union: a `Ruling`,
or `Undecided` when the round limit was spent without one. Both are records, and
both serialize, because a proceeding that could not decide is a finding about
the case and belongs in the audit artifact.

**`hear(case)`** — runs the proceeding and returns the `Hearing`.

**`hear_stream(case)`** — the same proceeding, watched as it happens: an async
context manager over a `Proceeding`, which yields each entry at the moment it is
filed. `hear()` is that stream consumed to the end.

**`Proceeding`** — the live handle. Async-iterable over `Entry`, carrying the
transcript as it grows and the `Hearing` once the proceeding ends. The one type
here that is not a record.

## Schemas

### Verdicts

```python
class Verdict(StrEnum):
    """The enum of allowed answers. Subclass it and enumerate the values."""

VerdictT = TypeVar("VerdictT", bound=Verdict)
```

`Verdict` declares no members, which is exactly what makes it subclassable —
Python permits extending an `Enum` only while it is empty.

`StrEnum` rather than `(str, Enum)` because verdict values are interpolated into
prompts and written into the transcript. Under `StrEnum`,
`f"{LoanDecision.APPROVE}"` is `"approve"`; under `(str, Enum)` it is
`"LoanDecision.APPROVE"`, which leaks a Python identifier into the audit
artifact silently and reaches the model as noise.

Nothing carries a separate description of what a verdict *means*, and nothing
needs to: the member name is the code identity and the **value is what the model
reads**. Where a bare word would be ambiguous, write the explanation into the
value.

```python
class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"
    REFER = "refer to a senior underwriter for manual review"
```

### The inputs

```python
class Statute(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    name: str | None = None
```

That is the whole of it. `text` is the rule, and it is **opaque to `enbanc`** —
you write it in whatever form suits the rule, and the library does not parse it,
validate its shape, split it into parts, or require any structure. A paragraph,
numbered clauses, Markdown, a pasted policy document: all are a statute, and all
reach the judge and the advocates whole and appear in the transcript verbatim.
The only constraint is the one the annotation states.

`name` is what a transcript cites when a reviewer asks which version of the
policy produced a decision — the field only earns its place because the
transcript is self-contained, and it is the reason a statute is a type rather
than a bare `str`. It labels the text; it claims nothing about it.

Construction is by keyword: `Statute(text=...)`. A `BaseModel` takes no
positional argument, and the alternative that would have preserved one
(`RootModel[str]`) holds exactly one field — `name` is a second one the
transcript needs.

Turning a statute into prompt text is `enbanc`'s job, not the statute's.
Putting rendering on the object would hand back the behavior
[`0001`](../decisions/0001-statute-carries-no-model.md) removed. There is no
`Statute.draft()` and there will not be: drafting needs a target representation
to compile prose into, and a statute has none by design. See
[`0007`](../decisions/0007-a-statute-is-opaque-text.md).

```python
class Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")
```

No fields, because the facts of a decision are yours. **Subclass it** to give
them a schema:

```python
class LoanApplication(Case):
    applicant: str
    income: int
    dti: float
    documents: list[str] = []

hearing = await tribunal.hear(
    LoanApplication(
        applicant="A. Okonkwo",
        income=182000,
        dti=0.51,
        documents=["w2-2024", "schedule-c-2024"],
    )
)
```

That is the path for anything that runs twice: the fields are validated at
construction, the facts the statute talks about are named in one place, and a
reviewer reading the transcript back sees that shape rather than whatever the
call site happened to pass.

**The base is open, so it is usable as it is.** `extra="allow"` makes
`Case(applicant="A. Okonkwo", income=182000)` a case — the shortest thing that
works while a tribunal is still being sketched. It also does a second job that
matters more than convenience: when a persisted transcript is validated back, a
subclass's fields land on the base `Case` as extras rather than being rejected,
so the artifact survives a round trip even where the static type does not.

**`Case` is not a type parameter.** `Transcript.case` is typed `Case`, not
`LoanApplication`, and nothing here is keyed on the case the way everything is
keyed on the verdict enum. Recovering the subclass from a persisted transcript is
`LoanApplication.model_validate(hearing.transcript.case.model_dump())`, which
names the concrete class exactly once — the same as a parameterized `Transcript`
would demand, without putting a second parameter on four public types. At the
call site the question does not arise: you are holding the object you passed to
`hear()`. See [`0013`](../decisions/0013-a-case-is-a-subclassable-base.md).

**Frozen, like a statute**, and for the same reason. The case is what the
transcript claims was decided on, and facts that could be edited mid-hearing
would make that account unfalsifiable.

Turning a case into prompt text is `enbanc`'s job, not the case's — the same
division `Statute` draws just above.

### What participants file

```python
class Exhibit(BaseModel):
    source: str              # the ledger id it cites; resolves in Transcript.ledger
    tool: str                # stamped on filing; the tool that produced it
    reference: str           # stamped on filing; where a reviewer looks
    content: str             # the advocate's excerpt
    label: str | None = None # stamped on filing, when the source had one

class Argument(BaseModel, Generic[VerdictT]):
    kind: Literal["argument"] = "argument"
    advocate: VerdictT
    claim: str
    exhibits: list[Exhibit] = []

class Concession(BaseModel, Generic[VerdictT]):
    kind: Literal["concession"] = "concession"
    advocate: VerdictT
    reason: str

class Interrogatory(BaseModel, Generic[VerdictT]):
    id: str                  # stamped on filing; names the issuing round
    to: VerdictT
    question: str

class Response(BaseModel, Generic[VerdictT]):
    kind: Literal["response"] = "response"
    advocate: VerdictT
    answering: str           # stamped on filing; the Interrogatory.id
    answer: str
    exhibits: list[Exhibit] = []
```

**An exhibit's `reference` is stamped, not written.** It is the string a
reviewer follows to check the evidence — a URL, a document key, a file path, the
query that produced a row — and its whole value is that it can be trusted, so
the advocate does not author it. It cites a source the tribunal ledgered from a
tool result, and the tribunal fills `tool`, `reference`, and `label` from that
ledger when it files. `content` is the one field the advocate writes: the
excerpt it relies on. What a `reference` may be, and why the excerpt is not
stamped verbatim too, is [`evidence.md`](./evidence.md); the mechanism is
[Where ids come from](#where-ids-come-from) and
[`0016`](../decisions/0016-exhibits-are-stamped-citations.md).

**An argument has no `position` field.** The filing already names its
`advocate`, and an advocate is assigned exactly one verdict, so the position it
argues for is not an independent fact — storing it twice would only create two
places that can disagree.

**Nobody carries an `author`.** `Argument`, `Concession`, and `Response` name an
advocate; `Continuance` and `Ruling` are the judge's by construction. A single
`author: VerdictT | Literal["judge"]` field would make a ruling issued by an
advocate expressible, and that is the kind of state this design keeps
unrepresentable.

**`Response.answering` links back by id** rather than by position. Pairing on
round-and-advocate alone breaks the moment the judge asks one advocate two
questions in a round, which it is free to do. Neither end of that link is
model-authored — the tribunal stamps both, as
[Where ids come from](#where-ids-come-from) describes.

### The judge's output

```python
class Ruling(BaseModel, Generic[VerdictT]):
    kind: Literal["ruling"] = "ruling"
    verdict: VerdictT
    reasoning: str

class Continuance(BaseModel, Generic[VerdictT]):
    kind: Literal["continuance"] = "continuance"
    interrogatories: list[Interrogatory[VerdictT]]

Deliberation = TypeAliasType(
    "Deliberation",
    Annotated[Ruling[VerdictT] | Continuance[VerdictT], Field(discriminator="kind")],
    type_params=(VerdictT,),
)
```

A ruling carries a verdict and reasoning and nothing else, because there is
nothing else the judge could know. The round it was issued in, what it cost, and
what came before it are the tribunal's facts, and they live on the `Entry` and
the `Hearing` instead.

The `kind` tags are defaulted, so the model never has to produce them, and they
are what lets a persisted transcript be read back without Pydantic guessing a
union member from field shape. That matters more here than for most unions: the
whole point of the artifact is that someone reads it later.

`TypeAliasType` rather than a plain `Deliberation = Ruling[VerdictT] | ...`
alias is a real constraint, not a style preference — see
[the implementation note](#a-note-on-generic-aliases) below.

#### Where ids come from

`Interrogatory.id` is required and has no default, because `Response.answering`
is a link and a transcript whose link does not resolve is not an audit artifact.
The judge cannot fill that field: it does not know its own round number, and
nothing would stop it issuing the same id in two rounds.

So it is never asked to. The judge agent's output type is a **private pair** —
`_Interrogatory`, which is `to` and `question`, and the `_Continuance` that
holds them — and the tribunal converts to the public types when it files the
deliberation:

```python
class _Interrogatory(BaseModel, Generic[VerdictT]):   # what the judge emits
    to: VerdictT
    question: str

class _Continuance(BaseModel, Generic[VerdictT]):
    kind: Literal["continuance"] = "continuance"
    interrogatories: list[_Interrogatory[VerdictT]]

# the judge's output_type is Ruling[VerdictT] | _Continuance[VerdictT]
```

Ids are `r{round}-q{n}`, `n` numbered from 1 within the continuance that issued
them. The round prefix carries uniqueness, so numbering restarts each round and
the id says where to look: a reviewer holding `answering="r1-q1"` knows the
question is in round 1. **Nothing the judge wrote is altered** — `to` and
`question` are recorded verbatim and the id is added beside them.

`Response.answering` is stamped the same way. The tribunal dispatches one
advocate run per interrogatory, so it knows which question that run answers and
fills the link from the dispatch rather than from the model. No participant
authors an id in either direction, and a response citing a question nobody asked
is not a state the library can reach.

**An advocate's exhibits are stamped by the same move.** Its output type
carries a private `_Exhibit` — a ledger id and the excerpt — and the tribunal
resolves the id into the public `Exhibit` when it files:

```python
class _Exhibit(BaseModel):   # what an advocate emits
    source: str              # a ledger id, e.g. "s2"
    content: str
```

The parallel is exact. In both cases a model is asked only for what it knows —
the question it wants asked, the passage it relies on — and every field whose
correctness the record depends on is filled by the tribunal from something it
observed. An advocate citing a source no tool returned is as unreachable a state
as a response citing a question nobody asked, and for the same reason. The one
difference is where an unresolvable value lands: an interrogatory id cannot be
wrong, because the tribunal writes both ends, while a source id is the
advocate's to get right and a bad one fails output validation. See
[`0016`](../decisions/0016-exhibits-are-stamped-citations.md).

This is the [`Entry`](#the-record) move applied one level down. `round` and
`filed_at` are the tribunal's facts and live on an envelope; an id is the same
kind of fact with nowhere to put an envelope, because interrogatories nest so
that each question appears in the record exactly once. Both are stamped at the
same seam — the moment a filing enters the record. The second type is what buys
`id` its required-no-default: a single class would need a default for the judge's
output to validate, and a defaulted id is one a malformed transcript reconstructs
silently. `Judge` being closed
([`0002`](../decisions/0002-the-judge-is-a-role.md)) is what keeps the emitted
pair private and off this surface. See
[`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md).

### The record

```python
Filing = TypeAliasType(
    "Filing",
    Annotated[
        Argument[VerdictT]
        | Concession[VerdictT]
        | Response[VerdictT]
        | Continuance[VerdictT]
        | Ruling[VerdictT],
        Field(discriminator="kind"),
    ],
    type_params=(VerdictT,),
)

class Entry(BaseModel, Generic[VerdictT]):
    round: int
    filed_at: datetime
    filing: Filing[VerdictT]

class Retrieval(BaseModel, Generic[VerdictT]):
    id: str                   # the ledger id; what an Exhibit.source cites
    round: int
    advocate: VerdictT        # whose tool call produced it
    tool: str
    reference: str
    content: str              # verbatim, as the tool returned it
    label: str | None = None

class ToolFailure(BaseModel, Generic[VerdictT]):
    round: int
    advocate: VerdictT
    tool: str
    reference: str            # the call that returned nothing
    detail: str               # what the advocate was told

class Transcript(BaseModel, Generic[VerdictT]):
    question: str
    statute: Statute
    case: SerializeAsAny[Case]
    entries: list[Entry[VerdictT]] = []
    ledger: list[Retrieval[VerdictT]] = []
    failures: list[ToolFailure[VerdictT]] = []

    def __iter__(self) -> Iterator[Entry[VerdictT]]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, i: int) -> Entry[VerdictT]: ...
    def render(self) -> str: ...
```

`Entry` is an envelope rather than fields spread onto each filing, for the same
reason `Hearing` wraps `Ruling`: `round` and `filed_at` are things the tribunal
knows and the filer does not. Putting `round` on `Ruling` would put a field on
the judge's own output schema that the judge cannot fill.

**`Transcript.case` is `SerializeAsAny[Case]`, and has to be.** Pydantic v2
serializes a field by its *declared* type, so a `LoanApplication` sitting in a
plain `case: Case` field dumps as a bare `Case` and every subclass field
disappears — silently, out of the artifact whose whole job is to be complete.
`SerializeAsAny` switches that one field to duck-typed serialization. It is the
same kind of forced detail as [the generic aliases](#a-note-on-generic-aliases)
below, and it is the price of `Case` not being a type parameter.

**`ledger` is every source every tool returned, verbatim** — not only the ones
an advocate filed. It is the second half of the audit artifact: `entries` says
what the ruling rests on, and `ledger` says what was available to rest on. A
reviewer checking whether an advocate argued fairly reads the retrievals no
exhibit cites, and can do it without leaving the document or holding credentials
to the systems the tools queried. See [`evidence.md`](./evidence.md) and
[`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md).

**Suppression is found by joining, not by a flag.** `Exhibit.source` holds the
ledger id it cites, and the join key is `(advocate, id)` — ids are numbered
within an advocate, so `APPROVE`'s `s1` and `DENY`'s `s1` are different
retrievals. Per-advocate numbering is deliberate: an advocate's tool calls are
sequential, so its ids are deterministic, whereas one counter shared across
advocates running concurrently would assign different ids on every run of the
same proceeding.

There is deliberately no `cited: bool` on `Retrieval`. Whether a round-1 source
is ever cited is not known until the proceeding ends, so the field would be
written on append and rewritten when a later round cites it — and a transcript
whose rows change after they are appended is not append-only. The join is exact
anyway, because both sides carry the same tribunal-stamped id.

**`failures` is every tool call that returned nothing.** A timed-out call
produces no source, so it produces no `Retrieval` and would otherwise appear
nowhere — leaving an advocate that was blocked from its best source
indistinguishable from one that did not look. One row per attempt, because
timing out three times is a different fact from timing out once. See
[`0022`](../decisions/0022-tool-failures-are-recorded.md).

**`ToolFailure` has no `id`, and that is the point.** A `Retrieval` carries one
so an `Exhibit.source` can name it; a failed call produced nothing and can never
be cited. Keeping failures in their own list rather than as `Retrieval`s with an
`outcome` flag is what keeps the ledger's rows meaning one thing: a successful
call yields a row per source, and a failed call yields no source at all.

**A populated `failures` is not a finding.** It records that a tool failed, not
that the ruling turned on it. `enbanc` does not mark a hearing degraded, warn,
or adjust the outcome — whether the judge should have weighed a gap is the
reviewer's call, and the record's job is to make it askable.

**`Retrieval.content` is verbatim; `Exhibit.content` is the advocate's excerpt.**
They are different facts about the same source and both are load-bearing: the
excerpt says what the advocate claimed mattered, the verbatim text is what it
actually had in front of it. Reading them side by side is how a misquote is
caught.

**The ledger's size is the caller's to control.** `enbanc` stores what a tool
returned and does not truncate it, so a tool that returns whole pages produces a
transcript that holds whole pages. The lever is the tool: return the snippet you
want the advocate to reason over, not the document it came from. This is the
same discipline that keeps an advocate's context small, and it is why
[`web_search`](./evidence.md#the-default-tool) does not request Tavily's
`raw_content`.

`Transcript` iterates over its entries and renders itself to readable proceeding
text. That is the whole of its behavior — it holds no model and makes no calls,
and `render()` is `enbanc` formatting its own artifact, not a statute acquiring
opinions.

### The result

```python
class Undecided(BaseModel):
    kind: Literal["undecided"] = "undecided"

Outcome = TypeAliasType(
    "Outcome",
    Annotated[Ruling[VerdictT] | Undecided, Field(discriminator="kind")],
    type_params=(VerdictT,),
)

class Hearing(BaseModel, Generic[VerdictT]):
    outcome: Outcome[VerdictT]
    transcript: Transcript[VerdictT]
    usage_by_participant: dict[VerdictT | Literal["judge"], RunUsage]
    usage: RunUsage
    rounds: int
```

`hear()` returns a `Hearing`, not a widened `Ruling`. The judge's output may
only carry what the judge knows; the transcript and the usage are the
tribunal's. And the two ways a proceeding can end have to land somewhere — a
widened `Ruling` could express the second only as `verdict: V | None`, which
re-admits exactly the invalid state the `Ruling | Continuance` union exists to
rule out.

**`outcome` is a union, not an optional.** `Ruling | None` would let a caller
reach a verdict without acknowledging that there might not be one; a
discriminated union makes the type checker insist on the narrowing first. It is
the same move `Ruling | Continuance` makes on the judge's output, applied to the
result — and `Outcome` needs `TypeAliasType` for the same Pydantic reason those
do, described in [the note below](#a-note-on-generic-aliases).

**`Undecided` carries nothing.** Not the round count, which is `Hearing.rounds`;
not the questions the judge still wanted answered, which are the interrogatories
on the last `Continuance` in the transcript. Either would be the same
store-it-twice mistake that kept `position` off `Argument`. It is not generic
either, because there is no verdict in it to key on.

**The outcome is the final entry's filing only when it is a `Ruling`.** There
the field is a pointer, not a copy, so callers do not walk the record backwards
to find the terminal ruling. An `Undecided` is not an entry at all: nobody filed
it, the transcript ends on the judge's last `Continuance`, and the outcome is
the tribunal's own statement that no round followed it.

See [`0005`](../decisions/0005-hear-returns-a-hearing.md) for the wrapper and
[`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md) for
what fills it. [`outcomes.md`](./outcomes.md) writes both arms out as values.

## What a transcript holds

Every filing any participant makes, in the order it was made. Three advocates,
two rounds, seven entries:

```text
round 1   Argument(advocate=APPROVE, exhibits=[psql, web_search])
          Argument(advocate=DENY,    exhibits=[psql])
          Concession(advocate=REFER)
          Continuance(interrogatories=[r1-q1 -> APPROVE, r1-q2 -> DENY])

round 2   Response(advocate=APPROVE, answering="r1-q1")
          Response(advocate=DENY,    answering="r1-q2", exhibits=[psql])
          Ruling(verdict=DENY)
```

A round is the advocates' filings **plus the deliberation that closes it**, so
`max_rounds` counts judge deliberations — the thing that actually drives cost —
and an interrogatory id names the round it was issued in, not the round it is
answered in.

What is deliberately *not* in `entries`:

- **The question, statute, and case.** They are `Transcript` fields. They are the
  standing record, not something a participant said.
- **Individual interrogatories.** They are nested inside the `Continuance` that
  issued them, so each question appears in the record exactly once.
- **Retrievals.** What an advocate's tools returned is recorded, but in
  `Transcript.ledger` rather than as entries. Nobody *filed* it — an entry is a
  filing, and there are exactly five — so it is a sibling field, not a sixth
  `kind`. The judge still sees only filings; the ledger is written for the
  reviewer, not for the proceeding. See
  [`evidence.md`](./evidence.md#the-ledger-is-part-of-the-record) and
  [`0019`](../decisions/0019-the-ledger-is-part-of-the-record.md), which
  supersedes the reading of
  [`0006`](../decisions/0006-the-transcript-schema.md) that kept it out.

Narrowing a filing works by `isinstance` or `match`, against the unparameterized
class:

```python
for entry in hearing.transcript:
    match entry.filing:
        case Ruling():
            ...
```

Note that `type(entry.filing) is Ruling` is **False** — Pydantic makes
`Ruling[LoanDecision]` a genuine subclass — so identity checks against the
origin class do not work. `isinstance` and `match` both do.

## Watching it live

`hear()` returns when the proceeding is over. `hear_stream()` is the same
proceeding with the record readable as it is written:

```python
async with tribunal.hear_stream(case) as proceeding:
    async for entry in proceeding:
        print(f"round {entry.round}: {entry.filing.kind}")
        # round 1: argument, argument, concession, continuance
        # round 2: response, response, ruling

hearing = proceeding.hearing        # the Hearing hear() would have returned
```

```python
class Proceeding(Generic[VerdictT]):
    transcript: Transcript[VerdictT]   # live: the entry just yielded is its last
    hearing: Hearing[VerdictT]         # raises until the proceeding ends well

    def __aiter__(self) -> AsyncIterator[Entry[VerdictT]]: ...

# on Tribunal
def hear_stream(
    self, case: Case
) -> AbstractAsyncContextManager[Proceeding[VerdictT]]: ...
```

**What it yields is the record.** Each value is the `Entry` appended to the
transcript at that moment — the same object, in filing order, and nothing else.
There are no lifecycle events, no partial filings, and no token deltas: a viewer
that saw something the transcript does not contain would be watching a second
channel, and the transcript would no longer be a complete account of what
happened. Round boundaries need no event either — `entry.round` names the round,
and a `Continuance` or a `Ruling` is what closes one.

**`hear()` is this, consumed.** It is defined as `hear_stream()` driven to
exhaustion, so there is one implementation of a proceeding and the two entry
points cannot come apart.

**`Proceeding` is a handle, not a record**, which is why it is not a `BaseModel`.
It holds no fact of its own — `transcript` and `hearing` are views of things that
exist anyway — it is never serialized, and it never appears on a result.

**Abandoning is allowed.** Break out of the loop and the block exits: the
in-flight advocate and judge runs are cancelled, `proceeding.transcript` holds
everything filed up to that point, and `proceeding.hearing` raises
`ProceedingUnfinished` — there was no hearing. Like `hear()`, `hear_stream()`
parks no state on the tribunal and is safe to run concurrently over several
cases. See [`0010`](../decisions/0010-streaming-yields-the-record.md).

**Ending is the same here as it is for `hear()`.** Exhaustion does not raise
from the stream: the `async for` simply ends after the judge's last
`Continuance`, and `proceeding.hearing.outcome` is `Undecided`. A failure does
raise — `ProceedingFailed` propagates out of the `async with`, and
`proceeding.transcript` survives it, holding everything filed before the
participant went silent. `proceeding.hearing` then re-raises that same
`ProceedingFailed` rather than reporting the blander `ProceedingUnfinished`,
which is reserved for a proceeding still running or one the caller walked away
from.

## When something goes wrong

A proceeding has two endings and one interruption. It rules, it spends its
rounds without ruling, or a participant cannot be heard and it stops. The first
two are outcomes and come back on a `Hearing`; the third raises.
[`outcomes.md`](./outcomes.md) works each one through end to end — including a
downed provider, a raising tool, and a misconfigured tribunal.

```python
EnbancError                 # base for everything enbanc raises
├── ConfigurationError      # the tribunal could not be built
├── ProceedingFailed        # a participant could not be heard
└── ProceedingUnfinished    # proceeding.hearing before there is one
```

```python
class ProceedingFailed(EnbancError, Generic[VerdictT]):
    participant: VerdictT | Literal["judge"]
    round: int
    transcript: Transcript[VerdictT]
    usage_by_participant: dict[VerdictT | Literal["judge"], RunUsage]
    usage: RunUsage
```

**No provider exception reaches you bare.** An unreachable model, an advocate
tool that raises, a tool that keeps timing out until its retries are spent, and
output validation that runs out of retries all surface as `ProceedingFailed`,
with the original error as `__cause__`. A tool timeout on its own is not a
failure — it returns a retry prompt and the advocate carries on; see
[`evidence.md`](./evidence.md#what-tools-may-do) and
[`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md). `enbanc` does not
classify them further: PydanticAI and httpx already raise specific types, and a
second taxonomy over them would be one more thing to keep true.

**`round` says where it stopped, and there is no `rounds`.** A `Hearing` reports
how many rounds ran because a finished proceeding is asked what it spent; a
failure is asked where it died. The two would be the same fact written twice — a
round completes when its deliberation is filed, so failing in round *N* always
leaves *N-1* behind it.

**The record survives.** `ProceedingFailed` carries the transcript as it stood,
plus who failed and in which round. It cannot carry a `Hearing` — `outcome` is
required and a failed proceeding has none — which is the point: an outage is not
an adjudication and must not be storable as one.

**A failure is terminal for the whole proceeding**, even when only one advocate
is affected and the judge and its peers are healthy. Letting the judge rule on
what is left produces a decision reached because the opposing advocate was
knocked offline rather than answered, and nothing in its type distinguishes it
from a ruling on a full bench. `enbanc` would rather return no ruling than a
quietly one-sided one; concession is how an advocate declines to argue, and an
outage is not a concession.

**The first failure cancels the round.** Advocates fan out concurrently, so a
failure in round *N* catches siblings mid-run; those runs are cancelled, and the
transcript on the exception is what had been filed at that moment — not what the
round would have contained. A filing enters the record when its run completes,
so a cancelled advocate leaves no trace, and two runs of the same outage can
leave different numbers of entries behind. This is the rule abandoning a stream
already follows, and it is why `participant` is singular: the first failure ends
the fan-out, so there is never a set of simultaneous ones. See
[`0012`](../decisions/0012-a-failure-cancels-the-round.md).

**`enbanc` retries nothing of its own.** HTTP retry and backoff live on the
httpx client inside the `Model` you inject
([`0009`](../decisions/0009-model-settings-live-on-the-model.md)), so an error
that reaches `enbanc` is one your policy already gave up on; a retry loop here
would sit silently above the one you configured. The library's own budget —
`Agent(retries=...)`, guarding the `Ruling | Continuance` contract — is spent
before `ProceedingFailed` is raised.

**`usage` on a failure is best-effort.** It sums the runs that completed. A run
that died mid-flight may not report what it spent, so a failure's usage is a
floor rather than a total. The breakdown inherits that: a participant whose run
was cancelled or died before reporting has **no key at all**, so
`usage_by_participant` on a failure is not guaranteed to name every participant
the way it is on a `Hearing`. Absence there means "did not report", never
"spent nothing".

**`ConfigurationError` is not a proceeding failure** and carries no transcript,
because nothing ran. It is what `Tribunal(...)` raises when the `advocates`
mapping misses a verdict, names one that does not exist, or when a verdict's
value is the reserved string `"judge"` — see
[Per participant](#per-participant).

**`participant` is not the `author` field this document rejects.** That
rejection — [above](#what-participants-file) — is about the *record*: a filing
carrying `VerdictT | Literal["judge"]` would make a ruling issued by an advocate
expressible, and the record is where that must stay impossible. An exception is
not a filing and enters no transcript. The same union keys
`usage_by_participant` on both a `Hearing` and this exception, and for the same
reason: usage is the tribunal's accounting of who spent what, not something
anyone filed. Here the shape is only the answer to "who went silent?", and there
is no invariant for it to weaken. See
[`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md).

## Usage

`hearing.usage` is `pydantic_ai.usage.RunUsage`, summed across the judge and
every advocate. `enbanc` defines no usage type of its own, for the same reason
it does not parse model strings: PydanticAI already has one that works.

```python
hearing.usage.requests            # LLM API calls
hearing.usage.tool_calls          # successful advocate tool calls
hearing.usage.input_tokens
hearing.usage.output_tokens
hearing.usage.cache_read_tokens
hearing.usage.cost                # Decimal | None, USD, best-effort
hearing.usage.details             # provider extras
```

Two of these are easy to read wrong:

- **Token buckets are inclusive, not disjoint.** `input_tokens` already contains
  `cache_read_tokens`, `cache_write_tokens`, and `input_audio_tokens`. Adding
  them together double-counts.
- **`cost is None` means unpriceable, not free.** PydanticAI keeps "the provider
  could not be priced" distinguishable from a genuine zero, and a proceeding
  that reports `None` has not established that it was cheap.

`RunUsage` is a stdlib dataclass rather than a `BaseModel`, but it ships
`__get_pydantic_core_schema__`, so it embeds in `Hearing` and serializes with
the rest of it.

### Per participant

`hearing.usage_by_participant` is the same spend, split by who incurred it: one
entry per advocate, one for the judge under the key `"judge"`.

```python
hearing.usage_by_participant
# {<LoanDecision.APPROVE: 'approve'>: RunUsage(requests=3, input_tokens=14820, ...),
#  <LoanDecision.DENY: 'deny'>:       RunUsage(requests=4, input_tokens=18960, ...),
#  <LoanDecision.REFER: 'refer ...'>: RunUsage(requests=2, input_tokens=7310, ...),
#  'judge':                           RunUsage(requests=2, input_tokens=20312, ...)}

hearing.usage_by_participant["judge"].cost      # what adjudication cost alone
```

**It exists because the model is per agent.** `Judge` and `Advocate` each take a
`model` overriding the tribunal's, and a strong judge over cheap advocates is
advertised above as a one-line change. Nothing about the aggregate says whether
that trade paid: the judge re-reads the whole record every round while each
advocate sees less, and there are *n* of them. Comparing two proceedings'
aggregates does not answer it either — different case, different round count.
The split is the only place that fact can be read, and it is one the transcript
does not carry.

**The breakdown is the stored fact; `usage` is its sum.** `RunUsage` adds, so
the total is computed from the mapping rather than accumulated beside it. There
is no second place for the two to disagree — the same reason `position` is not
on `Argument`. `usage` stays because "what did this proceeding cost?" is the
common question and should not require a fold.

**Every participant appears on a `Hearing`.** Round 1 fans out to every
advocate, so each has an entry even if it conceded immediately, and the judge
has one because a proceeding that produced a `Hearing` deliberated at least
once. No key is a zero placeholder: every one names a participant that actually
ran. The guarantee is a `Hearing`'s alone —
[on a failure](#when-something-goes-wrong) keys can be missing.

**Each value is that participant's whole proceeding, not one round.** An
advocate's entry sums every run it made across every round. There is no
per-round breakdown: watching cost grow round by round is a cost-*control*
question, and the governor is still open in
[`tribunal.md`](./tribunal.md#open-questions).

**An unpriced participant is visible here and invisible in the total.** Adding
`RunUsage`s treats a `None` cost as zero, so a total whose parts are mixed
reports the sum of the priceable ones and looks like a complete figure. In the
breakdown, the participant with `cost=None` names itself. This is the second
gotcha above with somewhere to land.

**`"judge"` is reserved, and construction enforces it.** Verdicts are a
`StrEnum`, so a member `JUDGE = "judge"` is equal to and hashes with the judge's
key: that advocate and the judge would collapse into one entry, silently, in the
one artifact that exists to attribute spend. `Tribunal(...)` raises
`ConfigurationError` when any verdict's value is `"judge"` — the same loud
construction-time check the `advocates` mapping already gets, and it keeps
`ProceedingFailed.participant` unambiguous for free.

See [`0014`](../decisions/0014-usage-is-broken-down-per-participant.md).

## A note on generic aliases

`Filing`, `Deliberation`, and `Outcome` are declared with `TypeAliasType`
rather than as plain aliases. This is forced, not cosmetic.

Pydantic's `__class_getitem__` returns the origin class when a generic model is
parameterized with a bare `TypeVar` — `Argument[VerdictT] is Argument` is
`True`. A module-level `Filing = Argument[VerdictT] | Concession[VerdictT]`
therefore collapses to `Argument | Concession`, loses its parameters, and
`Filing[VerdictT]` raises `TypeError: ... is not a generic class` when Pydantic
evaluates the annotation. A type checker does not catch this; only running it
does.

`TypeAliasType(..., type_params=(VerdictT,))` is how PEP 695 generic aliases are
spelled before 3.12. When the support floor moves to 3.12 these become
`type Filing[V: Verdict] = ...` and the import goes away.

## Design commitments

**Async-first.** Rounds fan out across advocates; a sync-first API would either
serialize that or lie about it.

**The transcript rides on the result.** It is not an optional debug flag or a
callback you have to install. If the result can be returned, the record that
produced it can be inspected — that is the product.

**A `Hearing` means the tribunal finished; an exception means it did not.**
Running the full process and finding no verdict is a result — it serializes, it
carries the record that shows why, and a reviewer can read it back. Losing a
provider mid-round is not a result, and there is no `Hearing` for it. The
division is not about how bad the ending was; it is about whether the tribunal
got to the end of its own process.

**Streaming is a view of the record, not a second channel.** `hear_stream()`
yields the entries the transcript is receiving, as it receives them. Everything
a caller can watch is in the artifact afterwards, and everything in the artifact
was watchable — which is what makes the live view and the audit trail the same
account of the proceeding rather than two.

**Verdicts are an enum, not free text.** The judge picks from a closed set, and
the type system knows the set.

**The verdict enum parameterizes everything.** `Tribunal(verdicts=LoanDecision)`
infers `Tribunal[LoanDecision]`, and the type flows through `Ruling`,
`Continuance`, `Interrogatory`, every filing, `Transcript`, `Outcome`, and
`Hearing`. This is what makes the previous commitment true at the call site
rather than merely true in the prompt: the `verdict` a `Ruling` arm binds is a
`LoanDecision`, and comparing it against a value from some other enum is a type
error.

**A statute is data, not an agent.** A statute carries no model, and its text is
the author's rather than the library's. Holding a rule fixed while swapping the
models that reason about it is a workflow this library must not obstruct — a
statute that owned a model would make every such comparison move two variables
at once. Keeping it inert also keeps it readable,
diffable, and committable alongside the code that applies it. Where models *do*
live is the next commitment.

**The model is injected, not named.** `enbanc` has no provider concept and no
model-string parser; it would be reinventing one that already works. You
construct a `pydantic_ai.models.Model` and hand it over. `Tribunal(model=...)`
is required and is the default every agent inherits; `Judge` and `Advocate` may
each override it, which is what makes a strong judge over cheap advocates — or a
model comparison on a fixed statute — a one-line change. A single `Model`
instance is safe to share across every agent, and sharing one is the good path.
See [`0003`](../decisions/0003-models-and-guidance-are-injected.md).

**Model settings ride on the model.** There is no `settings=` on `Tribunal`,
`Judge`, or `Advocate`. Temperature, `max_tokens`, `timeout`, thinking
configuration, and provider-specific settings go where PydanticAI already keeps
them — `Model(..., settings=ModelSettings(...))` — and `enbanc` passes none of
its own at request time, so what you configured is what the agent runs with.
Varying settings per agent is varying the model per agent: build a second
`Model` over the same provider and hand it to the `Judge`. HTTP retry and
backoff belong to the client inside that model too; tool and output-validation
retries are the library's, because they guard the `Ruling | Continuance`
contract. See [`0009`](../decisions/0009-model-settings-live-on-the-model.md).

**Guidance augments; the library owns the procedural prompt.** Each agent's
system prompt is assembled by `enbanc`: the `Ruling | Continuance` contract, the
rule that interrogatories are targeted rather than broadcast, the judge's
prohibition on gathering its own evidence, the advocate's licence to concede.
Your `guidance` is added to that, not substituted for it. A replaceable prompt
would let a caller silently break the output schema, and the failure would
present as a library bug. Guidance is per-agent and never inherited: the judge's
steer and an advocate's steer contradict each other by construction, and
anything genuinely common is already carried by `question` and `statute`.

Guidance is **yours**, in the same sense a statute's text is. You write it;
`enbanc` holds no assumption about its form or content and never generates,
rewrites, or tunes it. There is no optimizer, no guidance store, and no notion
inside the library of one steer being better than another — an external tuning
loop is free to produce a string and pass it in, but the string is the caller's,
and so is the account of where it came from. See
[`0003`](../decisions/0003-models-and-guidance-are-injected.md) and
[`0008`](../decisions/0008-guidance-is-human-written.md).

**Agents are reusable; a proceeding's state is not.** `Judge` and `Advocate` are
descriptions — model, tools, guidance — that you construct once and may share
across tribunals. The message history each accumulates over rounds is created
inside `hear()` and discarded when it returns. That split is what makes `hear()`
safe to call twice and safe to run concurrently over several cases; state parked
on the injected object would let one case's record leak into the next.

**The set of judge implementations is closed.** `Judge` is a concrete class, not
a protocol you implement. The guarantees that make a transcript auditable — the
judge has no tools, and nothing reaches it that is not already in the record —
are enforceable only while `enbanc` owns every judge. If a bench ever sits it
joins `judge=` as a union member (`Judge | Bench`) rather than arriving as a
second parameter; it would still be `enbanc`'s own. See
[`0002`](../decisions/0002-the-judge-is-a-role.md).

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. A question that is only *sharpened* — its options narrowed, nothing
decided — stays, rewritten in place. See rule 7 in
[`../../CLAUDE.md`](../../CLAUDE.md).

*None open.* The proceeding still has two, in
[`tribunal.md`](./tribunal.md#open-questions).
