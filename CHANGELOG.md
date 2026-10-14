# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-14

The first release intended to be used. Everything `docs/design/` describes is
implemented, and those documents now describe the library as it is rather than
the one being built.

### Added
- The public API: `Tribunal`, `Judge`, `Advocate`, `Statute`, `Case` and
  `Verdict` to stage a proceeding; `hear()` to run one to the end and
  `hear_stream()` to watch each filing as it is entered; and a `Hearing` that
  ends in either a `Ruling` or an `Undecided`, carrying the full `Transcript`,
  usage overall and per participant. Twenty-nine names in `enbanc.__all__`,
  listed in `docs/design/api.md`.
- `enbanc.tools.web_search`, a Tavily-backed search tool and the only tool this
  release ships. Any async function returning `Source`s is a tool.
- An evidence ledger. Every row an advocate's tools return is stamped with a
  reference and the call that produced it, and an exhibit may cite only a row
  the tribunal recorded. Rows no exhibit cites stay in the transcript.
- `Argument`, `Response` and `Ruling` carry a required `confidence` in
  `[0, 1]`: the filer's own estimate, not a calibrated probability.
- `ProceedingFailed`, raised with the record so far when a participant cannot be
  heard, and `ConfigurationError`, raised by `Tribunal(...)` before anything
  runs.
- Two runnable guides in `docs/guides/`: a loan assessment run through `hear()`,
  and a content-moderation decision watched live through `hear_stream()`. The
  `e2e` test tier runs both against a real provider.
- `anyio>=4.14.2` is a declared runtime dependency; the round's fan-out imports
  it directly.

### Changed
- The README and the design documents no longer describe a placeholder. The
  `status: draft` banners are gone from `docs/design/`.

### Note
- **The prompting surface ships as procedure `p1`, amended twice before this
  release**: by `0042`, which has every ledger row name the call that produced
  it, and by `0043`, which adds `confidence` to arguments, responses and
  rulings. `p1` was amended rather than bumped because nothing had shipped
  under it. From this release on, any change to a procedural prompt, a turn
  template, the tool-result format or the render format is a new procedure
  version, recorded on every transcript.
- `Retrieval.call` and the three `confidence` fields are required, with no
  default, so a transcript serialized during development before either change
  does not validate under `0.1.0`. No released version produced one, so there
  is no migration.

## [0.0.5] - 2026-09-12

### Added
- `tavily-python>=0.8.1` and `typing-extensions>=4.14.1` are now declared runtime
  dependencies. The default `web_search` tool calls Tavily directly, so it ships
  with the package rather than as an extra — a default a plain install cannot
  import is not a default. `typing-extensions` supplies `TypeAliasType` at the
  Python 3.11 floor, which the generic aliases in the public API require.
- The design is complete and published under `docs/design/`: the tribunal and
  how it reaches a decision, the public API, the execution layer, evidence and
  tools, prompting, outcomes, packaging, and the testing strategy. Every open
  question that stood in `0.0.4` is now answered in prose, with the reasoning
  and the rejected alternatives recorded as ADRs under `docs/decisions/` —
  thirty-seven of them, indexed in `docs/README.md`.
- A build plan in `docs/implementations/`: ten PRs, ordered, from the schemas to
  a working `0.1.0`.
- A tiered test harness. A test's tier is the directory it lives in, offline
  tiers are held offline by a socket guard, and the tiers that cost money run in
  CI only on demand.

### Changed
- The README now carries the intended API as a worked example and points at the
  design docs instead of summarizing them.

### Note
The package is still a placeholder. Nothing described in `docs/design/` is
importable yet; `0.1.0` is the release that makes it real.

## [0.0.4] - 2026-08-29

### Added
- `pydantic-ai>=2.36.0` is now a declared runtime dependency, so installing
  `enbanc` pulls in the framework it is built on. The package itself is still a
  placeholder and imports nothing from it yet.
- Published design documentation under `docs/design/`, linked from the README:
  how a tribunal reaches a decision, and the public API being designed toward
  `0.1.0`. Both carry open questions that are still open.

### Changed
- The README now leads with a compact example and points at the design docs
  rather than restating them, and the glossary moved to `docs/glossary.md`.
- Builds now use the `uv_build` backend.

## [0.0.3] - 2026-08-29

### Added
- A changelog, starting with this release.

### Changed
- The README now states plainly that `enbanc` is an early placeholder and describes
  what the package is intended to become, so the PyPI page no longer implies a
  usable library.

### Fixed
- The release workflow now verifies that the published tag matches the version in
  `pyproject.toml` before building, so a tag created on the wrong commit fails the
  run instead of publishing a mislabeled artifact to PyPI.
