# Seed-Core Architecture

**Control Plane for the Seed Meta-Model System**

Version: 1.0
Date: 2026-02-01
Status: Design Phase

---

## Executive Summary

Seed-core is the control center for the seed meta-model system. It monitors all linked realities (projects with BAM models), detects drift between models and reality, and provides a unified view of the entire seed ecosystem.

**Core Principles:**
1. **Model-First**: All configuration lives in the model, not files
2. **Self-Describing**: Seed-core models itself using BAM
3. **Pulse-Based**: Periodic heartbeats check reality health
4. **Lazy Verification**: Fast status checks for idle realities, deep verification only when needed
5. **Hierarchical**: Works with nested BAM models at any level

---

## 1. Package Structure

```
C:\seed\
├── model\
│   └── sketch.json                    # Seed meta-model (already exists)
│
├── seed_core\                         # New package
│   ├── __init__.py
│   ├── __main__.py                    # CLI entry point
│   │
│   ├── pulse\                         # Pulse mechanism
│   │   ├── __init__.py
│   │   ├── engine.py                  # PulseEngine - orchestrates heartbeats
│   │   ├── protocol.py                # Protocol definitions (request/response)
│   │   └── scheduler.py               # Scheduling logic for pulses
│   │
│   ├── reality\                       # Reality interface
│   │   ├── __init__.py
│   │   ├── client.py                  # RealityClient - talks to realities
│   │   ├── status.py                  # Status aggregation
│   │   └── verification.py            # Hash verification, drift detection
│   │
│   ├── monitor\                       # Monitoring TUI
│   │   ├── __init__.py
│   │   ├── app.py                     # Main Textual app
│   │   ├── views.py                   # UI views (reality list, detail, todos)
│   │   └── formatting.py              # Status symbols, colors
│   │
│   ├── model\                         # Model operations
│   │   ├── __init__.py
│   │   ├── loader.py                  # Load BAM models (hierarchical)
│   │   ├── navigator.py               # Navigate between models (zoom in/out)
│   │   └── sync.py                    # Keep seed model in sync
│   │
│   ├── cli\                           # CLI commands
│   │   ├── __init__.py
│   │   ├── pulse.py                   # pulse commands
│   │   ├── status.py                  # status commands
│   │   ├── monitor.py                 # monitor command
│   │   └── reality.py                 # reality management commands
│   │
│   └── config.py                      # Configuration (model-first!)
│
├── tests\
│   └── seed_core\                     # Test suite
│
└── SEED_CORE_ARCHITECTURE.md          # This document
```

---

## 2. Core Modules and Responsibilities

### 2.1 Pulse Engine (`pulse/`)

**Purpose**: Periodically send heartbeats to all realities and collect status.

#### `engine.py` - PulseEngine
```python
class PulseEngine:
    """Orchestrates pulse heartbeats to all realities."""

    def __init__(self, model_path: Path):
        self.model = load_model(model_path)
        self.scheduler = PulseScheduler()
        self.clients: dict[str, RealityClient] = {}

    async def start(self):
        """Start the pulse engine."""
        # Load all realities from model
        # Create clients for each
        # Start scheduler

    async def pulse_all(self) -> dict[str, RealityStatus]:
        """Send pulse to all realities, return aggregated status."""

    async def pulse_one(self, reality_id: str) -> RealityStatus:
        """Pulse a single reality."""
```

**Key Responsibilities:**
- Load reality definitions from seed model
- Maintain client connections to each reality
- Schedule periodic pulses (configurable interval)
- Aggregate status from all realities
- Trigger verification when needed

#### `protocol.py` - Pulse Protocol
```python
@dataclass
class PulseRequest:
    """Heartbeat request sent to reality."""
    timestamp: datetime
    check_level: str  # "fast" | "verify" | "deep"

@dataclass
class PulseResponse:
    """Heartbeat response from reality."""
    reality_id: str
    timestamp: datetime
    status: str  # "green" | "yellow" | "red"
    activity: str  # "idle" | "busy"

    # Model info
    model_hash: str | None  # Hash of current model
    model_modified: datetime | None

    # Activity info
    running_tasks: int
    pending_todos: int

    # Verification info (only if check_level != "fast")
    drift_detected: bool | None
    drift_files: list[str] | None  # Files with hash mismatches

    # Error info
    error: str | None
```

