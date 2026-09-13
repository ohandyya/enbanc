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

from collections.abc import AsyncIterator
from typing import Any

import pytest
from tavily import AsyncTavilyClient

from enbanc import Source
from enbanc.tools import _web_search as module
from enbanc.tools import web_search


@pytest.fixture
async def closed_after(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Close every client the factory built, once the test is done with it.

    `web_search` deliberately offers no `close()`: the factory returns a function and
    nothing else, so there is no object a caller could close and no lifecycle to document.
    In a program that is right — one pool, alive as long as the process. Under pytest it
    leaks, because pytest-asyncio gives each test its own event loop and the client outlives
    it; when the client is finally collected, asyncio's transport and the socket under it
    each emit a `ResourceWarning`, and `filterwarnings = ["error"]` turns that into a failed
    session *after* the test has already passed.

    So the awkwardness lives here. It is the seam `docs/design/testing.md` ("Faking Tavily")
    already sanctions — the module-level client class — used to track rather than to fake:
    the subclass adds a line to a list and changes nothing else, so the search below is a
    real search against the real service. A `close()` on the tool would be public surface
    existing for one caller who is not a user, which is the trade that section refuses.
    """
    built: list[AsyncTavilyClient] = []

    class _TrackedAsyncTavilyClient(AsyncTavilyClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built.append(self)

    monkeypatch.setattr(module, "AsyncTavilyClient", _TrackedAsyncTavilyClient)
    yield
    for client in built:
        await client.close()


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
