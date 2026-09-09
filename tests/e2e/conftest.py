"""The e2e tier: that `../../docs/design/api.md`'s example works as written.

The whole intended use case, start to finish, against a real provider. It asserts almost
nothing about content — a model is free to rule either way — and asserts that a `Hearing`
came back, that its transcript is coherent, and that its usage is non-zero. Its job is to
fail when the composition is broken in a way every faked tier was too kind to notice.

Which provider it runs against is the runner's, through `live_model` in `../conftest.py`.
`enbanc` commits to working with any `pydantic_ai.models.Model`, so a tier that could only
run against one provider would be testing less than the library promises.

Does not run in CI ([`0031`](../../docs/decisions/0031-tests-are-tiered.md)). Run it by hand
with `make e2e-tests`.
"""
