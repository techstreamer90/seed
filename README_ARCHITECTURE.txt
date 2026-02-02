SEED-CORE ARCHITECTURE DESIGN - COMPLETE
========================================

Date: 2026-02-01
Status: Design Complete, Ready for Implementation

WHAT WAS DELIVERED
------------------

A comprehensive, production-ready architecture design for seed-core, the control center
for the seed meta-model system.

THREE CORE DOCUMENTS CREATED
-----------------------------

1. SEED_CORE_ARCHITECTURE.md (~18,000 words)
   - Complete technical architecture
   - Package structure (pulse/, reality/, monitor/, model/, cli/)
   - Pulse protocol specification (PulseRequest/Response)
   - Data structures (RealityStatus, SeedStatus, TodoItem, TaskInfo)
   - Monitor TUI design (multi-reality view)
   - Spawnie integration (tracker.json reading)
   - Implementation phases (6 phases outlined)
   - Design decisions and rationale

2. IMPLEMENTATION_GUIDE.md (~10,000 words)
   - Step-by-step implementation instructions
   - Concrete code examples for each module
   - SpawnieClient implementation
   - Enhanced pulse protocol
   - Monitor migration strategy
   - CLI expansion
   - Testing strategy with fixtures
   - Deployment guide

3. DESIGN_SUMMARY.md
   - Executive overview
   - Quick reference
   - CLI command summary
   - Key design decisions
   - Success criteria

ARCHITECTURE HIGHLIGHTS
-----------------------

1. PULSE MECHANISM
   - Heartbeat-based monitoring with three levels:
     * Fast (~10ms): Hash check only for green+idle
     * Verify (~100ms): Check all source file hashes
     * Deep (~1s): Full scan + rebuild summary
   - Adaptive checking: fast when idle, thorough when active

2. SPAWNIE INTEGRATION
   - Read ~/.spawnie/tracker.json for live task data
   - Determine activity state (idle/busy/error)
   - Track running workflows and tasks
   - Extract todos from BAM model

3. MONITOR TUI
   - Multi-reality view (not just spawnie)
   - Shows all realities with status (green/yellow/red)
   - Aggregates todos across all realities
   - Detects drift and shows alerts
   - Real-time updates every 5 seconds

4. MODEL-FIRST ARCHITECTURE
   - All configuration lives in the model (C:\seed\model\sketch.json)
   - No ~/.seed/config.json file needed
   - Configuration as nodes in the model
   - Single source of truth

5. SELF-DESCRIBING
   - Seed-core models itself using BAM
   - Has its own model at seed_core/model/sketch.json
   - Appears in seed model as a reality
   - Monitors itself in its own TUI (meta-circularity!)

PACKAGE STRUCTURE
-----------------

C:\seed\seed_core\
├── pulse\
│   ├── engine.py         # PulseEngine - orchestrates heartbeats
│   ├── protocol.py       # PulseRequest/Response definitions
│   └── scheduler.py      # Adaptive scheduling logic
│
├── reality\
│   ├── client.py         # Generic RealityClient
│   ├── spawnie_client.py # Specialized spawnie client
│   ├── status.py         # RealityStatus, SeedStatus
│   └── verification.py   # Hash verification, drift detection
│
├── monitor\
│   ├── app.py            # Main Textual TUI app
│   ├── views.py          # Reality list, detail views
│   └── formatting.py     # Status symbols, colors
│
├── model\
│   ├── loader.py         # Load hierarchical BAM models
│   └── navigator.py      # Navigate between models (zoom in/out)
│
└── cli\
    ├── status.py         # seed status command
    ├── pulse.py          # seed pulse command
    ├── todos.py          # seed todos command
    └── reality.py        # seed reality subcommands

CLI COMMANDS DESIGNED
---------------------

# Monitor (TUI)
seed monitor                      # Show all realities
seed monitor --reality spawnie    # Focus on specific reality

# Status (text)
seed status                       # All realities (table)
seed status spawnie               # Single reality (detailed)
seed status --json                # JSON output
seed status --watch               # Watch mode (updates every 2s)

# Pulse (manual trigger)
seed pulse                        # Pulse all realities
seed pulse spawnie                # Pulse specific reality
seed pulse --level deep           # Deep verification

# Todo aggregation
seed todos                        # All pending todos across all realities
seed todos --reality spawnie      # Filter by reality
seed todos --priority high        # Filter by priority

# Reality management
seed reality list                 # List all realities
seed reality add PATH             # Add new reality to seed model
seed reality remove ID            # Remove reality
seed reality verify spawnie       # Verify + detailed drift report

IMPLEMENTATION PHASES
---------------------

Phase 0: Foundation (DONE)
- ✅ Package structure created
- ✅ Protocol definitions (pulse.py, status.py)
- ✅ Basic CLI skeleton

Phase 1: Spawnie Integration (NEXT, 1-2 days)
- Create SpawnieClient
- Read tracker.json
- Detect activity (idle/busy/error)
- Test with real spawnie tracker

Phase 2: Enhanced Pulse (2-3 days)
- Multi-level checking (fast/verify/deep)
- Adaptive check level selection
- Caching layer
- Hash verification integration

Phase 3: Monitor Migration (3-4 days)
- Multi-reality views
- Port spawnie monitor widgets
- Live pulse integration
- Alert panel for drift

Phase 4: CLI Expansion (1-2 days)
- Enhanced status command
- Todo aggregation command
- Watch mode
- JSON output support

