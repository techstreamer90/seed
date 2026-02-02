"""Pytest fixtures for seed_core tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files.

    Args:
        tmp_path: pytest's built-in temporary path fixture

    Returns:
        Path to a temporary directory
    """
    return tmp_path


@pytest.fixture
def mock_model_path(temp_dir: Path) -> Path:
    """Create a mock BAM model file.

    Args:
        temp_dir: Temporary directory from fixture

    Returns:
        Path to the created model file
    """
    model_dir = temp_dir / "bam" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "sketch.json"

    model_data = {
        "id": "test-model",
        "type": "BAM",
        "label": "Test Model",
        "nodes": [
            {
                "id": "test-node-1",
                "type": "Module",
                "label": "Test Module 1",
                "source": {
                    "path": "src/module1.py",
                    "hash": "abc123"
                }
            },
            {
                "id": "test-node-2",
                "type": "Module",
                "label": "Test Module 2",
                "source": {
                    "path": "src/module2.py",
                    "hash": "def456"
                }
            }
        ]
    }

    model_path.write_text(json.dumps(model_data, indent=2))
    return model_path


@pytest.fixture
def mock_reality_dir(temp_dir: Path) -> Path:
    """Create a mock reality directory structure.

    Args:
        temp_dir: Temporary directory from fixture

    Returns:
        Path to the reality directory
    """
    reality_dir = temp_dir / "reality"
    reality_dir.mkdir(parents=True, exist_ok=True)

    # Create source files
    src_dir = reality_dir / "src"
    src_dir.mkdir(exist_ok=True)

    (src_dir / "module1.py").write_text("# Test module 1\nprint('hello')")
    (src_dir / "module2.py").write_text("# Test module 2\nprint('world')")

    return reality_dir


@pytest.fixture
def mock_seed_model(temp_dir: Path) -> Path:
    """Create a mock seed meta-model.

    Args:
        temp_dir: Temporary directory from fixture

    Returns:
        Path to the seed model file
    """
    model_dir = temp_dir / "seed" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "sketch.json"

    seed_data = {
        "id": "seed-meta",
        "type": "BAM",
        "label": "Seed Meta-Model",
        "nodes": [
            {
                "id": "reality-project1",
                "type": "Reality",
                "label": "Project 1",
                "source": {
                    "path": str(temp_dir / "project1"),
                    "model": "bam/model/sketch.json"
                }
            },
            {
                "id": "reality-project2",
                "type": "Reality",
                "label": "Project 2",
                "source": {
                    "path": str(temp_dir / "project2"),
                    "model": "bam/model/sketch.json"
                }
            }
        ]
    }

    model_path.write_text(json.dumps(seed_data, indent=2))
    return model_path


@pytest.fixture
def mock_pulse_data() -> dict[str, Any]:
    """Provide mock pulse check data.

    Returns:
        Dictionary with mock pulse data
    """
    return {
        "reality_id": "test-reality",
        "status": "green",
        "verified": True,
        "hash_match": True,
        "timestamp": "2026-02-01T12:00:00Z"
    }


@pytest.fixture
def mock_status_data() -> dict[str, Any]:
    """Provide mock status data.

    Returns:
        Dictionary with mock status aggregation data
    """
    return {
        "overall": "green",
        "realities": [
            {
                "id": "reality-1",
                "status": "green",
                "verified": True
            },
            {
                "id": "reality-2",
                "status": "yellow",
                "verified": True
            }
        ]
    }


@pytest.fixture
def create_model_file(temp_dir: Path):
    """Factory fixture to create model files with custom data.

    Args:
        temp_dir: Temporary directory from fixture

    Returns:
        Function that creates model files
    """
    def _create(data: dict[str, Any], subdir: str = "model") -> Path:
        """Create a model file with the given data.

        Args:
            data: Model data to write
            subdir: Subdirectory path (default: "model")

        Returns:
            Path to the created model file
        """
        model_dir = temp_dir / subdir
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "sketch.json"
        model_path.write_text(json.dumps(data, indent=2))
        return model_path

    return _create
