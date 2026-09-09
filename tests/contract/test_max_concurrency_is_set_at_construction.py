"""`max_concurrency` is set at construction.

Pins the finding of the same name in `docs/design/execution.md`. It is an `Agent.__init__`
parameter and not a `run()` argument, which is what forces the shape
`docs/decisions/0024-a-budget-stops-the-proceeding-between-rounds.md` records: normalize the
caller's value once per proceeding and hand the same limiter object to every advocate agent,
rather than passing a number down at dispatch time.

If this fails after a `pydantic-ai` bump, the dependency moved and `execution.md` is now
wrong. Fix the document, then decide whether the design it forced still makes sense.

This is the first of the tier's modules; the remaining findings in
`execution.md#what-pydanticai-already-does` get one each as the code they describe lands.
"""

import inspect

from pydantic_ai import Agent


def test_max_concurrency_is_an_init_parameter() -> None:
    assert "max_concurrency" in inspect.signature(Agent.__init__).parameters


def test_max_concurrency_is_not_a_run_argument() -> None:
    # The half that constrains the design. Were it a run() argument, a proceeding could set
    # it per dispatch and there would be nothing to normalize once and share.
    assert "max_concurrency" not in inspect.signature(Agent.run).parameters
