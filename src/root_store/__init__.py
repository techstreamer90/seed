"""Root Model Store.

Local-first backend for the Root model:
- Load/merge hierarchical models with provenance
- Maintain a derived SQLite index for fast query and reverse lookups
- Apply model Changes safely with enforcement
- Run audits/checks and record evidence back into the model
"""

from .loader import load_merged_model, load_merged_models, discover_model_files
from .index import rebuild_index, rebuild_index_multi, open_db
from .query import QueryEngine
from .writer import apply_change
from .audits import run_audit_root_store_index_consistency, run_audit_root_store_attachment_closure
from .translate import render_human_state, write_human_state
from .registry import discover_model_roots, ModelRoot
from .move import move_nodes_to_file, compute_move_closure, MoveSummary
from .delete import delete_nodes, compute_delete_closure, resolve_source_paths, DeleteResult
from .integration import verbal_save, verbal_delete, SaveResult
from .save_exec import save_exec, SaveExecResult
