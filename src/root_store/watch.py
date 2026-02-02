from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Callable, Optional

def discover_model_files(root_model_path: Path) -> list[Path]:
    """Return the set of model JSON files that make up the merged graph."""

    from .loader import discover_model_files as _discover

    return _discover([root_model_path])


@dataclass
class WatchConfig:
    root_model_path: Path
    poll_seconds: float = 1.0


def run_watch_loop(config: WatchConfig, on_change: Callable[[], None]) -> None:
    config.root_model_path = config.root_model_path.resolve()

    def snapshot() -> dict[Path, float]:
        files = discover_model_files(config.root_model_path)
        snap: dict[Path, float] = {}
        for f in files:
            try:
                snap[f] = f.stat().st_mtime
            except FileNotFoundError:
                continue
        return snap

    prev = snapshot()
    on_change()  # initial run

    while True:
        time.sleep(max(config.poll_seconds, 0.2))
        cur = snapshot()
        if cur != prev:
            prev = cur
            on_change()
