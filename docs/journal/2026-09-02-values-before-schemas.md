---
status: current
updated: 2026-09-02
---

# Worked examples caught what schema review missed

The session settled how a proceeding reports not reaching a verdict — exhaustion
became a recorded `Undecided` outcome, infrastructure failure became a raised
`ProceedingFailed`. That decision and everything rejected on the way to it are
in [`0011`](../decisions/0011-exhaustion-is-an-outcome-failure-is-an-error.md);
this entry is about the part the diff cannot show, which is *when* two of the
changes in it were found.

Both were found after the schemas were written, reviewed, and committed to an
ADR — by writing out what `hear()` would literally return in each case. This
repo has no code yet, so there is no test that can disagree with a design. A
worked example is the closest thing available, and it turned out to be a
materially stronger check than reading the types.

## What the examples caught

**A redundant field that survived a full review.** `ProceedingFailed` carried
both `round` (where it stopped) and `rounds` (how many completed). Reading the
class, they look like different facts. Writing out two failure cases put
`round=1, rounds=0` and `round=2, rounds=1` next to each other, and the
invariant was suddenly obvious: a round completes when its deliberation is
filed, so a failure in round *N* always leaves exactly *N-1* behind. One fact
stored twice — the precise thing this design rejects elsewhere, in the same
document, twice over (no `position` on `Argument`, no `author` on any filing).
It survived writing the schema, writing the prose justifying the schema, and
writing an ADR about the schema.

**A gap the types could not express.** Advocates fan out concurrently, so a
failure catches its peers mid-run. Writing a concrete transcript for the failure
case forced the question of whether a peer's filing appears in it — and nothing
in `api.md`, `tribunal.md`, or `0011` answered. At the type level there was
nothing to notice: `transcript: Transcript[VerdictT]` is equally true either
way. It is now an open question in `api.md` rather than something an examples
file decided by accident.

## Why values found what types did not

A schema says what is *representable*. A value has to commit to what is actually
there, so every field must be filled in with something defensible — and a field
that can only ever be computed from another field has nowhere to hide once you
write both down. The same pressure surfaced the gap: a transcript sketch has a
specific number of entries in it, and you cannot write one without answering
what happened to the participants you did not mention.

The cost was low. `outcomes.md` took one pass and is now a design doc in its own
right, so the check is not throwaway work.

## What to do with this

Before treating a new type's schema as settled, write one concrete value per
branch of it — including the failure branches, which are the ones nobody
sketches. Do it before the ADR, not after. Both findings here arrived late
enough that fixing them meant editing an ADR that had already been written; it
was still uncommitted, so no immutability rule was strained, but that was luck
rather than sequencing.
