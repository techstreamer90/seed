# Seed-Core Design Summary

**Executive Summary of Complete Architecture Design**

Date: 2026-02-01
Status: Design Complete, Ready for Implementation

---

## What is Seed-Core?

Seed-core is the **control center** for the seed meta-model system.

Current stance: **the model is the truth**.

Seed-core supports two distinct loops:

- **Model loop**: keep the model consistent and record progress/evidence (e.g. `seed-core watch`, `seed-core save`).
- **Reality loop**: verify that real files match model claims (drift detection via hashes; `seed-core verify`).

### Documents Created

1. **SEED_CORE_ARCHITECTURE.md** (18,000+ words)
   - Complete technical architecture
   - Module responsibilities
   - Protocol specifications
   - Data structure definitions
   - Implementation phases
   - Design decisions and rationale

2. **SEED_CORE_OVERVIEW.md** (Quick reference)
   - Visual diagrams
   - CLI command reference
   - Key concepts summary
   - Integration points

3. **This summary** (DESIGN_SUMMARY.md)

### Code Location (after 2026-02-02 restructure)

```
C:\seed\
├── model\sketch.json           # Root model (with zones)
├── src\
│   ├── seed_core\              # Core package
│   │   ├── __init__.py
│   │   ├── __main__.py         # CLI entry point
│   │   ├── pulse.py            # Heartbeat mechanism
│   │   ├── status.py           # Status aggregation
│   │   ├── registry.py         # Reality discovery
│   │   ├── reality.py          # Reality checks
│   │   ├── verification.py     # Hash verification
│   │   ├── model\              # seed_core's own model
│   │   └── tests\              # Test suite
│   ├── root_store\             # Model store package
│   └── ui\                     # Browser renderer
├── artifacts\                  # Generated files (read-only)
├── tools\                      # Scripts and tests
└── .state\                     # Runtime state (writable)
```

**Status**: Foundation protocols and data structures implemented.

---

## Architecture Highlights

### 1. Pulse Mechanism

**Heartbeat-based monitoring** with three verification levels:

- **Fast**: Hash check only (for idle+green realities)
- **Verify**: Check all source file hashes
- **Deep**: Full scan + rebuild model summary

**Lazy optimization**: Skip expensive verification when reality is idle and healthy.

### 2. Reality Interface

**Unified client interface** with specialized implementations:

- **SpawnieClient**: Reads tracker.json for live task info
- **GenericClient**: Works with any BAM model
- **Future: RealityAPI**: Native pulse protocol implementation

### 3. Monitor TUI

**Textual-based interface** showing:

- All realities with status (green/yellow/red)
- Running tasks across all realities
- Pending todos aggregated
- Drift detection alerts
- Hierarchical task display (reuses spawnie patterns)

### 4. Model-First Architecture

**All configuration lives in the model**:

```json
{
  "id": "config-seed-core",
  "type": "Config",
  "pulse": {
    "default_interval": 30,
    "fast_interval": 10,
    "slow_interval": 300
  },
  "monitor": {
    "refresh_rate": 5,
    "default_view": "list"
  }
}
```

No `~/.seed/config.json` file!

### 5. Self-Describing

Seed-core **models itself**:

- Has its own BAM model at `C:\seed\src\seed_core\model\sketch.json`
- Appears in seed meta-model as a reality
- Can monitor itself in its own TUI (meta-circularity!)

### 6. Hierarchical Navigation

Works with **nested BAM models**:

```
seed (meta-model)
 └── reality-spawnie
      └── model._ref → C:/spawnie/bam/model/sketch.json
           └── subsystem-core
                └── model.nodes: [mod-api, mod-workflow, ...]
```

Zoom in for detail, zoom out for overview.

---

## CLI Commands Designed

```bash
# Monitor (TUI)
seed monitor                      # Show all realities
seed monitor --reality spawnie    # Focus on one

# Status (text)
seed status                       # All realities (table)
seed status spawnie               # Single reality (detailed)
seed status --json                # JSON output
seed status --watch               # Watch mode

# Pulse (manual)
seed pulse                        # Pulse all realities
seed pulse spawnie                # Pulse one reality
seed pulse --level deep           # Deep verification

# Reality management
seed reality list                 # List all realities
seed reality add PATH             # Add new reality
seed reality remove ID            # Remove reality
seed reality verify spawnie       # Verify + drift report

# Todo aggregation
seed todos                        # All pending todos
seed todos --reality spawnie      # Filter by reality
seed todos --priority high        # Filter by priority
```

