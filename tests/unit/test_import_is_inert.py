"""`import enbanc` does nothing: no I/O, no provider SDK, no `enbanc.tools`.

The three invariants `docs/design/packaging.md` ("What `import enbanc` may do") requires, and
the one test `docs/design/testing.md` sanctions running in a **subprocess**.

It has to be a subprocess. By the time a test function runs, pytest has imported half the
tree in-process and the question is no longer askable — and the socket guard that holds the
offline tiers offline is an autouse fixture, which has not existed at any point an import
happened. A child process carries none of the guard, which is exactly why the child installs
its own before importing anything.

That argument is made for this module and no other. A second subprocess test would need it
made again, from scratch.
"""

import json
import os
import subprocess
import sys

import pytest

#: Runs in the child. Blocks the socket first, imports `enbanc`, then reports what that
#: pulled in. Anything the import touched shows up in `sys.modules`.
_CHILD = """
import json, socket, sys

def _blocked(*args, **kwargs):
    raise AssertionError("import enbanc opened a socket")

socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked

import enbanc

json.dump(sorted(sys.modules), sys.stdout)
"""

#: Provider SDKs, which would silently contradict
#: `docs/decisions/0003-models-and-guidance-are-injected.md`. `enbanc` has no provider concept:
#: you construct a `pydantic_ai.models.Model` and hand it over, so nothing here may reach for
#: one itself. Each entry is matched as a module path prefix.
#:
#: Google's is spelled out rather than banned at `google`, and the distinction is load-bearing
#: rather than pedantic: `google` is a namespace package shared by unrelated distributions, and
#: `google.protobuf` legitimately arrives through OpenTelemetry, which `pydantic_ai.usage`
#: pulls in. Banning the namespace would fail this test for a dependency of a dependency that
#: is not a provider SDK at all — and the useful version of this test is one that still fails
#: the day someone imports `google.genai`.
PROVIDER_SDKS = (
    "anthropic",
    "openai",
    "google.genai",
    "google.generativeai",
    "groq",
    "mistralai",
    "cohere",
    "boto3",
    "ollama",
    "huggingface_hub",
)


@pytest.fixture(scope="module")
def imported_modules() -> frozenset[str]:
    """`sys.modules` in a child that did nothing but `import enbanc`.

    The child runs with a **minimal environment**, so "no environment variable required" is
    asserted rather than assumed: a module reading a credential at import time would fail
    here rather than on a user's machine. `PATH` is kept because the interpreter may need it
    to resolve its own tooling; no credential is.
    """
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD],
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", "")},
        check=False,
    )
    assert completed.returncode == 0, (
        f"the child could not import enbanc cleanly:\n{completed.stderr}"
    )
    return frozenset(json.loads(completed.stdout))


def test_importing_enbanc_opens_no_socket(imported_modules: frozenset[str]) -> None:
    """The child's own guard is what proves this — the fixture fails the run if it tripped.

    This invariant closes the realistic gap in the offline guarantee: an import happens at
    collection, before any autouse fixture, so a module-level client that connected eagerly
    would go straight past the socket guard in `tests/conftest.py`.
    """
    assert "enbanc" in imported_modules


def test_importing_enbanc_does_not_import_enbanc_tools(
    imported_modules: frozenset[str],
) -> None:
    """The top-level package re-exports no tool, which is why `docs/design/api.md` spells
    that import separately and what keeps `tavily` off the `import enbanc` path.

    Vacuous until `docs/implementations/web-search-tool.md` creates the module; it is here
    from the start so that PR cannot introduce the coupling unnoticed.
    """
    assert "enbanc.tools" not in imported_modules
    assert "tavily" not in imported_modules


def test_importing_enbanc_imports_no_provider_sdk(imported_modules: frozenset[str]) -> None:
    found = sorted(
        name
        for name in imported_modules
        if any(name == sdk or name.startswith(f"{sdk}.") for sdk in PROVIDER_SDKS)
    )
    assert found == [], f"import enbanc pulled in a provider SDK: {found}"
