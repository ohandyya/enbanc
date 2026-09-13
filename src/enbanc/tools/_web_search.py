"""The default tool: web search through Tavily, returning `Source`.

A factory closing over one client, returning a plain async function — Step 3 of
`docs/design/evidence.md` ("Adding your own tool") with nothing added. That is the whole
point of the shape: the tool `enbanc` ships and the tool you write are the same kind of
object, and there is no privileged path for a built-in.

What it knows is the mapping and nothing else. The ledger that turns a `Source` into a
citable exhibit is the tribunal's, and this module has never heard of a proceeding.

See `docs/design/evidence.md` ("The default tool") for the field mapping and what is
deliberately dropped, and
`docs/decisions/0018-the-search-client-is-a-core-dependency.md` for why Tavily's own SDK
rather than PydanticAI's `tavily_search_tool`.
"""

from collections.abc import Awaitable, Callable

from tavily import AsyncTavilyClient

from .._evidence import Source


def web_search(api_key: str, *, max_results: int = 5) -> Callable[[str], Awaitable[list[Source]]]:
    """Build a web search tool bound to a Tavily key.

        Advocate(tools=[web_search(api_key=...)])

    **`max_results` is the caller's, not the model's.** How much lands in the ledger is a
    decision about the size of the record, and every result that comes back is recorded
    verbatim — so putting the count in front of the model would hand that lever to the
    participant whose context it exists to bound. Five rather than Tavily's own default of
    ten, for the reason `raw_content` is refused.

    **Nothing is caught.** A Tavily error — a bad key, an exhausted quota, the SDK's own
    timeout — propagates, ends the round, and surfaces as `ProceedingFailed` with the
    original exception as `__cause__`. The bound belongs on the tool object the caller
    wraps, not in here: `Tool(web_search(api_key=...), timeout=15.0, max_retries=5)`. See
    `docs/decisions/0020-tool-timeouts-ride-on-the-tool.md`.
    """
    # One client per factory call, shared by every call the tool makes — the rule
    # evidence.md ("What tools may do") gives users, and the default tool is an example of
    # it rather than an exception to it. Constructing it here opens nothing: __init__ builds
    # an httpx.AsyncClient, performs no I/O, and does not require a running event loop, so
    # `web_search(api_key=...)` at a user's module scope is inert. There is correspondingly
    # nothing to close, and an uncollected client emits no ResourceWarning.
    client = AsyncTavilyClient(api_key=api_key)

    # The inner name is the tool name, and the shadowing is the mechanism rather than a
    # slip. PydanticAI reads `__name__` and `__doc__` off the function it is handed, so a
    # factory returning `async def _inner(...)` would put a tool called `_inner` in front of
    # the model — while docs/design/outcomes.md prints tool='web_search' and
    # reference='web_search(query="…")' throughout. Renaming this breaks the record.
    async def web_search(query: str) -> list[Source]:
        """Search the web and return the results, most relevant first."""
        response = await client.search(query, max_results=max_results)
        sources: list[Source] = []
        for result in response.get("results", []):
            reference = result.get("url")
            content = result.get("content")
            if not reference or not content:
                # Unreachable against a Tavily behaving as evidence.md describes, and
                # specified anyway: `Source.reference` is required, so a row with no locator
                # cannot be represented and something has to happen to it. Skipping rather
                # than raising, because one malformed row out of five would otherwise end
                # the proceeding and discard the four usable sources beside it. The cost is
                # that a skipped row never reaches the ledger — accepted, because a row that
                # cannot be cited is not the thing the ledger was built to hold.
                continue
            # `score`, `id`, `raw_content` and the top-level `answer` are dropped here by
            # not being read. The request asked for none of them either: every
            # response-shaping parameter on `search` defaults to None and is stripped from
            # the body before it is sent, so the tool suppresses nothing — it declines to
            # ask. `raw_content` still arrives, as a null; a key whose value is None is
            # dropped by the same code that drops a key that never came.
            sources.append(Source(reference=reference, content=content, label=result.get("title")))
        return sources

    return web_search
