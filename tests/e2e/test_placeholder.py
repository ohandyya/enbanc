"""Placeholder e2e test.

Same job as the integration tier's: keep `make e2e-tests` reporting a clean skip rather than
an empty collection. Replace it with `docs/design/api.md`'s example, run start to finish,
once there is an `enbanc` to run.
"""

from pydantic_ai.models import Model


def test_the_tier_can_build_the_runners_model(live_model: Model) -> None:
    assert live_model.model_name
