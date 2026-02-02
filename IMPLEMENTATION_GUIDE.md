# Seed-Core Implementation Guide

**Practical guide for implementing the seed-core control center**

Date: 2026-02-01
Status: Ready for Implementation

---

## Quick Start

This guide provides **concrete implementation steps** for building seed-core based on the architecture defined in `SEED_CORE_ARCHITECTURE.md`.

---

## 1. Current State Analysis

### 1.1 What Exists (as of 2026-02-01)

```
C:\seed\seed_core\
├── __init__.py               ✅ Basic exports (Pulse, Status)
├── __main__.py               ✅ CLI (status/pulse/monitor/describe/watch/save/verify)
├── pulse.py                  ✅ Basic pulse mechanism
├── status.py                 ✅ Status tracking classes
├── reality.py                ✅ Reality state management
├── verification.py           ✅ Hash verification
├── monitor.py                ✅ Basic TUI monitor
└── pyproject.toml            ✅ Package config

✅ Complete: Basic pulse, status, verification, and expanded CLI
⬜ Missing: Deeper spawnie tracker integration, monitor migration, richer workflow/task view

Also present (Root Store):

```
C:\seed\root_store\
├── loader.py        ✅ merged graph loader with provenance
├── writeback.py     ✅ provenance-aware evidence writeback
├── audits.py        ✅ runnable audits that write evidence back
├── watch.py         ✅ polling watcher for model file changes
└── integration.py   ✅ verbal save (integration queue evidence)
```
```

### 1.2 What Needs to be Built

**Priority 1: Spawnie Integration**
- Read spawnie's `tracker.json` for active tasks
- Parse spawnie's model for todos
- Determine activity state (idle/busy)

**Priority 2: Enhanced Pulse**
- Multi-level checking (fast/verify/deep)
- Activity detection
- Todo scanning

**Priority 3: Monitor Migration**
- Multi-reality view
- Workflow panel showing spawnie workflows
- Alert panel for drift/errors

**Priority 4: CLI Expansion**
- Enhanced status command
- Todo aggregation command
- Reality management commands

---

## 2. Implementation Roadmap

### Phase 1: Spawnie Integration (1-2 days)

#### Step 1.1: Read Spawnie Tracker

Create `src/seed_core/reality/spawnie_client.py`:

