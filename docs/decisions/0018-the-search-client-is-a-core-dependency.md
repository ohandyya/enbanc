---
status: accepted
updated: 2026-09-04
---

# 0018. The search client is a core dependency, not an extra

## Context

[`0016`](./0016-exhibits-are-stamped-citations.md) settled that
`enbanc.tools.web_search` ships in `0.1.0`, written against Tavily's own SDK
rather than wrapping PydanticAI's `tavily_search_tool`. In passing, it said:
*"Tavily is an optional dependency (`enbanc[web]`)."*

That clause was reasoned from install weight alone — a tribunal whose advocates
only query internal systems should not have to install a search client — and it
was decided before the surrounding documentation existed. Once it did, the
clause was in tension with it. `web_search` is not a sample; it is the only tool
`0.1.0` ships, and it appears in `README.md`'s first code block, in
[`../design/api.md`](../design/api.md#shape), and throughout
[`../design/outcomes.md`](../design/outcomes.md).

## Decision

**`tavily-python` moves to `[project.dependencies]`.** There is no `web` extra
and no `enbanc[web]` install.

## Consequences

**A default that a default install cannot import is not a default.** The
strongest argument is the first-run one: the README sample is the first thing
anyone copies, and under an extra it raises `ImportError` on a plain
`uv add enbanc`. The failure lands at the exact moment a reader is deciding
whether the library works, and the fix — read further, find the extra, reinstall
— is friction bought for very little.

**The install cost is smaller than it looked.** `tavily-python` requires
`requests`, `httpx`, and `tiktoken`. The first two already arrive with
`pydantic-ai`, so the genuinely new weight is `tiktoken` and its `regex`. That
is not nothing, but it is not the "a search client for everyone" the extra was
protecting against either. The clause in `0016` asserted the cost rather than
measuring it.

**One install path instead of two.** An extra is a second configuration to
document, to test, and to keep true in every install snippet. The `0.1.0` docs
had already grown two `uv add` lines in `README.md` for it.

**Cost, stated plainly: every user pays for a tool most will not use.** The
`0016` reasoning was not wrong, only outweighed. A tribunal whose advocates
query only internal systems still installs a search client it never calls. This
is accepted for `0.1.0` and is worth revisiting if the default toolset grows —
the argument here is about *one* small client for *the* default tool, and it
does not extend to a third or fourth provider SDK. The moment there is a second
search backend, an extra per backend is the right shape and this ADR should not
be read as precedent against it.

**This supersedes one clause of `0016` and nothing else.** ADRs are immutable,
so `0016` still reads as written; everything else it decided — the ledger,
stamped references, `Source`, and why `web_search` uses Tavily's SDK rather than
PydanticAI's wrapper — stands unchanged. Only the packaging aside is replaced.
