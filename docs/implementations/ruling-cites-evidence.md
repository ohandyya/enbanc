---
status: draft
updated: 2026-10-18
---

# The ruling cites evidence

**A ruling points into the record it rests on.** Today a `Ruling` carries a
verdict, reasoning and a confidence, and nothing that names a filing or an
exhibit. What the judge relied on can only be guessed from its prose. So the
defensibility claim, *deny, because of this document*, holds for an advocate's
exhibits but not for the judge's decision. This is the `0.2.0` headline.

## Scope

**Settle [`api.md`'s open question](../design/api.md#open-questions).** It
names three shapes:

- **Exhibit ids the ruling cites, checked the way an advocate's citations
  are.** A citation that resolves to nothing fails output validation.
- **Filings cited by position** in the transcript.
- **Reasoning stays prose,** and the docs say so.

The shape is the main decision in this PR. It is made when the PR starts and
recorded in an ADR.

**It is a prompting change, so it is a new procedure version.** If
[`round-one-advocate.md`](./round-one-advocate.md) has shipped as `p2`, this is
`p3`, with a row in
[`prompting.md` → Procedure versions](../design/prompting.md#procedure-versions).

**Every shape except prose changes `Ruling`'s public schema,** so this is a
minor bump, `0.2.0`. A transcript serialized under an earlier version may no
longer validate, and the changelog says so.

## Implements

- [`api.md` § Open questions](../design/api.md#open-questions): the
  ruling-names-no-evidence bullet, settled under `CLAUDE.md` rule 7 (prose,
  ADR, bullet removed).
- [`api.md` § The judge's output](../design/api.md#the-judges-output).
- [`prompting.md` § The judge's procedural prompt](../design/prompting.md#the-judges-procedural-prompt)
  and [§ `Transcript.render()`](../design/prompting.md#transcriptrender).
- [`outcomes.md`](../design/outcomes.md), wherever a ruling is written out.

## Depends on

[`round-one-advocate.md`](./round-one-advocate.md). Both change the procedure
version, and they land in order so the versions stay sequential.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
