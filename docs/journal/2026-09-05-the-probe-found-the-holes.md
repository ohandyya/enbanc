---
status: current
updated: 2026-09-05
---

# 2026-09-05 — the probe found the holes

`docs/progress.md` carried an instruction from the previous session: *before
writing its prose, write the literal message sequence — two rounds, three
advocates, one twice-questioned.* The reason given was
[`2026-09-04-writing-the-prompt-found-the-holes.md`](./2026-09-04-writing-the-prompt-found-the-holes.md),
which is itself the second instance of a pattern
[`2026-09-02-values-before-schemas.md`](./2026-09-02-values-before-schemas.md)
recorded.

This is the third instance, and the first where the artifact was **code** rather
than prose. That difference is what this entry is about.

## What happened

`execution.md` is a document about a dependency. Every load-bearing sentence in
it is a claim about what `pydantic-ai 2.36.0` does, and the placeholder already
said so — its findings section existed *"so the finding is not re-derived, and so
it is falsifiable"*.

Writing it meant running the thing. Five scratch scripts, each isolating one
claim: a ledgering toolset over a `FunctionModel`, a two-run usage accumulator, a
union output type, a failing task group, a tool timing out repeatedly.

They found five defects. **Four were in documents already marked settled**, and
one was in an accepted ADR.

| Where | What |
|---|---|
| `0024` | `UsageLimits.request_limit` defaults to 50, so a `$2.00` budget silently also capped the proceeding at fifty requests — and would record `Undecided(reason='budget')` for a hearing that spent thirty cents |
| `evidence.md`, `api.md` | `Agent(retries=…)` is two independent budgets, not one. Three documents described a single budget a flaky tool and a miscited exhibit competed for |
| `outcomes.md` §1 | At PydanticAI's default of `1`, the worked example showing two timeouts and a ruling is unreachable — the second timeout ends the proceeding |
| `api.md`, `outcomes.md` §4 | "A participant whose run was cancelled or died has **no key at all**" was false about the mechanism, and pessimistic: `run(usage=u)` mutates in place, so a dying run leaves its spend behind |
| `prompting.md` | The rendered continuance listed `r1-q1` and `r1-q2`; the subsection immediately below it uses an `r1-q3` addressed to the same advocate |

Two of those — the budget and the retry default — would have shipped as bugs that
present as *correct-looking audit artifacts*. A hearing stopped by an unasked-for
request cap does not look broken. It looks like a proceeding that ran out of
money.

## Why the docs could not have caught them

The four settled documents are internally consistent. They cross-reference each
other correctly, their worked examples agree, and the reasoning in the ADRs is
sound *given what the ADRs believed about the dependency*.

`0024` is the clearest case. It named the right checkers, at the right seam, for
the right reason, and it did more dependency verification than any ADR before it
— it corrected two prior claims about `pydantic-ai` in its own Context section.
What it could not see by reading is that `UsageLimits` is a dataclass whose field
arrives **pre-filled**. That is not a fact about the API's shape. It is a fact
about a default, and defaults are invisible to every form of review except
construction.

The same is true of `retries`. Both documents that spend it say
"`Agent(retries=…)`", which is the correct symbol. Neither says a number, because
neither had one, and the shape of the value — `int | AgentRetries` — is exactly
the kind of thing a careful reader glosses as "an int" without loss until the
moment it matters.

**The pattern generalises past prose.** The previous two entries found holes by
rendering a design into a concrete form — values, then prompt text. This one
found them by rendering a design into a *running system* whose other half was
written by someone else. Wherever a document asserts something about a
dependency, review can only check that the assertion is coherent. Execution
checks that it is true.

## What went the other way

Two of the session's findings made the design smaller, and both deserve
recording because they were expected to be the hard parts.

**The ledgering toolset is not the hardest piece of code in the library.**
`evidence.md` had said it was, twice, and the placeholder repeated it. It is a
`WrapperToolset` with `call_tool` overridden — about thirty-five lines, verified
end to end against a `FunctionModel`. The reason it collapses is that PydanticAI
puts the timeout *inside* `FunctionToolset.call_tool`, so a wrapper sees the
`ModelRetry` a timeout becomes and can write `Transcript.failures` and
`Transcript.ledger` at one seam. Nothing had to be built to make that true; it
had to be discovered.

**`0012`'s singular `participant` is structural rather than chosen.** The
expectation was an `ExceptionGroup` from the task group and a rule for picking one
failure out of it. There is no group to unpack: a child that records its own
failure and cancels the scope lets the group exit cleanly, and only one slot is
ever filled. The one subtlety — re-raising the cancelled-exception class *before*
the general handler, or a cancelled sibling wins the race and the exception names
the wrong participant — is the sort of thing that would have been a bug rather
than a paragraph if the pattern had gone unwritten.

## The thing worth not repeating

The five probes are throwaway scripts in a scratch directory, and every one of
them asserts a sentence `execution.md` now states as fact. `execution.md` says so
in its own opening: these claims *"are worth re-checking when the pin moves"*.

They should become tests the moment `tests/` holds anything real. A document
whose truth depends on `pydantic-ai>=2.36.0` and whose only verification lives in
`/tmp` is a document that goes stale silently — which is the failure mode the
whole `docs/` split exists to prevent, arriving through the dependency rather
than through the prose.
