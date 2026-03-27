"""
Enterprise AI Video Production Platform (AVP)
Shared base models, enums, and utilities.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────

class SceneState(str, Enum):
    """Strict scene lifecycle state machine.
    DRAFT → REVIEW → LOCKED → QUEUED → GENERATING → COMPLETED
    """
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    LOCKED = "LOCKED"
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Valid state transitions (adjacency map)
STATE_TRANSITIONS: dict[SceneState, set[SceneState]] = {
    SceneState.DRAFT:      {SceneState.REVIEW},
    SceneState.REVIEW:     {SceneState.DRAFT, SceneState.LOCKED},
    SceneState.LOCKED:     {SceneState.REVIEW, SceneState.QUEUED},
    SceneState.QUEUED:     {SceneState.LOCKED, SceneState.GENERATING},
    SceneState.GENERATING: {SceneState.COMPLETED, SceneState.FAILED},
    SceneState.COMPLETED:  set(),
    SceneState.FAILED:     {SceneState.DRAFT},
}


def validate_transition(from_state: SceneState, to_state: SceneState) -> bool:
    return to_state in STATE_TRANSITIONS.get(from_state, set())


# ── RBAC ───────────────────────────────────────────────────────

class Role(str, Enum):
    ADMIN = "admin"
    DIRECTOR = "director"
    WRITER = "writer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


# Field-level permissions: role → allowed field prefixes
FIELD_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN:    {"*"},
    Role.DIRECTOR: {"*"},
    Role.WRITER:   {"narrative.", "dialogue.", "visual.", "metadata.", "tags"},
    Role.REVIEWER: set(),  # read-only
    Role.VIEWER:   set(),  # read-only
}


# ── Base Models ────────────────────────────────────────────────

class TimestampedModel(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    action: str
    details: Optional[dict[str, Any]] = None
