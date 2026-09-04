---
status: draft
updated: 2026-09-04
---

# Packaging

**PLACEHOLDER — not yet designed. Left for future: not needed for `0.1.0`.**

Not MVP-blocking, and possibly never a document. These are decisions to make in
code as the first modules land, recorded here only so they are not mistaken for
oversights.

## What is unsettled

- **Module layout.** [`api.md`](./api.md)'s examples import everything public
  from `enbanc` and tools from `enbanc.tools`
  ([`evidence.md`](./evidence.md#the-default-tool)). What sits behind those two
  namespaces — one module or several, and where the private `_Exhibit` /
  `_Continuance` pair lives — is open.
- **The export surface.** What `enbanc/__init__.py` re-exports, and whether
  `__all__` is the contract or merely a convenience. Everything named in
  [`api.md`](./api.md#shape) is public by construction; nothing says what else
  is.
- **Where the error hierarchy lives.** `EnbancError` and its three subclasses
  are specified in [`api.md`](./api.md#when-something-goes-wrong); the module
  they live in is not.
- **Dependency floor.** `tavily-python` is core
  ([`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md)); the
  Python floor is not stated anywhere, and
  [`api.md`](./api.md#a-note-on-generic-aliases) notes that moving it to 3.12
  removes the `TypeAliasType` spelling.

## Open questions

*Not yet opened.*
