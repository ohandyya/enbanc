"""Placeholder integration test.

Same job as the unit tier's placeholder: pytest exits non-zero on an empty collection, so
`make integration-tests` cannot report a clean skip until at least one test exists here.

What it checks is small but not nothing — that the tier is wired end to end: `.env` is found
and parsed, and `live_model` turns whatever `ENBANC_TEST_MODEL` names into a real `Model`
without `enbanc` knowing which provider that is. Replace it when the first real integration
test lands (`web_search` against real Tavily, which wants `tavily_api_key` instead).
"""

from pydantic_ai.models import Model


def test_the_tier_can_build_the_runners_model(live_model: Model) -> None:
    # Reaching this line means ENBANC_TEST_MODEL was set and its provider had credentials.
    # Nothing here names a provider, which is the property the tier exists to preserve.
    assert live_model.model_name
