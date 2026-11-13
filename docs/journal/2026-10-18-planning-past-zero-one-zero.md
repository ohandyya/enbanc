---
status: current
updated: 2026-10-18
---

# Planning past `0.1.0`

`0.1.0` shipped with no plan after it. This session turned a list of
candidate enhancements into an ordered plan: rows 16–23 of
[`implementations/`](../implementations/README.md). The plan's documents say
what each PR does. This entry records why the order is what it is, and what was
considered and left out. None of it can be reconstructed from the diff.

## The premise the order rests on

`progress.md` recorded that the library had "a handful of live runs in total,
all from this repository — nothing yet from an outside user." So each idea was
ranked by whether it helps someone find `enbanc`, trust it, and get it running,
rather than by how much it adds. On that measure a documentation site and a
benchmark outrank new tools. A new tool makes a library more capable, but it
does not show that the library works.

## What was decided

- **The order:**
  1. The round-1 `advocate` fix, as `0.1.1`.
  2. The documentation site.
  3. The excerpt-check helper.
  4. The benchmark.
  5. For `0.2.0`: the ruling cites evidence, the local file tool, and images in
     `web_search`.
  6. The SQL tool, in a release not yet chosen.
- **The round-1 fix goes first and ships alone.** It is the only known defect
  that can put a wrong citation in a released transcript, and `progress.md` had
  already named it the `0.1.1` candidate.
- **The excerpt check comes before the benchmark.** The benchmark's
  citation-faithfulness metric is the helper run over each transcript, so
  building it first avoids writing it twice.
- **The benchmark lives in this repository and must never ship.** The user
  chose this over a separate repository. A build of `0.1.0` was inspected
  during the session: the wheel holds only `enbanc/` and its metadata, and the
  sdist adds only `README.md`, `LICENSE` and `pyproject.toml`. That is because
  the build backend ships only what it is told to. The plan adds a CI guard so
  this is checked rather than assumed.
- **Images in `web_search` are opt-in.** The original idea made them the
  default. That was dropped: an image description is written by Tavily's own
  model, not taken from the source, and turning it on would change a released
  default. See [`web-search-images.md`](../implementations/web-search-images.md).

## Considered and deferred

- **Re-hearing a case with new information.** Two different things went under
  this name. *Re-hearing*, a new proceeding on an amended `Case`, already works
  by calling `hear()` again. The only thing missing is a link between the two
  hearings, which a caller can store. The harder question is whether the new
  bench should see the old ruling, since a judge shown its earlier verdict
  anchors on it. *Resuming*, adding evidence to a proceeding mid-record, is the
  question [`execution.md`](../design/execution.md#history-is-a-dict-written-after-each-run)
  chose to delete rather than answer. Deferred until an outside user asks. At
  most a guide paragraph showing a re-hearing as a fresh `hear()`.
- **A NoSQL tool.** Rejected. Mongo, Dynamo, Redis and Elastic share no query
  language, so "NoSQL" would mean owning one driver per store. A guide showing
  a hand-written tool that returns `Source`, plus a pointer to MCP, serves the
  need.

## Planned last, behind the local file tool

- **A SQL tool.** It was first listed as deferred, then planned as row 23
  ([`sql-tool.md`](../implementations/sql-tool.md)): it follows the local file
  tool and lands in a release not yet chosen. If `enbanc` ships a tool that
  runs model-written SQL,
  [`0017`](../decisions/0017-read-only-is-a-contract.md)'s read-only contract
  becomes `enbanc`'s to enforce, at the database: every query runs in a
  read-only transaction, and a dialect without one is refused. Its driver goes
  behind an extra.

## Found along the way

- **MCP already covers databases and files, with coarse references.** An
  `Advocate` accepts `toolsets`, and `Ledgering` wraps an MCP server the same
  way as a plain function. So a Postgres or filesystem MCP server works today.
  What it lacks is precision: its payload becomes one anonymous source whose
  reference is the call. That changed the question for both tools from "can a
  user do this?" to "is a precise reference worth owning a tool for?"
- **Two prompting changes are planned, so the procedure version moves twice.**
  If the round-1 fix ships as `p2`, the ruling-cites-evidence change is `p3`.

## Dropped

- **A "persisted evidence store".** Raised as an aside, then dropped as not
  mattering.