```python
"""Specialized client for the Spawnie reality."""

from pathlib import Path
import json
from datetime import datetime
from typing import Optional

from .client import RealityClient
from ..pulse.protocol import PulseResponse


class SpawnieClient(RealityClient):
    """Client for communicating with Spawnie reality.

    Spawnie provides rich activity data through its tracker.json file,
    making it a first-class reality with accurate busy/idle detection.
    """

    def __init__(self, reality_node: dict):
        super().__init__(reality_node)
        self.tracker_path = Path.home() / ".spawnie" / "tracker.json"

    def read_tracker(self) -> dict:
        """Read spawnie's tracker.json file.

        Returns:
            Tracker data dict, or empty dict if file doesn't exist
        """
        if not self.tracker_path.exists():
            return {"tasks": {}, "workflows": {}, "alerts": []}

        try:
            return json.loads(self.tracker_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read spawnie tracker: {e}")
            return {"tasks": {}, "workflows": {}, "alerts": []}

    def get_active_tasks(self) -> list[dict]:
        """Get currently running tasks from tracker.

        Returns:
            List of task dicts with status="running"
        """
        tracker = self.read_tracker()
        return [
            task for task in tracker.get("tasks", {}).values()
            if task.get("status") == "running"
        ]

    def get_active_workflows(self) -> list[dict]:
        """Get currently running workflows from tracker.

        Returns:
            List of workflow dicts with status="queued" or "running"
        """
        tracker = self.read_tracker()
        return [
            wf for wf in tracker.get("workflows", {}).values()
            if wf.get("status") in ["queued", "running"]
        ]

    def determine_activity(self) -> str:
        """Determine spawnie's activity level.

        Returns:
            "idle" | "busy" | "error"
        """
        tracker = self.read_tracker()

        # Check for running tasks/workflows
        active_tasks = [
            t for t in tracker.get("tasks", {}).values()
            if t.get("status") == "running"
        ]
        active_workflows = [
            w for w in tracker.get("workflows", {}).values()
            if w.get("status") in ["queued", "running"]
        ]

        # Check for errors
        error_tasks = [
            t for t in tracker.get("tasks", {}).values()
            if t.get("status") in ["failed", "timeout"]
        ]

        if error_tasks:
            return "error"
        elif active_tasks or active_workflows:
            return "busy"
        else:
            return "idle"

    async def pulse(self, request) -> PulseResponse:
        """Pulse spawnie reality.

        Args:
            request: PulseRequest with check_level

        Returns:
            PulseResponse with detailed spawnie status
        """
        # Get activity from tracker
        activity = self.determine_activity()
        active_tasks = self.get_active_tasks()
        active_workflows = self.get_active_workflows()

        # Read model for todos
        model = self.load_model()
        todo_nodes = [n for n in model.get("nodes", []) if n.get("type") == "Todo"]
        pending_todos = [t for t in todo_nodes if t.get("status") == "pending"]

        # Determine if we need verification
        drift_detected = None
        drift_files = None

        if request.check_level == "fast" and activity == "idle":
            # Fast check: only verify model hash
            model_hash = self.compute_model_hash()
            drift_detected = (model_hash != self.cached_model_hash)

        elif request.check_level in ["verify", "deep"]:
            # Full verification
            from ..verification import verify_reality
            result = verify_reality(self.model_path, self.path)
            drift_detected = len(result.drift_items) > 0
            drift_files = [d.file_path for d in result.drift_items]

        # Determine overall health
        if drift_detected:
            status = "yellow"
        elif activity == "error":
            status = "red"
        else:
            status = "green"

        return PulseResponse(
            reality_id=self.reality_id,
            timestamp=datetime.now(),
            status=status,
            activity=activity,
            model_hash=self.compute_model_hash(),
            running_tasks=len(active_tasks),
            pending_todos=len(pending_todos),
            drift_detected=drift_detected,
            drift_files=drift_files or [],
        )
```

#### Step 1.2: Integrate into Pulse Engine

Update `src/seed_core/pulse/engine.py`:

```python
from ..reality.spawnie_client import SpawnieClient

class PulseEngine:
    def create_client(self, reality_node: dict) -> RealityClient:
        """Factory method to create appropriate client for reality.

        Args:
            reality_node: Reality node from seed model

        Returns:
            Specialized client (SpawnieClient) or generic RealityClient
        """
        reality_id = reality_node.get("id", "")

        # Use specialized client for spawnie
        if reality_id == "reality-spawnie":
            return SpawnieClient(reality_node)

        # Generic client for others
        return RealityClient(reality_node)
```

#### Step 1.3: Test Spawnie Integration

Create `tests/test_spawnie_integration.py`:

```python
"""Test spawnie integration."""

from pathlib import Path
import json
import tempfile

from seed_core.reality.spawnie_client import SpawnieClient


def test_read_tracker():
    """Test reading spawnie tracker.json."""
    # Create fake tracker
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_path = Path(tmpdir) / "tracker.json"
        tracker_data = {
            "tasks": {
                "task1": {"id": "task1", "status": "running"},
                "task2": {"id": "task2", "status": "completed"},
            },
            "workflows": {
                "wf1": {"id": "wf1", "status": "running"},
            }
        }
        tracker_path.write_text(json.dumps(tracker_data))

        # Create client with fake tracker path
        client = SpawnieClient({
            "id": "reality-spawnie",
            "source": {"path": tmpdir, "model_path": "bam/model/sketch.json"}
        })
        client.tracker_path = tracker_path

        # Test methods
        assert len(client.get_active_tasks()) == 1
        assert len(client.get_active_workflows()) == 1
        assert client.determine_activity() == "busy"
```

---

### Phase 2: Enhanced Pulse Protocol (2-3 days)

