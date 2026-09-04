---
status: draft
updated: 2026-09-04
---

# Prompting and rendering

**PLACEHOLDER — not yet designed.** This file exists to hold a design, and to
name what that design has to settle. Nothing below is a decision.

Required for `0.1.0`. Every behavioural claim in [`tribunal.md`](./tribunal.md)
is only true if the prompt makes it true, and four places in
[`api.md`](./api.md) defer to a document that does not exist yet.

## What this document will own

How `enbanc` turns its own types into text a model reads, and how it turns a
proceeding back into text a human reads. The library owns all of it — the
caller's only lever is `guidance`, which is appended and never substituted
([`0003`](../decisions/0003-models-and-guidance-are-injected.md),
[`0008`](../decisions/0008-guidance-is-human-written.md)).

## Where the existing docs defer to it

- [`api.md`](./api.md#the-inputs) — "Turning a statute into prompt text is
  `enbanc`'s job, not the statute's."
- [`api.md`](./api.md#the-inputs) — the same sentence for `Case`.
- [`api.md`](./api.md#design-commitments) — "Guidance augments; the library owns
  the procedural prompt", listing four things that prompt must carry: the
  `Ruling | Continuance` contract, the rule that interrogatories are targeted
  rather than broadcast, the judge's prohibition on gathering its own evidence,
  and the advocate's licence to concede.
- [`0023`](../decisions/0023-advocates-argue-blind-and-rebut-informed.md) — from
  round 2 an advocate "sees the record as it stood when the continuance was
  filed", with no statement of what that looks like.
- [`evidence.md`](./evidence.md#how-a-source-becomes-an-exhibit) — sketches
  `[s1] Schedule C, 2024 — "net profit: 182,000 …"` explicitly as illustration,
  not as a specified format.
- [`api.md`](./api.md#the-record) — `Transcript.render() -> str`, specified as
  one line.

## Questions it has to answer

- **The two procedural prompts.** What the judge's says and what an advocate's
  says, in full. Both are `enbanc`'s and both are load-bearing: the judge's
  carries the output contract and the no-tools rule, the advocate's carries the
  licence to concede and the citation discipline.
- **Where guidance attaches.** `0003` notes that in PydanticAI `instructions`
  *is* the system prompt, so "append to the procedural prompt" needs a
  mechanical answer: one `instructions` string, a second static system prompt,
  or something else.
- **The round-1 turn.** How `question`, `Statute`, `Case`, and the assigned
  verdict are rendered — and how a `Case` subclass's fields are rendered, given
  that `enbanc` reads no field of one
  ([`0013`](../decisions/0013-a-case-is-a-subclassable-base.md)).
- **The round-2+ advocate turn.** What "the record as it stood" is as text:
  which filings, in what order, how a peer's exhibits appear, and how the
  interrogatory addressed to this advocate is presented beside them.
- **The deliberation turn.** What the judge is shown each round, and whether a
  later round re-renders the record or appends only what is new.
- **How ledger ids reach the model.** The format of a tool result after the
  ledgering toolset has stamped ids onto it, and what an advocate is told about
  how to cite one.
- **What `Transcript.render()` produces, and whether it is the same renderer.**
  A real fork. One renderer serving both the agents and the reviewer makes the
  transcript-completeness invariant checkable by construction; two renderers
  let each read well for its audience and make the invariant something only
  review can enforce. [`tribunal.md`](./tribunal.md#constraints-that-define-the-design)
  is what is at stake — *nothing enters an agent's context that is not also in
  the transcript*.

## What it must not do

Nothing here may put a fact into an agent's context that no transcript holds.
The one standing exception is the retry prompt
([`0021`](../decisions/0021-retry-prompts-are-outside-the-invariant.md)); this
document must not add a second.

## Open questions

*Not yet opened.* The bullets above are the agenda for writing this document,
not a list of live questions in the sense
[`../../CLAUDE.md`](../../CLAUDE.md) rule 7 means.
