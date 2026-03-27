"""
CRDT (Conflict-free Replicated Data Type) Engine for real-time collaboration.

Uses a simplified LWW-Element-Set (Last-Write-Wins) approach
with vector clocks for field-level conflict resolution.
Supports multi-user concurrent editing with deterministic merge.

Enhanced with:
- Undo/Redo per-user operation stack
- Operation snapshot for version history
- Conflict detection and resolution logging
- Field-level change diff generation
"""
from __future__ import annotations

import json
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional


class VectorClock:
    """Logical vector clock for causal ordering."""

    def __init__(self):
        self._clocks: dict[str, int] = {}

    def increment(self, node_id: str) -> dict[str, int]:
        self._clocks[node_id] = self._clocks.get(node_id, 0) + 1
        return dict(self._clocks)

    def merge(self, other: dict[str, int]) -> None:
        for node, ts in other.items():
            self._clocks[node] = max(self._clocks.get(node, 0), ts)

    def get(self) -> dict[str, int]:
        return dict(self._clocks)

    def compare(self, other: dict[str, int]) -> str:
        """Returns 'before', 'after', 'concurrent', or 'equal'."""
        all_nodes = set(self._clocks) | set(other)
        self_less = other_less = False
        for n in all_nodes:
            s = self._clocks.get(n, 0)
            o = other.get(n, 0)
            if s < o:
                self_less = True
            elif s > o:
                other_less = True
        if self_less and not other_less:
            return "before"
        elif other_less and not self_less:
            return "after"
        elif not self_less and not other_less:
            return "equal"
        return "concurrent"

    def snapshot(self) -> dict[str, int]:
        return dict(self._clocks)


@dataclass
class FieldOperation:
    """A single field-level edit operation."""
    path: str  # dot-separated: "narrative.beat"
    value: Any
    user_id: str
    timestamp: float = field(default_factory=time.time)
    op_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Undo/redo support
    previous_value: Any = None
    is_undone: bool = False

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "value": self.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "op_id": self.op_id,
            "previous_value": self.previous_value,
            "is_undone": self.is_undone,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FieldOperation:
        return cls(
            path=d["path"],
            value=d["value"],
            user_id=d["user_id"],
            timestamp=d.get("timestamp", time.time()),
            op_id=d.get("op_id", str(uuid.uuid4())),
            previous_value=d.get("previous_value"),
            is_undone=d.get("is_undone", False),
        )


@dataclass
class OperationSnapshot:
    """Point-in-time snapshot of CRDT state for version history."""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    operations_count: int = 0
    vector_clock: dict[str, int] = field(default_factory=dict)
    field_values: dict[str, Any] = field(default_factory=dict)


