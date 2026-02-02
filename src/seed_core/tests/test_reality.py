"""Tests for seed_core.registry module (Reality and RealityRegistry)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from seed_core.registry import Reality, RealityRegistry


class TestReality:
    """Test Reality dataclass."""

    def test_reality_creation(self):
        """Test creating a Reality instance."""
        reality = Reality(
            id="reality-test",
            label="Test Reality",
            description="A test reality",
            path="/test/path",
            model_path="bam/model/sketch.json",
            status="active",
            model_summary={"nodes": 5}
        )

        assert reality.id == "reality-test"
        assert reality.label == "Test Reality"
        assert reality.description == "A test reality"
        assert reality.path == "/test/path"
        assert reality.model_path == "bam/model/sketch.json"
        assert reality.status == "active"
        assert reality.model_summary == {"nodes": 5}

    def test_full_model_path(self):
        """Test full_model_path property."""
        reality = Reality(
            id="test",
            label="Test",
            description="Test",
            path="/base/path",
            model_path="model/sketch.json",
            status=None
        )

        full_path = reality.full_model_path
        assert full_path is not None
        assert str(full_path).endswith("model/sketch.json") or str(full_path).endswith("model\\sketch.json")

    def test_full_model_path_none(self):
        """Test full_model_path returns None when no path."""
        reality = Reality(
            id="test",
            label="Test",
            description="Test",
            path=None,
            model_path=None,
            status=None
        )

        assert reality.full_model_path is None

    def test_has_model_with_existing_file(self, mock_model_path: Path):
        """Test has_model property with existing file."""
        reality = Reality(
            id="test",
            label="Test",
            description="Test",
            path=str(mock_model_path.parent.parent.parent),
            model_path=str(mock_model_path.relative_to(mock_model_path.parent.parent.parent)),
            status=None
        )

        assert reality.has_model is True

    def test_has_model_without_file(self):
        """Test has_model property without file."""
        reality = Reality(
            id="test",
            label="Test",
            description="Test",
            path=None,
            model_path=None,
            status=None
        )

        assert reality.has_model is False


class TestRealityRegistry:
    """Test RealityRegistry class."""

    def test_registry_init_with_seed_model(self, temp_dir: Path):
        """Test RealityRegistry initialization with valid seed model."""
        # Create seed model
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "reality-1",
                    "type": "Reality",
                    "label": "Reality 1",
                    "description": "First reality",
                    "source": {
                        "path": "/path/to/reality1",
                        "model_path": "bam/model/sketch.json"
                    },
                    "status": "active"
                }
            ]
        }

        model_file.write_text(json.dumps(model_data, indent=2))

        registry = RealityRegistry(seed_path=temp_dir)

        assert registry.seed_path == temp_dir
        assert registry.model_file == model_file
        assert len(registry._realities) == 1

    def test_registry_init_missing_model(self, temp_dir: Path):
        """Test RealityRegistry initialization with missing model."""
        with pytest.raises(FileNotFoundError):
            RealityRegistry(seed_path=temp_dir)

    def test_list_all(self, temp_dir: Path):
        """Test listing all realities."""
        # Create seed model with multiple realities
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "reality-1",
                    "type": "Reality",
                    "label": "Reality 1",
                    "description": "First reality",
                    "source": {"path": "/path1"},
                },
                {
                    "id": "reality-2",
                    "type": "Reality",
                    "label": "Reality 2",
                    "description": "Second reality",
                    "source": {"path": "/path2"},
                }
            ]
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        realities = registry.list_all()

        assert len(realities) == 2
        assert all(isinstance(r, Reality) for r in realities)

    def test_get_by_id(self, temp_dir: Path):
        """Test getting reality by ID."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "reality-test",
                    "type": "Reality",
                    "label": "Test Reality",
                    "description": "Test",
                    "source": {"path": "/path"},
                }
            ]
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        reality = registry.get("reality-test")

        assert reality is not None
        assert reality.id == "reality-test"
        assert reality.label == "Test Reality"

    def test_get_by_id_not_found(self, temp_dir: Path):
        """Test getting non-existent reality."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": []
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        reality = registry.get("nonexistent")

        assert reality is None

    def test_find_by_label(self, temp_dir: Path):
        """Test finding reality by label."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "reality-test",
                    "type": "Reality",
                    "label": "Test Reality",
                    "description": "Test",
                    "source": {"path": "/path"},
                }
            ]
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        reality = registry.find_by_label("Test Reality")

        assert reality is not None
        assert reality.id == "reality-test"

    def test_find_by_label_case_insensitive(self, temp_dir: Path):
        """Test finding reality by label (case-insensitive)."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "reality-test",
                    "type": "Reality",
                    "label": "Test Reality",
                    "description": "Test",
                    "source": {"path": "/path"},
                }
            ]
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        # Test various case combinations
        reality1 = registry.find_by_label("test reality")
        reality2 = registry.find_by_label("TEST REALITY")
        reality3 = registry.find_by_label("TeSt ReAlItY")

        assert reality1 is not None
        assert reality2 is not None
        assert reality3 is not None
        assert reality1.id == reality2.id == reality3.id == "reality-test"

    def test_find_by_label_not_found(self, temp_dir: Path):
        """Test finding non-existent reality by label."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": []
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        reality = registry.find_by_label("Nonexistent")

        assert reality is None


