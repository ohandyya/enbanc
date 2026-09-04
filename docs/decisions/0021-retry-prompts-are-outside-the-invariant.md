---
status: accepted
updated: 2026-09-04
---

# 0021. Retry prompts are outside the transcript invariant

## Context

[`0002`](./0002-the-judge-is-a-role.md) states the invariant that the audit
claim rests on: *nothing enters an agent's context that is not also in the
transcript.* [`0006`](./0006-the-transcript-schema.md) had to narrow it to
*nothing from outside itself*, because an advocate's tool results reached its
context and stopped there.
[`0019`](./0019-the-ledger-is-part-of-the-record.md) recorded those results and
restored the absolute wording.

Settling [`0020`](./0020-tool-timeouts-ride-on-the-tool.md) showed the absolute
wording is still false, for a reason none of the three ADRs addressed. When a
tool times out, PydanticAI puts a retry prompt into the agent's message
history — observed verbatim as `Timed out after 0.25 seconds.` — and the model
sees it. The same happens when an advocate cites a ledger id that does not
resolve, which `../design/evidence.md` relies on as the enforcement mechanism
for citations.

These are not tool results and not another participant's filing. They are text
the library writes, into one agent's context, that no transcript holds. The
invariant as written forbids them, and `enbanc` cannot stop producing them
without giving up retries entirely.

This is not a regression introduced by `0019`. Output-validation retries have
injected such prompts since `Agent(retries=...)` was adopted; restoring the
absolute wording only made the gap visible.

## Decision

**The invariant excludes the library's own procedural retry prompts**, and says
so rather than being quietly true-ish:

> Nothing enters an agent's context that is not also in the transcript, except
> `enbanc`'s own retry prompts — which carry no fact about the case, the
> statute, or another participant.

The qualifier is exactly that: a retry prompt reports a mechanical failure of
the agent's own last action. It never carries evidence, never carries what
another participant said, and never carries anything about the case that the
agent did not already have.

## Consequences

**The invariant's purpose survives intact.** What it protects is that the
transcript completely explains the *ruling*. A retry prompt cannot bear on the
ruling, because it introduces no fact that could be reasoned from — and anything
the agent goes on to file in response *is* in the transcript.

**Cost, stated plainly: the record does not show that a tool timed out.** An
advocate whose search timed out three times and then filed a thin argument reads
in the transcript as an advocate that argued thinly. The ledger shows what came
back, not what failed to. A reviewer cannot distinguish a weak case from a
degraded one.

That is the sharp edge of this decision, and it is accepted for `0.1.0` on
`0006`'s reasoning: the alternative is recording intra-agent churn, which is the
bulk problem that kept tool traffic out of the record in the first place. It is
also the most likely successor — a `Retrieval` with an `outcome` field, or a
failures list beside the ledger, would close it without recording every prompt.
Recorded as an open question in `../design/evidence.md`.

**Rejected: recording retry prompts as filings.** They are not filings, nobody
issued them, and `0006` already fixed the set of filings at five. A sixth
`kind` for "the library told an agent to try again" puts library mechanics in a
record of what participants said.

**Rejected: leaving the invariant absolute and treating the prompts as an
implementation detail.** This is what the documents did by accident until now.
An invariant listed under *constraints that define the design* that is known to
be false is worse than a narrower one that is true —
[`0017`](./0017-read-only-is-a-contract.md) made the same call about read-only
tools being "enforced at the tool boundary."

**Rejected: dropping retries to keep the invariant absolute.** It would be
literally true and would cost the library its enforcement of both the
`Ruling | Continuance` contract and citation resolution, turning recoverable
model errors into failed proceedings. The invariant is a means to an auditable
transcript, not the end.
