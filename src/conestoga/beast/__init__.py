"""
Beast Components Module

Provides Beast messaging integration with HACP governance, observability,
and semantic alignment for the Eudorus platform.
"""

from conestoga.beast.adapter import BeastAdapter
from conestoga.beast.envelope import (
    BeastEnvelope,
    validate_envelope,
    create_envelope,
    EnvelopeValidationError,
)
from conestoga.beast.observability import ObservabilityStack
from conestoga.beast.semantics import SemanticAlignmentLayer, BEAST, EUDORUS

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
