"""
Reality Registry - Loads and tracks all realities from the seed meta-model.

The Registry component provides discovery and lookup of all realities
tracked in the seed ecosystem. It loads the seed model and exposes
reality nodes for monitoring and management.

Key Features:
- Automatic loading from seed model (sketch.json)
- Reality lookup by ID or label
- Model path resolution
- Reality status checking

Example:
    >>> registry = RealityRegistry()
    >>> realities = registry.list_all()
    >>> spawnie = registry.find_by_label("Spawnie")
    >>> print(spawnie.has_model)  # True if model exists
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class Reality:
    """A reality (project) tracked in the seed meta-model.

    Represents a single Reality node from the seed model, containing
    all metadata needed to locate and verify the reality's model.

    Attributes:
        id: Unique identifier (e.g., "reality-spawnie")
        label: Human-readable name
        description: Brief description of this reality
        path: Filesystem path to the reality's root directory
        model_path: Relative path from root to model file
        status: Current status (active/no-model-yet/etc.)
        model_summary: Summary metadata from the model
    """
    id: str
    label: str
    description: str
    path: Optional[str]
    model_path: Optional[str]
    status: Optional[str]
    model_summary: Optional[Dict[str, Any]] = None

    @property
    def full_model_path(self) -> Optional[Path]:
        """Get the full path to this reality model file.

        Returns:
            Resolved Path to sketch.json, or None if path not configured
        """
        if self.path and self.model_path:
            return Path(self.path) / self.model_path
        return None

    @property
    def has_model(self) -> bool:
        """Check if this reality has a model file.

        Returns:
            True if model file exists on disk, False otherwise
        """
        model_file = self.full_model_path
        return model_file is not None and model_file.exists()


class RealityRegistry:
    """Loads and manages all realities from the seed meta-model.

    The registry is the central discovery mechanism for all realities.
    It parses the seed model and provides lookup methods.

    Attributes:
        seed_path: Root path to the seed project
        model_file: Path to seed's sketch.json
    """

    def __init__(self, seed_path: Path = None):
        """Initialize the registry and load realities.

        Args:
            seed_path: Path to seed root (defaults to parent of this file)
        """
        # __file__ is in src/seed_core/, so go up 3 levels to reach seed root
        self.seed_path = seed_path or Path(__file__).parent.parent.parent
        self.model_file = self.seed_path / "model" / "sketch.json"
        self._realities: Dict[str, Reality] = {}
        self._load()

    def _load(self):
        """Load realities from the seed model.

        Parses sketch.json and extracts all Reality nodes.

        Raises:
            FileNotFoundError: If seed model doesn't exist
            json.JSONDecodeError: If model is invalid JSON
        """
        if not self.model_file.exists():
            raise FileNotFoundError(f"Seed model not found: {self.model_file}")

        with open(self.model_file, 'r', encoding='utf-8') as f:
            model = json.load(f)

        for node in model.get('nodes', []):
            if node.get('type') == 'Reality':
                source = node.get('source', {})
                model_info = node.get('model', {})

                reality = Reality(
                    id=node['id'],
                    label=node['label'],
                    description=node.get('description', ''),
                    path=source.get('path'),
                    model_path=source.get('model_path'),
                    status=node.get('status'),
                    model_summary=model_info.get('_summary')
                )
                self._realities[reality.id] = reality

    def list_all(self) -> List[Reality]:
        """Get all realities.

        Returns:
            List of all Reality objects from the seed model
        """
        return list(self._realities.values())

    def get(self, reality_id: str) -> Optional[Reality]:
        """Get a specific reality by ID.

        Args:
            reality_id: Reality ID (e.g., "reality-spawnie")

        Returns:
            Reality object if found, None otherwise
        """
        return self._realities.get(reality_id)

    def find_by_label(self, label: str) -> Optional[Reality]:
        """Find a reality by label (case-insensitive).

        Args:
            label: Human-readable label (e.g., "Spawnie")

        Returns:
            Reality object if found, None otherwise
        """
        label_lower = label.lower()
        for reality in self._realities.values():
            if reality.label.lower() == label_lower:
                return reality
        return None