---

## Integration with Spawnie

### Monitor Migration

**Current state**: `spawnie monitor` shows only spawnie tasks.

**Future state**: `seed monitor` shows ALL realities.

**Benefits**:
- Unified view of entire ecosystem
- Track work across all projects
- Detect drift in any reality
- Aggregate todos from all realities

### Code Reuse

- Reuse Textual widgets from spawnie monitor
- Reuse task rendering logic
- Reuse status symbols and formatting
- Add reality-level aggregation layer

### SpawnieClient

Specialized client that leverages spawnie's tracker:

```python
class SpawnieClient(RealityClient):
    async def pulse(self, request: PulseRequest) -> PulseResponse:
        # Read tracker.json for live task info
        # Read model for todos
        # Determine activity from tracker
        # Verify hashes only when needed
        return PulseResponse(...)
```

---

## Data Structures

### Core Protocol

```python
@dataclass
class PulseRequest:
    timestamp: datetime
    check_level: str  # "fast" | "verify" | "deep"

@dataclass
class PulseResponse:
    reality_id: str
    timestamp: datetime
    status: str  # "green" | "yellow" | "red"
    activity: str  # "idle" | "busy" | "unknown"
    running_tasks: int
    pending_todos: int
    drift_detected: bool | None
    drift_files: list[str]
    error: str | None
```

### Status Aggregation

