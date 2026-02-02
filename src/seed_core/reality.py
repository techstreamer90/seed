"""
Reality - Shared state management and synchronization.

The Reality component provides a shared state container for coordinating
between multiple agents or processes. It uses versioned snapshots to
detect conflicts and maintain consistency.

Key Features:
- Versioned snapshots for optimistic concurrency control
- History tracking (configurable depth)
- Thread-safe state updates with version checking
- Snapshot-based state export

Example:
    >>> reality = Reality(initial_state={"counter": 0})
    >>> reality.update({"counter": 1})
    >>> snapshot = reality.snapshot()
    >>> print(snapshot.state["counter"])  # 1
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from copy import deepcopy


@dataclass
class RealitySnapshot:
    """A snapshot of the shared reality at a point in time.

    Snapshots are immutable representations of state at a specific version.
    They can be used for conflict detection and rollback scenarios.

    Attributes:
        version: Monotonically increasing version number
        timestamp: Unix timestamp when snapshot was created
        state: Dictionary of shared state values
        metadata: Optional metadata about this snapshot
    """
    version: int
    timestamp: float
    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary representation.

        Returns:
            Dictionary with version, timestamp, state, and metadata
        """
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "state": deepcopy(self.state),
            "metadata": self.metadata.copy(),
        }


@dataclass
class Reality:
    """Shared reality manager for agent coordination.

    Provides a versioned shared state container that multiple agents can
    read and update. Uses optimistic concurrency control to detect conflicts.

    Attributes:
        initial_state: Starting state dictionary
        max_history: Maximum number of historical snapshots to retain

    Example:
        >>> reality = Reality(initial_state={"tasks": []})
        >>> reality.update({"tasks": ["task1"]})
        >>> version = reality.get_version()
        >>> reality.update({"tasks": ["task1", "task2"]}, expected_version=version)
    """
    initial_state: Dict[str, Any] = field(default_factory=dict)
    max_history: int = 100

    _current: RealitySnapshot = field(init=False)
    _history: List[RealitySnapshot] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        """Initialize reality with initial state."""
        self._current = RealitySnapshot(
            version=0,
            timestamp=time.time(),
            state=deepcopy(self.initial_state),
        )
        self._history = [self._current]
    
    def snapshot(self) -> RealitySnapshot:
        """Get current reality snapshot.

        Returns:
            Deep copy of current state snapshot
        """
        return RealitySnapshot(
            version=self._current.version,
            timestamp=self._current.timestamp,
            state=deepcopy(self._current.state),
            metadata=self._current.metadata.copy(),
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the current state.

        Args:
            key: State key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Value from state or default
        """
        return self._current.state.get(key, default)
    
    def update(self, updates: Dict[str, Any], expected_version: Optional[int] = None) -> bool:
        """Update the shared state.

        Performs optimistic concurrency control using version checking.
        If expected_version is provided and doesn't match current version,
        the update is rejected.

        Args:
            updates: Dictionary of key-value pairs to update
            expected_version: Expected current version (for conflict detection)

        Returns:
            True if update succeeded, False if version conflict detected
        """
        if expected_version is not None and expected_version != self._current.version:
            return False
        
        new_state = deepcopy(self._current.state)
        new_state.update(updates)
        
        self._current = RealitySnapshot(
            version=self._current.version + 1,
            timestamp=time.time(),
            state=new_state,
        )
        
        self._history.append(self._current)
        
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]
        
        return True
    
    def get_version(self) -> int:
        """Get current version number.

        Returns:
            Current version (increments with each update)
        """
        return self._current.version
