"""
Beast Components Module

Provides Beast messaging integration with HACP governance, observability,
and semantic alignment for the Eudorus platform.
"""

from eudorus.beast.adapter import BeastAdapter
from eudorus.beast.envelope import (
    BeastEnvelope,
    validate_envelope,
    create_envelope,
    EnvelopeValidationError,
)
from eudorus.beast.observability import ObservabilityStack
from eudorus.beast.semantics import SemanticAlignmentLayer, BEAST, EUDORUS

__all__ = [
    "BeastAdapter",
    "BeastEnvelope",
    "validate_envelope",
    "create_envelope",
    "EnvelopeValidationError",
    "ObservabilityStack",
    "SemanticAlignmentLayer",
    "BEAST",
    "EUDORUS",
]
