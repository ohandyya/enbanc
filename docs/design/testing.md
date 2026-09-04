---
status: draft
updated: 2026-09-04
---

# Testing

**PLACEHOLDER — not yet designed. Left for future: not needed for `0.1.0`.**

Not MVP-blocking: nothing here changes a public type, and the strategy can be
settled by the first tests that get written. Worth deciding before the suite
grows past a handful of cases, because reversing it later means rewriting all
of them.

## What this document would own

How a library whose behaviour is LLM-driven is asserted on deterministically.
PydanticAI ships `TestModel` and `FunctionModel`, and
[`0003`](../decisions/0003-models-and-guidance-are-injected.md) makes the model
an injected dependency — so a whole proceeding can be driven with no provider
in the loop, which is what makes the question tractable.

- **Where the line sits between faked and live.** What, if anything, must run
  against a real provider, and whether that lives in the default `make test`.
- **[`outcomes.md`](./outcomes.md) as the spine.** It already reads as a test
  plan — every ending written out as concrete values, including a downed
  provider, a raising tool, and a misconfigured tribunal. Whether those examples
  become executable, and stay in sync with the doc, is the main decision.
- **How the transcript invariant is tested.** *Nothing enters an agent's context
  that is not also in the transcript* is the guarantee the product is sold on.
  Whether it is enforceable by a test — comparing what each agent was sent
  against what the record holds — depends on the renderer fork in
  [`prompting.md`](./prompting.md).
- **Serialization round-trips.** [`outcomes.md`](./outcomes.md) §7 specifies the
  behaviour; it needs a property or a fixture set behind it.

## Open questions

*Not yet opened.*
