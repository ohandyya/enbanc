"""The contract tier: claims `../../docs/design/execution.md` makes about `pydantic-ai`.

These tests are not about `enbanc`. Each one pins a finding that document recorded after
reading the installed source and running it, so a version bump cannot falsify the document
silently. A failure here means the pin moved and a design document is now wrong; the fix is
usually prose rather than code.

Offline for the same reason the unit tier is: none of these findings needs a provider.
"""

import pytest


@pytest.fixture(autouse=True)
def _offline(block_network: None) -> None:
    """Every test in this tier runs with the network blocked. See `../conftest.py`."""
