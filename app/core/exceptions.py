class SmartOpsError(Exception):
    """Base class for expected application errors."""


class LLMServiceError(SmartOpsError):
    """Raised when the language model provider cannot complete a request."""


class ToolExecutionError(SmartOpsError):
    """Raised when a requested tool cannot be safely executed."""

