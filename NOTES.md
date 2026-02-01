# Notes for Future Claude

## What is Seed?

Seed is the **meta-model**. A model of all models. The user's home.

```
seed/                     ← you are here
├── model/
│   └── sketch.json       ← lists all realities the user works with
│
├── Spawnie → C:/spawnie/bam/
├── BAM → C:/BAM (no model yet)
└── ...future realities
```

Each "reality" is a project that contains its own BAM model. Seed tracks them all.

## The Hierarchy

```
seed (meta-model)
 │
 ├── reality: Spawnie
 │     └── C:/spawnie/bam/model/sketch.json (40 nodes)
 │
 ├── reality: BAM
 │     └── no model yet
 │
 └── ...more realities as you add them
```

## Core Concepts (captured in sketch.json)

1. **Reality is Part of the Model** - Models embed source refs with hashes
2. **Intent vs Reality** - No source = goal, with source = current state
3. **Self-Containing Models** - Each reality contains its own model

## Current Realities

| Reality | Path | Model | Status |
|---------|------|-------|--------|
| Spawnie | C:/spawnie | bam/model/sketch.json | verified |
| BAM | C:/BAM | - | no model yet |

## How to Add a New Reality

1. Create the project
2. Add `bam/` directory with model inside it
3. Add a node to seed's sketch.json:
```json
{
  "id": "reality-myproject",
  "type": "Reality",
  "label": "MyProject",
  "source": {
    "path": "C:/myproject",
    "model": "bam/model/sketch.json"
  }
}
```

## The Vision

Seed is where you see everything. It's your map of all the systems you're building.

- Add intent nodes here for new realities you want to create
- Each reality then contains its own detailed model
- Agents can navigate from seed to any reality's model

## Key Insight from the Session

We started building a model OF spawnie (external). Then realized: the model should live INSIDE spawnie. Reality contains its own model.

Then: seed isn't just another model. It's YOUR model. Your home. The root of your tree of realities.

## Aspiration Layer

Refinement of "Intent vs Reality": not all intent is equal.

**Aspiration** = the golden goal. Immutable by AI. Human-controlled.
- AI can read aspiration, work toward it, but cannot modify it
- This is the constitution, the north star
- Prevents AI from moving goalposts

**Layers of reality (top to bottom):**
```
Aspiration     [human-controlled, immutable by AI]
Orchestration  [how to achieve aspiration]
Implementation [AI works autonomously here]
Base reality   [actual artifacts, verified by hash]
```

Key insight: If the model is complete enough, **base reality becomes disposable**.
Artifacts are regenerable projections of the model. The model is the source of truth,
artifacts are rendered on demand.

## Agent Architecture

How humans and AI work together in seed:

```
Human
   ↓
Controller (Claude in conversation)
   - Knows all aspirations
   - Tracks all running agents
   - Helps human context-switch
   - Single point of contact
   ↓
Aspiration Orchestrators (one per aspiration)
   - Dedicated AI focused on ONE aspiration
   - Autonomous within its scope
   - Uses spawnie for parallel work
   ↓
Spawnie Workers
   - Parallel execution
   - Specific tasks
   ↓
Reality (artifacts)
```

**Aspiration** = an unfinished model. A goal being worked toward.

The human switches between aspirations. The controller maintains context across all of them.
Each aspiration has its own orchestrator driving it forward.

## How This Works in Practice

1. Human defines aspiration in a "golden file" (immutable source of intent)
2. Orchestrator reads the golden file, builds plan
3. Workers (via spawnie) implement the plan
4. Reality is generated/updated
5. If golden file changes → hash mismatch detected → orchestrator wakes up
6. Orchestrator sees delta, updates reality to match

The golden file is the only thing the human edits. Everything downstream is derived.

## The Model is the Working Vehicle, Not Files

**Critical principle**: The model is where you work. Files are optional projections.