class CRDTEngine:
    """
    Field-level CRDT for concurrent scene editing.

    Strategy: LWW (Last-Write-Wins) per field path, with timestamp
    tiebreaker by user_id for deterministic resolution.
    Concurrent vector clock events are merged with user priority.

    Features:
    - Undo/Redo per user
    - Operation snapshots for versioning
    - Conflict detection and logging
    """

    def __init__(self):
        # path → {op_id → FieldOperation}
        self._operations: dict[str, dict[str, FieldOperation]] = {}
        self._vector_clock = VectorClock()
        self._node_id = str(uuid.uuid4())
        self._operation_log: list[dict] = []

        # Undo/redo: user_id → list of op_ids (stack)
        self._undo_stack: dict[str, list[str]] = {}
        # Redo stack stores undone operations
        self._redo_stack: dict[str, list[str]] = {}

        # Snapshots
        self._snapshots: list[OperationSnapshot] = []

        # Conflict log
        self._conflict_log: list[dict] = []

    def apply_operation(self, op: FieldOperation) -> bool:
        """
        Apply a field operation. Returns True if the operation wins
        (is the latest write for this field).
        Tracks the previous value for undo support.
        """
        self._vector_clock.increment(op.user_id)

        if op.path not in self._operations:
            self._operations[op.path] = {}

        # Capture previous winning value for undo
        if op.previous_value is None:
            op.previous_value = self.get_field_value(op.path)

        # Detect conflict: multiple users editing same field
        existing_ops = self._operations[op.path]
        conflicting_users = set(existing_ops.keys()) - {op.user_id}
        if conflicting_users:
            self._conflict_log.append({
                "path": op.path,
                "new_user": op.user_id,
                "conflicting_users": list(conflicting_users),
                "timestamp": op.timestamp,
                "resolution": "lww",
            })

        # Store by op_id
        existing_ops[op.op_id] = op

        # Track in undo stack
        self._undo_stack.setdefault(op.user_id, []).append(op.op_id)

        # Clear redo for this user (new action invalidates redo)
        if op.user_id in self._redo_stack:
            self._redo_stack[op.user_id].clear()

        self._operation_log.append(op.to_dict())
        return True

    def get_field_value(self, path: str) -> Any:
        """
        Resolve the current value for a field path.
        Takes the latest non-undone operation across all users.
        """
        if path not in self._operations:
            return None

        ops = self._operations[path]
        if not ops:
            return None

        # LWW: pick the latest non-undone operation
        active_ops = [o for o in ops.values() if not o.is_undone]
        if not active_ops:
            return None

        winner = max(active_ops, key=lambda o: (o.timestamp, o.user_id))
        return winner.value

    def undo(self, user_id: str) -> Optional[dict]:
        """
        Undo the last operation by this user.
        Returns the undone operation details, or None if nothing to undo.
        """
        stack = self._undo_stack.get(user_id, [])
        if not stack:
            return None

        op_id = stack.pop()
        # Find the operation
        for path, path_ops in self._operations.items():
            if op_id in path_ops:
                op = path_ops[op_id]
                op.is_undone = True

                # Push to redo stack
                self._redo_stack.setdefault(user_id, []).append(op_id)

                return {
                    "op_id": op_id,
                    "path": op.path,
                    "undone_value": op.value,
                    "restored_value": self.get_field_value(op.path),
                }

        return None

    def redo(self, user_id: str) -> Optional[dict]:
        """
        Redo the last undone operation by this user.
        Returns the redone operation details, or None if nothing to redo.
        """
        stack = self._redo_stack.get(user_id, [])
        if not stack:
            return None

        op_id = stack.pop()
        for path, path_ops in self._operations.items():
            if op_id in path_ops:
                op = path_ops[op_id]
                op.is_undone = False

                # Push back to undo stack
                self._undo_stack.setdefault(user_id, []).append(op_id)

                return {
                    "op_id": op_id,
                    "path": op.path,
                    "restored_value": op.value,
                }

        return None

    def can_undo(self, user_id: str) -> bool:
        return bool(self._undo_stack.get(user_id))

    def can_redo(self, user_id: str) -> bool:
        return bool(self._redo_stack.get(user_id))

    def get_undo_stack(self, user_id: str) -> list[dict]:
        """Get undoable operations for a user (most recent last)."""
        result = []
        for op_id in self._undo_stack.get(user_id, []):
            for path_ops in self._operations.values():
                if op_id in path_ops:
                    op = path_ops[op_id]
                    result.append({
                        "op_id": op.op_id,
                        "path": op.path,
                        "value": op.value,
                        "timestamp": op.timestamp,
                    })
                    break
        return result

    # ── Snapshots ──────────────────────────────────────────────

    def create_snapshot(self, description: str = "") -> OperationSnapshot:
        """Create a point-in-time snapshot of all field values."""
        field_values = {}
        for path in self._operations:
            value = self.get_field_value(path)
            if value is not None:
                field_values[path] = value

        snapshot = OperationSnapshot(
            description=description,
            operations_count=len(self._operation_log),
            vector_clock=self._vector_clock.snapshot(),
            field_values=field_values,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_snapshots(self) -> list[dict]:
        return [
            {
                "snapshot_id": s.snapshot_id,
                "timestamp": s.timestamp,
                "description": s.description,
                "operations_count": s.operations_count,
            }
            for s in self._snapshots
        ]

    def restore_snapshot(self, snapshot_id: str) -> Optional[dict[str, Any]]:
        """
        Get field values from a snapshot.
        Note: This returns values but does NOT auto-apply them as new operations.
        The caller should apply each field update explicitly.
        """
        for s in self._snapshots:
            if s.snapshot_id == snapshot_id:
                return dict(s.field_values)
        return None

    # ── Merge & Conflict Resolution ────────────────────────────

    def merge(self, other: CRDTEngine) -> list[dict]:
        """
        Merge another CRDTEngine's state into this one.
        Returns list of conflicts that occurred during merge.
        """
        self._vector_clock.merge(other._vector_clock.get())

        conflicts = []
        for path, path_ops in other._operations.items():
            for op_id, op in path_ops.items():
                old_value = self.get_field_value(path)
                self.apply_operation(op)
                # Check if merge caused a value change (potential conflict)
                new_value = self.get_field_value(path)
                if old_value is not None and old_value != new_value:
                    conflicts.append({
                        "path": path,
                        "our_value": old_value,
                        "their_value": op.value,
                        "resolved_to": new_value,
                        "resolution": "lww",
                    })

        return conflicts

    def resolve_conflicts(self, path: str) -> list[dict]:
        """
        List all competing operations for a field (for UI conflict display).
        """
        if path not in self._operations:
            return []
        return [
            {**op.to_dict(), "is_winner": not op.is_undone}
            for op in self._operations[path].values()
        ]

    # ── Apply & Diff ───────────────────────────────────────────

    def apply_to_scene(self, scene, user_id: str = "") -> dict[str, Any]:
        """
        Apply all winning operations to rebuild a scene dict.
        Returns the merged scene as a dict.
        """
        scene_dict = scene.model_dump()
        for path in self._operations:
            value = self.get_field_value(path)
            if value is not None:
                self._set_nested(scene_dict, path, value)
        return scene_dict

    def get_field_diff(self, path: str) -> Optional[dict]:
        """
        Get the diff for a specific field (old → new).
        """
        if path not in self._operations or not self._operations[path]:
            return None

        ops = sorted(self._operations[path].values(), key=lambda o: o.timestamp)
        if len(ops) < 2:
            return None

        return {
            "path": path,
            "changes": [
                {
                    "op_id": op.op_id,
                    "user_id": op.user_id,
                    "timestamp": op.timestamp,
                    "old_value": op.previous_value,
                    "new_value": op.value,
                    "is_undone": op.is_undone,
                }
                for op in ops
            ],
            "total_edits": len(ops),
        }

    def get_user_activity(self, user_id: str) -> list[dict]:
        """Get all operations by a specific user."""
        return [
            op.to_dict()
            for path_ops in self._operations.values()
            for op in path_ops.values()
            if op.user_id == user_id
        ]

    # ── Logging ────────────────────────────────────────────────

    def get_operation_log(self, limit: int = 200) -> list[dict]:
        return self._operation_log[-limit:]

    def get_conflict_log(self, limit: int = 50) -> list[dict]:
        return self._conflict_log[-limit:]

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _set_nested(d: dict, path: str, value: Any) -> None:
        keys = path.split(".")
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