#### Step 2.1: Multi-Level Checking

Update `src/seed_core/pulse/protocol.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CheckLevel = Literal["fast", "verify", "deep"]
HealthStatus = Literal["green", "yellow", "red", "unreachable"]
ActivityLevel = Literal["idle", "busy", "error", "unknown"]


@dataclass
class PulseRequest:
    """Request to check a reality's pulse.

    Attributes:
        reality_id: ID of reality to check
        check_level: Level of checking to perform
            - fast: Only verify model hash (for green+idle)
            - verify: Check all source file hashes
            - deep: Full scan + rebuild model summary
        timestamp: When pulse was sent
    """
    reality_id: str
    check_level: CheckLevel
    timestamp: datetime


@dataclass
class PulseResponse:
    """Response from a reality pulse check.

    Attributes:
        reality_id: ID of reality
        timestamp: When pulse response was generated
        status: Overall health status
        activity: Current activity level

        # Model info
        model_hash: Hash of model file
        model_modified: When model was last modified

        # Work tracking
        running_tasks: Number of active tasks
        pending_todos: Number of pending todos

        # Verification (only if check_level != "fast")
        drift_detected: Whether drift was detected
        drift_files: List of files with hash mismatches

        # Metrics
        metrics: Additional metrics (task counts, etc.)

        # Error
        error: Error message if pulse failed
    """
    reality_id: str
    timestamp: datetime
    status: HealthStatus
    activity: ActivityLevel

    model_hash: str | None = None
    model_modified: datetime | None = None

    running_tasks: int = 0
    pending_todos: int = 0

    drift_detected: bool | None = None
    drift_files: list[str] | None = None

    metrics: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "reality_id": self.reality_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "activity": self.activity,
            "model_hash": self.model_hash,
            "model_modified": self.model_modified.isoformat() if self.model_modified else None,
            "running_tasks": self.running_tasks,
            "pending_todos": self.pending_todos,
            "drift_detected": self.drift_detected,
            "drift_files": self.drift_files or [],
            "metrics": self.metrics or {},
            "error": self.error,
        }
```

#### Step 2.2: Adaptive Checking Logic

Update `src/seed_core/pulse/engine.py`:

```python
class PulseEngine:
    def determine_check_level(self, reality_id: str, last_status: RealityStatus | None) -> CheckLevel:
        """Determine appropriate check level based on last status.

        Args:
            reality_id: ID of reality to check
            last_status: Last known status, or None if first pulse

        Returns:
            "fast" | "verify" | "deep"
        """
        if last_status is None:
            # First pulse: do full verification
            return "verify"

        # If green and idle, do fast check
        if last_status.status == "green" and last_status.activity == "idle":
            return "fast"

        # Otherwise, verify
        return "verify"

    async def pulse_one(self, reality_id: str, force_level: CheckLevel | None = None) -> RealityStatus:
        """Pulse a single reality.

        Args:
            reality_id: ID of reality to pulse
            force_level: Override check level (for manual pulses)

        Returns:
            Updated RealityStatus
        """
        # Get last status
        last_status = self.status_cache.get(reality_id)

        # Determine check level
        check_level = force_level or self.determine_check_level(reality_id, last_status)

        # Create request
        request = PulseRequest(
            reality_id=reality_id,
            check_level=check_level,
            timestamp=datetime.now()
        )

        # Get client
        client = self.clients[reality_id]

        # Pulse
        response = await client.pulse(request)

        # Build RealityStatus from response
        status = RealityStatus(
            reality_id=response.reality_id,
            label=self.get_reality_label(reality_id),
            path=self.get_reality_path(reality_id),
            status=response.status,
            activity=response.activity,
            last_pulse=response.timestamp,
            next_pulse=self.scheduler.next_pulse_time(response),
            running_tasks=response.running_tasks,
            pending_todos=response.pending_todos,
            drift_detected=response.drift_detected or False,
            drift_files=response.drift_files or [],
            model_hash=response.model_hash,
            error=response.error,
        )

        # Cache
        self.status_cache[reality_id] = status

        return status
```