**Protocol Design:**
- **Fast Check** (status=green, activity=idle): Only verify model hash
- **Verify Check** (status=yellow OR activity=busy): Check file hashes
- **Deep Check** (on demand): Full verification, rebuild model summary

#### `scheduler.py` - PulseScheduler
```python
class PulseScheduler:
    """Schedules pulses based on reality state."""

    def __init__(self, config: PulseConfig):
        self.default_interval = config.default_interval  # e.g., 30s
        self.fast_interval = config.fast_interval  # e.g., 10s for busy
        self.slow_interval = config.slow_interval  # e.g., 5min for idle

    def next_pulse_time(self, reality_status: RealityStatus) -> datetime:
        """Determine when to pulse this reality next."""
        # Busy → pulse more often
        # Idle + green → pulse less often
        # Yellow/red → pulse more often
```

---

### 2.2 Reality Interface (`reality/`)

**Purpose**: Communicate with realities, verify state, aggregate status.

#### `client.py` - RealityClient
```python
class RealityClient:
    """Client for communicating with a single reality."""

    def __init__(self, reality_node: dict):
        self.reality_id = reality_node["id"]
        self.path = Path(reality_node["source"]["path"])
        self.model_path = self.path / reality_node["source"]["model_path"]

    async def pulse(self, request: PulseRequest) -> PulseResponse:
        """Send pulse request, get response."""
        # For spawnie: check tracker.json + model hash
        # For generic reality: check model hash + scan source files

    async def get_todos(self) -> list[TodoItem]:
        """Get pending todos from this reality."""

    async def get_running_tasks(self) -> list[TaskInfo]:
        """Get running tasks (if reality supports it)."""
```

**Reality Communication Strategies:**

1. **Spawnie Reality** (has tracker):
   - Read `~/.spawnie/tracker.json` for running tasks
   - Read `C:/spawnie/bam/model/sketch.json` for model + todos
   - Check tracker status to determine activity (idle/busy)

2. **Generic Reality** (no tracker):
   - Read `{path}/bam/model/sketch.json`
   - Scan NEEDS edges to Todo nodes
   - Activity = idle (no way to know if busy)
   - Hash verification by scanning source files

3. **Future: Reality API** (if reality implements it):
   - HTTP/gRPC endpoint at reality
   - Reality implements pulse protocol natively
   - More accurate status, real-time updates

#### `status.py` - Status Aggregation
```python
@dataclass
class RealityStatus:
    """Aggregated status for a single reality."""
    reality_id: str
    label: str  # Human-readable name
    path: Path

    # Status
    status: str  # "green" | "yellow" | "red" | "unreachable"
    activity: str  # "idle" | "busy" | "unknown"

    # Model info
    has_model: bool
    model_hash: str | None
    model_modified: datetime | None

    # Work tracking
    running_tasks: int
    pending_todos: int
    todo_items: list[TodoItem]

    # Verification
    drift_detected: bool
    drift_files: list[str]

    # Timing
    last_pulse: datetime
    next_pulse: datetime

    # Error
    error: str | None

@dataclass
class SeedStatus:
    """Aggregated status for entire seed ecosystem."""
    realities: dict[str, RealityStatus]

    @property
    def total_pending_work(self) -> int:
        return sum(r.pending_todos for r in self.realities.values())

    @property
    def total_running_tasks(self) -> int:
        return sum(r.running_tasks for r in self.realities.values())

    @property
    def health(self) -> str:
        """Overall health: green if all green, red if any red, yellow otherwise."""
        statuses = [r.status for r in self.realities.values()]
        if all(s == "green" for s in statuses):
            return "green"
        if any(s == "red" for s in statuses):
            return "red"
        return "yellow"
```

#### `verification.py` - Hash Verification
```python
class Verifier:
    """Verify reality matches model."""

    def __init__(self, model_path: Path, source_root: Path):
        self.model = load_model(model_path)
        self.source_root = source_root

    def verify_fast(self) -> bool:
        """Fast check: only verify model file hash."""
        # Check if model file itself has changed

    def verify_full(self) -> VerificationResult:
        """Full verification: check all source file hashes in model."""
        # Walk model nodes with source.file + source.hash
        # Compute actual hash
        # Report drift

    def detect_drift(self) -> list[DriftItem]:
        """Return list of files with hash mismatches."""
```

