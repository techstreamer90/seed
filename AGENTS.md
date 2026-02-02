# Seed Agent Playbook

This repo treats **the model as the truth**.

---

## THE GOLDEN RULE: STAY IN THE MODEL

**Everything happens through the model. No exceptions.**

| Want to... | DO THIS | NOT THIS |
|------------|---------|----------|
| Spawn an agent | Use **Spawnie** (`reality-spawnie` at C:/spawnie) | Create custom spawn scripts |
| Make changes | Create a **Change node** | Edit files directly |
| Communicate | Use **modeled channels** | Ad-hoc messaging |
| Add capabilities | Add nodes to the **model** | Write standalone tools |

**Why?** The model IS the interface. If it's not in the model, it doesn't exist. Custom scripts bypass governance, auditing, and the entire Seed philosophy.

**Spawnie** is the workflow orchestrator. It knows how to:
- Activate nodes as agents
- Manage agent lifecycles
- Route work through proper channels
- Maintain model integrity

When the user says "spawn an agent for X", your response is: "I'll use Spawnie to spawn that."

---

## Zones First

Before doing anything, check which zone you're working in. Zones are defined in `model/sketch.json`:

| Zone | Paths | You Can |
|------|-------|---------|
| **model** | `model/` | read, propose changes via Change nodes |
| **source** | `src/` | read, propose changes via Change nodes |
| **artifacts** | `artifacts/` | read only - never edit |
| **tools** | `tools/` | read, invoke, propose changes |
| **state** | `.state/`, `src/ui/*.png`, `src/ui/layout.json` | read + write directly |
| **docs** | `*.md` | read only |

**Rule**: Direct writes only in `state/` zone. Everything else requires a Change node or explicit human approval.

## Directory Structure

```
seed/
├── model/sketch.json           # The truth
├── src/
│   ├── seed_core/              # Core Python package
│   ├── root_store/             # Model store
│   └── ui/                     # Browser renderer
├── artifacts/                  # Generated (read-only)
├── tools/                      # Scripts and tests
└── .state/                     # Runtime state (writable)
```

## Quick Commands

```bash
seed-core status              # Overview of all realities
seed-core describe            # Plain English description
seed-core watch               # Continuous model watch
seed-core save <node_id>      # Record save event
seed-core verify              # Check for drift
```

## How to Work as an Agent

### 1. Orient: Read the spawn point

Find your Reality node's `agent_context`:
- `_spawn_point` - where you are
- `focus` - current gap being addressed
- `work_queue` - prioritized todos
- `principles` - rules to follow (ZONES FIRST is #1)

### 2. Check zones before any file operation

```
Want to edit src/seed_core/pulse.py?
  → Zone: source
  → Permission: propose_change
  → Action: Create a Change node OR get human approval

Want to write artifacts/output/report.txt?
  → Zone: artifacts
  → Permission: read only
  → Action: DON'T. Artifacts are generated, not edited.

Want to update src/ui/layout.json?
  → Zone: state
  → Permission: read, write
  → Action: Edit directly - this is transient state.
```

### 3. Edit the model (truth updates)

- Keep JSON valid
- Follow bundle/closure rules when moving nodes
- After progress, run `seed-core save <node_id>`

### 4. Verification is the strict gate

When a node has `source.path`:
- Run `seed-core verify` regularly
- If drift detected: update model OR update reality
- Record evidence via save

## The Change Process

For non-trivial changes to model or source:

1. **Create a Change node** that:
   - ADDRESSES a Gap (what problem it solves)
   - ADVANCES an Aspiration (why it matters)
   - Has required evidence

2. **Execute the change** (or request a change executor)

3. **Record evidence** back into the model

## What Agents Can and Cannot Do

### CAN (in state zone)
- Write screenshots, layout files
- Update transient runtime data
- Modify `.state/` contents

### CAN (with Change node or approval)
- Edit model/sketch.json
- Edit source code in src/
- Add/modify tools

### CANNOT
- Edit artifacts/ (read-only, regenerate from source)
- Modify docs without human approval
- Skip the zones check

## Save Semantics

`seed-core save <node_id>` records:
- `evidence.integration_queue.last_save` on the node and its parent chain
- Git info (branch, head, dirty, upstream)
- Neighborhood scan (nearby edges and nodes)

## Verification Semantics

`seed-core verify` checks:
- File hashes declared in the model
- Drift between model claims and reality

Failures should drive work (create Todo or Change nodes).