---

### Phase 3: Monitor Migration (3-4 days)

#### Step 3.1: Multi-Reality List View

Create `src/seed_core/monitor/views.py`:

```python
"""Monitor UI views."""

from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Static, Rule
from rich.table import Table

from ..status import SeedStatus, RealityStatus


class RealityListView(Static):
    """Shows list of all realities with status.

    Displays a compact table of all realities showing:
    - Health status (🟢🟡🔴)
    - Activity (idle/busy)
    - Running tasks count
    - Pending todos count
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status: SeedStatus | None = None

    def update_status(self, status: SeedStatus):
        """Update with new status data."""
        self.status = status
        self.refresh()

    def render(self) -> Table:
        """Render reality list as Rich table."""
        table = Table(title="Realities", expand=True)
        table.add_column("Reality", style="cyan bold")
        table.add_column("Status", justify="center")
        table.add_column("Activity", justify="center")
        table.add_column("Tasks", justify="right")
        table.add_column("Todos", justify="right")

        if not self.status:
            return table

        for reality_id, reality in self.status.realities.items():
            # Status emoji
            status_emoji = {
                "green": "🟢",
                "yellow": "🟡",
                "red": "🔴",
                "unreachable": "⚫",
            }.get(reality.status, "❓")

            # Activity text
            activity_text = {
                "idle": "idle",
                "busy": "busy",
                "error": "ERROR",
                "unknown": "?",
            }.get(reality.activity, "?")

            table.add_row(
                reality.label,
                status_emoji,
                activity_text,
                str(reality.running_tasks),
                str(reality.pending_todos),
            )

        return table


class RealityDetailView(ScrollableContainer):
    """Shows detailed info for selected reality.

    Displays:
    - Basic info (path, model, last pulse)
    - Running tasks (hierarchical like spawnie monitor)
    - Pending todos
    - Drift information (if any)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reality: RealityStatus | None = None

    def update_reality(self, reality: RealityStatus):
        """Update with new reality data."""
        self.reality = reality
        # TODO: Update child widgets

    def compose(self) -> ComposeResult:
        """Compose the detail view."""
        yield Static("Reality Details", classes="header")
        yield Rule()
        # TODO: Add task list, todo list, drift info widgets


class EcosystemSummaryView(Static):
    """Shows overall ecosystem health.

    Compact summary:
    - Total realities
    - Health breakdown (green/yellow/red counts)
    - Total running tasks
    - Total pending todos
    """

    def render(self) -> str:
        """Render ecosystem summary."""
        if not self.status:
            return "[dim]No data[/dim]"

        return f"""[bold]Seed Ecosystem[/bold]

Total Realities: {len(self.status.realities)}
Health: 🟢 {self.status.healthy_count} | 🟡 {self.status.degraded_count} | 🔴 {self.status.critical_count}

Running Tasks: {self.status.total_running_tasks}
Pending Todos: {self.status.total_pending_todos}

Last Updated: {self.status.last_updated.strftime("%H:%M:%S")}
"""
```

#### Step 3.2: Main Monitor App

Update `src/seed_core/monitor/app.py`:

