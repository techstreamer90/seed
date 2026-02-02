#!/usr/bin/env python3
"""
Control Pulse - Self-updating system health monitor.

The Control agent runs this to maintain accurate system status in the model.
This is the embodiment of "model is truth" - the node updates itself.
"""

import json
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"
BROADCAST_PATH = Path(__file__).parent.parent.parent / ".state" / "broadcast.json"


class ControlPulse:
    """System health monitor that updates the model."""

    def __init__(self):
        self.model_path = MODEL_PATH
        self.pulse_count = 0

    def read_model(self) -> Dict[str, Any]:
        """Read the model."""
        with open(self.model_path, encoding="utf-8") as f:
            return json.load(f)

    def write_model(self, model: Dict[str, Any]) -> None:
        """Write the model back."""
        model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

    def check_ui_server(self, port: int = 8420) -> Dict[str, Any]:
        """Check if UI server is running."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                return {
                    "state": "running",
                    "port": port,
                    "last_check": datetime.now().isoformat(),
                    "health": "healthy"
                }
            else:
                return {
                    "state": "stopped",
                    "port": port,
                    "last_check": datetime.now().isoformat(),
                    "health": "unhealthy"
                }
        except Exception as e:
            return {
                "state": "error",
                "port": port,
                "last_check": datetime.now().isoformat(),
                "health": "unhealthy",
                "error": str(e)
            }

    def check_broadcast(self) -> Dict[str, Any]:
        """Check broadcast system status."""
        try:
            if not BROADCAST_PATH.exists():
                return {
                    "state": "not_initialized",
                    "last_check": datetime.now().isoformat(),
                    "health": "unhealthy"
                }

            with open(BROADCAST_PATH, encoding="utf-8") as f:
                data = json.load(f)

            msg_count = len(data.get("messages", []))
            last_msg = data.get("messages", [])[-1] if data.get("messages") else None

            return {
                "state": "active",
                "message_count": msg_count,
                "last_message_at": last_msg.get("at") if last_msg else None,
                "last_check": datetime.now().isoformat(),
                "health": "healthy"
            }
        except Exception as e:
            return {
                "state": "error",
                "last_check": datetime.now().isoformat(),
                "health": "unhealthy",
                "error": str(e)
            }

    def pulse(self) -> Dict[str, Any]:
        """
        Perform one health check pulse.

        Returns status dict that will be written to the model.
        """
        self.pulse_count += 1

        # Check services
        ui_server = self.check_ui_server()
        broadcast = self.check_broadcast()

        # Determine overall health
        all_healthy = (
            ui_server.get("health") == "healthy" and
            broadcast.get("health") == "healthy"
        )

        overall_health = "healthy" if all_healthy else "degraded"

        return {
            "last_pulse": datetime.now().isoformat(),
            "pulse_count": self.pulse_count,
            "health": overall_health,
            "services": {
                "ui-server": ui_server,
                "broadcast": broadcast
            }
        }

    def update_model(self) -> str:
        """
        Run a pulse and update the model with current status.

        This is self-documenting: the Control node IS the system status.
        """
        # Get current status
        status = self.pulse()

        # Read model
        model = self.read_model()

        # Find system-control node
        control_node = None
        for node in model.get("nodes", []):
            if node.get("id") == "system-control":
                control_node = node
                break

        if not control_node:
            return "ERROR: system-control node not found in model"

        # Update status
        control_node["status"] = status

        # Also update service nodes if they exist
        for node in model.get("nodes", []):
            if node.get("id") == "service-ui-server":
                node["status"] = status["services"]["ui-server"]
            elif node.get("id") == "channel-broadcast":
                node["status"] = {
                    "message_count": status["services"]["broadcast"].get("message_count", 0),
                    "last_message_at": status["services"]["broadcast"].get("last_message_at"),
                    "last_check": status["services"]["broadcast"].get("last_check"),
                    "state": status["services"]["broadcast"].get("state")
                }

        # Update control view
        if "views" not in model:
            model["views"] = {}

        model["views"]["control-status"] = {
            "name": "control-status",
            "description": "System Control status - live health monitoring",
            "updated_at": datetime.now().isoformat(),
            "render_target": "control-widget",
            "content": {
                "type": "status-widget",
                "health": status["health"],
                "last_pulse": status["last_pulse"],
                "pulse_count": status["pulse_count"],
                "services": {
                    "ui-server": status["services"]["ui-server"]["health"],
                    "broadcast": status["services"]["broadcast"]["health"]
                }
            }
        }

        # Write model back
        self.write_model(model)

        return f"Pulse {status['pulse_count']}: {status['health']} | UI: {status['services']['ui-server']['health']} | BC: {status['services']['broadcast']['health']}"


# CLI
if __name__ == "__main__":
    import sys
    import time

    control = ControlPulse()

    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        # Continuous mode: pulse every 30 seconds
        print("Control Pulse - Continuous monitoring")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                result = control.update_model()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {result}")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        # Single pulse
        result = control.update_model()
        print(result)
