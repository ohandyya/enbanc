---
status: accepted
updated: 2026-09-02
---

# 0006. The transcript records filings, not everything an agent saw

## Context

The transcript is the product claim. `../design/tribunal.md` calls it the audit
artifact, `README.md` sells the library on it, and
[`0002`](./0002-the-judge-is-a-role.md) closed the set of judge implementations
specifically to keep the guarantees behind it enforceable.

Nothing had ever defined it. `hear()` was documented as returning
`ruling.transcript` with no statement of what that object contained, and
settling [`0005`](./0005-hear-returns-a-hearing.md) made the gap unavoidable:
`Hearing.transcript` needs a type.

Writing one exposed three things the existing docs had left unsaid — there was
no name or shape for an advocate's answer to an interrogatory, the glossary's
`Argument` carried a "position" that duplicated the advocate's assigned verdict,
and nothing said where a round ends. It also collided with the invariant stated
in `0002`, which is the substantive part of this decision.

## Decision

**A transcript is an ordered list of entries, and an entry is an envelope.**

```python
class Entry(BaseModel, Generic[VerdictT]):
    round: int
    filed_at: datetime
    filing: Filing[VerdictT]
```

`round` and `filed_at` are facts the tribunal knows and the filer does not. This
is [`0005`](./0005-hear-returns-a-hearing.md)'s principle applied a second time:
putting `round` on `Ruling` would put a field on the judge's own output schema
that the judge cannot fill.

**There are exactly five filings**, discriminated by a defaulted `kind` literal:
`Argument`, `Concession`, `Response`, `Continuance`, `Ruling`. One per thing a
participant can enter into the record.

**Only filed exhibits enter the record. Raw tool traffic does not.** An advocate
queries freely and files what it chooses to rely on.

**This narrows the invariant `0002` states absolutely.** That ADR reads:
*nothing enters an agent's context that is not also in the transcript.* Under
this decision that is literally false — an advocate's tool results reach its
context and stop there unless filed. The invariant is restated as **nothing
reaches an agent from outside itself that is not also in the transcript**.
Nothing the library injects, and nothing another participant said, is
off-record. An advocate's own tool traffic is intra-agent: it never reaches
another participant except as a filed exhibit. The judge therefore sees only
filings, and filings remain a complete account of what the ruling rests on.

**The record is complete as to the ruling, not as to the search.**

**A transcript is self-contained.** It carries the question, the statute, and
the case alongside its entries, so a transcript dumped to JSON is a complete
account rather than a fragment that needs its `Hearing` to be legible.

**Author is implied by filing type.** `Argument`, `Concession`, and `Response`
name an `advocate`; `Continuance` and `Ruling` are the judge's by construction.

**An argument has no `position`.** The filing names its advocate, and an
advocate is assigned exactly one verdict.

**A `Response` cites the `Interrogatory.id` it answers**, and interrogatories
are nested inside the `Continuance` that issued them rather than being entries
of their own.

**A round is the advocates' filings plus the deliberation that closes it.**
`max_rounds` counts deliberations, and an interrogatory id names the round it
was issued in.

**`Transcript` iterates and renders**, and that is all it does.

## Consequences

**Rejected: recording every tool call as a sixth filing type.** This is the only
reading that satisfies `0002`'s invariant literally, and it buys something real
— an auditor could see that the advocate for approval pulled a credit report and
declined to file it. It was rejected on the artifact's usability. A proceeding
where four advocates each make a dozen queries produces a record whose evidence
is a small fraction of its bulk, and a transcript nobody reads end to end is not
an audit artifact. The claim being made is that the transcript explains the
ruling; the judge never sees unfiled tool output, so it does not bear on the
ruling.

**Cost, stated plainly: suppression is invisible.** An advocate that gathered
damaging evidence and quietly declined to file it leaves no trace. The
adversarial structure is what is relied on instead — the advocate for the
opposing verdict has its own tools and every incentive to find the same thing —
but that is a mitigation, not a guarantee. This is the consequence most likely
to force a successor ADR, and a successor would have to say what happens to
transcript size.

**Rejected: a per-filing tool-call count.** A middle position — exhibits are the
record, but each filing reports how many calls produced it, so "searched ten
times, filed once" is visible. It satisfies neither reading: it does not make
suppression auditable, since a count names nothing, and it puts a number in the
record whose only use is to provoke suspicion that nothing can resolve.

**Rejected: a stored `author: VerdictT | Literal["judge"]` field.** Uniform, and
it makes "everything this participant said" a single filter rather than an
`isinstance` check. But it makes a `Ruling` authored by an advocate
expressible, and the surrounding design spends real effort keeping states like
that unrepresentable.

**Rejected: interrogatories as top-level entries.** Flatter to iterate, and it
would let a response sit next to its question in the record. But the continuance
that issued them has to be an entry regardless — it is the judge's deliberation
for that round — so the questions would appear twice, and two copies of a
question in an audit record is a defect.

**Rejected: `round` and `filed_at` on each filing.** Flatter to read and filter.
Rejected for the reason the envelope exists; see above.

**Rejected: an entries-only transcript, with question/statute/case on
`Hearing`.** Nothing duplicated, and `Transcript` would not depend on how the
open `Case` question resolves. But the artifact people persist and hand to a
reviewer is the transcript, and one that cannot say what rule was applied to
what facts is not auditable on its own.

**Rejected: pairing responses to interrogatories by round and advocate.** Correct
whenever the judge asks each advocate at most one question per round, and
nothing constrains it to that.

**Consequence: the open `Case` question is now load-bearing.**
`Transcript.case` is typed against `Case`, so if `Case` becomes a generic
container rather than a base class, `Transcript` and `Hearing` each gain a
second type parameter. Recorded as an open question in `../design/api.md`.

**Consequence: `Statute.name` earns its place.** A self-contained transcript is
what makes an identifier for the rule worth storing.

**Constraint on the implementation.** `Filing` and `Deliberation` must be
declared with `TypeAliasType`, not as plain aliases: Pydantic's
`__class_getitem__` returns the origin class for a bare `TypeVar`, so
`Argument[VerdictT] is Argument`, and a plain union alias silently loses its
parameters and fails at annotation-evaluation time. A type checker does not
catch it. Recorded here because it binds the implementation; the detail is in
[`../design/api.md`](../design/api.md#a-note-on-generic-aliases).
