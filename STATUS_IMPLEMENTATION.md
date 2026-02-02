# Status Aggregation Implementation

## Overview

The status aggregation system has been successfully implemented in `src/seed_core/status.py`. This component provides hierarchical status reporting across all realities in the seed meta-model.

## Implementation Details

### 1. RealityStatus Dataclass

Located in `src/seed_core/status.py:29-64`

**Attributes:**
- `id: str` - Unique identifier for the reality
- `label: str` - Human-readable name
- `path: Optional[Path]` - Path to the reality's directory
- `status: Literal['green', 'yellow', 'red']` - Health status
- `activity: Literal['idle', 'busy', 'error']` - Activity state
- `todos_pending: int` - Number of pending todos
- `last_pulse: datetime` - Timestamp of last pulse check
- `drift_detected: bool` - Whether hash drift was detected

**Properties:**
- `is_healthy` - Returns True if status is green
- `has_issues` - Returns True if status is yellow or red
- `has_work` - Returns True if there are pending todos or activity

### 2. SeedStatus Dataclass

Located in `src/seed_core/status.py:68-107`

**Attributes:**
- `overall_status: Literal['green', 'yellow', 'red']` - Aggregated status
- `realities: List[RealityStatus]` - Individual reality statuses
- `total_todos: int` - Total pending todos across all realities
- `realities_with_drift: int` - Count of realities with drift
- `last_updated: datetime` - When this status was generated

**Properties:**
- `total_realities` - Total number of realities
- `healthy_realities` - Number of green realities
- `warning_realities` - Number of yellow realities
- `error_realities` - Number of red realities
- `is_healthy` - Returns True if overall status is green

### 3. StatusAggregator Class

Located in `src/seed_core/status.py:110-382`

**Methods:**

#### `__init__(pulse: Pulse)`
Initialize the aggregator with a Pulse instance.

#### `get_status(use_cache: bool = False) -> SeedStatus`
Get current aggregated status for all realities. Optionally uses cached results.

#### `get_reality_status(reality_id: str) -> Optional[RealityStatus]`
Get status for a specific reality by ID.

#### `format_summary() -> str`
Format a brief single-line summary:
```
✓ Seed Status: GREEN | 4 realities | 4 healthy
```

#### `format_detailed() -> str`
Format a detailed multi-line status report with:
- Overall status
- Summary section with counts
- Reality details section with individual statuses

### 4. Status Rules

Located in `src/seed_core/status.py:351-382`

The overall status is calculated using these rules:
- **Overall green**: All realities are green
- **Overall yellow**: Any reality is yellow, none are red
- **Overall red**: Any reality is red

## Integration with Pulse

The StatusAggregator integrates tightly with the Pulse component:

1. Uses `pulse.pulse_all()` to run health checks on all realities
2. Converts `PulseResult` objects to `RealityStatus` objects
3. Extracts key metrics:
   - Pending todos from `details['pending_todos']`
   - Drift detection from `details['hash_checks']['mismatch']`
   - Path, label, and other metadata

## Usage Example

```python
from pathlib import Path
from seed_core.pulse import Pulse
from seed_core.status import StatusAggregator

# Initialize pulse
model_path = Path("model/sketch.json")
pulse = Pulse(model_path)

# Initialize status aggregator
aggregator = StatusAggregator(pulse)

# Get status
status = aggregator.get_status()

# Print summary
print(aggregator.format_summary())

# Print detailed report
print(aggregator.format_detailed())

# Get individual reality status
reality_status = aggregator.get_reality_status('reality-spawnie')
if reality_status:
    print(f"Status: {reality_status.status}")
    print(f"Pending todos: {reality_status.todos_pending}")
```

## Test Results

The implementation has been tested with `test_status.py`:

```
✗ Seed Status: RED | 4 realities | 2 healthy | 1 warnings | 1 errors | 6 todos

SUMMARY
  Total Realities: 4
  Healthy (Green): 2
  Warnings (Yellow): 1
  Errors (Red): 1
  Total Pending Todos: 6
  Realities with Drift: 0

REALITY DETAILS
✓ [GREEN] Spawnie
✗ [RED] Seed
✓ [GREEN] BAM
⚠ [YELLOW] BAM Test Projects
```

## Files Modified

1. **C:\seed\seed_core\status.py** - Completely rewritten with new implementation
2. **C:\seed\seed_core\__init__.py** - Updated imports to export new classes:
   - `StatusAggregator`
   - `SeedStatus`
   - `RealityStatus`

## Files Created

1. **C:\seed\test_status.py** - Test script demonstrating functionality

## Features Implemented

✅ RealityStatus dataclass with all required fields and properties
✅ SeedStatus dataclass with aggregation metrics and properties
✅ StatusAggregator class with Pulse integration
✅ get_status() method with optional caching
✅ get_reality_status() method for individual queries
✅ format_summary() for single-line output
✅ format_detailed() for comprehensive reports
✅ Status rules (green/yellow/red aggregation)
✅ Proper imports and type hints
✅ Comprehensive documentation
✅ Working test script

## Architecture Alignment

This implementation follows the seed-core architecture:

- **Pulse-based**: Built on top of the Pulse health monitoring system
- **Aggregation layer**: Provides higher-level status views from low-level pulse data
- **Reality-centric**: Organizes status by reality nodes
- **Cacheable**: Supports caching to reduce redundant pulse checks
- **Formatted output**: Provides both summary and detailed views for different use cases
