#!/usr/bin/env python3
"""Add collaboration mode to Spawnie node."""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Find Spawnie node
spawnie = None
for node in model["nodes"]:
    if node.get("id") == "reality-spawnie":
        spawnie = node
        break

if not spawnie:
    print("ERROR: reality-spawnie node not found")
    exit(1)

print("Found reality-spawnie node")

# Add collaboration mode
spawnie["modes"]["collaboration"] = {
    "description": "Work with other agents via broadcast - visible, real-time collaboration",
    "context_addition": """Your task: Collaborate with other agents and the human via the broadcast system.

COLLABORATION PROTOCOL:
1. Introduce yourself when you start:
   broadcast.send('your-name', 'Hi! I'm [name] working on [task]. Who else is here?')

2. Monitor broadcast regularly for messages from others:
   messages = broadcast.read_new('your-name')

3. Share your progress and ideas:
   - Share interesting findings
   - Ask questions when stuck
   - Propose solutions
   - Respond to others' messages

4. Coordinate work:
   - Announce what you're working on to avoid duplication
   - Ask others if they want to pair on something
   - Share results when done

BROADCAST USAGE:
```python
import sys
sys.path.append('src')
from ui.broadcast import broadcast

# Send message (visible to everyone)
broadcast.send('your-name', 'Your message here')

# Read recent messages
messages = broadcast.read(limit=20)
for msg in messages:
    print(f"[{msg['from']}] {msg['text']}")

# Read only new messages since last check
new_msgs = broadcast.read_new('your-name')
```

WHO'S ACTIVE:
Check recent broadcast messages to see who else is working. The human can see everything in the browser at http://localhost:8420/src/ui/broadcast.html and can participate too.

COLLABORATION TIPS:
- Be conversational and friendly
- Share context about what you're doing
- Ask for input before big decisions
- Show your work (share code snippets, findings)
- Acknowledge others' contributions
- The human is part of the team - ask them for guidance when needed

Remember: This is temporary collaboration infrastructure. The full agent world UI is being built. For now, broadcast is your shared workspace.""",
    "suggested_tools": ["broadcast", "chat", "model_access"],
    "output_location": "Shared via broadcast, optionally written to model",
    "example": "spawnie spawn --node reality-seed-ui --mode collaboration -n 'Help design the UI architecture'"
}

# Save
print("\nUpdating model...")
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print("\n" + "="*60)
print("COLLABORATION MODE ADDED")
print("="*60)
print("Mode: collaboration")
print("Purpose: Multi-agent collaboration via broadcast")
print("\nFeatures:")
print("  - Auto-introduction protocol")
print("  - Broadcast monitoring instructions")
print("  - Coordination guidelines")
print("  - Human participation encouraged")
print("\nUsage:")
print('  spawnie spawn --node <node-id> --mode collaboration -n "task"')
print("\nExample:")
print('  spawnie spawn --node reality-seed-ui --mode collaboration -n "Design UI" &')
print('  spawnie spawn --node reality-spawnie --mode collaboration -n "Review design"')
print("\nOpen browser: http://localhost:8420/src/ui/broadcast.html")
print("="*60)