```python
@dataclass
class RealityStatus:
    reality_id: str
    label: str
    path: Path
    status: str
    activity: str
    has_model: bool
    running_tasks: int
    pending_todos: int
    todo_items: list[TodoItem]
    task_items: list[TaskInfo]
    drift_detected: bool
    drift_files: list[str]
    last_pulse: datetime | None
    next_pulse: datetime | None
    error: str | None

@dataclass
class SeedStatus:
    realities: dict[str, RealityStatus]
    updated_at: datetime

    @property
    def health(self) -> str:
        # "green" if all green, "red" if any red, "yellow" otherwise
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1) ✅ Started
- ✅ Package structure
- ✅ Protocol definitions (PulseRequest, PulseResponse)
- ✅ Status data structures (RealityStatus, SeedStatus)
- ⏳ Model loader with hierarchical support
- ⏳ Basic RealityClient

### Phase 2: Pulse Engine (Week 2)
- PulseEngine core
- PulseScheduler (adaptive intervals)
- SpawnieClient (specialized)
- Status aggregation
- Verification (hash checking)

### Phase 3: CLI (Week 3)
- `seed status` command
- `seed pulse` command
- `seed reality` commands
- `seed todos` command

### Phase 4: Monitor TUI (Week 4)
- Port spawnie monitor widgets
- Multi-reality list view
- Reality detail view
- Live pulse integration

### Phase 5: Self-Model (Week 5)
- Create seed-core's own model
- Add seed-core to seed model as reality
- Seed-core monitors itself

### Phase 6: Optimization (Week 6)
- Lazy verification
- Caching layer
- Performance tuning

---

## Key Design Decisions

### 1. Pulse-Based (not Event-Driven)

**Why**: Simpler, decoupled, works with dumb realities.

Realities don't need to know about seed-core. Works even if reality doesn't implement push API. Can optimize polling frequency based on activity.

### 2. Model-First Configuration

**Why**: Consistency, versioning, single source of truth.

Configuration as nodes in model, not files. Same pattern as workflows, reality definitions. Config changes tracked with model.

### 3. Lazy Verification

**Why**: Performance.

Skip expensive file hash verification when reality is idle and model unchanged. Fast check = just model hash. Verify check = all file hashes.

### 4. Hierarchical Models

**Why**: Scalability, lazy loading, navigation.

Nodes can contain sub-BAMs. Load only what you need. Zoom in for detail, zoom out for overview. Same pattern at every level.

### 5. Self-Describing

**Why**: Dogfooding, validation, meta-circularity.

Seed-core models itself using BAM. If it works for seed-core, it works for everything. Demonstrates the principle.

---

## Success Criteria

Seed-core is successful when:

1. ✅ **Monitors all realities** from a single interface
2. ✅ **Detects drift** automatically (model vs reality mismatch)
3. ✅ **Fast for idle realities** (hash check only, no full scan)
4. ✅ **Shows pending work** across all realities
5. ✅ **Self-describes** (seed-core models itself)
6. ✅ **Model-first** (no configuration files)
7. ✅ **Integrates with spawnie** (shows spawnie tasks in unified view)

---

## Next Steps

### Immediate (Phase 1 completion)

1. Implement `model/loader.py` (load BAM models with hierarchy)
2. Implement `reality/client.py` (base RealityClient + GenericClient)
3. Write tests for protocol and status structures
4. Document API

### Short-term (Phase 2)

1. Implement PulseEngine core
2. Implement PulseScheduler with adaptive intervals
3. Implement SpawnieClient with tracker integration
4. Implement verification module (hash checking)

### Medium-term (Phase 3-4)

1. Implement CLI commands
2. Build Monitor TUI
3. Test with real realities (spawnie, BAM)

### Long-term (Phase 5-6)

1. Create seed-core's own model
2. Add seed-core as reality in seed model
3. Optimize performance (caching, lazy verification)

---

## Files Created

### Documentation
- `C:\seed\SEED_CORE_ARCHITECTURE.md` (complete architecture)
- `C:\seed\SEED_CORE_OVERVIEW.md` (quick reference)
- `C:\seed\DESIGN_SUMMARY.md` (this file)

### Code
- `C:\seed\src\seed_core\__init__.py`
- `C:\seed\src\seed_core\__main__.py`
- `C:\seed\src\seed_core\pulse\protocol.py` ✅
- `C:\seed\src\seed_core\reality\status.py` ✅
- `C:\seed\src\seed_core\pulse\__init__.py`
- `C:\seed\src\seed_core\reality\__init__.py`
- `C:\seed\src\seed_core\monitor\__init__.py`
- `C:\seed\src\seed_core\model\__init__.py`
- `C:\seed\src\seed_core\cli\__init__.py`

---

## Questions for Implementation

### 1. Pulse Interval Defaults

What should the default intervals be?
- `default_interval`: 30s (normal polling)
- `fast_interval`: 10s (for busy realities)
- `slow_interval`: 5min (for idle+green realities)

These should be configurable in model. Suggestions?

### 2. Verification Strategy

How aggressive should verification be?
- **Conservative**: Always verify all files on every pulse
- **Balanced**: Skip verification for idle+green realities
- **Aggressive**: Only verify on-demand or when drift suspected

Current design uses **Balanced**. Acceptable?

### 3. Monitor Update Rate

How often should monitor refresh?
- 1s (very responsive, may flicker)
- 5s (balanced)
- 10s (conservative)

Should this be configurable? Default?

### 4. Daemon vs On-Demand

Should seed-core run as:
- **On-demand**: Only when user runs `seed monitor` or `seed status`
- **Daemon**: Background service always running

Current design: Start with on-demand, add daemon later. Correct?

### 5. Reality Discovery

How should seed-core discover new realities?
- **Manual**: User runs `seed reality add PATH`
- **Auto**: Scan filesystem for BAM models
- **Hybrid**: Manual with discovery suggestions

Current design uses **Manual**. Should we add auto-discovery?

---

## Open Questions

1. Should seed-core support **remote realities** (over SSH/HTTP)?
2. Should pulse responses be **cached** and for how long?
3. Should drift detection trigger **automatic notifications** (email, Slack)?
4. Should monitor support **filtering/searching** realities?
5. Should todos support **assignment** to humans/agents?

---

## Conclusion

A comprehensive, well-architected control plane for the seed meta-model system.

**Key innovations**:
- Pulse-based monitoring with lazy verification
- Model-first configuration (no files!)
- Self-describing (models itself)
- Hierarchical navigation (zoom in/out)
- Unified view of all realities

**Ready for implementation**: Phase 1 started, protocols defined, structure in place.

**Next**: Complete foundation modules and validate with real realities.

---

**Design Status**: ✅ Complete
**Implementation Status**: 🟡 In Progress (Phase 1)
**Documentation**: ✅ Comprehensive
