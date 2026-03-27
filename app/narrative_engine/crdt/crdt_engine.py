"""
CRDT (Conflict-free Replicated Data Type) Engine for real-time collaboration.

Uses a simplified LWW-Element-Set (Last-Write-Wins) approach
with vector clocks for field-level conflict resolution.
Supports multi-user concurrent editing with deterministic merge.
"""
from __future__ import annotations

import json
import time
import uuid
from copy import deepcopy
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


class FieldOperation:
    """A single field-level edit operation."""

    def __init__(self, path: str, value: Any, user_id: str,
                 timestamp: float = None, op_id: str = None):
        self.path = path  # dot-separated: "narrative.beat"
        self.value = value
        self.user_id = user_id
        self.timestamp = timestamp or time.time()
        self.op_id = op_id or str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "value": self.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "op_id": self.op_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FieldOperation:
        return cls(**d)


class CRDTEngine:
    """
    Field-level CRDT for concurrent scene editing.

    Strategy: LWW (Last-Write-Wins) per field path, with timestamp
    tiebreaker by user_id for deterministic resolution.
    Concurrent vector clock events are merged with user priority.
    """

    def __init__(self):
        # path → {user_id → FieldOperation}
        self._operations: dict[str, dict[str, FieldOperation]] = {}
        self._vector_clock = VectorClock()
        self._node_id = str(uuid.uuid4())
        self._operation_log: list[dict] = []

    def apply_operation(self, op: FieldOperation) -> bool:
        """
        Apply a field operation. Returns True if the operation wins
        (is the latest write for this field).
        """
        self._vector_clock.increment(op.user_id)

        if op.path not in self._operations:
            self._operations[op.path] = {}

        existing = self._operations[op.path].get(op.user_id)

        # LWW: keep the operation with the latest timestamp
        if existing is None or op.timestamp >= existing.timestamp:
            self._operations[op.path][op.user_id] = op
            self._operation_log.append(op.to_dict())
            return True
        return False

    def get_field_value(self, path: str) -> Any:
        """
        Resolve the current value for a field path.
        Takes the latest operation across all users.
        """
        if path not in self._operations:
            return None

        ops = self._operations[path]
        if not ops:
            return None

        # LWW: pick the operation with highest timestamp
        # Tiebreak: lexicographic user_id
        winner = max(ops.values(), key=lambda o: (o.timestamp, o.user_id))
        return winner.value

    def merge(self, other: CRDTEngine) -> None:
        """Merge another CRDTEngine's state into this one."""
        self._vector_clock.merge(other._vector_clock.get())

        for path, user_ops in other._operations.items():
            for user_id, op in user_ops.items():
                self.apply_operation(op)

    def resolve_conflicts(self, path: str) -> list[dict]:
        """
        List all competing operations for a field (for UI conflict display).
        """
        if path not in self._operations:
            return []
        return [op.to_dict() for op in self._operations[path].values()]

    def apply_to_scene(self, scene, user_id: str) -> dict[str, Any]:
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

    def get_operation_log(self, limit: int = 200) -> list[dict]:
        return self._operation_log[-limit:]

    @staticmethod
    def _set_nested(d: dict, path: str, value: Any) -> None:
        keys = path.split(".")
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
