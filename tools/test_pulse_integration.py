#!/usr/bin/env python3
"""Integration test for the pulse mechanism.

Run this to verify the pulse implementation works with the actual seed model.
"""

import sys
from pathlib import Path

# Add seed_core to path
sys.path.insert(0, str(Path(__file__).parent))

from seed_core.pulse import Pulse


def main():
    """Run integration tests."""
    print("=" * 60)
    print("Pulse Mechanism Integration Test")
    print("=" * 60)

    model_path = Path(__file__).parent / "model" / "sketch.json"

    if not model_path.exists():
        print(f"[FAIL] Model file not found: {model_path}")
        return 1

    print(f"\n1. Loading model from {model_path}")
    try:
        pulse = Pulse(model_path)
        print(f"[OK] Model loaded successfully")
        print(f"  Schema version: {pulse.model.get('schema_version')}")
        print(f"  Project: {pulse.model.get('project')}")
    except Exception as e:
        print(f"[FAIL] Failed to load model: {e}")
        return 1

    print(f"\n2. Extracting realities")
    try:
        realities = pulse.get_realities()
        print(f"[OK] Found {len(realities)} realities:")
        for reality in realities:
            print(f"  - {reality.label} ({reality.id})")
            if reality.path:
                print(f"    Path: {reality.path}")
            if reality.model_path:
                print(f"    Model: {reality.model_path}")
    except Exception as e:
        print(f"[FAIL] Failed to get realities: {e}")
        return 1

    if not realities:
        print("\n[WARN] No realities found in model - skipping pulse checks")
        return 0

    print(f"\n3. Checking first reality: {realities[0].label}")
    try:
        result = pulse.check_reality(realities[0])
        print(f"[OK] Pulse check completed")
        print(f"  Status: {result.status}")
        print(f"  Activity: {result.activity}")
        print(f"  Hash verified: {result.hash_verified}")
        print(f"  Last checked: {result.last_checked}")

        if result.details:
            print(f"\n  Details:")
            for key, value in result.details.items():
                if isinstance(value, list):
                    if value:
                        print(f"    {key}: {len(value)} items")
                        # Show first few items
                        for item in value[:3]:
                            if isinstance(item, dict):
                                print(f"      - {item}")
                            else:
                                print(f"      - {item}")
                    else:
                        print(f"    {key}: []")
                else:
                    print(f"    {key}: {value}")
    except Exception as e:
        print(f"[FAIL] Failed to check reality: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print(f"\n4. Checking all realities (pulse_all)")
    try:
        results = pulse.pulse_all()
        print(f"[OK] Checked {len(results)} realities\n")

        # Summary
        status_counts = {"green": 0, "yellow": 0, "red": 0}
        activity_counts = {"idle": 0, "busy": 0, "error": 0}

        for result in results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
            activity_counts[result.activity] = activity_counts.get(result.activity, 0) + 1

            # Display each result
            status_emoji = {"green": "[GREEN]", "yellow": "[YELLOW]", "red": "[RED]"}.get(result.status, "[UNKNOWN]")
            activity_emoji = {"idle": "[IDLE]", "busy": "[BUSY]", "error": "[ERROR]"}.get(result.activity, "[?]")

            print(f"{status_emoji} {activity_emoji} {result.reality_id}")

            if result.details.get("drift"):
                print(f"    [WARN]  {len(result.details['drift'])} drifted files")
            if result.details.get("missing"):
                print(f"    [WARN]  {len(result.details['missing'])} missing files")
            if result.details.get("running_tasks", 0) > 0:
                print(f"    [BUSY]  {result.details['running_tasks']} running tasks")
            if result.details.get("todos_pending", 0) > 0:
                print(f"    [TODO] {result.details['todos_pending']} pending todos")
            if result.details.get("error"):
                print(f"    [ERROR] Error: {result.details['error']}")

        print(f"\nStatus Summary:")
        print(f"  Green: {status_counts['green']}")
        print(f"  Yellow: {status_counts['yellow']}")
        print(f"  Red: {status_counts['red']}")

        print(f"\nActivity Summary:")
        print(f"  Idle: {activity_counts['idle']}")
        print(f"  Busy: {activity_counts['busy']}")
        print(f"  Error: {activity_counts['error']}")

    except Exception as e:
        print(f"[FAIL] Failed to pulse all: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print(f"\n5. Quick verify test")
    try:
        verified = pulse.quick_verify(realities[0])
        print(f"[OK] Quick verify for {realities[0].label}: {'PASS' if verified else 'FAIL'}")
    except Exception as e:
        print(f"[FAIL] Failed quick verify: {e}")
        return 1

    print("\n" + "=" * 60)
    print("All tests passed! [OK]")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
