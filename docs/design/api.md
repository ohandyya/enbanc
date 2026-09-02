---
status: draft
updated: 2026-09-02
---

# Public API

The surface being designed toward `0.1.0`. Mechanics behind it are in
[`tribunal.md`](./tribunal.md); terms are defined in
[`../glossary.md`](../glossary.md).

> `status: draft` — none of this exists yet, and it will change. This is the
> target, not a reference.

## Shape

```python
from pydantic_ai.models.anthropic import AnthropicModel

from enbanc import Tribunal, Judge, Advocate, Statute, Case, Verdict

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
        LoanDecision.APPROVE: Advocate(tools=[psql, tavily]),
        LoanDecision.DENY: Advocate(
            tools=[psql],
            guidance="Weigh documented income over stated income.",
        ),
    },
    max_rounds=5,
)

hearing = await tribunal.hear(Case(applicant=..., income=...))

if hearing.ruling is not None:      # None only when the round limit was hit
    hearing.ruling.verdict          # LoanDecision.DENY
    hearing.ruling.reasoning

hearing.transcript                  # every filing, in order
hearing.usage                       # tokens and cost, judge plus advocates
```

That `if` is not decoration. `hearing.ruling` is optional because
round-limit exhaustion is still unsettled — see
[`tribunal.md`](./tribunal.md#open-questions) — and writing the sample out
honestly is the clearest argument that exhaustion should resolve toward an
exception instead, which would let the check go.

## What each piece carries

**`Verdict`** — you subclass it to enumerate the allowed answers. The set of
values determines how many advocates exist; there is exactly one advocate per
value, and no way to end up with an advocate arguing for an answer outside the
enum. It is also the type parameter every other generic here is keyed on:
`verdicts=LoanDecision` is what makes `hearing.ruling.verdict` a
`LoanDecision` rather than a `str`.

**`Statute`** — the rule being judged against, and nothing else. You author it;
it carries no model and does nothing on its own. Its `text` is yours: whatever
format and content you write, `enbanc` holds no assumption about it and passes
it through whole. Frozen, because it is shared across tribunals and across
concurrent proceedings, and because a rule that could be edited mid-hearing
would make the transcript's account of what was applied unfalsifiable. See
[`0001`](../decisions/0001-statute-carries-no-model.md) and
[`0007`](../decisions/0007-a-statute-is-opaque-text.md).

**`Case`** — the facts of a single decision. Deliberately open: applicant
details, business info, whatever the statute needs to be applied. Like
`Statute`, it is a noun in the record — supplied by you, never an agent.

**`Advocate`** — assigned one verdict value, given its own read-only tools. Tools
are per-advocate on purpose: the advocate for approval may need different
evidence sources than the advocate for denial, and giving both the same toolbox
would flatten a real asymmetry. Takes an optional `model`, overriding the
tribunal's, and optional `guidance` — prose you write, which `enbanc` appends to
the procedural prompt it owns and does not otherwise touch.

**`Judge`** — exactly one, and it has no tools. It reasons only over what
advocates put into the record, which is what keeps the transcript a complete
explanation of the ruling. Its output type belongs to the library and is derived
from your `Verdict` enum — a `Ruling` or a `Continuance`, never free text — so
there is nothing to configure there. Like an advocate, it takes an optional
`model` and optional `guidance`.

**`Tribunal`** — holds the question, statute, judge, advocates, default model,
and round limit. Async, because every round fans out across advocates. The
`advocates` mapping must cover every value of the verdict enum: a missing key
and an unknown key are both errors at construction, so adding an enum member
fails loudly instead of quietly seating a tool-less advocate nobody meant to
create.

**`Transcript`** — the append-only record of every filing, and the audit
artifact. Self-contained: it carries the question, the statute, and the case
alongside the entries, so a transcript dumped to JSON is a complete account on
its own rather than a fragment that needs the `Hearing` to be legible.

**`Hearing`** — what `hear()` returns: the judge's ruling, the transcript, the
aggregate usage, and how many rounds ran.

**`hear(case)`** — runs the proceeding and returns the `Hearing`.

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

### What participants file

```python
class Exhibit(BaseModel):
    source: str              # the tool that produced it
    content: str

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
    id: str                  # assigned by enbanc; names the issuing round
    to: VerdictT
    question: str

class Response(BaseModel, Generic[VerdictT]):
    kind: Literal["response"] = "response"
    advocate: VerdictT
    answering: str           # Interrogatory.id
    answer: str
    exhibits: list[Exhibit] = []
```

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
questions in a round, which it is free to do.

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

class Transcript(BaseModel, Generic[VerdictT]):
    question: str
    statute: Statute
    case: Case
    entries: list[Entry[VerdictT]] = []

    def __iter__(self) -> Iterator[Entry[VerdictT]]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, i: int) -> Entry[VerdictT]: ...
    def render(self) -> str: ...