```python
"""Main monitor TUI application."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Container, Horizontal

from ..pulse import PulseEngine
from ..status import StatusAggregator
from .views import RealityListView, RealityDetailView, EcosystemSummaryView


class SeedMonitor(App):
    """TUI monitor for the entire seed ecosystem.

    Shows:
    - List of all realities (left)
    - Selected reality details (right)
    - Ecosystem summary (top)

    Updates via pulse every 5 seconds.
    """

    CSS = """
    RealityListView {
        width: 40%;
        height: 100%;
    }

    RealityDetailView {
        width: 60%;
        height: 100%;
    }

    EcosystemSummaryView {
        height: 6;
        background: $panel;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
        ("s", "screenshot", "Screenshot"),
    ]

    def __init__(self, model_path, **kwargs):
        super().__init__(**kwargs)
        self.pulse_engine = PulseEngine(model_path)
        self.aggregator = StatusAggregator(self.pulse_engine)

    def compose(self) -> ComposeResult:
        """Compose the monitor layout."""
        yield Header()
        yield EcosystemSummaryView()
        with Horizontal():
            yield RealityListView()
            yield RealityDetailView()
        yield Footer()

    async def on_mount(self):
        """Start pulse engine and refresh timer."""
        await self.pulse_engine.start()
        self.set_interval(5.0, self.refresh_data)
        await self.refresh_data()

    async def refresh_data(self):
        """Refresh all data from pulse engine."""
        status = await self.aggregator.get_ecosystem_status(force_refresh=True)

        # Update views
        self.query_one(EcosystemSummaryView).update_status(status)
        self.query_one(RealityListView).update_status(status)

        # TODO: Update detail view with selected reality

    async def action_refresh(self):
        """Force refresh data."""
        await self.refresh_data()
```

---

### Phase 4: CLI Expansion (1-2 days)

#### Step 4.1: Enhanced Status Command

Update `src/seed_core/cli/status.py`:

```python
"""Status CLI command."""

import click
from rich.console import Console
from rich.table import Table

from ..pulse import PulseEngine
from ..status import StatusAggregator

console = Console()


@click.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--watch", is_flag=True, help="Watch mode (update every 2s)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.argument("reality_id", required=False)
def status(json_output, watch, verbose, reality_id):
    """Show status of seed ecosystem or specific reality.

    Examples:
        seed status              # Show all realities
        seed status spawnie      # Show specific reality
        seed status --watch      # Watch mode
        seed status --json       # JSON output
    """
    from pathlib import Path

    # Initialize
    seed_model = Path("C:/seed/model/sketch.json")
    engine = PulseEngine(seed_model)
    aggregator = StatusAggregator(engine)

    if watch:
        # TODO: Implement watch mode
        import time
        try:
            while True:
                _show_status(aggregator, reality_id, json_output, verbose)
                time.sleep(2)
                console.clear()
        except KeyboardInterrupt:
            pass
    else:
        _show_status(aggregator, reality_id, json_output, verbose)


def _show_status(aggregator, reality_id, json_output, verbose):
    """Show status (called in loop for watch mode)."""
    import asyncio

    # Get status
    status = asyncio.run(aggregator.get_ecosystem_status(force_refresh=True))

    if json_output:
        console.print_json(data=status.to_dict())
        return

    if reality_id:
        # Show specific reality
        reality = status.realities.get(f"reality-{reality_id}")
        if not reality:
            console.print(f"[red]Reality not found:[/red] {reality_id}")
            return

        _show_reality_detail(reality)
    else:
        # Show all realities
        _show_all_realities(status, verbose)


def _show_all_realities(status, verbose):
    """Show table of all realities."""
    table = Table(title="Seed Ecosystem Status")
    table.add_column("Reality", style="cyan bold")
    table.add_column("Status", justify="center")
    table.add_column("Activity", justify="center")
    table.add_column("Tasks", justify="right")
    table.add_column("Todos", justify="right")

    if verbose:
        table.add_column("Path", style="dim")
        table.add_column("Last Pulse", style="dim")

    for reality in status.realities.values():
        row = [
            reality.label,
            _status_emoji(reality.status),
            reality.activity,
            str(reality.running_tasks),
            str(reality.pending_todos),
        ]

        if verbose:
            row.append(str(reality.path))
            row.append(reality.last_pulse.strftime("%H:%M:%S"))

        table.add_row(*row)

    console.print(table)
    console.print()
    console.print(f"Total: {len(status.realities)} realities | "
                 f"{status.total_running_tasks} running | "
                 f"{status.total_pending_todos} pending")


def _show_reality_detail(reality):
    """Show detailed info for a specific reality."""
    console.print(f"[bold cyan]{reality.label}[/bold cyan]")
    console.print(f"Path: {reality.path}")
    console.print(f"Status: {_status_emoji(reality.status)} {reality.status}")
    console.print(f"Activity: {reality.activity}")
    console.print()

    if reality.running_tasks > 0:
        console.print(f"[bold]Running Tasks ({reality.running_tasks}):[/bold]")
        # TODO: Show task details

    if reality.pending_todos > 0:
        console.print(f"[bold]Pending Todos ({reality.pending_todos}):[/bold]")
        # TODO: Show todo details

    if reality.drift_detected:
        console.print("[bold red]Drift Detected![/bold red]")
        for file in reality.drift_files:
            console.print(f"  - {file}")


def _status_emoji(status: str) -> str:
    """Get emoji for status."""
    return {
        "green": "🟢",
        "yellow": "🟡",
        "red": "🔴",
        "unreachable": "⚫",
    }.get(status, "❓")
```

