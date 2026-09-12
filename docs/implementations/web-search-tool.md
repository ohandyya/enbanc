---
status: draft
updated: 2026-09-12
---

# The default tool

**`enbanc.tools.web_search`, and the second importable namespace.** The only
tool `0.1.0` ships, written against Tavily's own SDK as a plain async function
returning `list[Source]` — the same kind of object a user's own tool is.

## Scope

`tools/__init__.py` and `tools/_web_search.py`. The factory takes `api_key`,
sends `query` and `max_results` and nothing that changes the response shape, and
maps three Tavily fields onto `Source` while dropping the rest.

**Not in this PR.** The ledgering that turns what this returns into a citable
exhibit — that is [`ledgering-toolset.md`](./ledgering-toolset.md). This tool
knows nothing about a proceeding.

**The public factory grows no seam for the tests.** `web_search(api_key=...)` is
fixed by the design; the unit tests monkeypatch the Tavily client class in this
module instead.

## Implements

- [`evidence.md` § The default tool](../design/evidence.md#the-default-tool) —
  the field mapping, and what is deliberately dropped
- [`evidence.md` § Step 3 — a factory](../design/evidence.md#step-3--a-factory-when-the-tool-needs-configuration)
  — the shape this tool shares with a user's own
- [`packaging.md` § Two namespaces](../design/packaging.md#two-namespaces-and-nothing-else)
- [`testing.md` § Faking Tavily](../design/testing.md#faking-tavily)

## Depends on

[`schemas.md`](./schemas.md), for `Source`.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*None recorded yet.*
