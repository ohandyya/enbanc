---
status: accepted
updated: 2026-09-02
---

# 0015. Interrogatory ids are stamped on filing

## Context

`Interrogatory` carries an `id`, and `Response.answering` is that id. The pair
is what makes a transcript's questions and answers resolvable: pairing on
round-and-advocate alone breaks the moment the judge asks one advocate two
questions in a round, which it is free to do
([`0006`](./0006-the-transcript-schema.md)).

The awkwardness is that an interrogatory is not filed on its own. It nests
inside a `Continuance`, and a `Continuance` **is the judge's output type**. One
class was therefore serving two roles at once: the schema a model fills, and the
record a reviewer reads. As the schema, `id` is a field the judge cannot fill —
it does not know its own round number, and nothing stops it emitting the same id
in two rounds. As the record, `id` must be present and unique or the artifact
has a dangling link.

`api.md` has said "assigned by `enbanc`" since the schema was written, which
means the recorded interrogatory is not byte-identical to what the model
emitted. The open question was where that seam goes: two types, one emitted and
one recorded, or one type with a field the judge's schema omits.

This design has already answered the same question once, in a place where an
envelope was available. `round` and `filed_at` are things the tribunal knows and
the filer does not, so they live on `Entry` rather than on `Ruling` — putting
them on the filing would put fields on the judge's own output schema that the
judge cannot fill. An id is that kind of fact exactly. What it does not have is
an envelope to go on: interrogatories nest so that each question appears in the
record once, and giving them one would undo that.

The `kind` tags pull the other way and look like a precedent for a single type:
they are fields on the judge's output that the model never produces, defaulted
so it does not have to. The difference is that `kind` has a *correct* constant
default. `Literal["continuance"] = "continuance"` is right every time it is
used, including when a persisted transcript is read back without it. An id has
no correct default, so any default is a value that is wrong wherever it
survives.

Nothing is implemented, so this is settled on the surface rather than found by
building.

## Decision

**Two types, and the emitted one is private.** The judge agent's `output_type`
is `Ruling[VerdictT] | _Continuance[VerdictT]`, where `_Continuance` holds
`list[_Interrogatory[VerdictT]]` and `_Interrogatory` is `to` and `question` and
nothing else. When the tribunal files the deliberation it converts to the public
`Continuance` and `Interrogatory`, stamping the id as it goes. `Ruling` is
shared between the two unions unchanged; it has no tribunal-known field.

**On the recorded type, `id` is required with no default.** That is the whole
point of the split: a persisted transcript whose interrogatory has lost its id
fails validation loudly instead of reconstructing a link that does not resolve.

**The format is `r{round}-q{n}`**, `n` numbered from 1 within the continuance
that issued it. The round prefix carries uniqueness, so numbering restarts each
round, and the id names where to look — a reviewer holding `answering="r1-q1"`
knows the question is in round 1.

**Nothing the judge wrote is altered.** `to` and `question` are recorded
verbatim; the id is added beside them. The conversion adds a field and changes
no other.

**`Response.answering` is stamped too.** The tribunal dispatches one advocate
run per interrogatory, so it knows which question that run answers and fills the
link from the dispatch rather than from the model's output. No participant
authors an id in either direction.

## Consequences

**The public surface does not change.** `Interrogatory` and `Continuance` are
what `api.md` already showed, and `outcomes.md`'s worked values are already
written in the recorded shape. The split is entirely inside the library — which
is affordable only because [`0002`](./0002-the-judge-is-a-role.md) closed the set
of judge implementations. Nobody outside `enbanc` writes a judge, so the emitted
schema can never be a type a caller must name. Were `Judge` ever a protocol, the
private pair would become public API and this decision would need revisiting.

**Every `answering` resolves, by construction rather than by validation.** The
tribunal is the only writer of ids and it writes both ends, so a response citing
a question that was never asked is not a state the implementation can reach.
There is no check to run and no failure mode to document.

**It fixes one advocate run per interrogatory.** Stamping the link requires
knowing which question the run was for. `tribunal.md` already described a
response as answering one interrogatory, so this makes an existing shape
load-bearing rather than adding a constraint — but if a run is ever allowed to
answer several, `answering` becomes model-emitted and needs validating against
the issued set, at the cost of spending the `Agent(retries=...)` budget on
bookkeeping.

**Cost: two private classes that must move with the public ones.** A field added
to `Continuance` has to be added to `_Continuance` or deliberately withheld from
the judge, and the conversion is a place the two can drift apart. It is one
function at one seam — the same seam that already builds an `Entry` — and it is
the price of the recorded type being strict.

**Rejected: one type, `id: str = ""`, stamped in place.** The cheapest option
and the one the open question was written against. It loses on read-back: with a
default, an artifact missing the field validates into an empty id and the link
dangles silently, in the one document whose job is to be a complete account. It
also makes `Interrogatory(to=..., question=...)` constructible with a
meaningless id, which is the kind of expressible-invalid-state this design
spends types to prevent.

**Rejected: one type with `SkipJsonSchema[str]`.** Pydantic can hide a field
from the generated JSON schema, so the judge would never see `id` while the type
kept it. This is the closest thing to a real single-type answer, and it is worth
recording why it is not one: `SkipJsonSchema` affects schema *generation* only,
not validation, so the field still needs a default or the judge's own output
fails to validate — which lands back on the previous option's weakness with an
extra annotation. It also strips the field from every generated schema,
including one published to describe the artifact.

**Rejected: no stored id, derived from position.** `Interrogatory` would be
exactly what the model emitted, `"r1-q2"` rendered into the advocate's prompt
from `(round, index)` and stored nowhere. The record becomes byte-faithful, and
the count of types stays where it is. It loses because the link becomes
resolvable only by re-deriving the numbering rule: a transcript is meant to be
legible on its own, and this one would need the library's rendering convention —
and the promise never to change it — to be read back at all.

**Rejected: the judge emits ids and the tribunal validates them.** Keeps one
type with `id` genuinely required, and mismatches are already retryable through
the output-validation budget. It loses because uniqueness across rounds is a
property of the record, not of a turn, and asking a model to maintain it spends
retries on bookkeeping the tribunal is holding anyway. It would also make the
audit artifact's link integrity depend on model output, which is the one place
this design consistently refuses to put it.
