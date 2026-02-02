# seed-core

**Universal process monitoring and reality management for the Root (Seed) ecosystem.**

## Quick Start

### Installation

```bash
# From the seed-core directory
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Basic Usage

```python
from seed_core.pulse import PulseMonitor, HealthStatus

# Create a pulse monitor
monitor = PulseMonitor(timeout=10.0)

# Register a process
monitor.register_process("worker-1", interval=2.0, timeout=10.0)

# Send a heartbeat
monitor.pulse("worker-1", metadata={"task": "processing"})

# Check health
health = monitor.check_health("worker-1")
print(f"Status: {health.status.value}")  # "healthy"
print(f"Message: {health.message}")

# Get health for all processes
all_health = monitor.get_all_health()
```

### CLI Commands

```bash
# Check overall Root ecosystem status
seed-core status

# Check if spawnie is running
seed-core pulse

# List all known realities
seed-core reality list

# Check a specific reality
seed-core reality check /path/to/reality
```

## What is Seed-Core?

Seed-core provides the foundational monitoring infrastructure for the seed ecosystem:

- **Pulse**: Heartbeat-based process health monitoring
- **Status**: Aggregated status across all realities
- **Verification**: Hash-based drift detection
- **Monitor**: Real-time TUI for ecosystem visualization
- **CLI**: Command-line tools for management

## Core Concepts

### Pulse - Process Health Monitoring

Traditional process monitoring tells you *if* a process exists. Pulse tells you *how well* it's running.

**Health States:**
- `healthy`: Process is pulsing within expected interval
- `degraded`: Pulse delayed but within timeout
- `unhealthy`: No pulse within timeout period
- `unknown`: Process not registered or no pulse received

**Example:**
```python
monitor = PulseMonitor(timeout=10.0)
monitor.register_process("worker", interval=2.0)

# Process sends pulses every 2 seconds
monitor.pulse("worker")

# Health check
health = monitor.check_health("worker")
if health.is_healthy:
    print("All systems nominal")
```

### Status Aggregation

Collect and aggregate status across all realities in the Root meta-model.

**Example:**
```python
from seed_core.status import StatusAggregator

aggregator = StatusAggregator(pulse_monitor)
status = aggregator.get_status()

print(status.format_summary())
# 🟢 GREEN | 3 realities | 5 todos | 0 with drift

print(status.format_detailed())
# Full multi-line report with per-reality details
```

### Hash Verification

Detect when reality has drifted from the model by verifying source hashes.

**Example:**
```python
from seed_core.verification import verify_model

# Verify all sources in a model
results = verify_model(Path("/path/to/model/sketch.json"))

for check in results:
    if not check.is_ok:
        print(f"Drift detected: {check.node_id}")
        print(f"  Expected: {check.expected_hash}")
        print(f"  Actual: {check.actual_hash}")
```

## Why Seed-Core?

Seed-core solves a fundamental problem: **how do you know if your distributed system is healthy?**

Traditional approaches:
- ❌ Check PIDs → tells you if it exists, not if it's working
- ❌ Check exit codes → only tells you after it's dead
- ❌ Parse logs → brittle, slow, inconsistent

Seed-core approach:
- ✅ Active health monitoring via Pulse
- ✅ Model-based verification (hash checking)
- ✅ Aggregated status across the entire ecosystem
- ✅ Real-time visualization

## Architecture

```
seed-core/
├── pulse.py          # Heartbeat mechanism
│   ├── PulseMonitor   # Core monitoring engine
│   ├── PulseInfo      # Pulse data structure
│   └── HealthReport   # Health status report
│
├── status.py         # Status aggregation
│   ├── StatusAggregator  # Aggregate across realities
│   ├── SeedStatus        # Overall status
│   └── RealityStatus     # Per-reality status
│
├── verification.py   # Hash verification
│   ├── verify_model           # Verify a single model
│   ├── verify_all_realities   # Verify all realities
│   └── HashCheck             # Verification result
│
├── monitor.py        # TUI monitor
│   └── Monitor        # Rich-based live monitor
│
└── seed_core/
    └── __main__.py   # CLI entry point
```

## Development

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_pulse.py

# Run with verbose output
pytest -v
```

### Type Checking

```bash
mypy seed_core
```

### Code Formatting

```bash
# Format code
black seed_core

# Check style
ruff seed_core
```

## Integration with Seed

Seed-core is **infrastructure**, not domain logic:

1. **Independent**: Operates separately from any specific reality
2. **Universal**: Works across all realities in the seed meta-model
3. **Non-intrusive**: Processes opt-in to monitoring
4. **Model-aware**: Integrates with BAM models for verification

Other systems (like spawnie) use seed-core for:
- Monitoring worker process health
- Detecting when source files have changed
- Aggregating status across multiple concurrent operations

## License

MIT
