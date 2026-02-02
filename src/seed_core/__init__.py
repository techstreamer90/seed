"""
seed-core: Universal Pulse-based Coordination System

A lightweight, language-agnostic coordination layer that enables multiple
AI agents to work together through a pulse-based status mechanism.

Core Components:
- Pulse: Heartbeat mechanism for agent liveness and coordination
- Status: Structured status aggregation and reporting
- Reality: Shared state management and synchronization

Author: spawnie project
License: MIT
"""

from typing import Final

__version__: Final[str] = "0.1.0"
__author__: Final[str] = "spawnie project"
__license__: Final[str] = "MIT"

# Core exports
from .pulse import Pulse, PulseResult
from .status import StatusAggregator, SeedStatus, RealityStatus
from .reality import Reality, RealitySnapshot
from .registry import RealityRegistry
from .verification import verify_model, HashCheck

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Pulse
    "Pulse",
    "PulseResult",
    # Status
    "StatusAggregator",
    "SeedStatus",
    "RealityStatus",
    # Reality
    "Reality",
    "RealitySnapshot",
    # Registry
    "RealityRegistry",
    # Verification
    "verify_model",
    "HashCheck",
]
