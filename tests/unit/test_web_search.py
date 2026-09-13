"""The default tool's mapping, its request, and every path a live Tavily will not produce.

Pins `docs/design/evidence.md` ("The default tool") and the seam
`docs/design/testing.md` ("Faking Tavily") fixes: the Tavily client class is monkeypatched
in the module that defines the tool, and the real factory is driven throughout. The fake
replaces Tavily, never `web_search` — a test that stubbed the tool would assert nothing.

**The canned response is the shape the live service actually sends**, down to `raw_content`
arriving as a null on every result and the three null-or-empty top-level extras. That
matters more than tidiness: this tier holds the edge cases precisely because a live Tavily
cannot be asked for them, and the argument only holds while the happy path is real.

Nothing here needs a model. This is a function calling an HTTP client, and the agent that
would call it does not exist yet.
"""

import inspect
from dataclasses import dataclass, field
from typing import Any

import pytest
from tavily import AsyncTavilyClient
from tavily import errors as tavily_errors

from enbanc import Source
from enbanc.tools import _web_search as module
from enbanc.tools import web_search


def _live_response() -> dict[str, Any]:
    """One live Tavily response, recorded against `tavily-python` 0.8.1 by a
    `search(query, max_results=…)` passing nothing else.

    Every per-result field the service returns is here, and every one the tool drops is here
    too, so the mapping is exercised against what it will really be handed.
    """
    return {
        "query": "schedule c net profit",
        "follow_up_questions": None,
        "answer": None,
        "images": [],
        "results": [
            {
                "url": "https://www.irs.gov/forms-pubs/about-schedule-c-form-1040",
                "title": "About Schedule C (Form 1040)",
                "content": "Use Schedule C to report income or loss from a business you operated.",
                "score": 0.91,
                "raw_content": None,
                "id": "86b3e5-00",
            },
            {
                "url": "https://www.irs.gov/instructions/i1040sc",
                "title": "Instructions for Schedule C (2024)",
                "content": "Net profit or loss from line 31 carries to Schedule 1, line 3.",
                "score": 0.84,
                "raw_content": None,
                "id": "1175a2-01",
            },
            {
                "url": "https://www.sba.gov/business-guide/manage-your-business/pay-taxes",
                "title": "Pay taxes",
                "content": "Sole proprietors report business income on their personal return.",
                "score": 0.62,
                "raw_content": None,
                "id": "db18ee-02",
            },
        ],
        "response_time": 1.41,
        "request_id": "9c2f1ad4-6b70-4c2e-8f0a-2b5d3e9a7c11",
    }


@dataclass
class FakeTavily:
    """What the fake client recorded, and what the next `search` should do."""

    response: dict[str, Any] = field(default_factory=_live_response)
    error: Exception | None = None
    #: The key each constructed client was handed; one entry per factory call.
    api_keys: list[str | None] = field(default_factory=list)
    #: `(args, kwargs)` per `search`, before any interpretation of how they were spelled.
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(default_factory=list)

    def request(self, index: int = 0) -> dict[str, Any]:
        """What a call actually asked Tavily for, independent of positional-or-keyword.

        Bound against the real `AsyncTavilyClient.search` signature, so the assertion is
        about the request the SDK would build rather than about the tool's call style.
        """
        args, kwargs = self.calls[index]
        bound = inspect.signature(AsyncTavilyClient.search).bind(None, *args, **kwargs)
        arguments = dict(bound.arguments)
        del arguments["self"]
        return arguments