#### Step 4.2: Todo Aggregation Command

Create `src/seed_core/cli/todos.py`:

```python
"""Todo aggregation CLI command."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command()
@click.option("--reality", help="Filter by reality ID")
@click.option("--priority", type=click.Choice(["high", "medium", "low"]), help="Filter by priority")
@click.option("--json", "json_output", is_flag=True)
def todos(reality, priority, json_output):
    """Show todos across all realities.

    Examples:
        seed todos                      # All todos
        seed todos --reality spawnie    # Spawnie todos only
        seed todos --priority high      # High priority only
    """
    from pathlib import Path
    from ..pulse import PulseEngine
    from ..model import ModelLoader

    # Load seed model
    seed_model = Path("C:/seed/model/sketch.json")
    loader = ModelLoader()
    model = loader.load(seed_model)

    # Collect todos from all realities
    all_todos = []

    for node in model.get("nodes", []):
        if node.get("type") != "Reality":
            continue

        reality_id = node["id"]
        reality_label = node.get("label", reality_id)

        # Filter by reality if specified
        if reality and f"reality-{reality}" != reality_id:
            continue

        # Load reality model
        source = node.get("source", {})
        if not source.get("model_path"):
            continue

        reality_model_path = Path(source["path"]) / source["model_path"]
        if not reality_model_path.exists():
            continue

        reality_model = loader.load(reality_model_path)

        # Find todos
        for todo_node in reality_model.get("nodes", []):
            if todo_node.get("type") != "Todo":
                continue

            if todo_node.get("status") != "pending":
                continue

            todo_priority = todo_node.get("priority", "medium")

            # Filter by priority if specified
            if priority and todo_priority != priority:
                continue

            all_todos.append({
                "reality": reality_label,
                "reality_id": reality_id,
                "label": todo_node.get("label", ""),
                "description": todo_node.get("description", ""),
                "priority": todo_priority,
            })

    if json_output:
        console.print_json(data={"total": len(all_todos), "todos": all_todos})
        return

    # Display as table
    table = Table(title="Pending Todos Across All Realities")
    table.add_column("Reality", style="cyan")
    table.add_column("Priority", justify="center")
    table.add_column("Todo", style="bold")

    for todo in all_todos:
        priority_style = {
            "high": "[red]HIGH[/red]",
            "medium": "[yellow]MEDIUM[/yellow]",
            "low": "[dim]LOW[/dim]",
        }.get(todo["priority"], todo["priority"])

        table.add_row(
            todo["reality"],
            priority_style,
            todo["label"],
        )

    console.print(table)
    console.print(f"\nTotal: {len(all_todos)} pending todos")
```

---

## 3. Testing Strategy

### 3.1 Unit Tests

Create comprehensive unit tests for each module:

```
tests/
├── test_pulse_engine.py          # Pulse engine logic
├── test_spawnie_client.py        # Spawnie integration
├── test_status_aggregator.py     # Status aggregation
├── test_verification.py          # Hash verification
├── test_model_loader.py          # Model loading
└── fixtures/
    ├── seed_model.json           # Minimal seed model
    ├── spawnie_model.json        # Minimal spawnie model
    └── tracker.json              # Sample tracker data
```

### 3.2 Integration Tests

