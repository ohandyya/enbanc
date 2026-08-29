"""Placeholder tests.

Two jobs. First, they keep the test gate honest: pytest exits non-zero on an empty collection, so
`make check-all` and CI's test job cannot be green until at least one test exists. Second, the
async one proves the pytest-asyncio wiring works *before* there is async code to exercise — when
the first real `await` lands, a failure here means the code is wrong, not the harness.

Replace both as real behaviour arrives.
"""

import asyncio

from enbanc import hello


def test_hello_greets() -> None:
    assert hello() == "Hello from enbanc!"


# No `@pytest.mark.asyncio` decorator: `asyncio_mode = "auto"` in pyproject.toml means an
# `async def test_` just runs. If this test errors with "async def functions are not natively
# supported", that setting is what regressed.
async def test_hello_greets_from_a_coroutine() -> None:
    await asyncio.sleep(0)
    assert hello() == "Hello from enbanc!"
