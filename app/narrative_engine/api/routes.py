"""
Narrative Engine API — FastAPI routes.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.narrative_engine.services.narrative_service import NarrativeEngine
from app.narrative_engine.models.scene import Narrative
from app.shared import SceneState, Role


router = APIRouter(prefix="/api/v1/narrative", tags=["Narrative Engine"])

# Singleton engine instance
_engine = NarrativeEngine()


def get_engine() -> NarrativeEngine:
    return _engine


# ── Request/Response Schemas ────────────────────────────────────

class CreateSceneRequest(BaseModel):
    title: str
    user_id: str = "system"
    narrative_beat: str = ""
    narrative_description: str = ""


class UpdateFieldRequest(BaseModel):
    path: str = Field(..., description="Dot-path, e.g. 'narrative.beat'")
    value: str | dict | list | int | float | bool
    user_id: str = "system"
    role: str = "writer"


class TransitionRequest(BaseModel):
    new_state: SceneState
    user_id: str = "system"


class CreateBranchRequest(BaseModel):
    branch_name: str
    user_id: str = "system"


class AdaptTextRequest(BaseModel):
    text: str
    title: str
    user_id: str = "system"


# ── Routes ─────────────────────────────────────────────────────

@router.get("/health")
async def health():
    engine = get_engine()
    return {"status": "ok", "stats": engine.get_stats()}


@router.post("/scenes")
async def create_scene(req: CreateSceneRequest):
    engine = get_engine()
    narrative = Narrative(
        beat=req.narrative_beat,
        description=req.narrative_description,
    )
    scene = engine.create_scene(
        title=req.title,
        user_id=req.user_id,
        narrative=narrative,
    )
    return {"scene": scene.model_dump(), "id": str(scene.id)}


@router.get("/scenes")
async def list_scenes(state: Optional[SceneState] = None):
    engine = get_engine()
    scenes = engine.list_scenes()
    if state:
        scenes = [s for s in scenes if s.state == state]
    return {
        "scenes": [s.model_dump() for s in scenes],
        "total": len(scenes),
    }


@router.get("/scenes/{scene_id}")
async def get_scene(scene_id: str):
    engine = get_engine()
    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    return scene.model_dump()


@router.patch("/scenes/{scene_id}/field")
async def update_field(scene_id: str, req: UpdateFieldRequest):
    engine = get_engine()
    try:
        role = Role(req.role)
    except ValueError:
        raise HTTPException(400, f"Invalid role: {req.role}")
    try:
        engine.update_scene_field(
            scene_id, req.path, req.value, req.user_id, role
        )
        return {"status": "ok", "path": req.path}
    except (ValueError, PermissionError) as e:
        raise HTTPException(400, str(e))


@router.post("/scenes/{scene_id}/transition")
async def transition_scene(scene_id: str, req: TransitionRequest):
    engine = get_engine()
    try:
        engine.transition_scene(scene_id, req.new_state, req.user_id)
        scene = engine.get_scene(scene_id)
        return {"status": "ok", "new_state": scene.state.value}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/scenes/{scene_id}/valid-transitions")
async def valid_transitions(scene_id: str):
    engine = get_engine()
    return {"transitions": engine.get_valid_next_states(scene_id)}


@router.get("/scenes/{scene_id}/consistency")
async def check_consistency(scene_id: str):
    engine = get_engine()
    return engine.check_scene_consistency(scene_id)


@router.get("/consistency/global")
async def global_consistency():
    engine = get_engine()
    return engine.check_global_consistency()


@router.post("/scenes/{scene_id}/branch")
async def create_branch(scene_id: str, req: CreateBranchRequest):
    engine = get_engine()
    try:
        branched = engine.create_branch(
            scene_id, req.branch_name, req.user_id
        )
        return {"scene": branched.model_dump(), "id": str(branched.id)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/adapt")
async def adapt_text(req: AdaptTextRequest):
    engine = get_engine()
    arc = engine.adapt_from_text(req.text, req.title, req.user_id)
    return {"arc": arc.model_dump(), "id": str(arc.id)}


@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str, user_id: str = "system"):
    engine = get_engine()
    if engine.delete_scene(scene_id, user_id):
        return {"status": "deleted"}
    raise HTTPException(404, "Scene not found")


@router.get("/graph/stats")
async def graph_stats():
    engine = get_engine()
    return engine.graph.get_graph_stats()
