# Seed-Core Overview

**Quick Reference for the Control Plane Architecture**

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                        SEED META-MODEL                          │
│                     (C:\seed\model\sketch.json)                 │
│                                                                 │
│  Tracks all realities:                                          │
│  - Spawnie (C:/spawnie)                                         │
│  - BAM (C:/BAM)                                                 │
│  - RF Semiconductor (future)                                    │
│  - Seed-Core (itself!)                                          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ managed by
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                         SEED-CORE                               │
│                  (C:\seed\seed_core\)                           │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ Pulse Engine   │  │ Reality Client │  │ Monitor TUI    │   │
│  │                │  │                │  │                │   │
│  │ - Heartbeats   │→ │ - Communicate  │→ │ - Visualize    │   │
│  │ - Scheduling   │  │ - Verify       │  │ - Aggregate    │   │
│  │ - Aggregation  │  │ - Detect drift │  │ - Real-time    │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ CLI: seed monitor | status | pulse | reality | todos   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ pulses
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                          REALITIES                              │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Spawnie         │  │  BAM             │  │  RF Semi     │ │
│  │                  │  │                  │  │              │ │
│  │  • Model         │  │  • Model         │  │  • Model     │ │
│  │  • Tracker       │  │  • Todos         │  │    (future)  │ │
│  │  • Running tasks │  │  • Source files  │  │              │ │
│  │  • Workflows     │  │                  │  │              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pulse Protocol Flow

```
PulseEngine
    │
    ├─── every 30s ───────────────────────────┐
    │                                          │
    ↓                                          ↓
┌─────────────────┐                    ┌─────────────────┐
│   Spawnie       │                    │   BAM           │
│   Reality       │                    │   Reality       │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │ PulseRequest                         │ PulseRequest
         │ check_level: "fast" | "verify"       │ check_level: "fast"
         │                                      │
         ↓                                      ↓
    Read tracker.json                      Read model only
    Read model                             Scan todos
    Check running tasks                    activity=unknown
    Scan todos
    Verify hashes (if needed)
         │                                      │
         ↓                                      ↓
    PulseResponse                          PulseResponse
    status: green                          status: green
    activity: busy                         activity: unknown
    running_tasks: 2                       running_tasks: 0
    pending_todos: 3                       pending_todos: 1
    drift_detected: false                  drift_detected: false
         │                                      │
         └──────────────┬───────────────────────┘
                        │
                        ↓
                ┌───────────────┐
                │  SeedStatus   │
                │  (aggregated) │
                └───────────────┘
                        │
                        ↓
                ┌───────────────┐
                │  Monitor TUI  │
                │   or CLI      │
                └───────────────┘
```

---

## Monitor TUI Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ SEED - Control Plane                                          [q]  │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌─────────────────────────┐  ┌───────────────────────────────────┐│
│ │ REALITIES               │  │ REALITY DETAIL: Spawnie           ││
│ │                         │  │                                   ││
│ │ 🟢 Seed-Core     idle   │  │ Path: C:/spawnie                  ││
│ │    0 tasks, 0 todos     │  │ Model: bam/model/sketch.json ✓    ││
│ │                         │  │ Status: 🟢 Green | Activity: Busy  ││
│ │ 🟢 Spawnie       busy   │← │ Last pulse: 2s ago                ││
│ │    2 tasks, 3 todos     │  │                                   ││
│ │                         │  │ Running Tasks (2):                ││
│ │ 🟢 BAM           idle   │  │   🔄 haiku - Analyzing benchmarks ││
│ │    0 tasks, 1 todo      │  │      ID: task_abc123              ││
│ │                         │  │                                   ││
│ │ ⚫ RF Semi       n/a    │  │   🔄 sonnet - Feature dev         ││
│ │    (no model yet)       │  │      ID: task_def456              ││
│ │                         │  │                                   ││
│ │                         │  │ Pending Todos (3):                ││
│ │ ─────────────────────── │  │   ⏳ Build BAM Tool (high)        ││
│ │ Overall: 🟢 Green       │  │   ⏳ Add drift detection (med)    ││
│ │ 2 running | 4 pending   │  │   ⏳ Write docs (low)             ││
│ └─────────────────────────┘  └───────────────────────────────────┘│
│                                                                     │
├────────────────────────────────────────────────────────────────────┤
│ [r] Refresh  [1-9] Select Reality  [q] Quit                        │
└────────────────────────────────────────────────────────────────────┘
```

---

## Package Structure

```
C:\seed\seed_core\
│
├── pulse\                   # Pulse mechanism
│   ├── engine.py            # PulseEngine - orchestrates heartbeats
│   ├── protocol.py          # PulseRequest/Response data structures
│   └── scheduler.py         # Scheduling logic (fast/slow intervals)
│
├── reality\                 # Reality interface
│   ├── client.py            # RealityClient base + SpawnieClient
│   ├── status.py            # RealityStatus, SeedStatus aggregation
│   └── verification.py      # Hash verification, drift detection
│
├── monitor\                 # Monitor TUI
│   ├── app.py               # Main Textual app
│   ├── views.py             # RealityListView, RealityDetailView
│   └── formatting.py        # Status symbols, colors
│
├── model\                   # Model operations
│   ├── loader.py            # Load BAM models (hierarchical)
│   ├── navigator.py         # Navigate between models (zoom in/out)
│   └── sync.py              # Update seed model with status
│
├── cli\                     # CLI commands
│   ├── pulse.py             # seed pulse
│   ├── status.py            # seed status
│   ├── monitor.py           # seed monitor
│   └── reality.py           # seed reality [add|remove|verify]
│
├── config.py                # Load config from model
├── __init__.py
└── __main__.py              # Entry point
```

---

## CLI Commands Quick Reference

```bash
# Monitor all realities (TUI)
seed monitor
seed monitor --reality spawnie    # Focus on one reality

