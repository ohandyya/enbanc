# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
