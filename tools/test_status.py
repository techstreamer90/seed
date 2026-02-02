#!/usr/bin/env python3
"""
Test script for the status aggregation system.
"""

import sys
from pathlib import Path
from seed_core.pulse import Pulse
from seed_core.status import StatusAggregator


# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def main():
    # Path to seed model
    model_path = Path(__file__).parent / "model" / "sketch.json"

    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        return 1

    print(f"Loading seed model from: {model_path}")
    print()

    # Initialize pulse
    pulse = Pulse(model_path)

    # Initialize status aggregator
    aggregator = StatusAggregator(pulse)

    # Get status
    print("Gathering status information...")
    print()

    # Print summary
    summary = aggregator.format_summary()
    print("SUMMARY:")
    print(summary)
    print()

    # Print detailed report
    detailed = aggregator.format_detailed()
    print(detailed)

    # Test individual reality status
    print()
    print("=" * 70)
    print("TESTING INDIVIDUAL REALITY STATUS")
    print("=" * 70)

    status = aggregator.get_status()
    if status.realities:
        first_reality = status.realities[0]
        print(f"Testing get_reality_status for: {first_reality.id}")

        reality_status = aggregator.get_reality_status(first_reality.id)
        if reality_status:
            print(f"  ID: {reality_status.id}")
            print(f"  Label: {reality_status.label}")
            print(f"  Status: {reality_status.status}")
            print(f"  Activity: {reality_status.activity}")
            print(f"  Pending Todos: {reality_status.todos_pending}")
            print(f"  Drift Detected: {reality_status.drift_detected}")
            print(f"  Is Healthy: {reality_status.is_healthy}")
            print(f"  Has Issues: {reality_status.has_issues}")
            print(f"  Has Work: {reality_status.has_work}")

    return 0


if __name__ == "__main__":
    exit(main())
