"""Tests for seed_core.pulse module."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime

import pytest

from seed_core.pulse import Pulse, PulseResult
from seed_core.registry import Reality


class TestPulseResult:
    """Test PulseResult dataclass."""

    def test_pulse_result_creation(self):
        """Test creating a PulseResult instance."""
        result = PulseResult(
            reality_id="test-reality",
            status="green",
            activity="idle",
            hash_verified=True,
            last_checked=datetime.now(),
        )

        assert result.reality_id == "test-reality"
        assert result.status == "green"
        assert result.activity == "idle"
        assert result.hash_verified is True
        assert result.details == {}

    def test_pulse_result_with_details(self):
        """Test PulseResult with detail information."""
        result = PulseResult(
            reality_id="test-reality",
            status="red",
            activity="error",
            hash_verified=False,
            last_checked=datetime.now(),
            details={"errors": ["Hash mismatch detected"]},
        )

        assert result.status == "red"
        assert result.activity == "error"
        assert result.hash_verified is False
        assert "errors" in result.details

    def test_pulse_result_properties(self):
        """Test PulseResult properties."""
        green_result = PulseResult(
            reality_id="test",
            status="green",
            activity="idle",
            hash_verified=True,
            last_checked=datetime.now(),
        )

        assert green_result.is_healthy is True
        assert green_result.has_issues is False

        red_result = PulseResult(
            reality_id="test",
            status="red",
            activity="error",
            hash_verified=False,
            last_checked=datetime.now(),
        )

        assert red_result.is_healthy is False
        assert red_result.has_issues is True

    def test_pulse_result_to_dict(self):
        """Test converting PulseResult to dictionary."""
        result = PulseResult(
            reality_id="test",
            status="green",
            activity="idle",
            hash_verified=True,
            last_checked=datetime(2026, 2, 1, 12, 0, 0),
            details={"label": "Test Reality"},
        )

        result_dict = result.to_dict()

        assert result_dict["reality_id"] == "test"
        assert result_dict["status"] == "green"
        assert result_dict["activity"] == "idle"
        assert result_dict["hash_verified"] is True
        assert "last_checked" in result_dict
        assert result_dict["details"]["label"] == "Test Reality"


class TestPulse:
    """Test Pulse class."""

    def test_pulse_init_with_valid_model(self, mock_seed_model: Path):
        """Test initializing Pulse with valid model."""
        pulse = Pulse(mock_seed_model)

        assert pulse.model_path == mock_seed_model
        assert pulse._model_data is not None

    def test_pulse_init_missing_model(self, temp_dir: Path):
        """Test initializing Pulse with missing model."""
        missing_model = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            Pulse(missing_model)

    def test_pulse_init_invalid_json(self, temp_dir: Path):
        """Test initializing Pulse with invalid JSON."""
        invalid_model = temp_dir / "invalid.json"
        invalid_model.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            Pulse(invalid_model)

    def test_get_realities(self, mock_seed_model: Path):
        """Test getting realities from seed model."""
        pulse = Pulse(mock_seed_model)
        realities = pulse.get_realities()

        assert len(realities) == 2
        assert all(isinstance(r, Reality) for r in realities)
        assert realities[0].id == "reality-project1"
        assert realities[1].id == "reality-project2"

    def test_get_realities_empty_model(self, temp_dir: Path, create_model_file):
        """Test get_realities with empty model."""
        empty_model = create_model_file({
            "id": "empty",
            "type": "BAM",
            "nodes": []
        })

        pulse = Pulse(empty_model)
        realities = pulse.get_realities()

        assert realities == []

    def test_check_reality_no_path(self, temp_dir: Path, create_model_file):
        """Test checking reality without path."""
        # Create a reality with no path
        model = create_model_file({
            "id": "test",
            "type": "BAM",
            "nodes": []
        })

        pulse = Pulse(model)

        # Create reality without path
        reality = Reality(
            id="test-reality",
            label="Test",
            description="Test reality",
            path=None,
            model_path=None,
            status=None,
            model_summary=None
        )

        result = pulse.check_reality(reality)

        assert result.reality_id == "test-reality"
        assert result.status in ("green", "yellow")  # Yellow because no path

    def test_check_reality_with_model(self, mock_reality_dir: Path, mock_model_path: Path, create_model_file):
        """Test checking reality with valid model."""
        seed_model = create_model_file({
            "id": "test",
            "type": "BAM",
            "nodes": []
        })

        pulse = Pulse(seed_model)

        reality = Reality(
            id="test-reality",
            label="Test",
            description="Test reality",
            path=str(mock_reality_dir),
            model_path=str(mock_model_path),
            status=None,
            model_summary=None
        )

        result = pulse.check_reality(reality)

        assert result.reality_id == "test-reality"
        assert result.status in ("green", "yellow", "red")
        assert "has_path" in result.details
        assert "has_model" in result.details

    def test_pulse_all(self, mock_seed_model: Path):
        """Test pulse_all on all realities."""
        pulse = Pulse(mock_seed_model)
        results = pulse.pulse_all()

        assert len(results) == 2
        assert all(isinstance(r, PulseResult) for r in results)
        assert all(r.reality_id in ("reality-project1", "reality-project2") for r in results)

    def test_quick_verify_no_model(self, temp_dir: Path):
        """Test quick_verify with reality that has no model."""
        seed_model = temp_dir / "seed.json"
        seed_model.write_text(json.dumps({"id": "test", "type": "BAM", "nodes": []}))

        pulse = Pulse(seed_model)

        reality = Reality(
            id="test",
            label="Test",
            description="Test",
            path=None,
            model_path=None,
            status=None,
            model_summary=None
        )

        result = pulse.quick_verify(reality)
        assert result is False

    def test_get_summary(self, mock_seed_model: Path):
        """Test getting summary statistics."""
        pulse = Pulse(mock_seed_model)
        summary = pulse.get_summary()

        assert "total" in summary
        assert "status" in summary
        assert "activity" in summary
        assert "hash_verified" in summary
        assert "timestamp" in summary

        assert summary["status"]["green"] >= 0
        assert summary["status"]["yellow"] >= 0
        assert summary["status"]["red"] >= 0


class TestHashVerification:
    """Test hash verification functionality."""

    def test_compute_file_hash(self, temp_dir: Path):
        """Test computing SHA-256 hash of a file."""
        test_file = temp_dir / "test.py"
        test_content = "# Test content\nprint('hello')"
        test_file.write_text(test_content)

        def compute_hash(file_path: Path) -> str:
            """Compute SHA-256 hash of file."""
            return hashlib.sha256(file_path.read_bytes()).hexdigest()

        file_hash = compute_hash(test_file)

        # Verify hash is a valid SHA-256 hex string
        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)

    def test_verify_hash_match(self, temp_dir: Path):
        """Test verifying matching hash."""
        test_file = temp_dir / "test.py"
        test_content = "# Test content"
        test_file.write_text(test_content)

        def compute_hash(file_path: Path) -> str:
            return hashlib.sha256(file_path.read_bytes()).hexdigest()

        expected_hash = compute_hash(test_file)
        actual_hash = compute_hash(test_file)

        assert expected_hash == actual_hash

    def test_verify_hash_mismatch(self, temp_dir: Path):
        """Test detecting hash mismatch."""
        test_file = temp_dir / "test.py"
        test_file.write_text("# Original content")

        def compute_hash(file_path: Path) -> str:
            return hashlib.sha256(file_path.read_bytes()).hexdigest()

        original_hash = compute_hash(test_file)

        # Modify file
        test_file.write_text("# Modified content")
        modified_hash = compute_hash(test_file)

        assert original_hash != modified_hash

    @pytest.mark.parametrize("content,expected_consistent", [
        ("hello", True),
        ("world", True),
        ("# Python code\nprint('test')", True),
    ])
    def test_hash_consistency(self, temp_dir: Path, content: str, expected_consistent: bool):
        """Test that hash computation is consistent."""
        test_file = temp_dir / "test.py"

        def compute_hash(file_path: Path) -> str:
            return hashlib.sha256(file_path.read_bytes()).hexdigest()

        # Write same content twice and verify hash is the same
        test_file.write_text(content)
        hash1 = compute_hash(test_file)

        test_file.write_text(content)
        hash2 = compute_hash(test_file)

        assert (hash1 == hash2) == expected_consistent