# Status (text output)
seed status                       # All realities (table)
seed status spawnie               # Single reality (detailed)
seed status --json                # JSON output
seed status --watch               # Watch mode

# Pulse (manual trigger)
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

## Key Concepts

### 1. Pulse Protocol
Heartbeat-based monitoring with three levels:
- **fast**: Only check model hash (cheap, for idle+green)
- **verify**: Check all source file hashes (medium cost)
- **deep**: Full scan + rebuild summary (expensive)

### 2. Status Colors
- 🟢 **Green**: Verified, no drift, no errors
- 🟡 **Yellow**: Drift detected or unverified changes
- 🔴 **Red**: Error or model unreachable
- ⚫ **Unreachable**: Path doesn't exist

### 3. Activity States
- **Idle**: No running tasks
- **Busy**: Has running tasks
- **Unknown**: No tracker available

### 4. Lazy Verification
Optimization: Only verify file hashes when reality is busy or model changed.
If idle + green + model unchanged → skip verification (fast check).

### 5. Model-First
All configuration lives in the model, not files:
- ✅ Workflows → nodes in model
- ✅ Config → node in model
- ✅ Reality definitions → nodes in model
- ❌ No `~/.seed/config.json`
- ❌ No `~/.seed/workflows/*.json`

### 6. Self-Describing
Seed-core models itself. It appears in its own monitor!

### 7. Hierarchical Models
Nodes can contain sub-BAMs:
```
seed (meta-model)
 └── reality-spawnie
      └── model._ref → C:/spawnie/bam/model/sketch.json
           └── subsystem-core
                └── model.nodes: [mod-api, mod-workflow, ...]
```

---

## Integration with Spawnie

### Spawnie as First-Class Reality

Spawnie is special because it has a **tracker**:
- Live task tracking via `~/.spawnie/tracker.json`
- Accurate activity state (idle/busy)
- Workflow execution state

### SpawnieClient
Specialized client that:
1. Reads `tracker.json` for running tasks
2. Reads `bam/model/sketch.json` for model + todos
3. Determines activity from tracker status
4. Performs verification only when needed

### Monitor Migration
- **Current**: `spawnie monitor` shows only spawnie tasks
- **Future**: `seed monitor` shows ALL realities (including spawnie)
- **Eventually**: `spawnie monitor` → redirects to `seed monitor --reality spawnie`

---

## Implementation Phases

1. **Foundation** (Week 1): Package structure, model loader, basic client
2. **Pulse Engine** (Week 2): PulseEngine, scheduler, status aggregation
3. **CLI** (Week 3): status, pulse, reality, todos commands
4. **Monitor TUI** (Week 4): Multi-reality monitor interface
5. **Self-Model** (Week 5): Seed-core models itself
6. **Optimization** (Week 6): Lazy verification, caching

---

## Design Decisions

### Why Pulse-Based? (not event-driven)
- Simpler: realities don't need to know about seed-core
- Decoupled: realities work without seed-core running
- Resilient: works with dumb realities (just model files)
- Optimizable: can adjust polling frequency

### Why Model-First? (not config files)
- Consistent: same pattern as workflows
- Versioned: config changes tracked with model
- Inspectable: agents can read config
- Single source of truth

### Why Hierarchical? (not flat models)
- Scalable: large codebases need hierarchy
- Lazy loading: load only what you need
- Zoom in/out: navigate abstraction levels
- Summary views: show overview without loading everything

---

## Success Criteria

Seed-core is successful when:
1. ✅ Monitors all realities from single interface
2. ✅ Detects drift automatically
3. ✅ Fast for idle realities (hash check only)
4. ✅ Shows pending work across all realities
5. ✅ Self-describes (models itself)
6. ✅ Model-first (no config files)
7. ✅ Integrates with spawnie (unified view)

---

## Next Steps

1. **Validate design** with stakeholder feedback
2. **Implement Phase 1** (Foundation)
3. **Test with existing realities** (spawnie, BAM)
4. **Iterate based on real usage**

---

**See SEED_CORE_ARCHITECTURE.md for full details.**
