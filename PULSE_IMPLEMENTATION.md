# Pulse Mechanism Implementation

## Overview

The pulse mechanism has been successfully implemented in `src/seed_core/pulse.py`. It provides health monitoring and status detection for all realities in the seed model.

## Components Implemented

### 1. Data Classes

#### `Reality`
Represents a reality node from the seed model with:
- `id`: Unique identifier
- `label`: Human-readable name
- `path`: Filesystem path to the reality's root
- `model_path`: Path to the reality's BAM model file
- `description`: Description of the reality

#### `PulseResult`
Contains the result of checking a reality's pulse:
- `reality_id`: ID of the checked reality
- `status`: Health status (green/yellow/red)
  - **green**: All good, no drift, no errors
  - **yellow**: Minor issues (drift detected, busy with work)
  - **red**: Major issues (missing files, errors, todos in error state)
- `activity`: Activity level (idle/busy/error)
  - **idle**: No active work happening
  - **busy**: Active spawnie tasks or pending todos
  - **error**: Errors detected in todos or tasks
- `hash_verified`: Whether all source hashes match reality
- `last_checked`: Timestamp of the pulse check
- `details`: Dictionary with additional information

### 2. Pulse Class

The main `Pulse` class provides the following methods:

#### `__init__(model_path: Path)`
Initializes the pulse checker by loading the seed model.

**Error Handling:**
- `FileNotFoundError`: If model file doesn't exist
- `json.JSONDecodeError`: If model file is invalid JSON
- `ValueError`: If model is missing required fields

#### `get_realities() -> list[Reality]`
Extracts all Reality nodes from the model.

#### `quick_verify(reality: Reality) -> bool`
Performs a quick hash-only verification. Returns True if all hashes match.

#### `check_reality(reality: Reality) -> PulseResult`
Performs comprehensive pulse check including:
1. Hash verification of all source files
2. Detection of running spawnie tasks
3. Detection of pending/error todos
4. Status determination
5. Activity level determination

#### `pulse_all() -> list[PulseResult]`
Checks the pulse of all realities in the model. Returns a list of results.

### 3. Internal Helper Methods

#### `_sha256_file(path: Path) -> str`
Calculates SHA256 hash of a file.

#### `_verify_reality_hashes(reality: Reality) -> dict`
Verifies all source hashes in a reality's model. Returns:
- `verified`: List of files that match their hash
- `drifted`: List of files with hash mismatches
- `missing`: List of files that don't exist

#### `_check_spawnie_tasks(reality: Reality) -> list[dict]`
Checks for running spawnie tasks by reading the `.spawnie/tracker.json` file.

#### `_check_todos(reality: Reality) -> dict`
Checks for todos in a reality's model. Returns counts:
- `pending`: Number of pending todos
- `error`: Number of todos in error state
- `completed`: Number of completed todos

## Status Detection Logic

### Status Level Determination

The status is determined by this priority:

1. **RED** - Critical issues:
   - Hash verification failed
   - Files are missing

2. **YELLOW** - Warning conditions:
   - Files have drifted (hash mismatch)
   - Todos in error state
   - Active tasks running
   - Pending todos exist

3. **GREEN** - All clear:
   - No drift
   - No errors
   - No active work

### Activity Level Determination

Activity is determined by:

1. **ERROR** - Todos in error state exist
2. **BUSY** - Running spawnie tasks OR pending todos exist
3. **IDLE** - No active work

## Comprehensive Error Handling

All methods include:
- Try/catch blocks for file I/O operations
- JSON parsing error handling
- Logging at appropriate levels (info, warning, error, debug)
- Graceful degradation (if verification fails, continue with other checks)
- Error result objects when pulse checks fail completely

## Testing

### Integration Test

Run the integration test with:
```bash
cd C:/seed
python test_pulse_integration.py
```

The test verifies:
1. Model loading
2. Reality extraction
3. Single reality pulse check
4. All realities pulse check
5. Quick verification

### Test Results

All tests passed successfully with the seed model containing 4 realities:
- reality-spawnie (C:/spawnie)
- reality-bam (C:/BAM)
- reality-rf-semiconductor (aspiration)
- reality-bam-test-projects (next-step)

## Usage Example

```python
from seed_core.pulse import Pulse

# Initialize pulse checker
pulse = Pulse(Path("model/sketch.json"))

# Get all realities
realities = pulse.get_realities()

# Check a specific reality
result = pulse.check_reality(realities[0])
print(f"Status: {result.status}")
print(f"Activity: {result.activity}")
print(f"Hash verified: {result.hash_verified}")

# Check all realities
results = pulse.pulse_all()
for result in results:
    print(f"{result.reality_id}: {result.status}")

# Quick hash verification
verified = pulse.quick_verify(realities[0])
print(f"Verified: {verified}")
```

## Files Created

1. `src/seed_core/pulse.py` - Main implementation (479 lines)
2. `src/seed_core/__init__.py` - Package initialization
3. `test_pulse_integration.py` - Integration test script

## Dependencies

- Python 3.10+
- Standard library only:
  - `hashlib` - For SHA256 hashing
  - `json` - For model parsing
  - `logging` - For logging
  - `dataclasses` - For data structures
  - `datetime` - For timestamps
  - `pathlib` - For path handling
  - `typing` - For type hints

No external dependencies required.

## Logging

The module uses Python's standard logging with logger name `seed_core.pulse`:

- **INFO**: Major operations (model loaded, pulse checks started)
- **DEBUG**: Detailed information (number of realities found, hash verification details)
- **WARNING**: Recoverable issues (missing files, hash mismatches)
- **ERROR**: Serious errors (failed to load model, file I/O errors)

Configure logging in your application:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Architecture Notes

The implementation follows the architecture specified:
- Clean separation between pulse checking and status reporting
- Hash verification reuses logic from spawnie's BAM verification
- Spawnie task detection looks for tracker.json in reality directories
- Todo detection reads the reality's own model file
- All methods include comprehensive error handling
- No placeholders - all code is fully functional
