"""
Custom Exception Hierarchy for flowgate
==========================================

This module defines all custom exceptions used throughout flowgate.

Exception Hierarchy:
    flowgateError (base)
    ├── ConfigError
    ├── ProviderError
    │   ├── AuthenticationError
    │   └── TimeoutError
    ├── ModelError
    ├── BudgetExceededError
    ├── HarnessStopError
    ├── RateLimitError
    ├── QualityThresholdError
    ├── RoutingError
    ├── ValidationError
    └── ToolExecutionError

Usage:
    >>> from flowgate import flowgateError, ProviderError
    >>>
    >>> try:
    ...     result = await agent.run(query)
    ... except ProviderError as e:
    ...     print(f"Provider failed: {e}")
    ... except flowgateError as e:
    ...     print(f"Cascade error: {e}")

See Also:
    - agent.py for main error handling patterns
    - providers.base for provider-specific errors
"""


class flowgateError(Exception):
    """Base exception for flowgate."""

    pass


class ConfigError(flowgateError):
    """Configuration error."""

    pass


class ProviderError(flowgateError):
    """Provider error."""

    def __init__(
        self,
        message: str,
        provider: str = None,
        original_error: Exception = None,
        status_code: int = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error
        self.status_code = status_code


class AuthenticationError(ProviderError):
    """Authentication error - API key missing or invalid.

    Raised when provider authentication fails due to missing or invalid API keys.

    Attributes:
        message: Error description
        provider: Provider name (e.g., 'openai', 'anthropic')
        env_var_name: Environment variable that should contain the API key

    Example:
        >>> raise AuthenticationError(
        ...     "OpenAI API key not found",
        ...     provider="openai",
        ...     env_var_name="OPENAI_API_KEY"
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: str = None,
        env_var_name: str = None,
        original_error: Exception = None,
    ):
        super().__init__(message, provider, original_error)
        self.env_var_name = env_var_name


class TimeoutError(ProviderError):
    """Timeout error - API request exceeded time limit.

    Raised when a provider API call times out.

    Attributes:
        message: Error description
        provider: Provider name
        timeout_ms: Timeout duration in milliseconds

    Example:
        >>> raise TimeoutError(
        ...     "OpenAI API request timed out after 60s",
        ...     provider="openai",
        ...     timeout_ms=60000
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: str = None,
        timeout_ms: int = None,
        original_error: Exception = None,
    ):
        super().__init__(message, provider, original_error)
        self.timeout_ms = timeout_ms


class ModelError(flowgateError):
    """Model execution error."""

    def __init__(self, message: str, model: str = None, provider: str = None):
        super().__init__(message)
        self.model = model
        self.provider = provider


class BudgetExceededError(flowgateError):
    """Budget limit exceeded."""

    def __init__(self, message: str, remaining: float = 0.0):
        super().__init__(message)
        self.remaining = remaining


class HarnessStopError(flowgateError):
    """Harness enforcement stop for non-budget hard limits."""

    def __init__(self, message: str, reason: str):
        super().__init__(message)
        self.reason = reason


class RateLimitError(flowgateError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = 3600):
        super().__init__(message)
        self.retry_after = retry_after


class QualityThresholdError(flowgateError):
    """Quality threshold not met."""

    pass


class RoutingError(flowgateError):
    """Routing error."""

    pass


class ValidationError(flowgateError):
    """Validation error."""

    pass


class ToolExecutionError(flowgateError):
    """Tool execution error - tool call failed during execution.

    Raised when a tool/function call fails during execution.

    Attributes:
        message: Error description
        tool_name: Name of the tool that failed
        cause: Original exception that caused the failure

    Example:
        >>> raise ToolExecutionError(
        ...     "Failed to execute weather tool",
        ...     tool_name="get_weather",
        ...     cause=ConnectionError("API unreachable")
        ... )
    """

    def __init__(
        self,
        message: str,
        tool_name: str = None,
        cause: Exception = None,
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.cause = cause


# ==================== EXPORTS ====================

__all__ = [
    "flowgateError",
    "ConfigError",
    "ProviderError",
    "AuthenticationError",
    "TimeoutError",
    "ModelError",
    "BudgetExceededError",
    "HarnessStopError",
    "RateLimitError",
    "QualityThresholdError",
    "RoutingError",
    "ValidationError",
    "ToolExecutionError",
]
