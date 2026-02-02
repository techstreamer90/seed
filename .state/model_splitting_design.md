# Model Splitting Architecture

## Problem
- Single `model/sketch.json` with 35+ nodes is becoming a bottleneck
- Race conditions when multiple agents write simultaneously
- File is huge and hard to diff in git
- Can't work on nodes in parallel efficiently

## Vision: Each Node Has Its Own File

### Directory Structure
```
model/
├── metadata.json          # Model version, updated_at, etc.
├── edges.json            # All edges (or derived from nodes?)
└── nodes/
    ├── reality-seed.json
    ├── reality-spawnie.json
    ├── reality-seed-ui.json
    ├── template-agent-node.json
    └── ... (one file per node)
```

### Benefits
✓ No race conditions - agents work on different files
✓ Better git diffs - see exactly which nodes changed
✓ Natural parallelization
✓ Easy to read/write specific nodes
✓ Nodes become truly independent entities
✓ Can have different permissions per node file

### Challenges to Solve

#### 1. Edge Storage
**Options:**
- A) Separate `edges.json` file (centralized)
- B) Each node contains its outgoing edges (distributed)
- C) Both - nodes have edges, edges.json is generated

**Recommendation: Option B (distributed)**
- Each node file contains `"edges": []` with its outgoing edges
- Type: "CONTAINS", "ADDRESSES", "ADVANCES", etc.
- Pro: Node is self-contained
- Con: Finding all edges to a node requires reading all nodes

#### 2. Loading Full Model
**Need a loader:**
```python
def load_full_model():
    """Load all nodes and edges into unified model structure."""
    nodes = []
    for file in Path("model/nodes").glob("*.json"):
        nodes.append(json.load(open(file)))

    # Extract edges from nodes
    edges = []
    for node in nodes:
        edges.extend(node.get("edges", []))

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": json.load(open("model/metadata.json"))
    }
```

#### 3. Querying and Indexing
**Challenge:** Finding nodes by ID, type, or property
**Solution:** Build index on load
```python
class ModelLoader:
    def __init__(self):
        self.nodes_by_id = {}
        self.nodes_by_type = {}
        self._load()

    def get_node(self, node_id):
        return self.nodes_by_id.get(node_id)

    def find_by_type(self, node_type):
        return self.nodes_by_type.get(node_type, [])
```

#### 4. Backward Compatibility
**Need:** Support old code that expects `model/sketch.json`
**Solution:** Generate sketch.json from split files
```python
def generate_sketch_json():
    """Generate unified sketch.json from split files for compatibility."""
    model = load_full_model()
    with open("model/sketch.json", "w") as f:
        json.dump(model, f, indent=2)
```

#### 5. Migration Path
**Phase 1: Split the model**
- Script to split current sketch.json into individual files
- Generate metadata.json

**Phase 2: Dual mode**
- Code works with both sketch.json (read) and split files (write)
- Update tools to write to individual node files

**Phase 3: Full transition**
- All code reads from split files
- sketch.json becomes generated artifact (for compatibility)

### Node File Format

Each node file is a complete node definition:

```json
{
  "id": "reality-seed",
  "type": "Root",
  "label": "Seed (Reality Root)",
  "description": "...",
  "capabilities": {...},
  "agent_context": {...},
  "plan": {...},
  "edges": [
    {"type": "CONTAINS", "to": "reality-spawnie"},
    {"type": "CONTAINS", "to": "reality-seed-ui"}
  ],
  "updated_at": "2026-02-02T22:30:00Z",
  "updated_by": "spawnie"
}
```

### Metadata File Format

```json
{
  "model_version": "0.2.0",
  "model_format": "split",
  "updated_at": "2026-02-02T22:30:00Z",
  "node_count": 35,
  "edge_count": 42,
  "schema_version": "1.0"
}
```

### API Design

```python
# Old way (still works for reading)
model = json.load(open("model/sketch.json"))

# New way - individual nodes
from model_loader import ModelLoader
loader = ModelLoader()

# Read specific node
node = loader.get_node("reality-seed")

# Update specific node
loader.update_node("reality-seed", {"plan": {...}})

# Find nodes
templates = loader.find_by_type("Template")
agents = loader.find_by_type("AgentNode")

# Get edges
incoming = loader.get_edges_to("reality-seed")
outgoing = loader.get_edges_from("reality-seed")

# Load full model (when needed)
full_model = loader.get_full_model()
```

### Migration Script Outline

```python
#!/usr/bin/env python3
"""Split model/sketch.json into individual node files."""

import json
from pathlib import Path

# 1. Load current sketch.json
model = json.load(open("model/sketch.json"))

# 2. Create directories
Path("model/nodes").mkdir(exist_ok=True)

# 3. Distribute edges to source nodes
edges_by_source = {}
for edge in model["edges"]:
    source = edge["from"]
    if source not in edges_by_source:
        edges_by_source[source] = []
    edges_by_source[source].append({
        "type": edge["type"],
        "to": edge["to"]
    })

# 4. Write individual node files
for node in model["nodes"]:
    node_id = node["id"]

    # Add edges to node
    node["edges"] = edges_by_source.get(node_id, [])

    # Write to file
    file_path = Path("model/nodes") / f"{node_id}.json"
    with open(file_path, "w") as f:
        json.dump(node, f, indent=2)

# 5. Create metadata.json
metadata = {
    "model_version": "0.2.0",
    "model_format": "split",
    "updated_at": model["updated_at"],
    "node_count": len(model["nodes"]),
    "edge_count": len(model["edges"]),
    "schema_version": "1.0"
}
with open("model/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

# 6. Keep sketch.json as backup (rename)
Path("model/sketch.json").rename("model/sketch.json.backup")

print(f"Split {len(model['nodes'])} nodes into individual files")
```

## Implementation Plan

1. **Design Review** - Validate this approach
2. **Create model_loader.py** - Core loading infrastructure
3. **Migration Script** - Split current model
4. **Update Tools** - Make existing tools use loader
5. **Test & Validate** - Ensure nothing breaks
6. **Commit & Document** - Update AGENTS.md with new model access patterns

## Open Questions

1. Should edges.json exist as a convenience cache?
2. How to handle node deletion (just rm the file?)
3. Should we version individual node files?
4. Git LFS for node files? (probably not needed yet)
