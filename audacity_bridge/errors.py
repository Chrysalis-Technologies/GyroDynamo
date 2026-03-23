"""Bridge-specific exception types."""


class AudacityBridgeError(Exception):
    """Base class for all bridge errors."""


class AudacityConnectionError(AudacityBridgeError):
    """Raised when the pipe transport cannot connect/read/write."""


class AudacityResponseTimeoutError(AudacityBridgeError):
    """Raised when a command response does not arrive in time."""


class AudacityCommandError(AudacityBridgeError):
    """Raised when an Audacity command fails or returns an error state."""
