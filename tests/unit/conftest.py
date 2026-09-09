"""The unit tier: `enbanc`'s own behaviour, offline and enforced.

This is the bulk of the suite and the only tier that tests edge cases. A complete
multi-round proceeding belongs here, not in `e2e`: ADR 0003 makes the model injected, so a
whole proceeding runs with no provider in the loop.
"""

import pytest


@pytest.fixture(autouse=True)
def _offline(block_network: None) -> None:
    """Every test in this tier runs with the network blocked. See `../conftest.py`."""
