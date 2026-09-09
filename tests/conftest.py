"""Shared test harness.

Two jobs, both of them consequences of `../docs/decisions/0031-tests-are-tiered.md`:
a test's tier is the directory it lives in, and the offline tiers enforce being offline
rather than promising it. The marker is applied here so nobody has to remember one; the
network guard is defined here so the two offline conftests share one implementation.

See `../docs/design/testing.md` for the strategy this serves.
"""

import os
import socket
from collections.abc import Iterator, Mapping
from typing import Any

import pytest
from pydantic_ai.models import Model, infer_model

#: The tier directories, which are also the marker names. A directory absent from this tuple
#: collects no marker — itself the signal that a test was filed somewhere the strategy does
#: not describe. Registered in pyproject.toml so an unknown marker is an error.
TIERS = ("unit", "contract", "integration", "e2e")

#: Addresses an offline test may still reach. A test is free to stand up a local server;
#: what the guard forbids is leaving the machine.
LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost", "0.0.0.0", ""})


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark every test with its tier, derived from the directory it was collected from.

    `make unit-tests` and friends select by path, so this exists for the `-m unit` form and
    for reports that group by marker. Deriving it from the path rather than from a decorator
    is the whole point: a marker can be forgotten, a directory cannot.
    """
    root = config.rootpath / "tests"
    for item in items:
        try:
            relative = item.path.relative_to(root)
        except ValueError:  # a test collected from outside tests/ — not ours to label
            continue
        tier = relative.parts[0] if relative.parts else ""
        if tier in TIERS:
            item.add_marker(getattr(pytest.mark, tier))


class NetworkAccessDenied(RuntimeError):
    """An offline-tier test tried to reach a third party."""


@pytest.fixture
def block_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make any non-loopback socket connection raise.

    Requested by an autouse fixture in `unit/conftest.py` and `contract/conftest.py`. It is
    not autouse here, because the live tiers share this file and need the network.

    `socket.socket.connect` is the choke point rather than `getaddrinfo`: `create_connection`
    routes through it, and so does asyncio's transport setup, so one patch covers httpx,
    the provider SDKs, and anything else that ends up opening a TCP connection.
    """
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _permitted(address: Any) -> bool:
        if isinstance(address, tuple) and address:
            return str(address[0]) in LOOPBACK
        return False  # a str address is an AF_UNIX path; nothing in these tiers needs one

    def _guarded_connect(self: socket.socket, address: Any) -> None:
        if not _permitted(address):
            raise NetworkAccessDenied(
                f"this test tried to connect to {address!r}. Tests under tests/unit/ and "
                f"tests/contract/ must not reach a third party — fake the model with "
                f"TestModel or FunctionModel, or move the test to tests/integration/. "
                f"See docs/design/testing.md."
            )
        real_connect(self, address)

    def _guarded_connect_ex(self: socket.socket, address: Any) -> int:
        if not _permitted(address):
            raise NetworkAccessDenied(
                f"this test tried to connect to {address!r}. See docs/design/testing.md."
            )
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    yield


@pytest.fixture(scope="session")
def live_env(pytestconfig: pytest.Config) -> Mapping[str, str]:
    """`os.environ` overlaid with `.env`, for the live tiers.

    Requested only by `integration/conftest.py` and `e2e/conftest.py`, so a key present on
    the machine cannot reach an offline test through this. `.env` is parsed here rather than
    with a dependency: it is a dozen lines, it is only ever read by tests, and
    `.env.example` is the committed template for what belongs in it.
    """
    values = dict(os.environ)
    env_file = pytestconfig.rootpath / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values.setdefault(key.strip(), value.strip().strip("'\""))
    return values


#: Names a `pydantic-ai` model string for the live tiers, e.g. "anthropic:claude-sonnet-5" or
#: "openai:gpt-5". `enbanc` has no provider concept (`docs/design/api.md`, "The model is
#: injected, not named"), so the harness has none either: which provider a live run uses is the
#: runner's choice, and the key it needs is that provider's own, read by PydanticAI from the
#: environment. This is test configuration, not library surface — ADR 0003's rejection of model
#: strings is about what `Tribunal` accepts.
MODEL_VAR = "ENBANC_TEST_MODEL"


@pytest.fixture
def live_model(live_env: Mapping[str, str], monkeypatch: pytest.MonkeyPatch) -> Model:
    """A real `Model` for the live tiers, built from whatever provider the runner chose.

    Skips when `ENBANC_TEST_MODEL` is unset, which is what "this machine is not set up for
    live runs" looks like. Fails when it is set and cannot be built, because then a live run
    was asked for and did not happen.
    """
    name = live_env.get(MODEL_VAR)
    if not name:
        pytest.skip(
            f"live tier: {MODEL_VAR} not set. Set it to a pydantic-ai model string "
            f"(e.g. anthropic:claude-sonnet-5, openai:gpt-5) along with whatever credential "
            f"that provider needs. See .env.example."
        )
    # infer_model resolves credentials from os.environ, so .env has to reach it.
    for key, value in live_env.items():
        monkeypatch.setenv(key, value)
    try:
        return infer_model(name)
    except Exception as exc:
        # Not a skip. Unset means "not configured for live runs" and skips above; set-but-
        # unusable means a live run was asked for and could not happen — a typo, an
        # uninstalled provider SDK, or a missing credential. Skipping would hide all three.
        # PydanticAI's own message names the variable or the package, so it is passed through.
        pytest.fail(f"{MODEL_VAR} is {name!r} and could not be built: {exc}")


@pytest.fixture
def tavily_api_key(live_env: Mapping[str, str]) -> str:
    """The key `enbanc.tools.web_search` needs.

    Unlike the model, this provider is not the runner's choice: `web_search` is written against
    Tavily's SDK and `tavily-python` is a core dependency
    (`docs/decisions/0018-the-search-client-is-a-core-dependency.md`), so naming it here names
    something the library already fixed.
    """
    key = live_env.get("TAVILY_API_KEY")
    if not key:
        pytest.skip("live tier: TAVILY_API_KEY not set. See .env.example.")
    return key
