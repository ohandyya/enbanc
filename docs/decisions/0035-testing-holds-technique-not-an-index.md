---
status: accepted
updated: 2026-09-11
---

# 0035. `testing.md` holds technique, not an index of what tests what

## Context

[`0032`](./0032-a-design-doc-is-mirrored-by-tests.md) settled that a design
document is mirrored by hand-written tests rather than extracted and executed as
them. It did not say *where the mirror is recorded*, because at the time there
was one mirror: `../design/outcomes.md`'s seven sections, mapped to seven modules
by a table in `../design/testing.md`.

[`../design/packaging.md`](../design/packaging.md) made that a real question. It
specifies two tests — `tests/unit/test_export_surface.py`, which pins the
twenty-nine-name `__all__`, and `tests/unit/test_import_is_inert.py`, which
checks that `import enbanc` performs no I/O and pulls in no provider SDK — and it
names both inline, in the paragraphs that state the claims they pin. Nothing in
`testing.md` knows they exist.

So either `testing.md` is the register of which test pins which claim and it is
missing two rows, or a document naming its own mirror is the pattern and the
table is something else. Left unanswered, the next design document that specifies
a test picks one by coin flip.

## Decision

**A design document names its own mirror, beside the claim it pins.**
`testing.md` holds technique — how a model is faked, how a prompt is pinned, how
Tavily is faked, how the transcript invariant is asserted, and what must not be
asserted at all — and is not an index of what tests what.

**`outcomes.md`'s table stays, as a stated exception.** It is in `testing.md`
because `outcomes.md` cannot hold it: that document is worked values written to
be read, and threading a module path through seven sections of `repr` prose would
damage the readability [`0032`](./0032-a-design-doc-is-mirrored-by-tests.md)
exists to protect.

The test that separates the two: **the mapping lives with the claim unless
putting it there would damage the document.**

## Consequences

**No second place to keep true.** An index in `testing.md` would have to be
updated whenever any design document gained a test, and its failure mode is
silence — a document gains a test, the index does not, and nothing catches it.
This is the objection the library already makes to `position` on an `Argument`
([`../design/api.md`](../design/api.md#what-participants-file)) and to a `cited`
flag on a `Retrieval` ([`0019`](./0019-the-ledger-is-part-of-the-record.md)):
two places that can disagree about one fact.

**A named test cannot drift from the claim it pins**, because they are in the
same paragraph. A claim edited without its test noticed is a diff a reviewer sees
in one hunk.

**`testing.md` stays readable as it grows.** Every section in it answers *how do
you test this at all?* Adding rows for tests that need no technique —
`sorted(enbanc.__all__) == [...]` needs none — would dilute a strategy document
into a catalogue.

**Cost: "where is X tested?" is a grep, not a table read.** Accepted. The grep is
exact, and the alternative is a table that is authoritative only while someone
maintains it.

**One thing did move to `testing.md`, and it is the right kind of thing.**
`test_import_is_inert.py` must run in a subprocess, and a subprocess carries none
of the socket guard that
[`0031`](./0031-tests-are-tiered.md) makes the offline tiers' enforcement. That is
technique, and it touches a guarantee `testing.md` owns, so the offline-guarantee
section now names that test as the single sanctioned exception and says why a
second one would need the argument made again. The rule and its exception landed
in the same edit.

**Rejected: `testing.md` as the register, with a row per test.** Every mirror in
one place, so "what covers this document?" is one read. Rejected for the
second-place-to-disagree reason above, and because it inverts the direction of
authority: a design document would state a claim and some other document would
decide whether it was checked.

**Rejected: moving `outcomes.md`'s table into `outcomes.md`.** It would make the
rule uniform with no exception to explain. Rejected because it costs the thing
`0032` was written to protect — `../journal/2026-09-02-values-before-schemas.md`
credits that document's readability with catching a redundant field and an
unanswerable gap that reviewing the schemas had not.

**Rejected: a generated index.** Some tool walking `tests/` and emitting the
mapping. Rejected on the same grounds `0032` rejected generating documents from
snapshots: it inverts authorship, and it can only report what the tests are
named, not what they were meant to pin.
