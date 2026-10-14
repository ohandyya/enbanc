"""`web_search` against real Tavily.

One happy path, which is the whole of this tier's job: the fake in `../unit/` drives every
branch, and what it cannot have is a moved API shape. If the response stops carrying `url`,
`title` or `content` where the mapping looks for them, this is what says so.

It asserts shape rather than content. A search engine is free to return different pages next
week, and a test that pinned one would fail for a reason that is not a defect.

**The provider is named here and nowhere else in the harness.** ADR 0018 fixed Tavily as the
library's search client, so naming it names something already decided — unlike the model,
which is the runner's choice through `live_model`.
"""

from enbanc import Source
from enbanc.tools import web_search


async def test_a_real_search_returns_citable_sources(
    tavily_api_key: str, closed_after: None
) -> None:
    sources = await web_search(api_key=tavily_api_key, max_results=3)("IRS Schedule C net profit")

    assert sources, "a live search for a common term returned nothing"
    assert len(sources) <= 3, "Tavily returned more results than max_results asked for"
    for source in sources:
        assert isinstance(source, Source)
        # `reference` is opaque to `enbanc`, but this tool's locator is the result URL, and a
        # reviewer holding it has to be able to follow it.
        assert source.reference.startswith("https://")
        assert source.content
