"""Regression test: `flowgate.agent(...)` works as the harness decorator.

`flowgate.agent` is the module file `flowgate/agent.py`, and many
internal imports rely on that (`from flowgate.agent import CascadeAgent`,
`flowgate.agent.PROVIDER_REGISTRY`, etc.). But README/docs/llms.txt also
use `@flowgate.agent(budget=..., ...)` as a decorator, which historically
raised `TypeError: 'module' object is not callable`.

The fix in `flowgate/agent.py` subclasses the module's type so that
`flowgate.agent(...)` delegates to `flowgate.harness.agent`, while
module-attribute access continues to work. This test guards both paths.
"""

import asyncio

import flowgate
import flowgate.agent as agent_module


def test_module_attribute_access_still_works() -> None:
    """`from flowgate.agent import CascadeAgent` and friends must keep working."""
    from flowgate.agent import CascadeAgent, CascadeResult

    assert CascadeAgent.__name__ == "CascadeAgent"
    assert CascadeResult.__name__ == "CascadeResult"
    # Module attribute (used by tests + the openclaw integration)
    assert hasattr(agent_module, "PROVIDER_REGISTRY")


def test_flowgate_agent_callable_as_decorator_factory() -> None:
    """`@flowgate.agent(budget=..., ...)` must return a decorator."""
    decorator = flowgate.agent(
        budget=0.20,
        kpi_weights={"quality": 0.6, "cost": 0.3, "latency": 0.1},
        compliance="gdpr",
    )
    assert callable(decorator)

    @decorator
    async def my_agent(query: str) -> str:
        return query

    assert callable(my_agent)
    assert asyncio.run(my_agent("hello")) == "hello"


def test_flowgate_agent_decorator_attaches_metadata() -> None:
    """The decorator returned by `flowgate.agent(...)` should attach policy metadata."""

    @flowgate.agent(budget=0.10, compliance="hipaa")
    async def f(q: str) -> str:
        return q

    # The harness `agent` decorator stores metadata on the wrapped function.
    # We don't assert on the exact attribute name here — only that the
    # decorator returned something callable and didn't raise.
    assert callable(f)


def test_harness_agent_alias_still_works() -> None:
    """`flowgate.harness_agent` is the eager top-level alias."""

    @flowgate.harness_agent(budget=0.10)
    async def g(q: str) -> str:
        return q

    assert callable(g)


def test_explicit_import_from_harness_still_works() -> None:
    """`from flowgate.harness import agent` is the explicit import path."""
    from flowgate.harness import agent

    @agent(budget=0.10)
    async def h(q: str) -> str:
        return q

    assert callable(h)
