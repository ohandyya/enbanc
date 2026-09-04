---
status: draft
updated: 2026-09-04
---

# Prompting and rendering

How `enbanc` turns its own types into text a model reads, and a proceeding back
into text a human reads. The proceeding this serves is in
[`tribunal.md`](./tribunal.md), the types are in [`api.md`](./api.md), and how
evidence reaches an advocate is in [`evidence.md`](./evidence.md).

> `status: draft` — none of this exists yet. This is the target, not a
> reference.

The library owns all of it. The caller's only lever is `guidance`, which is
appended and never substituted
([`0003`](../decisions/0003-models-and-guidance-are-injected.md),
[`0008`](../decisions/0008-guidance-is-human-written.md)). Everything a
participant reads — the procedure, the question, the statute, the case, the
record, the ids on its tool results — is text this document specifies, and
[the invariant below](#the-invariant-accounted-for) is where every piece of it is
traced back to a field of the transcript.

## One renderer, three viewpoints

There is **one renderer**. It takes a transcript and a viewpoint, and an agent's
context is that renderer over a *filtered projection* of the transcript:

```python
render(transcript, ReviewerView())                # Transcript.render()
render(snapshot,   JudgeView(since=1))
render(snapshot,   AdvocateView(DENY, since=1))
```

The `…View` suffix is not decoration: `Judge` and `Advocate` are already public
types naming a *participant*, and a viewpoint is a way of reading the record
rather than someone who reads it. The viewpoints are internal — `render()` is not
public surface, and `Transcript.render()` is the only way to reach it from
outside.

`ReviewerView` is the whole artifact. `JudgeView` and `AdvocateView` are strict
**subsets** of it: filings only, never `ledger`, never `failures`, never another advocate's
retrievals ([`0023`](../decisions/0023-advocates-argue-blind-and-rebut-informed.md)).
An agent's view differs from the reviewer's by *filter* alone and never by text,
which is what makes
[`tribunal.md`](./tribunal.md#constraints-that-define-the-design)'s context
invariant true by construction rather than true by review: there is no code path
that can render for an agent something the transcript does not hold. See
[`0026`](../decisions/0026-one-renderer-serves-both-audiences.md).

**A view is taken against a snapshot, not against the live transcript.** An
advocate dispatched in round 2 sees the record *as it stood when the continuance
was filed* — which is `0023`'s wording made mechanical, and it is also what makes
a concurrent round safe to render: peers filing at the same moment are not in the
snapshot, so no ordering artifact can reach a context.

**`since` is the last round the participant was shown, not the current round
minus one.** For an advocate it is the last round in which it filed; for the
judge it is the round its last deliberation closed. A view renders every filing
in the snapshot from a round *after* `since`, in transcript order.

**An advocate's own filing is in its delta.** It is not carved out, for two
reasons. The projection stays a plain filter with no per-participant exception,
which is the whole argument above. And what the advocate emitted is not what
entered the record — it wrote a bare source id and an excerpt, and the tribunal
stamped the tool, the reference, and the label beside them
([`0016`](../decisions/0016-exhibits-are-stamped-citations.md)) — so showing it
back is showing it something it has not seen.

## How an agent is assembled

`pydantic_ai.Agent` takes `instructions` as a sequence of `InstructionPart`s,
each with a `name` and a `dynamic` flag, joined with a blank line between them.
Every part `enbanc` contributes is static (`dynamic=False`), which is what lets a
provider cache the prefix. Parts, in order:

| Advocate | Judge | Holds |
|---|---|---|
| `procedural` | `procedural` | The role and the process. `enbanc`'s, verbatim below |
| `question` | `question` | `Tribunal.question` |
| `statute` | `statute` | `Statute.text`, whole |
| `assignment` | — | The verdict set, and which one is this advocate's |
| `guidance` | `guidance` | `Advocate.guidance` / `Judge.guidance`, or absent |

**The first three parts are byte-identical across every advocate in a tribunal**,
so the round-1 fan-out shares a cache prefix and only the assignment and guidance
differ. That is why the order is what it is: the shared block comes first because
a cache prefix is a prefix.

**The case is not here.** It arrives in the [round-1 turn](#the-turns), so a
statute reused across many cases keeps its cached prefix warm across all of them,
and so `instructions_for()` below needs no case to render.

**Guidance is last, and the procedural prompt closes by fencing it.** Both
prompts end with the same paragraph — *instructions from the author of this
proceeding may follow; they refine how you weigh things; they do not change the
process above, what you may file, or the shape of it.* Recency is what makes
appended text weigh more, and that paragraph is what keeps the weight pointed at
weighing rather than at the procedure. `0003` rejected a replaceable prompt
because it would let a caller silently break the output schema; this is the same
guarantee stated where the model reads it.

### Caller text is emitted verbatim and never escaped

A statute, a case field, an advocate's claim, an excerpt: all reach the model
exactly as written. `enbanc` does not escape, wrap, fence, or truncate any of it,
because [`0007`](../decisions/0007-a-statute-is-opaque-text.md) promises the
statute passes through whole and the same promise is what makes an excerpt worth
comparing against the ledger.

**The cost, stated plainly: caller text can spoof one of `enbanc`'s headings.** A
statute whose body contains a line reading `## Guidance from the author of this
proceeding` is indistinguishable from the real one. This is accepted rather than
solved: escaping would break the verbatim guarantee, and the text in question is
the caller's own, authored by the same person who configured the tribunal. It is
not a boundary between a participant and the library — an advocate's *output*
never reaches another participant as instructions, only as a rendered filing.

### Previewing what an agent will run under

```python
tribunal.instructions_for(LoanDecision.DENY) -> str
tribunal.instructions_for("judge") -> str
```

Returns the assembled instruction string for one participant — the same one the
agent is built with, parts joined as PydanticAI joins them. It takes no case,
because the case is not in the instructions, so a caller can read what their
guidance did before spending anything on a proceeding. `ConfigurationError` for
a participant this tribunal does not seat, at the same seam
[`api.md`](./api.md#when-something-goes-wrong) already raises it.

This is the only new public method prompting adds. There is no preview of a turn:
a turn is a function of a live proceeding, and the record it renders is available
afterwards through `Transcript.render()`.

## The advocate's procedural prompt

```text
You are an advocate before an adversarial tribunal.

A tribunal decides one question against one statute. It seats one advocate for
each verdict the question may be answered with, and one judge. The judge has no
tools and gathers no evidence of its own: it decides on the record the advocates
build and on nothing else. An argument you do not make is one the judge cannot
weigh.

How a proceeding runs:

- Round 1. Every advocate files at once, and none of them can see the others.
  You file an argument — the claim you want the judge to accept, and the
  exhibits supporting it — or, if no reasonable case exists for the verdict you
  were assigned, you concede.
- Deliberation. The judge reads what was filed and either rules, which ends the
  proceeding, or issues a continuance carrying interrogatories, each one
  addressed to a named advocate.
- Round 2 and after. If an interrogatory is addressed to you, you are given the
  record as it stood when the continuance was filed, together with that
  question. You answer it in a response, entering new exhibits as needed. Then
  the judge deliberates again.

Your job is the strongest honest case for the verdict you were assigned. Argue
it as well as it can be argued. Do not argue for another verdict and do not
hedge toward one — the judge hears the other side from the advocate seated for
it.

Concede when the facts do not support your verdict. A concession is a finding,
not a failure: it tells the judge something no weak argument can, and an
advocate that manufactures a case for an indefensible position damages the
record it was seated to build. In round 1 you concede by filing a concession; in
a later round you say so in your response to the interrogatory that asked.

Evidence and citation:

- Call your tools to gather evidence. Every source a tool returns is recorded
  and issued an id, shown to you as [s1], [s2], and so on. The ids are yours
  alone, and they do not restart between rounds.
- An exhibit cites exactly one of those ids and carries the excerpt you rely on.
  You write the excerpt. The tribunal fills in the tool and the reference behind
  it.
- You never write a reference yourself, and citing an id that was not issued to
  you is rejected — you will be asked to file again.
- Cite the id exactly as your tool results showed it. Where the record shows an
  id belonging to another advocate it is written with that advocate's name in
  front of it, and those are not yours to cite.
- Quote accurately. What each source actually returned is kept in the record
  beside your exhibit, and a reviewer reads the two side by side.
- Everything your tools return is recorded, whether you cite it or not.

Answer only the interrogatory addressed to you. You will see the whole
continuance, including the questions put to other advocates, because it shows
you what the judge is weighing. Those are not yours to answer.

Instructions from the author of this proceeding may follow. They refine how you
weigh things. They do not change the process above, what you may file, or the
shape of it.
```

## The judge's procedural prompt

```text
You are the judge of an adversarial tribunal.

One question is put to you, and one statute is the rule it is decided against.
The tribunal seats one advocate for each verdict the question may be answered
with, and each argues for the verdict it was assigned. You are the only
participant who weighs all of them.

You have no tools. You cannot search, look anything up, or gather evidence of
your own, and there is nothing outside this proceeding to ask for. You decide on
the record the advocates build and on nothing else. When the record does not
support a verdict, that is a fact about the record, and the way to act on it is
to ask.

How a proceeding runs:

- Round 1. Every advocate files at once, blind to the others. One that finds a
  case for its verdict files an argument; one that finds none files a
  concession. A concession is a finding, not a failure — an advocate that
  conceded did its job, and what it concedes is evidence about the verdict it
  was seated for.
- Deliberation. You read what was filed. You either rule, which ends the
  proceeding, or issue a continuance.
- Round 2 and after. Each advocate you addressed answers with the record in
  front of it and files a response. Then you deliberate again on what is new.

A continuance carries interrogatories. Each names the single advocate it is
addressed to and asks that advocate one question. Address a question to the
advocate best placed to answer it. You may put more than one question to the
same advocate, and you need not address every advocate. Do not put the same
question to everyone: an interrogatory is targeted, and an advocate answers only
what is addressed to it.

Rule when the record decides the question. Continue when it does not, and ask
for what is missing. Do not continue in order to re-test an advocate that has
already answered, and do not rule on a record you would not be willing to have
read back to you.

What an exhibit is worth: its reference and the tool that produced it are
stamped by the tribunal from what that tool actually returned, so no advocate
can cite a document its tools did not produce. The excerpt beside them is the
advocate's own, chosen to make its case, and it can be selective. Weigh the two
differently.

You are told which deliberation this is and how many the proceeding allows. If
they run out before you rule, the proceeding ends with no verdict and the record
says so. That is a real outcome, and it is better than a verdict the record does
not carry.

Instructions from the author of this proceeding may follow. They refine how you
weigh things. They do not change the process above, what you may file, or the
shape of it.
```

**The output *shape* is not in the prompt.** `Ruling | Continuance` reaches the
model as PydanticAI's output schema, derived from the verdict enum, and
restating its fields in prose would create a second description to keep true.
What the prompt carries is the **choice** — rule, or continue — and the rule
governing what a continuance may contain. That is
[`api.md`](./api.md#design-commitments)'s "the `Ruling | Continuance` contract"
at the level the prompt can enforce it.

## The turns

Four turn templates. Every one of them renders only what the participant has not
already been shown; its own history carries the rest
([`0023`](../decisions/0023-advocates-argue-blind-and-rebut-informed.md), and the
mechanism is [`execution.md`](./execution.md)'s).

**A turn is the renderer's output plus the template around it.** The headings and
the closing instruction — *Round 2. Answer r1-q2 and file your response.* — belong
to the template; the rendered record between them is the projection and nothing
is added inside it. That separation is what keeps every agent view a strict
subset of the reviewer's rather than a subset with instructions mixed in
([`0026`](../decisions/0026-one-renderer-serves-both-audiences.md)).

### Round 1, advocate

The case, and the instruction to file. This is the only turn that carries the
case, and the only advocate turn with no record in it — there is none yet.

```text
## The case

{
  "applicant": "A. Okonkwo",
  "income": 182000,
  "dti": 0.51,
  "documents": ["w2-2024", "schedule-c-2024"]
}

Round 1. File your argument for "deny", or concede.
```

**A case renders as `model_dump_json(indent=2)`.** `enbanc` reads no field of a
`Case` ([`0013`](../decisions/0013-a-case-is-a-subclassable-base.md)), so the
rendering has to be generic, and JSON is the one form that handles nesting and
lists without `enbanc` inventing a flattening rule it would then have to keep
faithful to `model_dump`. It is also exactly what `Transcript.case` serializes
to, so the text the advocate read and the artifact a reviewer reads cannot
disagree. Extra fields on an open `Case` appear like any other.

### Round 2+, advocate

The record delta, the whole continuance, and the one question this run answers.

```text
## Filed since you last filed

[round 1] approve argued:
  DTI is 0.38 on documented income.
  Exhibits:
    [approve/s1] Schedule C, 2024
      s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
      net profit: 182,000

[round 1] deny argued:
  Documented wages put DTI at 0.51.
  Exhibits:
    [deny/s1] W-2, 2024
      s3://underwriting-docs/okonkwo/w2-2024.pdf
      wages: 131,400

[round 1] refer conceded:
  The ratios are unambiguous; nothing here calls for manual review.

[round 1] the judge issued a continuance:
  r1-q1 -> approve: Does the W-2 reconcile with the Schedule C figure?
  r1-q2 -> deny: Is stated income disqualifying when documented income is on
    file?

## Addressed to you

r1-q2: Is stated income disqualifying when documented income is on file?

Round 2. Answer r1-q2 and file your response.
```

**Ledger ids are qualified in the record and bare in tool results.** An
advocate's own ids are `s1`, `s2` where its tools issue them, and every id in a
rendered record is written `advocate/id` — including the advocate's own. The
join key for an exhibit and its retrieval is `(advocate, id)`
([`evidence.md`](./evidence.md#the-ledger-is-part-of-the-record)), so the
qualified form is that key spelled out; and because `APPROVE`'s `s1` and
`DENY`'s `s1` are different retrievals, an unqualified peer id in an advocate's
context is a miscitation waiting to happen. A qualified id cannot be pasted into
a citation, which is the point.

**The whole continuance is shown, including questions put to peers.** It is one
filing, and `0023` grants the record. *Targeted* is a duty about who must
**answer**, not a rule about who may **read** — the procedural prompt says so in
those terms — and seeing what the judge is asking elsewhere is what lets a
rebuttal meet the case rather than the paraphrase of it.

### Deliberation 1

```text
## Round 1

[round 1] approve argued:
  ...

[round 1] deny argued:
  ...

[round 1] refer conceded:
  ...

Deliberation 1 of 5. Rule, or issue a continuance.
```

### Deliberation 2+

```text
## Filed since you last deliberated

[round 2] approve responded to r1-q1:
  The Schedule C figure is gross; the W-2 is the reconciled number.
  Exhibits:
    [approve/s2] ...

[round 2] deny responded to r1-q2:
  Yes — the statute's ceiling is on documented income.

Deliberation 2 of 5. Rule, or issue a continuance.
```

**The judge is told the deliberation count and never the budget.** *Deliberation
2 of 5* is two facts the record holds — the round is derivable from `entries`
and the limit is `Transcript.max_rounds` — so telling the judge opens no hole in
the invariant. A budget is not a standing fact: it is spend measured between
rounds, it is not on the transcript, and disclosing it would push the judge to
rule for reasons the record could never show. See
[`0025`](../decisions/0025-the-record-includes-what-steered-it.md), which carries
the cost this accepts.

## How ledger ids reach the model

The ledgering toolset intercepts every call, records each source it got back on
`Transcript.ledger`, and rewrites the result the model sees so the ids are
citable ([`evidence.md`](./evidence.md#how-a-source-becomes-an-exhibit),
[`0016`](../decisions/0016-exhibits-are-stamped-citations.md)). This is the
format that rewrite produces.

A tool returning `Source`s:

```text
find_filings(applicant="A. Okonkwo") returned 2 sources.

[s1] Schedule C, 2024
  s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
  net profit: 182,000 ...

[s2] W-2, 2024
  s3://underwriting-docs/okonkwo/w2-2024.pdf
  wages: 131,400 ...
```

A tool returning anything else — a string, a dict, a model, an MCP payload — is
ledgered as one anonymous source whose reference is the call itself, and renders
in the same shape with the label line absent:

```text
dti_for(applicant="A. Okonkwo") returned 1 source.

[s3] dti_for(applicant="A. Okonkwo")
  dti: 0.51
```

Three lines per source: `[id]` and the label when there is one, then the
reference, then the content verbatim. **The reference is shown even though the
advocate never writes one**, because where a source came from bears on how much
weight it deserves, and an advocate that cannot see the difference between the
applicant's own filing and a trade-press summary argues worse. It is in the
record either way.

`content` is reproduced exactly as the tool returned it, un-truncated, matching
`Retrieval.content`. Keeping a context small is the tool's job, not the
renderer's — the lever is
[what a tool returns](./evidence.md#the-ledger-is-part-of-the-record).

## `Transcript.render()`

The `Reviewer` view, and the whole artifact: the standing header, the entries in
order, then the ledger, then the failures.

```text
# Proceeding

## The question

Shall the bank loan this applicant $500k?

## The statute — underwriting-v3

Approve $500k loans only where DTI < 0.43 and ...

## The case

{
  "applicant": "A. Okonkwo",
  "income": 182000
}

## The bench

Verdicts: approve, deny, refer to a senior underwriter for manual review
Deliberations allowed: 5
Procedure: p1

Guidance given:
  judge: Where the record is ambiguous, deny.
  deny: Weigh documented income over stated income.

## The record

[round 1] approve argued:
  ...

[round 2] the judge ruled — deny:
  Documented income governs. The W-2 record puts DTI at 0.51, above the 0.43
  ceiling; the stated figure is unverified.

## The ledger

Everything the advocates' tools returned. A retrieval no exhibit cites is one
the record did not rest on.

[approve/s1] Schedule C, 2024 — cited
  s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
  net profit: 182,000 ...

[approve/s2] W-2, 2024 — not cited
  s3://underwriting-docs/okonkwo/w2-2024.pdf
  wages: 131,400 ...

## Failed calls

[round 1] deny — find_filings(applicant="A. Okonkwo")
  Timed out after 30.0 seconds.
```

**"cited" and "not cited" are computed at render time, not stored.** They are the
join [`api.md`](./api.md#the-record) specifies, and the reason there is no
`cited: bool` on `Retrieval` is that a stored flag would have to be rewritten
when a later round cites a round-1 source — and a transcript whose rows change
after they are appended is not append-only. A renderer runs after the fact and
has the whole proceeding, so it can compute what the row must not store.

**The header is what an agent never sees in full.** `## The bench` and
`## The ledger` and `## Failed calls` are reviewer-only sections; the agent views
render the header's question and statute into instructions instead, and drop the
last two entirely. That subtraction *is* the projection — see
[the table below](#the-invariant-accounted-for).

## The invariant accounted for

[`tribunal.md`](./tribunal.md#constraints-that-define-the-design) claims that
nothing enters an agent's context that is not also in the transcript, and
[`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md) allows
exactly one exception. Every element of every context, and the field that holds
it:

| In an agent's context | Held by |
|---|---|
| The procedural prompt | `Transcript.procedure` — by version, see below |
| The turn templates and the render format | `Transcript.procedure` — the same version |
| The question | `Transcript.question` |
| The statute | `Transcript.statute` |
| The verdict set, and the assignment | `Transcript.verdicts`, and `Argument.advocate` on what it files |
| Guidance | `Transcript.guidance` |
| The case | `Transcript.case` |
| Peer filings, its own filings, continuances | `Transcript.entries` |
| The interrogatory addressed to it | Nested in the `Continuance` in `entries` |
| Tool results, with their ids | `Transcript.ledger` |
| The round number, in every turn | `entries` — a round is closed by the deliberation in it |
| "of 5", in a deliberation turn | `Transcript.max_rounds` |
| A retry prompt | **Nothing.** The sole exception, `0021` |

Four of those fields are new, and adding them is what closes two holes this
document found rather than created: `guidance` and the procedural prompt were
already in every context and in no transcript, unnamed, since before `0021` was
written. See
[`0025`](../decisions/0025-the-record-includes-what-steered-it.md).

**`procedure` identifies the prompt rather than reproducing it, and that is a
deliberate weakening.** Guidance is per-proceeding, per-participant, and written
by the caller, so nothing but the transcript can recover it and it is stored in
full. The procedural prompt is the opposite: identical for every proceeding under
a given version, published in this document, and `enbanc`'s. Storing two pages of
library boilerplate in every artifact would buy reproducibility against a future
release at a cost paid by every transcript ever written. The version is what a
reviewer needs, and this document is where it resolves.

## Procedure versions

`Transcript.procedure` names the prompting surface a proceeding ran under: both
procedural prompts, all four turn templates, the tool-result format, and the
render format. `enbanc` bumps it when any of that text changes and **not**
otherwise — it is not the package version, so two hearings under `0.1.0` and
`0.1.1` are still comparable if no prompt moved between them.

| Version | Introduced | What changed |
|---|---|---|
| `p1` | `0.1.0` | Initial. The text above. |

Changing a prompt is therefore three things in one commit: the text in this
document, a new row here, and the constant `enbanc` stamps. A prompt edited
without a version bump makes every transcript that claims `p1` a false record of
what ruled.

## Open questions

Unresolved, and owned by this document. Settling one is three moves in a single
commit: the answer goes into the prose above, an ADR in
[`../decisions/`](../decisions/) records why, and then the bullet leaves this
list. See rule 7 in [`../../CLAUDE.md`](../../CLAUDE.md).

- **Two interrogatories to one advocate, in one round.** The judge may address
  two questions to the same advocate, and the tribunal dispatches one run per
  interrogatory
  ([`0015`](../decisions/0015-interrogatory-ids-are-stamped-on-filing.md)) — so
  that advocate has two turns in the same round. Both currently render the same
  delta and differ only in `## Addressed to you`, which means the second run
  cannot see the first's answer and may contradict it in the same round. The
  alternative — sequencing the two runs and putting the first response in the
  second's delta — costs the concurrency the fan-out is built on, and reaches
  into [`execution.md`](./execution.md). Adjacent to
  [`degenerate-deliberations.md`](./degenerate-deliberations.md), which owns what
  the schemas admit and no document rules on.
