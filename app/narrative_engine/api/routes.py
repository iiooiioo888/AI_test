"""
Narrative Engine API — FastAPI routes.

Enhanced with:
- Undo/Redo endpoints
- Version snapshots
- Dependency chain queries
- Character co-appearance analysis
- Orphan scene detection
- Arc management with reordering
- Conflict log
- Field history
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
    character_ids: list[str] = Field(default_factory=list)
    prop_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


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
    max_scenes: int = 20


class UndoRedoRequest(BaseModel):
    user_id: str = "system"


class SnapshotRequest(BaseModel):
    description: str = ""


class AddToArcRequest(BaseModel):
    scene_id: str
    position: Optional[int] = None


class ReorderArcRequest(BaseModel):
    scene_ids: list[str]


class ArcCreateRequest(BaseModel):
    title: str
    genre: str = ""
    logline: str = ""
    theme: Optional[str] = None


# ── Health & Stats ──────────────────────────────────────────────

@router.get("/health")
async def health():
    engine = get_engine()
    return {"status": "ok", "stats": engine.get_stats()}


# ── Scene CRUD ──────────────────────────────────────────────────

@router.post("/scenes")
async def create_scene(req: CreateSceneRequest):
    engine = get_engine()
    narrative = Narrative(
        beat=req.narrative_beat,
        description=req.narrative_description,
    )
    depends_on_uuids = [UUID(d) for d in req.depends_on] if req.depends_on else []
    scene = engine.create_scene(
        title=req.title,
        user_id=req.user_id,
        narrative=narrative,
        character_ids=req.character_ids,
        prop_ids=req.prop_ids,
        depends_on=depends_on_uuids,
    )
    return {"scene": scene.model_dump(), "id": str(scene.id)}


@router.get("/scenes")
async def list_scenes(state: Optional[SceneState] = None,
                      branch: Optional[str] = None):
    engine = get_engine()
    scenes = engine.list_scenes(state=state, branch=branch)
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


@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str, user_id: str = "system"):
    engine = get_engine()
    if engine.delete_scene(scene_id, user_id):
        return {"status": "deleted"}
    raise HTTPException(404, "Scene not found")


# ── State Transitions ──────────────────────────────────────────

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


# ── Consistency & Impact ────────────────────────────────────────

@router.get("/scenes/{scene_id}/consistency")
async def check_consistency(scene_id: str):
    engine = get_engine()
    return engine.check_scene_consistency(scene_id)


@router.get("/consistency/global")
async def global_consistency():
    engine = get_engine()
    return engine.check_global_consistency()


@router.get("/scenes/{scene_id}/impact-analysis")
async def impact_analysis(scene_id: str):
    engine = get_engine()
    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    return engine.check_scene_consistency(scene_id)


# ── Dependency Chains ───────────────────────────────────────────

@router.get("/scenes/{scene_id}/dependencies")
async def get_dependencies(scene_id: str):
    engine = get_engine()
    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    chains = engine.get_dependency_chains(scene_id)
    upstream = engine.get_upstream_scenes(scene_id)
    downstream = engine.get_downstream_scenes(scene_id)
    return {
        "scene_id": scene_id,
        "dependency_chains": chains,
        "upstream_scenes": upstream,
        "downstream_scenes": downstream,
        "chain_count": len(chains),
    }


@router.get("/orphans")
async def get_orphan_scenes():
    engine = get_engine()
    return {"orphans": engine.get_orphan_scenes()}


# ── Character Analysis ──────────────────────────────────────────

@router.get("/characters/co-appearances")
async def character_co_appearances():
    engine = get_engine()
    return engine.get_character_co_appearances()


# ── Undo / Redo ────────────────────────────────────────────────

@router.post("/undo")
async def undo(req: UndoRedoRequest):
    engine = get_engine()
    result = engine.undo(req.user_id)
    if result is None:
        raise HTTPException(400, "Nothing to undo")
    return {"status": "undone", "operation": result}


@router.post("/redo")
async def redo(req: UndoRedoRequest):
    engine = get_engine()
    result = engine.redo(req.user_id)
    if result is None:
        raise HTTPException(400, "Nothing to redo")
    return {"status": "redone", "operation": result}


@router.get("/undo-status/{user_id}")
async def undo_status(user_id: str):
    engine = get_engine()
    return {
        "can_undo": engine.can_undo(user_id),
        "can_redo": engine.can_redo(user_id),
        "undo_stack": engine.get_undo_stack(user_id),
    }


# ── Version Snapshots ──────────────────────────────────────────

@router.post("/snapshots")
async def create_snapshot(req: SnapshotRequest):
    engine = get_engine()
    return engine.create_snapshot(req.description)


@router.get("/snapshots")
async def list_snapshots():
    engine = get_engine()
    return {"snapshots": engine.get_snapshots()}


# ── Conflict & Field History ───────────────────────────────────

@router.get("/conflicts")
async def conflict_log(limit: int = Query(50, le=200)):
    engine = get_engine()
    return {"conflicts": engine.get_conflict_log()[:limit]}


@router.get("/scenes/{scene_id}/field-history")
async def field_history(scene_id: str, path: str):
    engine = get_engine()
    history = engine.get_field_history(scene_id, path)
    if history is None:
        return {"path": path, "changes": [], "message": "No history for this field"}
    return history


# ── Branching ───────────────────────────────────────────────────

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


@router.get("/branches")
async def list_branches():
    engine = get_engine()
    return {"branches": engine.list_branches()}


# ── Story Arcs ──────────────────────────────────────────────────

@router.post("/arcs")
async def create_arc(req: ArcCreateRequest):
    engine = get_engine()
    arc = engine.create_story_arc(
        title=req.title, genre=req.genre,
        logline=req.logline, theme=req.theme,
    )
    return {"arc": arc.model_dump(), "id": str(arc.id)}


@router.get("/arcs")
async def list_arcs():
    engine = get_engine()
    arcs = engine.list_story_arcs()
    return {"arcs": [a.model_dump() for a in arcs], "total": len(arcs)}


@router.get("/arcs/{arc_id}")
async def get_arc(arc_id: str):
    engine = get_engine()
    arc = engine.get_story_arc(arc_id)
    if not arc:
        raise HTTPException(404, "Story arc not found")
    return arc.model_dump()


@router.post("/arcs/{arc_id}/scenes")
async def add_scene_to_arc(arc_id: str, req: AddToArcRequest):
    engine = get_engine()
    try:
        engine.add_scene_to_arc(arc_id, req.scene_id, req.position)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/arcs/{arc_id}/scenes/{scene_id}")
async def remove_scene_from_arc(arc_id: str, scene_id: str):
    engine = get_engine()
    if engine.remove_scene_from_arc(arc_id, scene_id):
        return {"status": "ok"}
    raise HTTPException(404, "Scene not found in arc")


@router.put("/arcs/{arc_id}/reorder")
async def reorder_arc(arc_id: str, req: ReorderArcRequest):
    engine = get_engine()
    if engine.reorder_arc_scenes(arc_id, req.scene_ids):
        return {"status": "ok"}
    raise HTTPException(400, "Failed to reorder arc scenes")


# ── Novel Adaptation ───────────────────────────────────────────

@router.post("/adapt")
async def adapt_text(req: AdaptTextRequest):
    engine = get_engine()
    arc = engine.adapt_from_text(req.text, req.title, req.user_id, req.max_scenes)
    return {"arc": arc.model_dump(), "id": str(arc.id)}


# ── Graph Stats ────────────────────────────────────────────────

@router.get("/graph/stats")
async def graph_stats():
    engine = get_engine()
    return engine.graph.get_graph_stats()


@router.get("/graph/edges")
async def graph_edges():
    engine = get_engine()
    return {
        "edges": engine.graph._edges,
        "total": len(engine.graph._edges),
    }
