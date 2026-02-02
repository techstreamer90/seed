from __future__ import annotations

# v0 stub: can be HTTP (FastAPI) or local IPC.

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class ApiConfig:
    root_model_path: Path


def serve(config: ApiConfig) -> None:
    raise NotImplementedError("API server not implemented in v0")