class TestModelParsing:
    """Test model parsing functionality in RealityRegistry."""

    def test_parse_reality_with_all_fields(self, temp_dir: Path):
        """Test parsing reality with all optional fields."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "reality-full",
                    "type": "Reality",
                    "label": "Full Reality",
                    "description": "A complete reality",
                    "source": {
                        "path": "/full/path",
                        "model_path": "bam/model/sketch.json"
                    },
                    "status": "active",
                    "model": {
                        "_summary": {
                            "nodes": 10,
                            "edges": 5
                        }
                    }
                }
            ]
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        reality = registry.get("reality-full")

        assert reality is not None
        assert reality.path == "/full/path"
        assert reality.model_path == "bam/model/sketch.json"
        assert reality.status == "active"
        assert reality.model_summary == {"nodes": 10, "edges": 5}

    def test_parse_reality_minimal(self, temp_dir: Path):
        """Test parsing reality with minimal fields."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "reality-minimal",
                    "type": "Reality",
                    "label": "Minimal Reality"
                    # No description, source, status, or model
                }
            ]
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        reality = registry.get("reality-minimal")

        assert reality is not None
        assert reality.description == ""
        assert reality.path is None
        assert reality.model_path is None
        assert reality.status is None
        assert reality.model_summary is None

    def test_parse_ignores_non_reality_nodes(self, temp_dir: Path):
        """Test that parser ignores non-Reality nodes."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "Module",
                    "label": "Module 1"
                },
                {
                    "id": "reality-1",
                    "type": "Reality",
                    "label": "Reality 1",
                    "source": {}
                },
                {
                    "id": "node-2",
                    "type": "Workflow",
                    "label": "Workflow 1"
                }
            ]
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        realities = registry.list_all()

        # Should only have 1 reality, not 3 nodes
        assert len(realities) == 1
        assert realities[0].id == "reality-1"


class TestRealityValidation:
    """Test reality validation scenarios."""

    def test_reality_path_validation(self, temp_dir: Path):
        """Test that reality paths are stored correctly."""
        model_dir = temp_dir / "model"
        model_dir.mkdir()
        model_file = model_dir / "sketch.json"

        test_paths = [
            "/absolute/path",
            "relative/path",
            str(temp_dir / "another" / "path"),
        ]

        nodes = [
            {
                "id": f"reality-{i}",
                "type": "Reality",
                "label": f"Reality {i}",
                "source": {"path": path}
            }
            for i, path in enumerate(test_paths)
        ]

        model_data = {
            "id": "seed",
            "type": "BAM",
            "nodes": nodes
        }

        model_file.write_text(json.dumps(model_data))
        registry = RealityRegistry(seed_path=temp_dir)

        # Verify paths are preserved exactly
        for i, expected_path in enumerate(test_paths):
            reality = registry.get(f"reality-{i}")
            assert reality.path == expected_path