Phase 5: Self-Model (1 day)
- Create seed-core's own BAM model
- Add seed-core to seed model as reality
- Verify self-monitoring works

Phase 6: Optimization (ongoing)
- Lazy verification
- Caching improvements
- Performance tuning

KEY DESIGN DECISIONS
--------------------

1. PULSE-BASED (not event-driven)
   Why: Simpler, decoupled, works with "dumb" realities
   Realities don't need to know about seed-core
   No coupling between systems

2. MODEL-FIRST CONFIGURATION
   Why: Single source of truth, versioned, introspectable
   Configuration as nodes in model, not files
   Same pattern as workflows, reality definitions

3. LAZY VERIFICATION
   Why: Performance
   Skip expensive file scanning when reality is idle+green
   Only verify when activity detected or drift suspected

4. HIERARCHICAL MODELS
   Why: Scalability, lazy loading
   Nodes can contain sub-models
   Zoom in for detail, zoom out for overview

5. SELF-DESCRIBING
   Why: Dogfooding, validation
   Seed-core models itself using BAM
   If it works for seed-core, it works everywhere

DATA STRUCTURES
---------------

Core Protocol:

@dataclass
class PulseRequest:
    reality_id: str
    check_level: "fast" | "verify" | "deep"
    timestamp: datetime

@dataclass
class PulseResponse:
    reality_id: str
    status: "green" | "yellow" | "red"
    activity: "idle" | "busy" | "error"
    running_tasks: int
    pending_todos: int
    drift_detected: bool
    drift_files: list[str]
    timestamp: datetime

Status Aggregation:

@dataclass
class RealityStatus:
    reality_id: str
    label: str
    path: Path
    status: str
    activity: str
    running_tasks: int
    pending_todos: int
    drift_detected: bool
    last_pulse: datetime

@dataclass
class SeedStatus:
    realities: dict[str, RealityStatus]
    updated_at: datetime

    @property
    def health(self) -> str  # Overall ecosystem health

INTEGRATION WITH SPAWNIE
-------------------------

SpawnieClient reads:
1. ~/.spawnie/tracker.json → active tasks, workflows
2. C:/spawnie/bam/model/sketch.json → todos, aspirations
3. Determines activity from tracker
4. Verifies hashes only when not green+idle

Monitor migration:
- Current: spawnie monitor (single reality)
- Future: seed monitor (all realities)
- Reuses spawnie's Textual widgets
- Adds reality-level aggregation

WHAT EXISTS NOW
---------------

C:\seed\seed_core\
├── pulse.py              ✅ Basic pulse mechanism
├── status.py             ✅ Status tracking classes
├── reality.py            ✅ Reality state management
├── verification.py       ✅ Hash verification
├── monitor.py            ✅ Basic TUI monitor
├── __init__.py           ✅ Public API exports
├── __main__.py           ✅ CLI entry point (basic)
└── pyproject.toml        ✅ Package config

WHAT NEEDS TO BE BUILT
-----------------------

Priority 1: Spawnie Integration
- seed_core/reality/spawnie_client.py
- Test with real tracker.json

Priority 2: Enhanced Pulse
- seed_core/pulse/engine.py
- seed_core/pulse/scheduler.py
- Multi-level checking logic

Priority 3: Monitor Migration
- seed_core/monitor/views.py
- Multi-reality panels
- Workflow visualization

Priority 4: CLI Expansion
- seed_core/cli/status.py (enhanced)
- seed_core/cli/todos.py
- seed_core/cli/pulse.py

SUCCESS CRITERIA
----------------

Seed-core is complete when:
✅ Monitors all realities from single interface
✅ Detects spawnie activity accurately (idle/busy)
✅ Shows all pending todos across realities
✅ Detects drift automatically
✅ Fast checks (<100ms) for idle realities
✅ Monitor shows multi-reality view
✅ Self-describes (models itself)
✅ Model-first (no config files)

PERFORMANCE TARGETS
-------------------

- Pulse all realities (fast mode): <50ms
- Pulse all realities (verify mode): <500ms
- Monitor refresh: <100ms (cached)
- CLI status: <200ms (includes pulse)

NEXT STEPS
----------

1. Read DESIGN_SUMMARY.md for high-level overview
2. Read SEED_CORE_ARCHITECTURE.md for complete details
3. Follow IMPLEMENTATION_GUIDE.md Phase 1 to start building
4. Test with real spawnie tracker data
5. Iterate through remaining phases

DOCUMENTATION FILES
-------------------

C:\seed\
├── SEED_CORE_ARCHITECTURE.md     (~1100 lines, complete architecture)
├── IMPLEMENTATION_GUIDE.md        (~700 lines, step-by-step guide)
├── DESIGN_SUMMARY.md              (~470 lines, executive summary)
└── README_ARCHITECTURE.txt        (this file, quick reference)

QUESTIONS FOR IMPLEMENTATION
-----------------------------

1. Pulse interval defaults? (30s normal, 10s fast, 5min slow)
2. Verification strategy? (balanced: skip when idle+green)
3. Monitor update rate? (5s default)
4. Daemon vs on-demand? (start on-demand, add daemon later)
5. Reality discovery? (manual via CLI, auto-discovery later)

THE DESIGN IS COMPLETE AND READY FOR IMPLEMENTATION!

All architectural decisions documented.
All integration points specified.
Implementation path clear.

Time to build! 🚀
