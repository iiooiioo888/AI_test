"""
Character & Prop Models — nodes in the knowledge graph.
"""
from __future__ import annotations
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from app.shared import TimestampedModel


class Character(TimestampedModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    role_type: str = "supporting"  # protagonist, antagonist, supporting, extra
    description: str = ""
    appearance: dict = Field(default_factory=dict)  # visual traits for AI generation
    voice_profile: Optional[dict] = None  # TTS voice settings
    personality_traits: list[str] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)
    # e.g. [{"character_id": "X", "relation": "friend", "strength": 0.8}]


class Prop(TimestampedModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    category: str = "object"  # object, vehicle, weapon, clothing, furniture
    description: str = ""
    visual_style: Optional[str] = None
    associated_character_ids: list[str] = Field(default_factory=list)


class StoryArc(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    genre: str = ""
    logline: str = ""
    theme: Optional[str] = None
    characters: list[Character] = Field(default_factory=list)
    props: list[Prop] = Field(default_factory=list)
    scene_order: list[UUID] = Field(default_factory=list)  # ordered scene IDs

    # Branch management
    branches: dict[str, list[UUID]] = Field(default_factory=dict)
    active_branch: str = "main"

    # Novel adaptation source
    source_text: Optional[str] = None
    source_format: Optional[str] = None  # novel, screenplay, outline
