# Seed

Your home. A model of all your models.

## What is this?

Seed is the root of your reality tree. It tracks all the projects/systems you're building, each of which contains its own BAM model.

```
seed/
├── model/sketch.json    ← your map of everything
│
└── realities:
    ├── Spawnie (C:/spawnie/bam/)
    ├── BAM (C:/BAM - no model yet)
    └── ...
```

## Quick Start

```bash
# See what realities exist
cat model/sketch.json | jq '.nodes[] | select(.type=="Reality")'

# Check a specific reality's model
python C:/spawnie/bam/verify.py
```

## Structure

- **model/sketch.json** - The meta-model. Lists all realities and core concepts.
- **NOTES.md** - Context for future Claude sessions.

## Adding a New Reality

1. Create the project somewhere
2. Add a `bam/` directory with its own model
3. Add a Reality node to `seed/model/sketch.json`

## The Core Ideas

1. **Reality is part of the model** - Source references with hashes
2. **Intent vs Reality** - Nodes without source = goals
3. **Self-containing** - Each reality has its model inside it
4. **Seed is the root** - Your map of all realities
