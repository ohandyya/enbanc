---
status: accepted
updated: 2026-09-04
---

# 0017. Read-only advocate tools are a contract the caller keeps

## Context

`../design/tribunal.md` listed among the constraints that define the design:

> **Advocate tools are strictly read-only.** An adjudication must never mutate
> the world it is reasoning about. This is enforced at the tool boundary, not by
> instructing the model to behave.

The first two sentences are right. The third is not true and cannot be made
true. A tool is an arbitrary Python function supplied by the caller, and
`enbanc` cannot inspect one for side effects — there is no boundary at which to
enforce anything. The sentence went unchallenged while tools were undefined;
writing `../design/evidence.md` made it unavoidable, because the doc has to say
what a tool may do.

An untrue guarantee in a document labelled *constraints that define the design*
is worse than a stated limitation. A reader who believes it will pass a tool
that writes.

## Decision

**Read-only is a contract the caller keeps, not one `enbanc` checks**, and the
design docs say so.

What the library does do is stated positively, because it is real: `enbanc`
ships no tool that writes, the judge has no tools at all
([`0002`](./0002-the-judge-is-a-role.md)), and the library itself has no
mutation path. What it does not do is stated plainly: a tool you pass is your
code.

The *reason* for the constraint is unchanged and stays load-bearing — a
proceeding that changed the facts it was weighing would produce a record that no
longer describes the thing decided.

## Consequences

**Rejected: enforcing it with an approval-gated toolset.** PydanticAI ships
`ApprovalRequiredToolset`, and every advocate tool call could be routed through
it. It stops nothing: approval is per call, the approver is the library, and the
library has no more idea than before whether the function behind the name
writes. It would add a real gate to the hot path of every round in exchange for
the appearance of enforcement.

**Rejected: requiring tools to declare themselves read-only** — a flag on a
wrapper, or a marker the library checks at construction. `ConfigurationError` on
an undeclared tool is the kind of loud construction-time check this codebase
already likes ([`0004`](./0004-verdicts-are-a-strenum.md),
[`0014`](./0014-usage-is-broken-down-per-participant.md)), so it was considered
seriously. It fails because the declaration is the same promise spelled
differently: a caller who would pass a writing tool will set the flag. It also
breaks the "you pass PydanticAI tools" promise for no gain, since an ordinary
async function carries no such marker.

**Consequence: this is now a documented limitation rather than a guarantee.** It
appears in `../design/tribunal.md` among the constraints, and in
`../design/evidence.md` under what tools may do. `README.md` softens the
matching claim.

**Consequence: the adversarial structure is again the mitigation, not a
guarantee.** This is the same shape as `0006`'s stated cost, where suppression
is invisible and the opposing advocate's own tools are what is relied on
instead. Neither is enforcement, and the docs should not read as if either were.

**What would change this.** A sandboxed execution boundary — tools running
somewhere they cannot reach the network or the filesystem the proceeding is
reasoning about — would make enforcement real. That is a substantial piece of
machinery and no part of `0.1.0`. Recording it here so a future reader asking
"why not enforce it?" finds the answer, and knows what an answer would cost.
