---
status: accepted
updated: 2026-09-04
---

# 0026. One renderer serves both audiences

## Context

`enbanc` produces proceeding text for two readers. Agents read the record during
a proceeding — a peer's argument, the continuance, the case. A human reads it
afterwards, through `Transcript.render()`, which `../design/api.md` specifies in
one line and nothing else describes.

`../progress.md` named this the fork worth settling first, and the reason is
[`0002`](./0002-the-judge-is-a-role.md)'s invariant: *nothing enters an agent's
context that is not also in the transcript.* Whether that is checkable by
construction or only by review is decided here and nowhere else. Every other
document assumes it holds; this is the one that can make it hold.

The two audiences genuinely differ. A model reads text; a reviewer reads a
document. A reviewer wants the ledger and the failed calls; an agent must never
see another advocate's retrievals
([`0023`](./0023-advocates-argue-blind-and-rebut-informed.md),
[`0019`](./0019-the-ledger-is-part-of-the-record.md)). It is a real fork, not a
formality.

## Decision

**There is one renderer.** It takes a transcript and a viewpoint:

```python
render(transcript, ReviewerView())             # Transcript.render()
render(snapshot,   JudgeView(since=1))
render(snapshot,   AdvocateView(DENY, since=1))
```

The suffix keeps the viewpoints clear of `Judge` and `Advocate`, which already
name participants. They are internal; `Transcript.render()` is the only public
way in.

**Every agent viewpoint is a strict subset of the reviewer's.** `JudgeView` and
`AdvocateView` drop the ledger, drop the failures, and drop the filings the
participant has already been shown. They add nothing. An agent's view differs
from the reviewer's by *filter* alone and never by text.

**A view is taken against a snapshot.** An advocate dispatched in round 2 renders
the transcript as it stood when the continuance was filed, which is `0023`'s
wording made mechanical and is what makes a concurrent round safe to render:
peers filing at the same moment are not in the snapshot.

**An advocate's own filing is in its delta**, not carved out, so the projection
stays a plain filter with no per-participant exception.

`../design/prompting.md` owns the resulting text.

## Consequences

**The invariant becomes checkable by construction.** There is no code path that
renders for an agent something the transcript does not hold, because the only
input is a transcript and the only difference between views is which rows are
dropped. Under two renderers the guarantee would be a property of whatever the
agent-facing one happens to emit today — reviewable, and quietly breakable by any
change to it.

**A framing sentence cannot be added by accident.** The failure
`../design/tribunal.md` warns about — "a framing turn, a reminder, or a summary
injected into an agent's history and nowhere else" — is not reachable through a
filter. Anything an agent is to be told has to become a transcript field first,
which is the seam
[`0025`](./0025-the-record-includes-what-steered-it.md) just used for four of
them.

**Cost: the reviewer's view cannot be tuned independently of what models parse
well.** A rendering choice made because a model reads it more reliably is a
rendering choice a human then reads, and the reverse. That is a real loss —
prose and headings that would suit a report are constrained by having to double
as prompt text.

It is accepted because the alternative pays for that freedom with the invariant,
and because the constraint is weaker than it looks: the two audiences want the
same thing from this artifact. A reviewer auditing a ruling and a judge weighing
one both need the filings in order, the exhibits attached to their claims, and
the references legible. `../design/prompting.md`'s reviewer view is not a
compromise between two formats; it is the agent view plus the three sections an
agent may not see.

**Cost: the projections are where the risk moves, not where it disappears.** A
wrong `since`, or a filter that forgets to drop the ledger, breaks the invariant
as thoroughly as a second renderer could. What changes is that the mistake is in
one small, enumerable place — a viewpoint — rather than distributed through a
body of formatting code.

**Consequence: `Transcript.render()` is no longer a one-line specification.** It
is the `Reviewer` viewpoint, and what it emits is fixed by
`../design/prompting.md` rather than left to implementation. Its output is also
versioned: it is part of the prompting surface `Transcript.procedure` names,
because the same renderer feeds the agents.

**Rejected: two renderers, tuned per audience.** Each reads well for its reader,
and the agent-facing one is free to be terse and id-dense while
`Transcript.render()` is free to be a document. Rejected because it makes the
invariant something only review can enforce, in a library whose product claim is
that the record completely explains the ruling. The saving is aesthetic; the cost
is the guarantee.

**Rejected: one renderer with agent-only additions.** A single renderer that
takes a viewpoint but is permitted to *add* instruction text per view — "answer
only the interrogatory addressed to you" emitted alongside the record. Rejected
because an addition is exactly the thing the subset property forbids, and the
text in question belongs in the procedural prompt, where `0025` records it by
version. Turn instructions live in the turn template around the rendered record,
not inside it.