---

### 2.3 Monitor TUI (`monitor/`)

**Purpose**: Visual interface showing status of all realities.

#### `app.py` - MonitorApp
```python
class SeedMonitor(App):
    """Textual TUI for monitoring all realities."""

    CSS_PATH = "monitor.css"
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
        ("1-9", "select_reality", "Select Reality"),
    ]

    def __init__(self):
        super().__init__()
        self.pulse_engine = PulseEngine(SEED_MODEL_PATH)
        self.status: SeedStatus | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield RealityListView()  # Shows all realities
        yield RealityDetailView()  # Shows selected reality details
        yield Footer()

    async def on_mount(self):
        """Start pulse engine and refresh timer."""
        await self.pulse_engine.start()
        self.set_interval(5.0, self.refresh_status)
```

**Monitor Views:**

1. **Reality List View** (left panel)
   ```
   SEED - Control Plane
   ────────────────────────────────────
   🟢 Spawnie              busy  2 tasks, 3 todos
   🟢 BAM                  idle  0 tasks, 1 todo
   🔴 RF Semiconductor     n/a   (no model yet)
   ────────────────────────────────────
   Overall: 🟢 Green  |  2 running  |  4 pending
   ```

2. **Reality Detail View** (right panel)
   ```
   Reality: Spawnie
   Path: C:/spawnie
   Model: bam/model/sketch.json (verified ✓)
   Status: 🟢 Green | Activity: Busy
   Last pulse: 2s ago | Next pulse: 8s

   Running Tasks (2):
     🔄 haiku - Analyzing benchmark results
        ID: task_abc123 | Status: running

     🔄 sonnet - Implementing feature-dev workflow
        ID: task_def456 | Status: running

   Pending Todos (3):
     ⏳ Build BAM Tool (high priority)
     ⏳ Add drift detection (medium priority)
     ⏳ Write documentation (low priority)

   Model Summary:
     Schema: 3.0 | Level: system
     Subsystems: 3 (core, providers, workflows)
     Concepts: 5 | Aspirations: 2
   ```

3. **Drift View** (if drift detected)
   ```
   ⚠️  DRIFT DETECTED

   Files modified outside model:
     src/spawnie/api.py
       Expected: c32e2915...
       Actual:   a7f3d821...

   Action: Run 'seed reality verify spawnie' for details
   ```

#### `views.py` - UI Components
```python
class RealityListView(Static):
    """Shows list of all realities with status."""

class RealityDetailView(ScrollableContainer):
    """Shows details of selected reality."""

class TodoListWidget(Static):
    """Renders todo items."""

class TaskListWidget(Static):
    """Renders running tasks (hierarchical like spawnie monitor)."""
```

---

### 2.4 Model Operations (`model/`)

**Purpose**: Load, navigate, and sync BAM models.

#### `loader.py` - Model Loader
```python
class ModelLoader:
    """Load BAM models with hierarchical support."""

    def load(self, model_path: Path) -> dict:
        """Load a BAM model."""

    def load_with_refs(self, model_path: Path) -> dict:
        """Load model and resolve all _ref pointers."""
        # Recursively load referenced models

    def get_summary(self, model_path: Path) -> dict:
        """Get model summary without loading full tree."""
        # For displaying in monitor without loading everything
```

#### `navigator.py` - Model Navigator
```python
class ModelNavigator:
    """Navigate between hierarchical BAM models."""

    def __init__(self, seed_model: dict):
        self.root = seed_model
        self.current = seed_model
        self.path: list[str] = []

    def zoom_in(self, node_id: str):
        """Zoom into a node's sub-model."""

    def zoom_out(self):
        """Zoom back to parent model."""

    def find_reality(self, reality_id: str) -> dict | None:
        """Find a reality node in seed model."""
```

#### `sync.py` - Model Sync
```python
class ModelSyncer:
    """Keep seed model in sync with reality."""

    def update_reality_status(self, reality_id: str, status: RealityStatus):
        """Update reality node in seed model with latest status."""
        # Update model with status, last_pulse, etc.
        # This is execution layer data

    def add_reality(self, reality_config: dict):
        """Add new reality to seed model."""

    def remove_reality(self, reality_id: str):
        """Remove reality from seed model."""
```

