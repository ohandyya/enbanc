---
status: accepted
updated: 2026-09-09
---

# 0032. A design doc is mirrored by tests, not executed as them

## Context

`../design/outcomes.md` is 900 lines of every way a proceeding can end, each one
written out as concrete values: a full `Hearing` with seven entries, a five-row
ledger, per-participant usage, three `ConfigurationError` messages quoted
verbatim, and a serialization round trip. `../design/testing.md`'s original notes
called it "the spine" and named the question this ADR answers as the main
decision to make: *whether those examples become executable, and stay in sync
with the doc.*

The pull toward executing them is strong and worth stating fairly. Two artifacts
describe the same behaviour. One is checked by a machine on every commit and one
is checked by whoever happens to reread it. Everyone has seen the second kind go
stale.

`../journal/2026-09-02-values-before-schemas.md` records why the doc is written
the way it is: putting concrete values on the page caught a redundant field and
an unanswerable gap that reviewing the schemas had not. Its value comes from
being read.

This generalizes past `outcomes.md`. `../design/prompting.md` quotes both
procedural prompts and four turn templates in full; `../design/execution.md`
writes out a whole proceeding as literal messages. The question is a repository
policy, not a decision about one file.

## Decision

**Tests mirror a design document. Nothing extracts and runs it.**

`outcomes.md`'s seven sections become seven test modules under
`tests/unit/outcomes/`, sharing one factory that builds the tribunal the document
fixes at the top. The mapping is a table in `../design/testing.md`. The same
pattern applies to any future document written as worked values.

**What holds the two in step is rule 2 in `../../CLAUDE.md`** — a change to
behaviour updates the design doc in the same commit — and the fact that a change
to behaviour is exactly what turns these tests red. The tests are the alarm; the
rule is the remedy.

**The design document keeps its `repr` prose.** `<LoanDecision.DENY: 'deny'>`,
`entries=[...]`, and `# never cited by APPROVE` stay as they are. They are
written to be read.

## Consequences

**Documents stay written for humans.** Elision, inline commentary, and repr forms
are available wherever they make a point land, with no obligation to remain
parseable.

**A design document remains the spec.** It says what must be true; the tests
check that it is. That direction is `../../CLAUDE.md` rule 1 and this preserves
it.

**Cost: drift is possible.** A behaviour change that updates the tests and
forgets the prose leaves the document quietly wrong, and nothing catches it. This
is the genuine loss and it is the whole reason the alternatives are tempting. It
is accepted because the failure is bounded — the tests still encode the truth, so
the recovery is an edit rather than an investigation — and because the mechanisms
that would close it cost more than the gap, as below.

**Cost: some duplication.** The `outcomes.md` tribunal exists twice, once as
prose and once as a fixture. Accepted; it is one small object.

**Rejected: extracting and running the document's fenced code blocks.** Sync
becomes mechanical and drift becomes impossible. Rejected because the examples
are not executable and could only be made so by rewriting them for the machine:
the enum reprs are not valid expressions, `...` stands in for values a reader
does not need, and the inline comments sit inside the literals. The result is a
document optimized for a parser, and prose written to stay runnable degrades as
prose — which would cost exactly the property
`../journal/2026-09-02-values-before-schemas.md` credits with finding two real
defects.

**Rejected: generating the document from test snapshots.** The tests produce the
values and the document quotes what they produced, so it can never be wrong.
Rejected because it inverts authorship. The document stops being the thing the
code must satisfy and becomes a report of what the code did, which contradicts
`../../CLAUDE.md` rule 1 and would have made `outcomes.md` impossible to write —
it was written before there was any code to generate it from, and that is where
its value came from.

**Rejected: a linter that checks the doc against the tests.** Some third artifact
asserting the two agree. Rejected because it is a parser for prose, and it fails
in the direction that helps least: it is easy to make it complain about a
document that is fine and hard to make it notice one that is subtly wrong.
