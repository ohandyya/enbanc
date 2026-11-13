---
status: draft
updated: 2026-10-18
---

# A local file tool

**`enbanc.tools` gains a second tool: search and read files under a directory
the caller names.** The evidence for a decision is often a set of documents on
disk: a policy, a contract, an applicant's filings.
[`evidence.md`](../design/evidence.md#the-default-tool) already names local
file search as one of the next two tools, and it uses
`Source(reference="./policy.md#L40-L52")` as its example of a reference.

## Scope

**Why ship it when MCP already works.** An `Advocate` accepts `toolsets`, and
the ledger wraps an MCP server just like a plain function, so a filesystem MCP
server can be attached today. What it lacks is precise references. An MCP
payload is ledgered as one anonymous source whose reference is the call
itself, not a file and line range. A first-party tool returns `Source` with a
reference a reviewer can open.

**The proposed shape** is a factory in the same form as `web_search`: for
example `file_search(root, *, glob=..., max_results=5)`. It returns a small set
of tools, such as listing files, searching their text, and reading a line
range. Each returns `Source` with a `path#Lstart-Lend` reference. The exact
names and signature are settled when the PR starts.

**Confined to `root`.** A path outside it is refused, including one reached
through `..` or a symlink. This is the tool's half of the read-only contract
([`0017`](../decisions/0017-read-only-is-a-contract.md)). Since `enbanc` ships
the tool, `enbanc` is the one keeping that contract.

**Plain text first.** Reading PDF or Word files needs parsers. If those come in
at all, they go behind an extra such as `enbanc[files]`, because
[`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md)'s
argument for making a dependency core does not extend to them.

**Not in this PR:**

- **Semantic or embedding search.** It needs a vector store.
- **A database tool.** That is [`sql-tool.md`](./sql-tool.md), which follows
  this one.

## Implements

- [`evidence.md` § The default tool](../design/evidence.md#the-default-tool):
  the "not in `0.1.0`" paragraph becomes a description of the tool.
- [`evidence.md` § What tools may do](../design/evidence.md#what-tools-may-do):
  what confinement to `root` guarantees.
- [`packaging.md` § What `import enbanc` may do](../design/packaging.md#what-import-enbanc-may-do),
  if an extra is introduced.
- [`api.md`](../design/api.md): the new `enbanc.tools` export.

## Depends on

Nothing open. It follows the shape of
[`web-search-tool.md`](./web-search-tool.md) (#21).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
