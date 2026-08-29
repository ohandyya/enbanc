# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
