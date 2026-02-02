#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo of status aggregation functionality."""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add seed_core to path
sys.path.insert(0, str(Path(__file__).parent))

from seed_core import Pulse, StatusAggregator

# Example usage
if __name__ == "__main__":
    # Check if model path provided
    if len(sys.argv) < 2:
        print("Usage: python demo_status_aggregation.py <model_path>")
        print("\nExample with seed.model.json:")
        print("  python demo_status_aggregation.py seed.model.json")
        sys.exit(1)

    model_path = Path(sys.argv[1])

    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}")
        sys.exit(1)

    # Create Pulse instance
    print(f"Loading model: {model_path}")
    pulse = Pulse(model_path)

    # Create StatusAggregator
    aggregator = StatusAggregator(pulse)

    # Show summary
    print("\n" + "=" * 60)
    print("SUMMARY VIEW")
    print("=" * 60)
    print(aggregator.format_summary())

    # Show detailed view
    print("\n")
    print(aggregator.format_detailed())

    # Access programmatic status
    seed_status = aggregator.get_status()
    print("\nProgrammatic access:")
    print(f"  Overall: {seed_status.overall_status}")
    print(f"  Realities: {len(seed_status.realities)}")
    print(f"  Healthy: {seed_status.healthy_count}")
    print(f"  Need attention: {seed_status.attention_needed_count}")
    print(f"  Total todos: {seed_status.total_todos}")

    # Show individual reality details
    if seed_status.realities:
        print("\nIndividual reality lookup:")
        first_reality = seed_status.realities[0]
        reality_status = aggregator.get_reality_status(first_reality.id)
        if reality_status:
            print(f"  {reality_status.label}:")
            print(f"    Status: {reality_status.status}")
            print(f"    Activity: {reality_status.activity}")
            print(f"    Todos pending: {reality_status.todos_pending}")
            print(f"    Drift detected: {reality_status.drift_detected}")
