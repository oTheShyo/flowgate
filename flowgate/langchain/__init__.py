"""Public convenience import for FlowGate's LangChain integration.

This module exists for backwards-compatible imports:
  `from flowgate.langchain import FlowGate`

The implementation lives in `flowgate.integrations.langchain`.
"""

from flowgate.integrations.langchain import *  # noqa: F403
from flowgate.integrations.langchain import __all__  # type: ignore