---

## 3. Pulse Protocol Details

### 3.1 Pulse Levels

| Level | When Used | What It Checks | Cost |
|-------|-----------|----------------|------|
| **fast** | Reality is green + idle | Model file hash only | Very low |
| **verify** | Reality is yellow OR busy | All source file hashes | Medium |
| **deep** | On-demand or after drift | Full scan + rebuild summary | High |

### 3.2 Status Determination

**Status Colors:**
- 🟢 **Green**: Model verified, no drift, no errors
- 🟡 **Yellow**: Drift detected OR unverified changes
- 🔴 **Red**: Error occurred OR model unreachable
- ⚫ **Unreachable**: Reality path doesn't exist

**Activity States:**
- **Idle**: No running tasks (from tracker if available)
- **Busy**: Has running tasks
- **Unknown**: No tracker available

### 3.3 Pulse Flow

```
┌─────────────┐
│ PulseEngine │
└──────┬──────┘
       │
       ├─ every 30s (default) ───┐
       │                         │
       v                         v
┌──────────────┐          ┌──────────────┐
│   Spawnie    │          │     BAM      │
│  (has tracker)│         │ (no tracker) │
└──────┬───────┘          └──────┬───────┘
       │                          │
       │ Read tracker.json        │ Read model only
       │ Read model               │
       │ Determine activity       │ activity=unknown
       │                          │
       v                          v
┌──────────────────────────────────────┐
│         PulseResponse                │
│  status: green/yellow/red            │
│  activity: idle/busy/unknown         │
│  running_tasks: N                    │
│  pending_todos: M                    │
│  drift_detected: true/false          │
└──────────────────────────────────────┘
       │
       v
┌──────────────┐
│ SeedStatus   │ ← Aggregated view
└──────────────┘
```

### 3.4 Optimization: Lazy Verification

**Problem**: Verifying all file hashes on every pulse is expensive.

**Solution**: Multi-level checking.

```python
async def pulse_reality(reality: RealityClient) -> PulseResponse:
    # Step 1: Check activity (cheap)
    activity = await reality.check_activity()

    # Step 2: Determine check level
    if activity == "idle" and last_status == "green":
        check_level = "fast"  # Only model hash
    else:
        check_level = "verify"  # All hashes

    # Step 3: Perform check
    if check_level == "fast":
        model_hash = compute_hash(reality.model_path)
        drift_detected = (model_hash != cached_model_hash)
    else:
        drift_items = await reality.verify_full()
        drift_detected = len(drift_items) > 0

    return PulseResponse(
        status="green" if not drift_detected else "yellow",
        activity=activity,
        drift_detected=drift_detected,
        ...
    )
```

**Cache Strategy:**
- Cache model hash after verification
- If fast check shows model unchanged, skip file verification
- Only verify files when model changed or activity != idle

---

## 4. Integration with Spawnie

### 4.1 Spawnie as a Reality

Spawnie is a **first-class reality** that implements the pulse protocol natively through its tracker.

**Spawnie-specific capabilities:**
- Live task tracking via `tracker.json`
- Accurate activity state (idle/busy)
- Task hierarchy (parent/child tasks)
- Workflow execution state

**Integration points:**

```python
class SpawnieClient(RealityClient):
    """Specialized client for Spawnie reality."""

    def __init__(self, reality_node: dict):
        super().__init__(reality_node)
        self.tracker_path = Path.home() / ".spawnie" / "tracker.json"

    async def pulse(self, request: PulseRequest) -> PulseResponse:
        # Read tracker
        tracker_data = json.loads(self.tracker_path.read_text())

        # Get running tasks
        running_tasks = [
            t for t in tracker_data.get("tasks", {}).values()
            if t["status"] == "running"
        ]

        # Get workflows
        running_workflows = [
            w for w in tracker_data.get("workflows", {}).values()
            if w["status"] in ["queued", "running"]
        ]

        # Determine activity
        activity = "busy" if running_tasks or running_workflows else "idle"

        # Get model
        model = load_model(self.model_path)

        # Find todos
        todo_nodes = [n for n in model["nodes"] if n["type"] == "Todo"]
        pending_todos = [t for t in todo_nodes if t.get("status") == "pending"]

        # Verify if needed
        drift_detected = False
        if request.check_level != "fast":
            verifier = Verifier(self.model_path, self.path)
            drift = verifier.detect_drift()
            drift_detected = len(drift) > 0

        return PulseResponse(
            reality_id=self.reality_id,
            status="green" if not drift_detected else "yellow",
            activity=activity,
            running_tasks=len(running_tasks),
            pending_todos=len(pending_todos),
            drift_detected=drift_detected,
            ...
        )
```

