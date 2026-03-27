"""
Scene Object — JSON-structured scene storage.

This is the core data structure of the Narrative Engine.
Scenes are stored as structured JSON, not plain text.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.shared import TimestampedModel, SceneState, AuditEntry


# ── Sub-components ─────────────────────────────────────────────

class DialogueLine(BaseModel):
    character_id: str
    text: str
    emotion: Optional[str] = None
    tone: Optional[str] = None
    timing: Optional[float] = None  # seconds from scene start


class CameraDirection(BaseModel):
    shot_type: str = "medium"  # close_up, medium, wide, aerial, tracking
    movement: Optional[str] = None  # pan, tilt, dolly, crane, steadicam
    focus_point: Optional[str] = None
    lens_mm: Optional[int] = None


class LightingSetup(BaseModel):
    style: str = "natural"  # natural, dramatic, soft, high_key, low_key
    key_light: Optional[str] = None
    mood: Optional[str] = None
    color_temperature: Optional[int] = None  # Kelvin


class VisualDescription(BaseModel):
    """Structured visual description for AI video generation."""
    setting: str = ""
    time_of_day: Optional[str] = None  # morning, noon, dusk, night
    weather: Optional[str] = None
    atmosphere: Optional[str] = None
    camera: CameraDirection = Field(default_factory=CameraDirection)
    lighting: LightingSetup = Field(default_factory=LightingSetup)
    key_objects: list[str] = Field(default_factory=list)
    action_description: str = ""
    style_reference: Optional[str] = None  # reference to art style / film look


class AudioDesign(BaseModel):
    music_style: Optional[str] = None
    ambient: Optional[str] = None
    sfx: list[str] = Field(default_factory=list)
    voiceover: Optional[DialogueLine] = None


class SceneTransition(BaseModel):
    type: str = "cut"  # cut, fade, dissolve, wipe, zoom
    duration: float = 0.0  # seconds
    target_scene_id: Optional[UUID] = None


class SceneMetadata(BaseModel):
    genre: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    duration_estimate: Optional[float] = None  # seconds
    complexity_score: Optional[float] = None  # 0-1
    notes: Optional[str] = None
    custom: dict = Field(default_factory=dict)


class Narrative(BaseModel):
    """Story beat / narrative summary for the scene."""
    beat: str = ""  # one-line story beat
    description: str = ""  # expanded description
    emotional_arc: Optional[str] = None  # tension, relief, joy, etc.
    conflict: Optional[str] = None
    outcome: Optional[str] = None


# ── Main Scene Object ──────────────────────────────────────────

class SceneObject(TimestampedModel):
    """
    Core scene data structure. Stored as JSON, not plain text.
    Every field is structured for machine readability and AI consumption.
    """
    id: UUID = Field(default_factory=uuid4)
    title: str = ""

    # Lifecycle
    state: SceneState = SceneState.DRAFT

    # Narrative
    narrative: Narrative = Field(default_factory=Narrative)
    dialogue: list[DialogueLine] = Field(default_factory=list)

    # Visual
    visual: VisualDescription = Field(default_factory=VisualDescription)

    # Audio
    audio: AudioDesign = Field(default_factory=AudioDesign)

    # Transitions
    entry_transition: Optional[SceneTransition] = None
    exit_transition: Optional[SceneTransition] = None

    # Relationships
    character_ids: list[str] = Field(default_factory=list)
    prop_ids: list[str] = Field(default_factory=list)
    depends_on: list[UUID] = Field(default_factory=list)  # scene dependencies

    # Metadata
    metadata: SceneMetadata = Field(default_factory=SceneMetadata)
    audit_log: list[AuditEntry] = Field(default_factory=list)

    # Versioning
    branch: str = "main"
    parent_version: Optional[int] = None

    # Generated output
    generated_video_url: Optional[str] = None
    generated_preview_url: Optional[str] = None

    def transition_to(self, new_state: SceneState, user_id: str) -> bool:
        from app.shared import validate_transition
        if not validate_transition(self.state, new_state):
            return False
        old_state = self.state
        self.state = new_state
        self.version += 1
        self.audit_log.append(AuditEntry(
            user_id=user_id,
            action="STATE_TRANSITION",
            details={"from": old_state.value, "to": new_state.value},
        ))
        return True
