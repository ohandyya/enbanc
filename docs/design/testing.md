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

## Decisions regaridng test I have already made
- I will use `pytest` as the unit testing framework
- The test code should be in the `tests` directory
- All unit tests should NOT require 3rd party resource access (e.g., LLM, Web Search)
  - This means we need to use `TestModel` or `FunctionModel` for LLM, and we may need to mock the tools that requires internet access (e.g., Tavily search)

## What kind of tests we want
1. We want `unit tests` and `integration tests` and `e2e tests`

  - `unit tests`:
    - This should be the majority of the tests.
    - Unit tests should NOT require 3rd party resource access (e.g., LLM, Web Search). So no real LLM access and no real web information retrieval. They should be mocked (or other means)
    - For example, we may create a `tavily_search` function which calls Tavily to do real web search information retrieval. We should have a `unit tests` that maock the Tavily call. The point of the `unit tesws` is to test the pre and post process logtic in the `tavily_search`. Since we use mock, we can test all kinds of edge cases.


  - `integration tests`:
    - This is the tests that actually uses 3rd party resource access. For example, it sends REAL LLM requests and web seach engine.
    - In comparison to `smoke tests`, `integration tests` is still meant to test a small compoent.
    - For example, for the same `tavily_search` function, we shall have one integration tests that tests the most common path of using function that ACTUALLY calls Tavily. The purpose is to validate the plumbing (e.g, network) work. The edge case tests are covered in unit tests

  - `e2e tests`:
    - This is the end to end test that runs the full intended use case (e.g., see @api.md on the shape of the intended usage).
    = The post of the e2d tests is to demostrate the most common usage casse of the user is working.

## What we must have

1. In the `Makefile`, we want to create three make targets; one for each type of tests.

  - `make unit-tests`
  - `make integration-tests`
  - `make e2e-tests`

## Open questions

1. How do we structually separate `unit tests`, `integration tests`, and `e2e tests`?

  - All via pytest?
  - Or shall `unit tests` and `integration tests` are implemented using pytest, but `e2e tests` are implemented as stand-alone python script?