### 4.2 Moving Monitor from Spawnie to Seed

**Current**: `spawnie monitor` shows only spawnie tasks.
**Future**: `seed monitor` shows ALL realities.

**Migration path:**
1. Keep `spawnie monitor` as-is (backward compatibility)
2. Create `seed monitor` with multi-reality view
3. Eventually deprecate `spawnie monitor` → redirect to `seed monitor --reality spawnie`

**Code reuse:**
- Reuse Textual widgets from spawnie monitor
- Reuse rendering logic for tasks/workflows
- Add reality-level aggregation layer

---

## 5. CLI Commands

### 5.1 Command Structure

```bash
seed <command> [subcommand] [options]
```

### 5.2 Command Reference

#### `seed monitor`
Launch the monitor TUI showing all realities.

```bash
seed monitor                    # Show all realities
seed monitor --reality spawnie  # Focus on specific reality
seed monitor --refresh 5        # Refresh every 5 seconds
```

#### `seed pulse`
Manually trigger a pulse.

```bash
seed pulse                      # Pulse all realities
seed pulse spawnie              # Pulse specific reality
seed pulse --level deep         # Deep verification
```

#### `seed status`
Show status without TUI.

```bash
seed status                     # Show all realities (table)
seed status spawnie             # Show specific reality (detailed)
seed status --json              # JSON output
seed status --watch             # Watch mode (like top)
```

Example output:
```
SEED Status
───────────────────────────────────────────────────
Reality          Status    Activity  Tasks  Todos
───────────────────────────────────────────────────
Spawnie          🟢 Green  Busy      2      3
BAM              🟢 Green  Idle      0      1
RF Semiconductor ⚫ N/A     N/A       -      -
───────────────────────────────────────────────────
Overall: 🟢 Green  |  2 running  |  4 pending
```

#### `seed reality`
Manage realities.

```bash
seed reality list               # List all realities
seed reality add PATH           # Add new reality
seed reality remove ID          # Remove reality
seed reality verify spawnie     # Verify reality (detailed drift report)
seed reality sync spawnie       # Sync model from reality
```

#### `seed todos`
View todos across all realities.

```bash
seed todos                      # Show all pending todos
seed todos --reality spawnie    # Filter by reality
seed todos --priority high      # Filter by priority
```

Example output:
```
Pending Work Across All Realities
────────────────────────────────────────────────────
Reality          Priority  Todo
────────────────────────────────────────────────────
Spawnie          High      Build BAM Tool
Spawnie          Medium    Add drift detection
BAM              Medium    BAM Test Projects
Spawnie          Low       Write documentation
────────────────────────────────────────────────────
Total: 4 pending todos
```

#### `seed daemon`
Run pulse engine as background daemon (future).

```bash
seed daemon start               # Start daemon
seed daemon stop                # Stop daemon
seed daemon status              # Check daemon status
seed daemon logs                # View daemon logs
```

---

## 6. Configuration (Model-First!)

**Key principle**: Configuration lives in the model, not files.

### 6.1 Configuration Node in Seed Model

```json
{
  "id": "config-seed-core",
  "type": "Config",
  "label": "Seed-Core Configuration",
  "pulse": {
    "default_interval": 30,
    "fast_interval": 10,
    "slow_interval": 300,
    "enable_daemon": false
  },
  "monitor": {
    "refresh_rate": 5,
    "default_view": "list",
    "show_completed_tasks": false
  },
  "verification": {
    "hash_algorithm": "sha256",
    "skip_patterns": ["*.pyc", "__pycache__", ".git"],
    "auto_verify_on_idle": true
  }
}
```

