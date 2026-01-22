"""HACP (Hybrid Agentic Control Protocol) Interceptor Module"""


class HACPViolationError(Exception):
    """Raised when a message violates HACP policy"""

    pass


class HACPInterceptor:
    """
    Intercepts messages to enforce HACP governance policies.
    
    This is a minimal implementation for testing purposes.
    """

    def __init__(self, policies=None):
        """
        Initialize the HACP interceptor.
        
        Args:
            policies: Optional list of policy rules to enforce
        """
        self.policies = policies or []

    def intercept(self, message: dict, direction: str) -> dict:
        """
        Intercept and validate a message against HACP policies.
        
        Args:
            message: The message to validate
            direction: "in" for incoming, "out" for outgoing
            
        Returns:
            The message (potentially modified)
            
        Raises:
            HACPViolationError: If the message violates a policy
        """
        # Apply policies
        for policy in self.policies:
            if not policy(message, direction):
                raise HACPViolationError(f"Message violates HACP policy")
        
        return message
