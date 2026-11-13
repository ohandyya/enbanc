---
status: draft
updated: 2026-10-18
---

# A published documentation site

**A free documentation site with an API reference, rebuilt on every release.**
`enbanc` has no outside users yet, and a reader's only entry point is the
README on GitHub. PydanticAI's own site shows the shape a Python library reader
expects: narrative pages, a generated reference, and search.

## Scope

**MkDocs Material and mkdocstrings, deployed to GitHub Pages.** This is the
stack PydanticAI uses, and Pages is free for a public repository. Read the Docs
is the fallback if Pages proves awkward. A GitHub Actions workflow builds and
deploys on each release tag.

**The site carries user-facing material only:**

- `README.md`, as the landing page.
- [`docs/guides/`](../guides/).
- The user-facing design docs: `api.md`, `evidence.md`, `outcomes.md`,
  `tribunal.md`, and `glossary.md`.
- A generated reference for the two importable namespaces, `enbanc` and
  `enbanc.tools`, driven by `__all__`.

**It leaves out** `decisions/`, `journal/`, `implementations/`, `progress.md`,
and the internal design docs: `execution.md`, `prompting.md`, `testing.md`,
and `packaging.md`. They stay readable on GitHub.

**The site is a dev-only dependency.** Its packages go in a dependency group,
never into `[project]`, so nothing about it reaches `pip install enbanc`.

**Two things to settle when the PR starts:**

- **Two references can drift.** [`api.md`](../design/api.md) is already a
  hand-written reference. A generated one beside it is a second source of
  truth. The proposed split is that the generated reference carries signatures
  and docstrings, and `api.md` stays the narrative.
- **Docstrings point at repository paths.** Lines such as "See
  `docs/design/evidence.md`" do not resolve on the site. They need rewriting as
  links that work in both places, or a build step that maps them.

## Implements

No design document covers how the documentation is published, so this PR
writes that section. The proposed home is
[`packaging.md` § Stability, before 1.0](../design/packaging.md#stability-before-10),
which already says where the user-facing half of the surface lives.

## Depends on

Nothing. It can land at any point in the plan, and goes early because every
later PR's documentation benefits from it.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