### 6.2 Loading Configuration

```python
class SeedConfig:
    """Configuration for seed-core."""

    def __init__(self, model: dict):
        config_node = self.find_config_node(model)
        self.pulse = PulseConfig(**config_node.get("pulse", {}))
        self.monitor = MonitorConfig(**config_node.get("monitor", {}))
        self.verification = VerificationConfig(**config_node.get("verification", {}))

    @classmethod
    def load(cls, model_path: Path) -> "SeedConfig":
        model = load_model(model_path)
        return cls(model)
```

**No `~/.seed/config.json` file!** Configuration is in the model.

---

## 7. Data Structures Summary

### Core Types

```python
# Pulse Protocol
class PulseRequest
class PulseResponse

# Reality Status
class RealityStatus
class SeedStatus

# Model Navigation
class ModelLoader
class ModelNavigator

# Verification
class VerificationResult
class DriftItem

# Configuration (from model)
class SeedConfig
class PulseConfig
class MonitorConfig
```

### State Reuse from Spawnie

```python
# Reused from spawnie.tracker
class TaskState      # Running task info
class WorkflowState  # Workflow execution info
class StepState      # Workflow step info

# New for seed-core
class TodoItem       # Todo from any reality
class RealityInfo    # Basic reality metadata
```

---

## 8. Self-Describing: Seed-Core Models Itself

Seed-core **must model itself** in the seed model. This demonstrates the principle.

### 8.1 Seed-Core Reality Node

Add to `C:\seed\model\sketch.json`:

```json
{
  "id": "reality-seed-core",
  "type": "Reality",
  "label": "Seed-Core",
  "description": "Control plane for seed meta-model system. Monitors all realities.",
  "source": {
    "path": "C:/seed",
    "model_path": "src/seed_core/model/sketch.json"
  },
  "model": {
    "_ref": "C:/seed/src/seed_core/model/sketch.json",
    "_summary": {
      "schema_version": "3.0",
      "level": "system",
      "subsystems": ["pulse", "reality", "monitor", "model", "cli"]
    }
  }
}
```

### 8.2 Seed-Core's Own Model

Create `C:\seed\seed_core\model\sketch.json`:

```json
{
  "schema_version": "3.0",
  "project": "seed-core",
  "description": "Control plane for the seed meta-model system",
  "source_root": "..",

  "nodes": [
    {
      "id": "subsystem-pulse",
      "type": "Subsystem",
      "label": "Pulse",
      "description": "Pulse mechanism - heartbeat to realities",
      "model": {
        "nodes": [
          {
            "id": "mod-pulse-engine",
            "type": "Module",
            "label": "engine.py",
            "source": {"file": "pulse/engine.py"}
          },
          {
            "id": "mod-pulse-protocol",
            "type": "Module",
            "label": "protocol.py",
            "source": {"file": "pulse/protocol.py"}
          }
        ]
      }
    },
    {
      "id": "subsystem-reality",
      "type": "Subsystem",
      "label": "Reality Interface",
      "description": "Communicate with realities, verify status"
    },
    {
      "id": "subsystem-monitor",
      "type": "Subsystem",
      "label": "Monitor TUI",
      "description": "Visual interface for all realities"
    },
    {
      "id": "concept-pulse-protocol",
      "type": "Concept",
      "label": "Pulse Protocol",
      "description": "Heartbeat-based monitoring with lazy verification"
    },
    {
      "id": "aspiration-universal-monitor",
      "type": "Aspiration",
      "label": "Universal Reality Monitor",
      "description": "Monitor all realities from a single control plane"
    }
  ]
}
```

**Result**: Seed-core appears in its own monitor!

```
SEED - Control Plane
────────────────────────────────────
🟢 Seed-Core            idle  0 tasks, 0 todos
🟢 Spawnie              busy  2 tasks, 3 todos
🟢 BAM                  idle  0 tasks, 1 todo
```

**Meta-circularity**: The monitor monitors itself. Turtles all the way down!

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1)
- ✅ Package structure
- ✅ Model loader with hierarchical support
- ✅ Basic RealityClient (generic)
- ✅ PulseRequest/Response protocol

