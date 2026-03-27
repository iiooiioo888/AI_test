"""
State Machine Service — strict scene lifecycle management.

DRAFT → REVIEW → LOCKED → QUEUED → GENERATING → COMPLETED
                                  ↑              → FAILED → DRAFT

Enhanced with:
- Formal StateTransitionError with diagnostic context
- Pre/post transition hooks
- Batch transition validation
- Transition guard conditions
- Structured audit trail with metadata
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from app.shared import SceneState, STATE_TRANSITIONS, validate_transition, AuditEntry


# ── Custom Exception ───────────────────────────────────────────

class StateTransitionError(Exception):
    """
    Raised when an invalid or guarded state transition is attempted.
    Carries full diagnostic context for logging and API responses.
    """

    def __init__(
        self,
        from_state: SceneState,
        to_state: SceneState,
        scene_id: str = "",
        reason: str = "",
        valid_transitions: Optional[list[SceneState]] = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.scene_id = scene_id
        self.reason = reason
        self.valid_transitions = valid_transitions or list(
            STATE_TRANSITIONS.get(from_state, set())
        )

        parts = [f"Invalid transition: {from_state.value} → {to_state.value}"]
        if scene_id:
            parts.append(f"scene={scene_id}")
        if reason:
            parts.append(f"reason={reason}")
        parts.append(f"valid={[s.value for s in self.valid_transitions]}")
        super().__init__(" | ".join(parts))

    def to_dict(self) -> dict:
        return {
            "error": "StateTransitionError",
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "scene_id": self.scene_id,
            "reason": self.reason,
            "valid_transitions": [s.value for s in self.valid_transitions],
        }


# ── Transition Guard ───────────────────────────────────────────

@dataclass
class TransitionGuard:
    """
    A guard condition that must pass before a transition is allowed.
    Multiple guards can be composed via AND logic.
    """
    name: str
    check: Callable[[any], bool]  # takes scene, returns bool
    failure_message: str = ""


# ── Transition Record ──────────────────────────────────────────

@dataclass
class TransitionRecord:
    scene_id: str
    from_state: SceneState
    to_state: SceneState
    user_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    guards_passed: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── Main Service ───────────────────────────────────────────────

class StateMachineService:
    """
    Enforces strict state transitions and manages scene lifecycle.

    Features:
    - Transition guard system for conditional transitions
    - Pre/post hooks for side effects (notifications, validation)
    - Batch validation for multi-scene operations
    - Full transition audit log with timestamps
    """

    def __init__(self):
        self._transition_log: list[TransitionRecord] = []
        self._guards: dict[tuple[SceneState, SceneState], list[TransitionGuard]] = {}
        self._pre_hooks: list[Callable] = []
        self._post_hooks: list[Callable] = []

    # ── Guard Management ───────────────────────────────────────

    def add_guard(
        self,
        from_state: SceneState,
        to_state: SceneState,
        guard: TransitionGuard,
    ) -> None:
        """Register a guard condition for a specific transition."""
        key = (from_state, to_state)
        self._guards.setdefault(key, []).append(guard)

    def remove_guard(self, from_state: SceneState, to_state: SceneState, name: str) -> bool:
        """Remove a guard by name."""
        key = (from_state, to_state)
        guards = self._guards.get(key, [])
        for i, g in enumerate(guards):
            if g.name == name:
                guards.pop(i)
                return True
        return False

    # ── Hook Management ────────────────────────────────────────

    def register_pre_hook(self, hook: Callable) -> None:
        """Register a function called before every transition. Receives (scene, new_state, user_id)."""
        self._pre_hooks.append(hook)

    def register_post_hook(self, hook: Callable) -> None:
        """Register a function called after every transition. Receives (scene, old_state, user_id)."""
        self._post_hooks.append(hook)

    # ── Core Transition ────────────────────────────────────────

    def transition(self, scene, new_state: SceneState, user_id: str) -> bool:
        """
        Attempt a state transition on a scene.

        Raises:
            StateTransitionError: if the transition is not allowed by the
                adjacency map or by a registered guard.
        """
        # 1. Validate against adjacency map
        if not validate_transition(scene.state, new_state):
            raise StateTransitionError(
                from_state=scene.state,
                to_state=new_state,
                scene_id=str(getattr(scene, "id", "")),
                reason="Not in valid transition map",
            )

        # 2. Evaluate guards
        key = (scene.state, new_state)
        guards = self._guards.get(key, [])
        passed = []
        for guard in guards:
            if not guard.check(scene):
                raise StateTransitionError(
                    from_state=scene.state,
                    to_state=new_state,
                    scene_id=str(getattr(scene, "id", "")),
                    reason=guard.failure_message or f"Guard '{guard.name}' failed",
                )
            passed.append(guard.name)

        # 3. Pre-hooks
        old_state = scene.state
        for hook in self._pre_hooks:
            hook(scene, new_state, user_id)

        # 4. Apply transition
        scene.state = new_state
        scene.version += 1
        scene.updated_at = datetime.utcnow()

        # 5. Audit trail (on scene)
        entry = AuditEntry(
            user_id=user_id,
            action="STATE_TRANSITION",
            details={"from": old_state.value, "to": new_state.value},
        )
        scene.audit_log.append(entry)

        # 6. Global transition log
        record = TransitionRecord(
            scene_id=str(getattr(scene, "id", "")),
            from_state=old_state,
            to_state=new_state,
            user_id=user_id,
            guards_passed=passed,
        )
        self._transition_log.append(record)

        # 7. Post-hooks
        for hook in self._post_hooks:
            hook(scene, old_state, user_id)

        return True

    # ── Batch Validation ───────────────────────────────────────

    def validate_batch(
        self,
        transitions: list[tuple[any, SceneState]],
    ) -> list[Optional[StateTransitionError]]:
        """
        Validate multiple transitions without applying them.
        Returns a list of errors (None for valid transitions).

        Args:
            transitions: list of (scene, target_state) tuples

        Returns:
            list of StateTransitionError or None, same length as input
        """
        results: list[Optional[StateTransitionError]] = []
        for scene, target in transitions:
            try:
                # Check adjacency
                if not validate_transition(scene.state, target):
                    results.append(StateTransitionError(
                        from_state=scene.state,
                        to_state=target,
                        scene_id=str(getattr(scene, "id", "")),
                    ))
                    continue

                # Check guards
                key = (scene.state, target)
                for guard in self._guards.get(key, []):
                    if not guard.check(scene):
                        results.append(StateTransitionError(
                            from_state=scene.state,
                            to_state=target,
                            scene_id=str(getattr(scene, "id", "")),
                            reason=guard.failure_message or f"Guard '{guard.name}' failed",
                        ))
                        break
                else:
                    results.append(None)

            except Exception as e:
                results.append(StateTransitionError(
                    from_state=scene.state,
                    to_state=target,
                    scene_id=str(getattr(scene, "id", "")),
                    reason=str(e),
                ))

        return results

    # ── Query Methods ──────────────────────────────────────────

    def get_valid_transitions(self, current_state: SceneState) -> list[SceneState]:
        """Return all valid next states from the current state."""
        return list(STATE_TRANSITIONS.get(current_state, set()))

    def get_transition_history(self, scene) -> list[dict]:
        """Extract state transitions from a scene's audit log."""
        return [
            entry.details for entry in scene.audit_log
            if entry.action == "STATE_TRANSITION"
        ]

    def get_global_log(self, limit: int = 100) -> list[dict]:
        """Return recent global transition log as dicts."""
        return [
            {
                "scene_id": r.scene_id,
                "from": r.from_state.value,
                "to": r.to_state.value,
                "user_id": r.user_id,
                "timestamp": r.timestamp.isoformat(),
                "guards_passed": r.guards_passed,
            }
            for r in self._transition_log[-limit:]
        ]

    def get_scene_log(self, scene_id: str, limit: int = 50) -> list[dict]:
        """Return transition log filtered to a specific scene."""
        records = [r for r in self._transition_log if r.scene_id == scene_id]
        return [
            {
                "from": r.from_state.value,
                "to": r.to_state.value,
                "user_id": r.user_id,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records[-limit:]
        ]

    def get_state_distribution(self) -> dict[str, int]:
        """Return count of transitions per state pair (for analytics)."""
        from collections import Counter
        counter = Counter(
            (r.from_state.value, r.to_state.value)
            for r in self._transition_log
        )
        return {f"{f}→{t}: {c}" for (f, t), c in counter.items()}

    def is_terminal(self, state: SceneState) -> bool:
        """Check if a state has no outgoing transitions (terminal)."""
        return len(STATE_TRANSITIONS.get(state, set())) == 0

    def can_reach(self, from_state: SceneState, target: SceneState) -> bool:
        """
        BFS check: can we reach target from from_state via valid transitions?
        Useful for planning multi-step transitions.
        """
        visited = set()
        queue = [from_state]
        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(STATE_TRANSITIONS.get(current, set()))
        return False

    def shortest_path(self, from_state: SceneState, target: SceneState) -> Optional[list[SceneState]]:
        """
        BFS shortest path between two states.
        Returns list of states from from_state to target, or None if unreachable.
        """
        if from_state == target:
            return [from_state]

        visited = {from_state}
        queue = [(from_state, [from_state])]

        while queue:
            current, path = queue.pop(0)
            for next_state in STATE_TRANSITIONS.get(current, set()):
                if next_state == target:
                    return path + [next_state]
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))

        return None