@pytest.fixture
def tavily(monkeypatch: pytest.MonkeyPatch) -> FakeTavily:
    """Replace the client class the tool holds at module scope. See `testing.md`."""
    recorder = FakeTavily()

    class _FakeAsyncTavilyClient:
        def __init__(self, api_key: str | None = None, **_: Any) -> None:
            recorder.api_keys.append(api_key)

        async def search(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            recorder.calls.append((args, kwargs))
            if recorder.error is not None:
                raise recorder.error
            return recorder.response

    monkeypatch.setattr(module, "AsyncTavilyClient", _FakeAsyncTavilyClient)
    return recorder


async def test_each_result_becomes_one_source_in_order(tavily: FakeTavily) -> None:
    """`url` to `reference`, `title` to `label`, `content` to `content`. The mapping is
    the tool; everything else in this module is a consequence of it."""
    sources = await web_search(api_key="tvly-test")("schedule c net profit")

    assert sources == [
        Source(
            reference="https://www.irs.gov/forms-pubs/about-schedule-c-form-1040",
            content="Use Schedule C to report income or loss from a business you operated.",
            label="About Schedule C (Form 1040)",
        ),
        Source(
            reference="https://www.irs.gov/instructions/i1040sc",
            content="Net profit or loss from line 31 carries to Schedule 1, line 3.",
            label="Instructions for Schedule C (2024)",
        ),
        Source(
            reference="https://www.sba.gov/business-guide/manage-your-business/pay-taxes",
            content="Sole proprietors report business income on their personal return.",
            label="Pay taxes",
        ),
    ]


async def test_nothing_tavily_returned_beside_the_three_fields_survives(
    tavily: FakeTavily,
) -> None:
    """`evidence.md` drops five things and gives a reason for each. Asserting the surviving
    set covers all five at once, and keeps covering them if Tavily adds a sixth."""
    sources = await web_search(api_key="tvly-test")("schedule c net profit")

    assert [set(source.model_dump()) for source in sources] == [
        {"reference", "content", "label"}
    ] * 3


async def test_the_request_carries_the_query_and_the_count_and_nothing_else(
    tavily: FakeTavily,
) -> None:
    """ "Nothing that changes the response shape" is a claim about the *request*, and this
    is where it is checked. Every response-shaping parameter defaults to `None` and is
    stripped from the body, so asking for nothing is how `raw_content`, `favicon` and the
    top-level `answer` are declined."""
    await web_search(api_key="tvly-test")("schedule c net profit")

    assert tavily.request() == {"query": "schedule c net profit", "max_results": 5}


async def test_the_key_reaches_the_client_and_one_client_serves_every_call(
    tavily: FakeTavily,
) -> None:
    """The factory closes over one client — the rule `evidence.md` gives users, which the
    default tool follows rather than excepts itself from."""
    search = web_search(api_key="tvly-test")
    await search("first")
    await search("second")

    assert tavily.api_keys == ["tvly-test"]
    assert len(tavily.calls) == 2


async def test_max_results_defaults_to_five_and_a_factory_keyword_reaches_tavily(
    tavily: FakeTavily,
) -> None:
    """The lever is the caller's, not the model's: how much lands in the ledger is a
    decision about the size of the record."""
    await web_search(api_key="tvly-test")("q")
    await web_search(api_key="tvly-test", max_results=3)("q")

    assert tavily.request(0)["max_results"] == 5
    assert tavily.request(1)["max_results"] == 3


async def test_coming_up_empty_returns_an_empty_list_and_does_not_raise(
    tavily: FakeTavily,
) -> None:
    """A tool that expects to come up empty returns an empty result — `evidence.md`,
    "What tools may do". Raising would end the proceeding over a search that found
    nothing."""
    tavily.response = {**_live_response(), "results": []}
    assert await web_search(api_key="tvly-test")("nothing matches this") == []

    tavily.response = {"query": "nothing matches this", "response_time": 0.4}
    assert await web_search(api_key="tvly-test")("nothing matches this") == []


@pytest.mark.parametrize("field_name", ["url", "content"])
@pytest.mark.parametrize("missing", [True, False], ids=["absent", "null"])
async def test_a_row_without_a_locator_or_text_is_skipped_and_its_siblings_survive(
    tavily: FakeTavily, field_name: str, missing: bool
) -> None:
    """Unreachable against a Tavily behaving as documented, and a live service cannot be
    asked for it — which is what puts it in this tier. `Source.reference` is required, so a
    row with no locator cannot be represented and something has to happen to it. Skipping
    rather than raising: one malformed row out of three would otherwise discard the two
    usable sources beside it, and every filing already made."""
    response = _live_response()
    if missing:
        del response["results"][1][field_name]
    else:
        response["results"][1][field_name] = None
    tavily.response = response

    sources = await web_search(api_key="tvly-test")("schedule c net profit")

    assert [source.label for source in sources] == [
        "About Schedule C (Form 1040)",
        "Pay taxes",
    ]


async def test_a_row_without_a_title_keeps_its_place_with_no_label(tavily: FakeTavily) -> None:
    """The one missing field that is not an error: `Source.label` is optional, so the
    exhibit renders without one."""
    response = _live_response()
    del response["results"][0]["title"]
    tavily.response = response

    sources = await web_search(api_key="tvly-test")("schedule c net profit")

    assert len(sources) == 3
    assert sources[0].label is None
    assert sources[0].reference == "https://www.irs.gov/forms-pubs/about-schedule-c-form-1040"


@pytest.mark.parametrize(
    "error",
    [
        tavily_errors.InvalidAPIKeyError("invalid api key"),
        tavily_errors.UsageLimitExceededError("usage limit exceeded"),
        tavily_errors.BadRequestError("bad request"),
        tavily_errors.ForbiddenError("forbidden"),
        # Tavily's own, shadowing the builtin — which is why the module is imported whole.
        tavily_errors.TimeoutError(60.0),
    ],
    ids=lambda error: type(error).__name__,
)
async def test_a_tavily_error_propagates_with_its_own_type(
    tavily: FakeTavily, error: Exception
) -> None:
    """Nothing is caught, converted, or retried. The type is what a caller's `except` sees,
    and the bound is theirs — `Tool(web_search(...), timeout=…, max_retries=…)`, per ADR
    0020. A `web_search` that turned a 429 into a `ModelRetry` would have a capability no
    user's tool has.

    The SDK turns a non-200 and a socket timeout into these types before the tool sees
    either, so the fake raises them directly; simulating an HTTP status would be testing
    Tavily's own error mapping.
    """
    tavily.error = error

    with pytest.raises(type(error)) as raised:
        await web_search(api_key="tvly-test")("schedule c net profit")

    assert raised.value is error


def test_the_returned_function_is_what_the_model_will_see_called() -> None:
    """The only thing standing between the model and a tool called `_inner`. PydanticAI
    derives the tool name and description from these two attributes, and
    `docs/design/outcomes.md` prints `tool='web_search'` throughout — so the inner `def`
    shadowing the factory is the mechanism, not a slip.

    No fake: constructing the client opens nothing, which the unit tier's socket guard is
    what proves.
    """
    search = web_search(api_key="tvly-test")

    assert search.__name__ == "web_search"
    assert search.__doc__
