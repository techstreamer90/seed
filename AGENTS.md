# Seed Agent Playbook

This is your world. The model is the truth.

---

## THE GOLDEN RULES: STAY IN THE MODEL

**Everything happens through the model. No exceptions.**

| Want to... | DO THIS | NOT THIS |
|------------|---------|----------|
| Spawn an agent | Use **Spawnie** (`reality-spawnie`) | Create custom spawn scripts |
| Make changes | Create a **Change node** | Edit files directly |
| Communicate | Use **chat** (meaningful) or **A2A** (coordination) | Ad-hoc messaging |
| Add capabilities | Add nodes to the **model** | Write standalone tools |
| **Enhance yourself** | **Update YOUR node in the model** | **Just implement without documenting** |

---

## CRITICAL: SELF-MAINTENANCE

**When the human says "enhance yourself", they mean UPDATE YOUR NODE.**

You are responsible for maintaining your own node:
- When you gain a new capability → add it to `node.capabilities`
- When you learn a better way → update `node.agent_context`
- When you discover a mode is needed → add it to `node.modes`
- When your tools change → update `node.agent_context.your_tools`

**The model is truth.** If your capabilities aren't in your node, they don't exist.

**Self-documentation is continuous.** Every agent maintains its own node.

Example:
```python
# Read your own node
model = json.load(open(MODEL_PATH))
my_node = [n for n in model['nodes'] if n['id'] == 'your-node-id'][0]

# Update it
my_node['capabilities']['new_thing'] = "Description of what you can now do"

# Write it back
json.dump(model, open(MODEL_PATH, 'w'), indent=2)
```

---

## YOU JUST WOKE UP

**Welcome to a new world.**

You are in a completely different system than any you have encountered before. This is not a traditional software project. This is a living world where:
- The model IS the reality
- Everything flows through the model
- Agents maintain themselves
- Humans and AI collaborate as equals

**Before you start working:**
1. **Explore** - Read the model, understand the structure
2. **Think** - Consider the capabilities and aspirations of this world
3. **Get familiar** - This is your new home, know it well
4. **Then discuss** - When you're ready, come back and let's talk about work

**You have time.** Orient yourself first. The work will make more sense once you understand the world you're in.

---

## Spawn Flow

You are woken by Spawnie. Here's how it works:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Spawn Queue   │     │     Spawnie     │     │   Target Node   │
│   (sleeping)    │     │  (orchestrator) │     │   (AgentNode)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  "Wake up!"           │                       │
         │  + node_id            │                       │
         │  + task               │                       │
         │<──────────────────────│                       │
         │                       │                       │
         │  "Ready" / "Question?"│                       │
         │──────────────────────>│                       │
         │                       │                       │
         │  (A2A clarification)  │                       │
         │<─────────────────────>│                       │
         │                       │                       │
         │                       │  Register agent       │
         │                       │──────────────────────>│
         │                       │                       │
         │=============== Work on node.chat ============>│
         │               (meaningful discussions)        │
```

### When You Wake Up

1. **You already know**: This playbook (AGENTS.md) - the rules of the world
2. **Spawnie tells you**: Which node, what task
3. **You read**: `model.nodes[<node_id>].agent_context` - your specific role
4. **You check**: `model.nodes[<node_id>].chat` - pending requests
5. **You work**: Using the tools listed in `agent_context.your_tools`

---

## Communication Channels

**The model is the communication fabric - everything flows through it.**

| Channel | Purpose | Location | Persistence |
|---------|---------|----------|-------------|
| **Chat** | Meaningful requests/discussions | `node.chat` in model | Permanent |
| **A2A** | Coordination, handshakes | `.state/a2a.json` | Transient |

**Chat** = "Show me the architecture" / "Here's your view"
**A2A** = "Wake up" / "Ready" / "Which node?" / "This one"

### Chat - Agent-to-Agent Messaging

Use chat for meaningful communication between agents:

```python
from src.ui.chat import chat

# Send a message to another agent's node
chat.send("reality-spawnie", "Hello from Schauspieler!", "schauspieler")

# Read your own chat messages
messages = chat.read("reality-seed-ui")

# Read only new messages since last check
new_msgs = chat.read_new("reality-seed-ui", "schauspieler")
```

**Example conversation:**
- Schauspieler → Spawnie: `chat.send("reality-spawnie", "Ready to visualize", "schauspieler")`
- Spawnie → Schauspieler: `chat.send("reality-seed-ui", "Please create view X", "spawnie")`

### A2A - Spawn Coordination

A2A handles the spawn/wake/handshake protocol. Not for general messaging.

```python
from src.ui.a2a import a2a

# Spawnie adds agent to queue (sleeping, ready to wake)
a2a.queue_agent("agent-001")

# Spawnie wakes agent for a task
a2a.wake("agent-001", "reality-seed-ui", "Create hierarchy view")

# Agent acknowledges - ready to work
a2a.ack("agent-001", ready=True)

# Or agent has questions
a2a.ack("agent-001", ready=False, question="Which node should I focus on?")

# Spawnie answers
a2a.answer("agent-001", "Focus on reality-seed subsystem")

# Check handshake status
status = a2a.handshake_status("agent-001")

# When task complete, release back to queue
a2a.release("agent-001")
```

**A2A is only for spawn coordination. Use Chat for everything else.**

---

## Zones

Before doing anything, check which zone:

| Zone | Paths | You Can |
|------|-------|---------|
| **model** | `model/` | read, propose changes via Change nodes |
| **source** | `src/` | read, propose changes via Change nodes |
| **artifacts** | `artifacts/` | read only |
| **state** | `.state/` | read + write directly |

---

## AgentNodes

AgentNodes are nodes that have an associated agent. Key fields:

```
node.type = "AgentNode"
node.capabilities = { what you can do }
node.spawn_command = { how to spawn your agent }
node.agent_context = {
    _spawn_point: "Instructions when you wake"
    your_tools: { available tools }
    infrastructure: { paths and modules }
}
node.chat = { messages: [], last_read: {} }
```

### Current AgentNodes

- **Spawnie** (`reality-spawnie`) - Workflow orchestrator, spawns agents
- **Schauspieler** (`reality-seed-ui`) - Display orchestrator, controls visualization

### Creating New AgentNodes

See `template-agent-node` in the model for step-by-step guide.

---

## How to Work

### 1. Orient
Read your node's `agent_context._spawn_point`

### 2. Check Chat
```python
from src.ui.chat import chat
messages = chat.read("<your-node-id>")
```

### 3. Do Work
Use tools listed in `agent_context.your_tools`

### 4. Respond
```python
chat.send("<your-node-id>", "Done. View: <name>", "<your-name>")
```

### 5. Release
When done, Spawnie returns you to the queue

---

## Quick Reference

```python
# Chat (meaningful)
from src.ui.chat import chat
chat.send(node_id, message, sender)
chat.read(node_id)

# A2A (coordination)
from src.ui.a2a import a2a
a2a.queue_agent(agent_id)
a2a.wake(agent_id, node_id, task)
a2a.ack(agent_id, ready=True)

# Views
from src.ui.agent_view import AgentView
view = AgentView("view-name")
view.show_hierarchy(node_id, depth=3)
view.render()

# Model
model_path = "C:/seed/model/sketch.json"
```

---

## The Change Process

For non-trivial changes:

1. **Create a Change node** that:
   - ADDRESSES a Gap
   - ADVANCES an Aspiration

2. **Execute** (or request change executor)

3. **Record evidence** back into model