This applies to EVERYTHING:
- **Workflows** → nodes in the model, not `~/.spawnie/workflows/*.json`
- **Configurations** → nodes in the model, not `config.json` files
- **Task definitions** → nodes in the model
- **Documentation** → nodes in the model (README.md is a projection)
- **Code** → nodes in the model (source files are projections with hashes)

### Why This Matters

```
WRONG (file-first thinking):
  ~/.spawnie/workflows/code-quality-check.json  ← source of truth
  model references it                            ← backwards!

RIGHT (model-first thinking):
  bam/model/sketch.json contains workflow node   ← source of truth
  physical file is generated if needed           ← projection
```

### How Workflows Should Work

1. Define workflow as a node in the model:
```json
{
  "id": "workflow-code-quality",
  "type": "Workflow",
  "label": "Code Quality Check",
  "definition": {
    "steps": { ... },
    "inputs": { ... },
    "outputs": { ... }
  }
}
```

2. Spawnie reads workflows from the model, not from files
3. Physical files in `~/.spawnie/workflows/` are optional caches/projections
4. If model changes → regenerate projections (or just read from model directly)

### Benefits of Model-First

- **Single source of truth**: No sync issues between model and files
- **Introspectable**: Agents can query all workflows by reading the model
- **Versioned together**: Workflow changes tracked with model changes
- **Composable**: Workflows can reference other model nodes
- **Verifiable**: Hash verification applies to workflow definitions too

### The Disposability Test

Ask: "If I delete this file, can I regenerate it from the model?"

- YES → it's a projection, good
- NO → the file IS the source of truth, bad (move to model)

Physical files should only exist for:
1. Performance (caching)
2. External tool compatibility
3. Human editing convenience (then sync back to model)

## Schema as Model (Turtles)

The schema itself is a BAM model. There's no privileged "base layer."

```
seed (meta-model)
  └── reality: BAM-Schema
        └── defines: Node, Edge, Aspiration, Layer, Verification...
        └── self-describing (models its own structure)
        └── other models USES or EXTENDS it
```

Models define their own types. The schema model defines what types ARE.
Verification applies to schema too - is the schema implementation verified?

## What Needs to Change

Based on the model-first principle, these things are currently wrong:

| Current (Wrong) | Should Be (Right) |
|-----------------|-------------------|
| `~/.spawnie/workflows/*.json` files | Workflow nodes in `bam/model/sketch.json` |
| `~/.spawnie/config.json` | Config node in model |
| `~/.spawnie/tracker.json` | Status node in model (live state) |

### Implementation Path

1. ✅ **Add workflow nodes to spawnie's model** (`C:/spawnie/bam/model/sketch.json`)
   - Added `Workflow` node type to schema
   - Migrated 4 workflows as nodes: code-quality-check, reality-check, binary-search-analysis, merge-sort-analysis
   - Added `concept-model-first` node documenting this principle

2. ✅ **Modify spawnie to read workflows from model**
   - `spawnie workflows list` → reads model first, files as fallback
   - `spawnie workflows run NAME` → finds workflow node by name/ID
   - `spawnie workflows show NAME` → displays workflow from model

3. ✅ **Make physical files optional projections**
   - Files in `~/.spawnie/workflows/` still work as fallback
   - Model is source of truth
   - Shows source ("model" or "file") in list output

### Why We Didn't Do This Initially

- Bootstrapping: needed working system before perfect architecture
- Discovery: the principle emerged through building
- Physical files are easier to edit manually

**Status: IMPLEMENTED** (2026-02-01)

## Built

- 2026-01-31 (Friday night): Created seed, moved spawnie model into spawnie, reshaped seed as meta-model
- 2026-02-01 (Saturday): Added aspiration layer concept, agent architecture, golden file pattern
- 2026-02-01 (Saturday, later): Documented model-first principle - workflows, configs, and all definitions belong in the model, not physical files
- 2026-02-01 (Saturday, evening): **IMPLEMENTED model-first workflows** - migrated 4 workflows to BAM model nodes, modified spawnie to read from model first with file fallback
