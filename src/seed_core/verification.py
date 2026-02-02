"""Hash verification for reality models.

This module provides utilities for verifying source file hashes in BAM models,
enabling automatic drift detection when reality diverges from the model.

The verification process:
1. Read the model (sketch.json)
2. Extract all nodes with source references
3. Compute actual hash of each source file
4. Compare with expected hash in the model
5. Report any mismatches (drift detected)

Example:
    >>> from seed_core.verification import verify_model
    >>> results = verify_model(Path("/path/to/model/sketch.json"))
    >>> for check in results:
    ...     if not check.is_ok:
    ...         print(f"Drift: {check.node_id}")
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class HashCheck:
    """Result of a hash verification check.

    Attributes:
        node_id: ID of the node being verified
        source_path: Path to the source file
        expected_hash: Hash stored in the model
        actual_hash: Computed hash of the actual file
        status: Verification status (ok/mismatch/missing/error)
        error: Error message if status is error
    """
    node_id: str
    source_path: str
    expected_hash: Optional[str]
    actual_hash: Optional[str]
    status: str  # "ok", "mismatch", "missing", "error"
    error: Optional[str] = None

    @property
    def is_ok(self) -> bool:
        """Return True if verification passed."""
        return self.status == "ok"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file to hash

    Returns:
        Hexadecimal SHA-256 hash string

    Raises:
        OSError: If file cannot be read
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_node_source(node: dict, base_path: Path) -> HashCheck:
    """Verify a single node's source hash against the actual file.

    Args:
        node: Node dictionary from the BAM model
        base_path: Base path to resolve relative source paths

    Returns:
        HashCheck result with verification status
    """
    node_id = node.get('id', 'unknown')
    source = node.get('source', {})

    if not source:
        return HashCheck(
            node_id=node_id,
            source_path="",
            expected_hash=None,
            actual_hash=None,
            status="ok",  # No source to verify
        )

    source_path = source.get('path')
    expected_hash = source.get('hash')

    if not source_path:
        return HashCheck(
            node_id=node_id,
            source_path="",
            expected_hash=expected_hash,
            actual_hash=None,
            status="ok",
        )

    # Resolve path relative to base
    full_path = base_path / source_path

    if not full_path.exists():
        return HashCheck(
            node_id=node_id,
            source_path=str(source_path),
            expected_hash=expected_hash,
            actual_hash=None,
            status="missing",
            error=f"File not found: {full_path}"
        )

    try:
        actual_hash = compute_file_hash(full_path)

        if expected_hash:
            status = "ok" if actual_hash == expected_hash else "mismatch"
        else:
            status = "ok"  # No expected hash

        return HashCheck(
            node_id=node_id,
            source_path=str(source_path),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            status=status
        )
    except Exception as e:
        return HashCheck(
            node_id=node_id,
            source_path=str(source_path),
            expected_hash=expected_hash,
            actual_hash=None,
            status="error",
            error=str(e)
        )


def verify_model(model_path: Path) -> List[HashCheck]:
    """Verify all source hashes in a model.

    Args:
        model_path: Path to the model sketch.json file

    Returns:
        List of HashCheck results for all nodes with sources

    Raises:
        FileNotFoundError: If model file doesn't exist
        json.JSONDecodeError: If model file is invalid JSON
    """
    with open(model_path, 'r', encoding='utf-8') as f:
        model = json.load(f)

    base_path = model_path.parent.parent  # Go up from model/ to project root

    results = []
    for node in model.get('nodes', []):
        if 'source' in node:
            result = verify_node_source(node, base_path)
            results.append(result)

    return results


def verify_all_realities(registry) -> Dict[str, List[HashCheck]]:
    """Verify hashes for all realities that have models.

    Args:
        registry: RealityRegistry instance with list_all() method

    Returns:
        Dictionary mapping reality IDs to their verification results
    """
    results = {}

    for reality in registry.list_all():
        if reality.has_model:
            try:
                checks = verify_model(reality.full_model_path)
                results[reality.id] = checks
            except Exception as e:
                results[reality.id] = [
                    HashCheck(
                        node_id="model",
                        source_path=str(reality.full_model_path),
                        expected_hash=None,
                        actual_hash=None,
                        status="error",
                        error=str(e)
                    )
                ]

    return results
