---
status: draft
updated: 2026-09-12
---

# The schemas

**The types everything else stands on.** The first code in the package: the
verdict base, the inputs, the five filings and their private emit-shapes, the
record, the result, and the error hierarchy — laid into the module map
[`packaging.md`](../design/packaging.md#the-modules) fixed before any of it was
written.

## Scope

`_verdicts.py`, `_inputs.py`, `_evidence.py`, `_filings.py`, `_transcript.py`,
`_hearing.py`, and `_errors.py`, plus the `__init__.py` that re-exports what
exists so far. Declarative work: models, generic aliases, and the constraints
that make an invalid record unrepresentable.

**Not in this PR.** `Transcript.render()` — its body is `_prompting.py`, which
lands in [`rendering.md`](./rendering.md). The method and the forced import
cycle arrive with it.

**`__all__` is partial here and stays partial until
[`proceeding-core.md`](./proceeding-core.md).** Four of the twenty-nine names —
`Tribunal`, `Judge`, `Advocate`, `Proceeding` — do not exist yet, so
`tests/unit/test_export_surface.py` cannot land in this PR. This one exports
what it has. `tests/unit/test_import_is_inert.py` *can* land here: it needs only
an importable package.

## Implements

- [`api.md` § Schemas](../design/api.md#schemas) — every type in it, end to end
- [`api.md` § The judge's output](../design/api.md#the-judges-output) and
  [§ Where ids come from](../design/api.md#where-ids-come-from) — the public
  types and the private emit-pair beside them
- [`api.md` § A note on generic aliases](../design/api.md#a-note-on-generic-aliases)
  — `Filing`, `Deliberation`, and `Outcome` as `TypeAliasType`
- [`evidence.md` § A reference is what makes an exhibit auditable](../design/evidence.md#a-reference-is-what-makes-an-exhibit-auditable)
  — `Source`
- [`packaging.md` § The modules](../design/packaging.md#the-modules),
  [§ Where the errors live](../design/packaging.md#where-the-errors-live),
  [§ What `import enbanc` may do](../design/packaging.md#what-import-enbanc-may-do)

## Depends on

Nothing. This is the first PR.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
