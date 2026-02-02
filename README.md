# Root (Seed)

Your home. A model of all your models.

## What is this?

Root is the root of your reality tree. It tracks all the projects/systems you're building, each of which contains its own model.

Principle: **the model is the truth**.

- The model is easy to edit.
- Model consistency is checked continuously (audits + spawn work).
- "Reality" (source files) must be verified against the model.

## Directory Structure (with Zones)

```
seed/
├── model/                      # ZONE: model (read, propose_change)
│   └── sketch.json             # The truth - your map of everything
│
├── src/                        # ZONE: source (read, propose_change)
│   ├── seed_core/              # Core Python package
│   ├── root_store/             # Model store (SQLite index, query, safe writes)
│   └── ui/                     # Browser-based renderer
│
├── artifacts/                  # ZONE: artifacts (read only)
│   ├── db/                     # SQLite databases
│   ├── output/                 # Generated outputs
│   └── htmlcov/                # Test coverage reports
│
├── tools/                      # ZONE: tools (read, invoke, propose_change)
│   ├── scripts/                # Utility scripts
│   └── test_*.py, verify_*.py  # Tests and verification
│
├── .state/                     # ZONE: state (read, write)
│   └── (runtime state)         # Transient data agents can modify
│
└── *.md                        # ZONE: docs (read only)
                                # Should migrate into model over time
```

## Zones (Agent Permissions)

Zones define what agents can do where. Defined in `model/sketch.json`:

| Zone | Paths | Agent Can |
|------|-------|-----------|
| **model** | `model/` | read, propose_change |
| **source** | `src/` | read, propose_change |
| **artifacts** | `artifacts/` | read only |
| **tools** | `tools/` | read, invoke, propose_change |
| **state** | `.state/` | read, write |
| **docs** | `*.md` | read only |

**Key principle**: Agents check zones first. Direct writes only in `state/`. Everything else goes through Change nodes.

## Quick Start

```bash
# Describe Root in plain English
seed-core describe

# Check status of all realities
seed-core status

# Watch model files and continuously reassess
seed-core watch

# Record a "save" event on the node you're working on
seed-core save subsystem-root-store

# Verify source hashes to detect drift between model and reality
seed-core verify
```

## Realities Tracked

| Reality | Path | Status |
|---------|------|--------|
| Root (self) | C:/seed | active |
| Spawnie | C:/spawnie | active |
| BAM | C:/BAM | no-model-yet |
| Root Model Store | C:/seed/src/root_store | active |
| Browser Renderer | C:/seed/src/ui | active |

## The Core Ideas

1. **Model is truth** - Not documentation, THE truth
2. **Zones define permissions** - Clear boundaries for agents
3. **Reality is part of the model** - Source references with hashes
4. **Self-containing** - Each reality has its model inside it
5. **Root is the root** - Your map of all realities

## Adding a New Reality

1. Create the project somewhere
2. Add a `bam/` or `model/` directory with its own model
3. Add a Reality node to `seed/model/sketch.json`

## Key Files

- **model/sketch.json** - The Root meta-model (zones, schema, nodes, edges)
- **AGENTS.md** - How agents should operate (zones-first workflow)
- **NOTES.md** - Context for future Claude sessions
