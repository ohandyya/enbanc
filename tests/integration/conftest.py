"""The integration tier: that the plumbing to a real service works.

One happy path per external seam, against the real thing. If an edge case is being tested
here it is in the wrong tier — those belong in `../unit/`, where a faked client can be made
to return the responses a live service will not produce on demand. What this tier catches is
the failure a fake cannot have: a moved API shape, a changed auth flow, a response that no
longer parses.

There is no tier-wide skip. A test asks for what it needs — `live_model` for a provider,
`tavily_api_key` for `web_search` — and skips itself when that is missing, so a Tavily test
still runs on a machine with no model configured. Both fixtures are in `../conftest.py`.

Does not run in CI ([`0031`](../../docs/decisions/0031-tests-are-tiered.md)). Run it by hand
with `make integration-tests`.
"""
