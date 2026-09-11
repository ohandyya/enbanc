---
status: accepted
updated: 2026-09-11
---

# 0034. The export surface is the package

## Context

`src/enbanc/__init__.py` is a two-line `hello()` stub. The next commit writes the
`0.1.0` schemas into it, and the moment it does, three things are settled that
nobody deliberated over: which modules exist, which of them a user may import,
and what `__all__` means.

[`../design/packaging.md`](../design/packaging.md) had carried the question as a
placeholder — *"decisions to make in code as the first modules land, recorded here
only so they are not mistaken for oversights"* — on the reasoning that a layout is
small enough to settle while writing it. That reasoning does not survive contact
with the rest of the design.

[`../design/api.md`](../design/api.md) specifies twenty-nine public names across
seven schema sections, plus a private emit-pair
([`0015`](./0015-interrogatory-ids-are-stamped-on-filing.md),
[`0016`](./0016-exhibits-are-stamped-citations.md)) that must not reach a caller.
[`../design/execution.md`](../design/execution.md) names five internal machines.
[`0031`](./0031-tests-are-tiered.md) puts `enbanc`'s own behaviour in
`tests/unit/`, so those machines are imported by path from a test and their
locations are a public fact of the repository even when they are not a public
fact of the package. And a layout settled in code is settled *once* — the first
user to import `enbanc.transcript` makes it supported retroactively, whatever a
document says.

The question underneath is what kind of thing a boundary is. Every other boundary
in this library is structural: a filing cannot name a judge as its author because
no field can hold one; a transcript cannot disagree with the live stream because
one coroutine owns the append; an advocate cannot fabricate a reference because it
never writes one. A public API defined by a list in prose is the one boundary that
would be held by documentation alone.

## Decision

**Two importable namespaces, `enbanc` and `enbanc.tools`. Every other module is
underscore-prefixed.**

There is no `enbanc.transcript`, no `enbanc.errors`, no `enbanc.schemas`. The
private modules are named for the design documents that specify them —
`_prompting.py`, `_ledgering.py`, `_proceeding.py` — and the map is in
[`../design/packaging.md`](../design/packaging.md#the-modules).

**`__all__` is the contract, and `api.md` is the list.** Everything named in that
document's `Shape` and `Schemas` blocks is public, plus `Source`, which
[`../design/evidence.md`](../design/evidence.md#adding-your-own-tool) spells
`from enbanc import Source`. Nothing else is. The rule is mechanical: membership
is decided by whether the name appears in `api.md`, not name by name.

**A test mirrors the list.** `tests/unit/test_export_surface.py` asserts the
sorted `__all__` against the twenty-nine literals and that every one resolves.
This is [`0032`](./0032-a-design-doc-is-mirrored-by-tests.md) applied to a
document whose worked value happens to be a list of strings.

## Consequences

**Internal reorganization cannot break a caller.** Splitting `_filings.py`,
merging `_hearing.py` into `_transcript.py`, or renaming `_prompting.py` is a
patch-level change with nobody to notify, because no supported name pointed
inside. This is the whole return on the decision, and it is largest early, when
the layout is most likely to be wrong.

**The boundary stops being a promise.** "These are the public names" is checked by
the import system and by one test, rather than by whoever reads the README. It is
the same substitution this library makes everywhere else, and `0.1.0` is the only
release in which it is free.

**Adding a public name becomes a deliberate act.** It requires editing `api.md`,
editing `__all__`, and editing the test's literal list — three places, one diff,
reviewable. A name cannot become public by being defined in a module someone
happened to import.

**`Deliberation` is exported although no public signature returns one.** The
judge's real `output_type` is `Ruling[VerdictT] | _Continuance[VerdictT]`, and a
transcript holds `Filing`. Accepted, and the cost is one name: a mechanical rule
that occasionally exports an unused alias is worth more than a per-name judgment
that has to be re-made on every addition. If the alias should not be public, the
edit belongs in `api.md`.

**Cost: a user who needs an internal has no supported path, and will take an
unsupported one.** Someone will `from enbanc._transcript import Entry` and it will
work, because Python enforces nothing. The difference is that they cannot claim it
was supported, and a break is theirs. Accepted; the alternative gives that user a
guarantee at everyone's expense.

**Cost: deep imports are unavailable as a tree-shaking or import-cost lever.** A
caller wanting only `Statute` still executes `enbanc/__init__.py` and so the whole
package. Accepted because `../design/packaging.md` constrains what that import may
*do* — no I/O, no provider SDK, no `enbanc.tools` — so the cost is module
execution, not connections or credentials.

**Rejected: public module names with `__all__` as a convenience.**
`enbanc.transcript`, `enbanc.filings`, `enbanc.errors` importable and documented,
with the top level re-exporting for ease. Rejected because it creates two public
paths to every name and obliges both forever: `from enbanc import Transcript` and
`from enbanc.transcript import Transcript` would both have to keep working, which
pins the module layout as tightly as the type layout. It buys a caller nothing
here — the surface is twenty-nine names, not a framework, and there is no
disambiguation problem for a namespace to solve.

**Rejected: one `_schemas.py` holding every type in `api.md`.** Fewer files and no
intra-schema import ordering to think about. Rejected because it puts roughly six
hundred lines of unrelated concerns in one module, breaks the
module-named-for-its-design-document mapping that rule 2 in
[`../../CLAUDE.md`](../../CLAUDE.md) leans on, and makes the one genuinely
interesting import relationship — the renderer and `Transcript.render()`,
described in
[`../design/packaging.md`](../design/packaging.md#what-imports-what) — invisible
by collapsing it rather than resolving it.

**Rejected: a `PUBLIC_API.md` or a documented list with no structural backing.**
The status quo the placeholder implied. Rejected for the reason in Context: it is
the only boundary in the library that documentation alone would hold, and the
failure mode is silent — an accidental export is indistinguishable from an
intended one until someone depends on it.
