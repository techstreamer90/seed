"""Tests for seed_core.status module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from datetime import datetime
from pathlib import Path

import pytest

from seed_core.status import StatusAggregator, RealityStatus, SeedStatus
from seed_core.pulse import Pulse


class TestRealityStatus:
    """Test RealityStatus dataclass."""

    def test_reality_status_creation(self):
        """Test creating a RealityStatus instance."""
        status = RealityStatus(
            id="reality-test",
            label="Test Reality",
            path=Path("/test/path"),
            status="green",
            activity="idle",
            todos_pending=0,
            last_pulse=datetime.now(),
            drift_detected=False
        )

        assert status.id == "reality-test"
        assert status.label == "Test Reality"
        assert status.status == "green"
        assert status.activity == "idle"
        assert status.todos_pending == 0
        assert status.drift_detected is False

    def test_reality_status_with_issues(self):
        """Test RealityStatus with error information."""
        status = RealityStatus(
            id="reality-test",
            label="Test Reality",
            path=Path("/test/path"),
            status="red",
            activity="error",
            todos_pending=5,
            last_pulse=datetime.now(),
            drift_detected=True
        )

        assert status.status == "red"
        assert status.activity == "error"
        assert status.todos_pending == 5
        assert status.drift_detected is True

    def test_reality_status_properties(self):
        """Test RealityStatus properties."""
        green_status = RealityStatus(
            id="test",
            label="Test",
            path=None,
            status="green",
            activity="idle",
            todos_pending=0,
            last_pulse=datetime.now(),
            drift_detected=False
        )

        assert green_status.is_healthy is True
        assert green_status.has_issues is False
        assert green_status.has_work is False

        red_status = RealityStatus(
            id="test",
            label="Test",
            path=None,
            status="red",
            activity="error",
            todos_pending=3,
            last_pulse=datetime.now(),
            drift_detected=True
        )

        assert red_status.is_healthy is False
        assert red_status.has_issues is True
        assert red_status.has_work is True


class TestSeedStatus:
    """Test SeedStatus dataclass."""

    def test_seed_status_creation(self):
        """Test creating a SeedStatus instance."""
        realities = [
            RealityStatus(
                "r1", "Reality 1", None, "green", "idle", 0, datetime.now(), False
            ),
            RealityStatus(
                "r2", "Reality 2", None, "green", "idle", 0, datetime.now(), False
            ),
        ]

        status = SeedStatus(
            overall_status="green",
            realities=realities,
            total_todos=0,
            realities_with_drift=0,
            last_updated=datetime.now()
        )

        assert status.overall_status == "green"
        assert status.total_realities == 2
        assert status.total_todos == 0
        assert status.realities_with_drift == 0

    def test_seed_status_properties(self):
        """Test SeedStatus computed properties."""
        realities = [
            RealityStatus(
                "r1", "Reality 1", None, "green", "idle", 0, datetime.now(), False
            ),
            RealityStatus(
                "r2", "Reality 2", None, "yellow", "busy", 2, datetime.now(), False
            ),
            RealityStatus(
                "r3", "Reality 3", None, "red", "error", 1, datetime.now(), True
            ),
        ]

        status = SeedStatus(
            overall_status="red",
            realities=realities,
            total_todos=3,
            realities_with_drift=1,
            last_updated=datetime.now()
        )

        assert status.total_realities == 3
        assert status.healthy_realities == 1
        assert status.warning_realities == 1
        assert status.error_realities == 1
        assert status.is_healthy is False


class TestStatusAggregator:
    """Test StatusAggregator class."""

    def test_init(self, mock_seed_model: Path):
        """Test StatusAggregator initialization."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        assert aggregator.pulse is pulse
        assert aggregator._cached_status is None

    def test_get_status(self, mock_seed_model: Path):
        """Test getting aggregated status."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        status = aggregator.get_status()

        assert isinstance(status, SeedStatus)
        assert status.overall_status in ("green", "yellow", "red")
        assert len(status.realities) == 2
        assert status.total_todos >= 0
        assert status.realities_with_drift >= 0

    def test_get_status_with_cache(self, mock_seed_model: Path):
        """Test status caching."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        # First call
        status1 = aggregator.get_status()

        # Second call with cache
        status2 = aggregator.get_status(use_cache=True)

        # Should be same object from cache
        assert status1 is status2

        # Third call without cache
        status3 = aggregator.get_status(use_cache=False)

        # Should be new object
        assert status3 is not status1

    def test_get_reality_status(self, mock_seed_model: Path):
        """Test getting status for specific reality."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        reality_status = aggregator.get_reality_status("reality-project1")

        assert reality_status is not None
        assert isinstance(reality_status, RealityStatus)
        assert reality_status.id == "reality-project1"

    def test_get_reality_status_not_found(self, mock_seed_model: Path):
        """Test getting status for non-existent reality."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        reality_status = aggregator.get_reality_status("nonexistent")

        assert reality_status is None

    def test_format_summary(self, mock_seed_model: Path):
        """Test formatting status summary."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        aggregator.get_status()  # Populate cache
        summary = aggregator.format_summary()

        assert isinstance(summary, str)
        assert "Seed Status:" in summary
        assert "realities" in summary

    def test_format_detailed(self, mock_seed_model: Path):
        """Test formatting detailed status report."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        aggregator.get_status()  # Populate cache
        detailed = aggregator.format_detailed()

        assert isinstance(detailed, str)
        assert "SEED STATUS REPORT" in detailed
        assert "SUMMARY" in detailed
        assert "REALITY DETAILS" in detailed

    def test_calculate_overall_status(self, mock_seed_model: Path):
        """Test overall status calculation logic."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        # All green
        all_green = [
            RealityStatus("r1", "R1", None, "green", "idle", 0, datetime.now(), False),
            RealityStatus("r2", "R2", None, "green", "idle", 0, datetime.now(), False),
        ]
        overall = aggregator._calculate_overall_status(all_green)
        assert overall == "green"

        # Has yellow
        has_yellow = [
            RealityStatus("r1", "R1", None, "green", "idle", 0, datetime.now(), False),
            RealityStatus("r2", "R2", None, "yellow", "busy", 0, datetime.now(), False),
        ]
        overall = aggregator._calculate_overall_status(has_yellow)
        assert overall == "yellow"

        # Has red
        has_red = [
            RealityStatus("r1", "R1", None, "green", "idle", 0, datetime.now(), False),
            RealityStatus("r2", "R2", None, "yellow", "busy", 0, datetime.now(), False),
            RealityStatus("r3", "R3", None, "red", "error", 0, datetime.now(), False),
        ]
        overall = aggregator._calculate_overall_status(has_red)
        assert overall == "red"

        # Empty list
        overall = aggregator._calculate_overall_status([])
        assert overall == "green"


class TestStatusRules:
    """Test status determination rules."""

    @pytest.mark.parametrize("statuses,expected_overall", [
        (["green", "green", "green"], "green"),
        (["green", "yellow", "green"], "yellow"),
        (["green", "green", "red"], "red"),
        (["yellow", "yellow"], "yellow"),
        (["red", "red"], "red"),
        (["yellow", "red"], "red"),
    ])
    def test_status_aggregation_rules(self, statuses, expected_overall, temp_dir: Path, create_model_file):
        """Test status aggregation follows priority rules."""
        # Create a seed model
        seed_model = create_model_file({"id": "test", "type": "BAM", "nodes": []})
        pulse = Pulse(seed_model)
        aggregator = StatusAggregator(pulse)

        # Create reality statuses
        reality_statuses = [
            RealityStatus(
                f"r{i}", f"Reality {i}", None, status, "idle", 0, datetime.now(), False
            )
            for i, status in enumerate(statuses)
        ]

        overall = aggregator._calculate_overall_status(reality_statuses)
        assert overall == expected_overall


class TestFormatting:
    """Test status formatting functions."""

    def test_format_summary_basic(self, mock_seed_model: Path):
        """Test basic summary formatting."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        aggregator.get_status()
        summary = aggregator.format_summary()

        assert "Seed Status:" in summary
        assert "realities" in summary.lower()

    def test_format_detailed_structure(self, mock_seed_model: Path):
        """Test detailed report structure."""
        pulse = Pulse(mock_seed_model)
        aggregator = StatusAggregator(pulse)

        aggregator.get_status()
        detailed = aggregator.format_detailed()

        # Check for key sections
        assert "SEED STATUS REPORT" in detailed
        assert "SUMMARY" in detailed
        assert "REALITY DETAILS" in detailed
        assert "Overall Status:" in detailed
        assert "Total Realities:" in detailed
