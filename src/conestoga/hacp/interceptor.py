"""
HACP Interceptor Module

Provides interceptor and violation error handling for HACP governance.
"""


class HACPViolationError(Exception):
    """
    Exception raised when a message violates HACP governance rules.

    This exception is raised by the HACP interceptor when it detects
    protocol violations in agent communication.
    """
    pass
