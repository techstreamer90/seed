#!/usr/bin/env python3
"""
Claude UI Controller - Master interface for Claude to control the Seed UI.

Uses the model-as-API pattern: writes UICommand nodes to the model,
which the UI polls and renders.

Usage:
    from src.ui.claude_ui import ui

    ui.message("Processing...")           # Show overlay message
    ui.focus("reality-bam")               # Focus/zoom to node
    ui.status("BAM")                      # Show hierarchical status panel
    ui.query("BAM children")              # Get info as text (for Claude)
    ui.clear()                            # Clear overlays
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

# Default model path (can be overridden)
MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"

# Command node ID - UI looks for this specific node
UI_COMMAND_NODE_ID = "ui-command"


class ClaudeUI:
    """Master interface for Claude to control the Seed UI."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH

    def _read_model(self) -> Dict[str, Any]:
        """Read the current model."""
        with open(self.model_path, encoding="utf-8") as f:
            return json.load(f)

    def _write_model(self, model: Dict[str, Any]) -> None:
        """Write the model back to disk."""
        model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

    def _find_or_create_command_node(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Find or create the UICommand node."""
        for node in model.get("nodes", []):
            if node.get("id") == UI_COMMAND_NODE_ID:
                return node

        # Create new UICommand node
        command_node = {
            "id": UI_COMMAND_NODE_ID,
            "type": "UIState",
            "label": "UI Command",
            "description": "Command node for Claude to control the UI",
            "ui": {"x": -800, "y": -600},  # Off-screen position
        }
        model.setdefault("nodes", []).append(command_node)
        return command_node

    def _send_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a command to the UI by updating the UICommand node."""
        model = self._read_model()
        node = self._find_or_create_command_node(model)

        # Update command data
        node["command"] = {
            "type": command,
            "params": params or {},
            "timestamp": datetime.now().isoformat(),
            "processed": False,
        }

        self._write_model(model)

    def message(
        self,
        text: str,
        duration: int = 5000,
        style: Literal["info", "success", "warning", "error"] = "info",
    ) -> None:
        """Show an overlay message in the UI.

        Args:
            text: Message text to display
            duration: How long to show (ms), 0 = until dismissed
            style: Visual style (info=blue, success=green, warning=yellow, error=red)
        """
        self._send_command(
            "message",
            {"text": text, "duration": duration, "style": style},
        )

    def focus(
        self,
        node_id: str,
        zoom: float = 1.0,
        highlight: bool = True,
    ) -> None:
        """Focus the graph view on a specific node.

        Args:
            node_id: ID of the node to focus on
            zoom: Zoom level (1.0 = fit to view, 2.0 = closer)
            highlight: Whether to highlight/select the node
        """
        self._send_command(
            "focus",
            {"nodeId": node_id, "zoom": zoom, "highlight": highlight},
        )

    def status(
        self,
        root_id: Optional[str] = None,
        depth: int = 3,
    ) -> None:
        """Show the hierarchical status panel for a node.

        Args:
            root_id: ID of the root node (e.g., "reality-bam"), None = "reality-seed"
            depth: How many levels deep to show
        """
        self._send_command(
            "status",
            {"rootId": root_id or "reality-seed", "depth": depth},
        )

    def clear(self) -> None:
        """Clear all overlays (message and status panel)."""
        self._send_command("clear", {})

    def query(self, query_text: str) -> str:
        """Query the model and return information as text.

        This is for Claude to get information, not for showing UI.
        Uses the quick_query module.

        Args:
            query_text: Natural language query like "BAM children" or "status of reality-seed"

        Returns:
            Text response suitable for Claude to read
        """
        from src.ui.quick_query import query as quick_query

        return quick_query(query_text)

    def get_status(self, node_id: str) -> str:
        """Get human-readable status text for a node.

        Args:
            node_id: ID of the node

        Returns:
            Status text for Claude to read
        """
        from src.ui.quick_query import get_status

        return get_status(node_id)

    def get_hierarchy(self, node_id: str, depth: int = 3) -> str:
        """Get ASCII tree view of a node's hierarchy.

        Args:
            node_id: ID of the root node
            depth: How many levels to show

        Returns:
            ASCII tree text for Claude to read
        """
        from src.ui.quick_query import get_hierarchy_text

        return get_hierarchy_text(node_id, depth)

    def get_children(self, node_id: str) -> List[str]:
        """Get list of child node IDs.

        Args:
            node_id: ID of the parent node

        Returns:
            List of child node IDs
        """
        from src.ui.quick_query import get_children

        return get_children(node_id)


# Global instance for easy import
ui = ClaudeUI()


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python claude_ui.py <command> [args...]")
        print("Commands: message, focus, status, clear, query")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "message" and len(sys.argv) >= 3:
        ui.message(" ".join(sys.argv[2:]))
    elif cmd == "focus" and len(sys.argv) >= 3:
        ui.focus(sys.argv[2])
    elif cmd == "status":
        root_id = sys.argv[2] if len(sys.argv) >= 3 else None
        ui.status(root_id)
    elif cmd == "clear":
        ui.clear()
    elif cmd == "query" and len(sys.argv) >= 3:
        result = ui.query(" ".join(sys.argv[2:]))
        print(result)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
