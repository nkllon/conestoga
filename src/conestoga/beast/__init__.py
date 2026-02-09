"""
Beast Components Module

Provides Beast messaging integration with HACP governance, observability,
and semantic alignment for the Eudorus platform.
"""

from conestoga.beast.adapter import BeastAdapter
from conestoga.beast.envelope import (
    BeastEnvelope,
    EnvelopeValidationError,
    create_envelope,
    validate_envelope,
)
from conestoga.beast.observability import ObservabilityStack
from conestoga.beast.semantics import BEAST, EUDORUS, SemanticAlignmentLayer

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
