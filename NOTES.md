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

## Built

- 2026-01-31 (Friday night): Created seed, moved spawnie model into spawnie, reshaped seed as meta-model
