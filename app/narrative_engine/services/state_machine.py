"""
State Machine Service — strict scene lifecycle management.

DRAFT → REVIEW → LOCKED → QUEUED → GENERATING → COMPLETED
                                 ↑              → FAILED → DRAFT
"""
from __future__ import annotations

from app.shared import SceneState, STATE_TRANSITIONS, validate_transition, AuditEntry
from datetime import datetime


class InvalidTransitionError(Exception):
    def __init__(self, from_state: SceneState, to_state: SceneState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition: {from_state.value} → {to_state.value}. "
            f"Valid transitions: {[s.value for s in STATE_TRANSITIONS.get(from_state, set())]}"
        )


class StateMachineService:
    """
    Enforces strict state transitions and manages scene lifecycle.
    """

    def __init__(self):
        self._transition_log: list[dict] = []

    def transition(self, scene, new_state: SceneState, user_id: str) -> bool:
        """
        Attempt a state transition on a scene.
        Raises InvalidTransitionError if the transition is not allowed.
        """
        if not validate_transition(scene.state, new_state):
            raise InvalidTransitionError(scene.state, new_state)

        old_state = scene.state
        scene.state = new_state
        scene.version += 1
        scene.updated_at = datetime.utcnow()

        # Audit trail
        entry = AuditEntry(
            user_id=user_id,
            action="STATE_TRANSITION",
            details={"from": old_state.value, "to": new_state.value},
        )
        scene.audit_log.append(entry)

        # Global transition log
        self._transition_log.append({
            "scene_id": str(scene.id),
            "from": old_state.value,
            "to": new_state.value,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return True

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
        """Return recent global transition log."""
        return self._transition_log[-limit:]