Test end-to-end flows:

```python
def test_pulse_workflow():
    """Test complete pulse workflow."""
    # 1. Load seed model
    # 2. Pulse spawnie
    # 3. Verify response contains tracker data
    # 4. Check status aggregation
    pass


def test_drift_detection():
    """Test drift detection workflow."""
    # 1. Load model with hash refs
    # 2. Modify a source file
    # 3. Pulse reality
    # 4. Verify drift detected
    pass
```

---

## 4. Configuration

### 4.1 Add Config Node to Seed Model

Edit `C:\seed\model\sketch.json`, add:

```json
{
  "id": "config-seed-core",
  "type": "Config",
  "label": "Seed-Core Configuration",
  "pulse": {
    "default_interval": 30,
    "fast_interval": 10,
    "slow_interval": 300
  },
  "monitor": {
    "refresh_rate": 5,
    "show_completed_tasks": false
  },
  "verification": {
    "hash_algorithm": "sha256",
    "skip_patterns": ["*.pyc", "__pycache__", ".git", "node_modules"]
  }
}
```

### 4.2 Load Config in Code

```python
class SeedConfig:
    """Load configuration from seed model."""

    @classmethod
    def load(cls, model_path: Path):
        model = load_model(model_path)
        config_node = next(
            (n for n in model["nodes"] if n["id"] == "config-seed-core"),
            {}
        )
        return cls(config_node)
```

---

## 5. Deployment

### 5.1 Install as Package

```bash
# From C:\seed
pip install -e src/seed_core/

# Verify installation
seed --help
```

### 5.2 CLI Usage

```bash
# Status
seed status                 # All realities
seed status spawnie         # Specific reality
seed status --watch         # Watch mode

# Monitor
seed monitor                # TUI monitor

# Pulse
seed pulse                  # Pulse all
seed pulse spawnie          # Pulse one

# Todos
seed todos                  # All todos
seed todos --priority high  # High priority only
```

---

## 6. Performance Optimizations

### 6.1 Caching

```python
class PulseEngine:
    def __init__(self):
        self.status_cache = {}  # Cache RealityStatus
        self.model_hash_cache = {}  # Cache model hashes
        self.cache_ttl = 30  # seconds
```

### 6.2 Lazy Loading

```python
class ModelLoader:
    def load_with_refs(self, model_path: Path, max_depth: int = 1):
        """Load model with limited depth.

        Don't load entire hierarchy unless needed.
        """
        pass
```

### 6.3 Parallel Pulse

```python
async def pulse_all(self) -> dict[str, RealityStatus]:
    """Pulse all realities in parallel."""
    tasks = [
        self.pulse_one(reality_id)
        for reality_id in self.reality_ids
    ]
    results = await asyncio.gather(*tasks)
    return {r.reality_id: r for r in results}
```

---

## 7. Next Steps

1. **Implement Spawnie Integration** (Phase 1)
   - Create `SpawnieClient`
   - Test tracker reading
   - Test activity detection

2. **Enhance Pulse Protocol** (Phase 2)
   - Multi-level checking
   - Adaptive check level selection
   - Caching layer

3. **Migrate Monitor** (Phase 3)
   - Multi-reality views
   - Port spawnie widgets
   - Test TUI

4. **Expand CLI** (Phase 4)
   - Enhanced status command
   - Todo aggregation
   - Watch mode

5. **Self-Model** (Phase 5)
   - Create seed-core's own model
   - Add to seed model
   - Verify self-monitoring works

---

## 8. Success Metrics

Seed-core is complete when:

- ✅ Monitors all realities from seed model
- ✅ Detects spawnie activity (idle/busy) accurately
- ✅ Shows all pending todos across realities
- ✅ Detects drift automatically
- ✅ Fast checks for idle realities (<100ms)
- ✅ Monitor shows multi-reality view
- ✅ Self-describes (seed-core models itself)
- ✅ Model-first (no config files)

---

**This implementation guide provides concrete, actionable steps to build seed-core.**

Ready to implement!