### Phase 2: Pulse Engine (Week 2)
- ✅ PulseEngine core
- ✅ PulseScheduler
- ✅ SpawnieClient (specialized)
- ✅ Status aggregation
- ✅ Basic verification (hash checking)

### Phase 3: CLI (Week 3)
- ✅ `seed status` command
- ✅ `seed pulse` command
- ✅ `seed reality` commands
- ✅ `seed todos` command

### Phase 4: Monitor TUI (Week 4)
- ✅ Port spawnie monitor widgets
- ✅ Multi-reality list view
- ✅ Reality detail view
- ✅ Live pulse integration
- ✅ `seed monitor` command

### Phase 5: Self-Model (Week 5)
- ✅ Create seed-core's own model
- ✅ Add seed-core to seed model as reality
- ✅ Seed-core monitors itself

### Phase 6: Optimization (Week 6)
- ✅ Lazy verification optimization
- ✅ Caching layer
- ✅ Performance tuning

### Phase 7: Daemon (Future)
- Background pulse daemon
- System service integration
- WebSocket API for real-time updates

---

## 10. Key Design Decisions

### 10.1 Why Pulse-Based Instead of Event-Driven?

**Considered**: Realities push events to seed-core (event-driven).

**Chosen**: Seed-core pulls status via pulses (poll-based).

**Reasoning**:
1. **Simplicity**: Realities don't need to know about seed-core
2. **No coupling**: Realities can exist without seed-core running
3. **Resilience**: Works even if reality doesn't implement push API
4. **Lazy optimization**: Can optimize polling frequency based on activity
5. **Bootstrapping**: Works with dumb realities (just model files)

**Trade-off**: Slight latency (polling interval), but acceptable for monitoring use case.

### 10.2 Why Model-First Configuration?

**Considered**: `~/.seed/config.json` file.

**Chosen**: Configuration as node in seed model.

**Reasoning**:
1. **Consistency**: Same pattern as workflows, reality definitions
2. **Versioned**: Config changes tracked with model
3. **Inspectable**: Agents can read config from model
4. **Self-documenting**: Model defines what configuration means
5. **Single source of truth**: No sync between file and model

### 10.3 Why Hierarchical Models?

**Considered**: Flat model for each reality.

**Chosen**: Nodes can contain sub-models.

**Reasoning**:
1. **Scalability**: Large codebases need hierarchy
2. **Lazy loading**: Load only what you need
3. **Zoom in/out**: Navigate between abstraction levels
4. **Fractal structure**: Same pattern at every level
5. **Summary views**: Can show _summary without loading full tree

---

## 11. Success Criteria

Seed-core is successful when:

1. ✅ **Monitors all realities** from a single interface
2. ✅ **Detects drift** automatically (model vs reality mismatch)
3. ✅ **Fast for idle realities** (hash check only, no full scan)
4. ✅ **Shows pending work** across all realities
5. ✅ **Self-describes** (seed-core models itself)
6. ✅ **Model-first** (no configuration files)
7. ✅ **Integrates with spawnie** (shows spawnie tasks in unified view)

---

## 12. Future Enhancements

### Reality API Standard
Define standard HTTP/gRPC API for realities to implement pulse protocol natively.

### Real-Time Updates
WebSocket connection to realities for push-based updates (supplement polling).

### Drift Auto-Sync
Automatically update model when files change (with confirmation).

### Multi-User
Track which human is working on which reality.

### Execution Layer
Model running processes, triggers, events (not just static state).

### Graph Visualization
Visual graph of all realities and their relationships.

---

## 13. Dependencies

### Required
- Python 3.11+
- textual (for TUI)
- aiofiles (for async file I/O)
- hashlib (stdlib, for hash computation)

### Optional
- uvloop (for performance)
- watchfiles (for file watching)
- httpx (for future reality API)

---

## Conclusion

Seed-core provides the control plane for the seed meta-model system. It brings together:

1. **Pulse mechanism** for monitoring all realities
2. **Status aggregation** for unified view
3. **Drift detection** for model verification
4. **Monitor TUI** for visualization
5. **Model-first** architecture (configuration, workflows, everything)
6. **Self-description** (seed-core models itself)

The design is **simple**, **scalable**, and **true to seed philosophy**: the model is the interface to reality.

---

**Next Steps**: Implement Phase 1 (Foundation) and validate design with working code.
