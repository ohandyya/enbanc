---
status: draft
updated: 2026-10-18
---

# A relational database tool

**`enbanc.tools` gains a tool that queries a relational database the caller
connects.** Much of the evidence behind a structured decision sits in tables:
an applicant's accounts, a claims history, a policy register.
[`evidence.md`](../design/evidence.md#a-reference-is-what-makes-an-exhibit-auditable)
already names what such a tool's reference is: the query that produced the
row. It also names database query as one of the two tools to follow
`web_search` ([§ The default tool](../design/evidence.md#the-default-tool)).

## Scope

**Three requirements, and the rest of this document serves them:**

1. **The model can explore the database:** list the tables, see each table's
   columns and types, and find its way to the data without being told the
   schema in advance.
2. **The model can read the database's contents** with queries it writes.
3. **The model can never change the database.** Not through an `UPDATE`, an
   `INSERT`, a `DELETE`, DDL, a stored procedure, a side-effecting function,
   or a lock. This is a guarantee of the tool, not a default and not a
   recommendation. Where the tool cannot guarantee it, it does not run.

**Relational databases only.** The tool reaches them through SQLAlchemy, so one
tool covers PostgreSQL, MySQL, SQLite and any other database SQLAlchemy has a
dialect for. NoSQL stores are out of scope: they share no query language, so
supporting them would mean one tool per store. The
[2026-10-18 journal entry](../journal/2026-10-18-planning-past-zero-one-zero.md)
records why.

**Why ship it when MCP already works.** An `Advocate` accepts `toolsets`, so a
database MCP server can be attached today. Its payload, though, is ledgered as
one anonymous source whose reference is the call. A first-party tool returns
`Source` with the query, and enough to identify each row, as the reference.

**The caller owns the connection.** The proposed factory takes an engine the
caller built, for example `sql_query(engine, *, max_rows=...)`, and never sees
a connection string or a password. That matches `web_search`, which takes a key
and nothing more, and it leaves pooling, credentials and drivers with the
caller. An async engine is the natural fit, since tools are async.

**The factory returns tools for both jobs.** One or more tools explore: list
the tables, describe a table's columns. One reads: it runs a query the model
wrote. Their exact names and number are settled when the PR starts. A design
in which the caller writes parameterized queries and the model only fills in
parameters was considered and rejected. It fails requirement 1, since the
model cannot explore, and it is what a caller can already write as a plain
async function returning `Source`
([§ Adding your own tool](../design/evidence.md#adding-your-own-tool)).

**Never writing is `enbanc`'s to enforce, at the database.**
[`0017`](../decisions/0017-read-only-is-a-contract.md) holds today because
`enbanc` ships nothing that writes, and it leaves read-only to the caller for
the caller's own tools. A shipped tool that runs model-written SQL is
`enbanc`'s code, so the guarantee is built in. There are three layers, and
**the first one is mandatory**:

- **The database refuses writes.** Every query runs in a transaction or
  connection the database itself holds read-only: `SET TRANSACTION READ ONLY`
  on PostgreSQL, `START TRANSACTION READ ONLY` on MySQL, a `mode=ro`
  connection or `PRAGMA query_only` on SQLite. **This is the guarantee.**
  Parsing alone cannot be, because a `SELECT` can still write: PostgreSQL's
  `nextval()`, a user-defined function with side effects, `SELECT … INTO`, or
  `SELECT … FOR UPDATE`, which takes locks. A read-only transaction refuses
  all of these.
- **The tool refuses anything but a single query** before it reaches the
  database: the SQL is parsed, and a second statement or any non-`SELECT` is
  rejected. This layer gives the model a clear error to correct, rather than a
  database error, and it is the backstop if the first layer is ever
  misconfigured. It is not the guarantee.
- **The docs tell the caller to connect as a read-only role.** This is the
  layer the caller controls, and the tool never relies on it.

**A dialect with no read-only transaction is refused, not trusted.** The
factory raises at construction for an engine whose dialect `enbanc` cannot put
into read-only mode, rather than falling back to parsing alone. The supported
dialects are a list the tool states, and growing it is a change to the tool. It
is never inferred.

**A read-only failure is not a retry.** A write the database refuses, or a
statement the parser rejects, goes back to the model as a tool error, the same
way a bad query does. Nothing about it can loosen the transaction.

How each dialect is put into read-only mode, and which dialects the first
release supports, is settled when the PR starts and recorded in an ADR.

**The result size is the caller's.** `max_rows` is set on the factory and not
shown to the model, for the reason `web_search` keeps `max_results`: every row
that comes back is recorded verbatim, so the count is a decision about the
size of the record.

**Its dependencies go behind an extra,** for example `enbanc[sql]`.
[`0018`](../decisions/0018-the-search-client-is-a-core-dependency.md)'s
argument for making a dependency core does not extend to a database toolkit,
and the drivers stay the caller's to install. The extra means `enbanc.tools`
must still import when SQLAlchemy is absent, so the tool's imports are deferred
until it is built, and
[`packaging.md`](../design/packaging.md#what-import-enbanc-may-do) gains that
rule.

**A slow query is bounded on the tool,** as every tool is
([`0020`](../decisions/0020-tool-timeouts-ride-on-the-tool.md)): `Tool(...,
timeout=...)`. A statement timeout in the database is a sensible addition the
docs recommend, not one the tool sets.

**Not in this PR:** NoSQL stores and a query cache. Writing to a database is
not deferred. It is excluded, permanently, by requirement 3.

## Implements

- [`evidence.md` § The default tool](../design/evidence.md#the-default-tool):
  the "not in `0.1.0`" paragraph describes the tool.
- [`evidence.md` § A reference is what makes an exhibit auditable](../design/evidence.md#a-reference-is-what-makes-an-exhibit-auditable):
  the database row of the table, made exact.
- [`evidence.md` § What tools may do](../design/evidence.md#what-tools-may-do)
  and [`0017`](../decisions/0017-read-only-is-a-contract.md): read-only
  enforced by a shipped tool. The ADR this PR writes extends `0017` rather
  than editing it.
- [`packaging.md` § What `import enbanc` may do](../design/packaging.md#what-import-enbanc-may-do)
  and [§ One distribution](../design/packaging.md#one-distribution): the extra,
  and the deferred import.
- [`api.md`](../design/api.md): the new `enbanc.tools` export.

## Depends on

[`local-file-tool.md`](./local-file-tool.md). It is the first factory that
returns more than one tool, and this one follows the shape it settles.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