```

`Entry` is an envelope rather than fields spread onto each filing, for the same
reason `Hearing` wraps `Ruling`: `round` and `filed_at` are things the tribunal
knows and the filer does not. Putting `round` on `Ruling` would put a field on
the judge's own output schema that the judge cannot fill.

`Transcript` iterates over its entries and renders itself to readable proceeding
text. That is the whole of its behavior — it holds no model and makes no calls,
and `render()` is `enbanc` formatting its own artifact, not a statute acquiring
opinions.

### The result

```python
class Hearing(BaseModel, Generic[VerdictT]):
    ruling: Ruling[VerdictT] | None
    transcript: Transcript[VerdictT]
    usage: RunUsage
    rounds: int
```

`hear()` returns a `Hearing`, not a widened `Ruling`. The judge's output may
only carry what the judge knows; the transcript and the usage are the
tribunal's. And exhaustion has to land somewhere — a widened `Ruling` could
express it only as `verdict: V | None`, which re-admits exactly the invalid
state the `Ruling | Continuance` union exists to rule out.

`hearing.ruling` **is** the final entry's filing, not a copy of it. The
transcript is complete on its own; the field is a pointer to the terminal
ruling so callers do not have to walk backwards to find it.

## What a transcript holds

Every filing any participant makes, in the order it was made. Three advocates,
two rounds, seven entries:

```text
round 1   Argument(advocate=APPROVE, exhibits=[psql, tavily])
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
- **Raw tool traffic.** An advocate queries freely and files what it chooses to
  rely on. The judge only ever sees filings, so filings are a complete account
  of what the ruling rests on — but not of what was searched. See the invariant
  in [`tribunal.md`](./tribunal.md#constraints-that-define-the-design) and
  [`0006`](../decisions/0006-the-transcript-schema.md).

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

## A note on generic aliases

`Filing` and `Deliberation` are declared with `TypeAliasType` rather than as
plain aliases. This is forced, not cosmetic.

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

**Verdicts are an enum, not free text.** The judge picks from a closed set, and
the type system knows the set.

**The verdict enum parameterizes everything.** `Tribunal(verdicts=LoanDecision)`
infers `Tribunal[LoanDecision]`, and the type flows through `Ruling`,
`Continuance`, `Interrogatory`, every filing, `Transcript`, and `Hearing`. This
is what makes the previous commitment true at the call site rather than merely
true in the prompt: `hearing.ruling.verdict` is a `LoanDecision`, and comparing
it against a value from some other enum is a type error.

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
are enforceable only while `enbanc` owns every judge. See
[`0002`](../decisions/0002-the-judge-is-a-role.md).

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. A question that is only *sharpened* — its options narrowed, nothing
decided — stays, rewritten in place. See rule 7 in
[`../../CLAUDE.md`](../../CLAUDE.md).

- Whether `ModelSettings` — temperature, `max_tokens`, retries — is exposed per
  agent, or stays something you bake into the `Model` you construct.
- Whether a bench ever sits. If it does, it joins `judge=` as a union member
  (`Judge | Bench`) rather than arriving as a second parameter. This is not an
  extension point: any bench would be `enbanc`'s own, for the reason in
  [`0002`](../decisions/0002-the-judge-is-a-role.md).
- Whether `hear()` has a streaming counterpart for observing rounds live.
- Whether `Hearing.ruling` is optional at all. It is `Ruling | None` above only
  because round-limit exhaustion is unsettled. That question belongs to
  [`tribunal.md`](./tribunal.md#open-questions); what this document owns is its
  consequence for the public surface — if exhaustion resolves toward an
  exception, `ruling` stops being optional and the `if` in the sample goes away.
- Whether `Case` is a base class users subclass, or a generic container. This is
  now load-bearing rather than cosmetic: `Transcript.case` is typed against it,
  so if `Case` becomes generic, `Transcript` and `Hearing` each gain a second
  type parameter.
- Whether usage is ever broken down per agent. `hearing.usage` is the aggregate
  [`0002`](../decisions/0002-the-judge-is-a-role.md) committed to; a
  `dict[VerdictT | Literal["judge"], RunUsage]` alongside it would let a caller
  see that the judge cost more than every advocate combined. Nothing is built
  for it.
- How an `Interrogatory.id` is assigned. The judge produces the question and the
  tribunal stamps the id when the continuance is filed, so the recorded
  interrogatory is not byte-identical to what the model emitted. Whether that
  wants two types — one emitted, one recorded — or one type with a field the
  judge's schema omits is unsettled.
