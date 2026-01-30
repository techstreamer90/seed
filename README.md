# Seed: BAM Model of Spawnie

This is a BAM model (digital twin) of the Spawnie workflow orchestrator.

## Purpose

This model serves as:
1. **Accurate documentation** - The sketch defines what exists, color adds details
2. **Shared context for agents** - Spawnie agents can query this model instead of re-reading files
3. **Proof of concept** - Testing BAM + Spawnie integration

## Structure

```
seed/
├── project.json           # Project metadata
├── model/
│   ├── sketch.json        # Graph structure (nodes, edges, types)
│   └── colors/            # Detailed properties per node
│       ├── modules.json   # Python modules
│       ├── classes.json   # Classes and their methods
│       ├── concepts.json  # Architectural patterns
│       └── cli.json       # CLI commands
├── sources/               # Source data (if any)
└── intermediate/          # Intermediate extraction format
```

## The Model

### Node Types

| Type | Description | Count |
|------|-------------|-------|
| Module | Python module (file) | 10 |
| Class | Python class | 10 |
| Function | Standalone function | 4 |
| Dataclass | Data structure | 5 |
| CLICommand | CLI command | 6 |
| Concept | Architectural pattern | 5 |

### Edge Types

| Type | Description |
|------|-------------|
| IMPORTS | Module imports another |
| DEFINES | Module defines class/function |
| INHERITS | Class inherits from another |
| CALLS | Function/method calls another |
| USES | Class uses another class |
| IMPLEMENTS | CLI command implemented by handler |
| EMBODIES | Code embodies a concept |

### Key Concepts Captured

1. **Tasks as Single-Step Workflows** - Unified tracking
2. **Model Routing** - Abstract model names → concrete providers
3. **Parallel Step Execution** - Concurrent independent steps
4. **Orphan Detection** - Cleanup dead processes
5. **Quality Levels** - Review strategies (normal/extra-clean/hypertask)

## Usage

### Query the model

```python
import json
from pathlib import Path

# Load sketch
sketch = json.loads(Path("model/sketch.json").read_text())

# Find all classes
classes = [n for n in sketch["nodes"] if n["type"] == "Class"]

# Find what Tracker uses
tracker_edges = [e for e in sketch["edges"]
                 if e["from"] == "cls-tracker" and e["type"] == "USES"]
```

### Enrich with color

```python
# Load color
modules = json.loads(Path("model/colors/modules.json").read_text())

# Get details for tracker module
tracker_info = modules["nodes"]["mod-tracker"]
print(f"LOC: {tracker_info['loc']}")
print(f"Public API: {tracker_info['public_api']}")
```

## Next Steps

1. **Python extractor for BAM** - Auto-generate this from source code
2. **Keep model in sync** - Update when Spawnie changes
3. **Agent integration** - Spawnie workflows that query this model
4. **Cross-references** - Link to other BAM models

## The Vision

This is a test of the BAM + Spawnie architecture:

```
        ┌─────────────────────────────┐
        │      BAM Model (Sketch)     │  ← Desired state
        │         + Color             │  ← Current state
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │      Spawnie Agents         │  ← Work to converge
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │        Real World           │  ← Reflects back
        │    (code, systems)          │
        └─────────────────────────────┘
```

The model is not just documentation. It's the **source of truth** that agents converge reality towards.
