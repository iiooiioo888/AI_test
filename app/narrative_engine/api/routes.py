"""
Narrative Engine API Routes

Implements the core API contract:
  PATCH  /scenes/{id}           — partial update + ripple analysis → 200 / 409
  GET    /scripts/{id}/graph    — dependency graph JSON → 200
  POST   /scenes/{id}/branch    — create story branch → 201

Plus supplementary endpoints for full scene CRUD, state transitions,
consistency checks, and stats.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.narrative_engine.services.narrative_service import NarrativeEngine
from app.narrative_engine.services.state_machine import StateTransitionError
from app.narrative_engine.services.ripple_analyzer import RippleEffectAnalyzer
from app.shared import SceneState, Role


router = APIRouter(prefix="/narrative", tags=["Narrative Engine"])

# Singleton engine instance (replaced with DI in production)
_engine: Optional[NarrativeEngine] = None
_analyzer: Optional[RippleEffectAnalyzer] = None


def get_engine() -> NarrativeEngine:
    global _engine
    if _engine is None:
        _engine = NarrativeEngine()
    return _engine


def get_analyzer() -> RippleEffectAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = RippleEffectAnalyzer(get_engine().graph)
    return _analyzer


# ── Request / Response Models ──────────────────────────────────

class SceneCreateRequest(BaseModel):
    title: str
    narrative_beat: str = ""
    narrative_desc: str = ""
    emotional_arc: Optional[str] = None
    conflict: Optional[str] = None
    character_ids: list[str] = Field(default_factory=list)
    prop_ids: list[str] = Field(default_factory=list)


class ScenePatchRequest(BaseModel):
    """Partial update — only provided fields are modified."""
    title: Optional[str] = None
    narrative_beat: Optional[str] = None
    narrative_desc: Optional[str] = None
    emotional_arc: Optional[str] = None
    conflict: Optional[str] = None
    visual_setting: Optional[str] = None
    visual_time: Optional[str] = None
    camera_shot: Optional[str] = None
    lighting_style: Optional[str] = None
    action_description: Optional[str] = None
    dialogue: Optional[list[dict]] = None
    character_ids: Optional[list[str]] = None
    prop_ids: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    duration_estimate: Optional[float] = None
    complexity_score: Optional[float] = None
    notes: Optional[str] = None


class TransitionRequest(BaseModel):
    target_state: SceneState
    user_id: str = "system"


class BranchRequest(BaseModel):
    branch_name: str
    user_id: str = "system"


class RippleCheckResponse(BaseModel):
    safe: bool
    conflicts: list[dict] = Field(default_factory=list)
    max_severity: str = "low"
    total_affected: int = 0


# ── Endpoints ──────────────────────────────────────────────────

@router.post("/scenes", status_code=status.HTTP_201_CREATED)
async def create_scene(req: SceneCreateRequest):
    """Create a new scene."""
    engine = get_engine()
    from app.narrative_engine.models.scene import Narrative

    scene = engine.create_scene(
        title=req.title,
        user_id="system",
        narrative=Narrative(
            beat=req.narrative_beat,
            description=req.narrative_desc,
            emotional_arc=req.emotional_arc,
            conflict=req.conflict,
        ),
        character_ids=req.character_ids,
        prop_ids=req.prop_ids,
    )
    return _scene_to_dict(scene)


@router.get("/scenes/{scene_id}")
async def get_scene(scene_id: str):
    """Get scene details."""
    engine = get_engine()
    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {scene_id} not found")
    return _scene_to_dict(scene)


@router.get("/scenes")
async def list_scenes(
    state: Optional[str] = Query(None, description="Filter by state"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
):
    """List all scenes with optional filters."""
    engine = get_engine()
    state_enum = SceneState(state) if state else None
    scenes = engine.list_scenes(state=state_enum, branch=branch)
    return [_scene_to_dict(s) for s in scenes]


@router.patch("/scenes/{scene_id}", status_code=status.HTTP_200_OK)
async def patch_scene(scene_id: str, req: ScenePatchRequest):
    """
    Partially update a scene. Triggers ripple effect analysis.
    Returns 200 on success, 409 if conflicts are detected.
    """
    engine = get_engine()
    analyzer = get_analyzer()

    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {scene_id} not found")

    # Cannot edit completed or generating scenes
    if scene.state in (SceneState.COMPLETED, SceneState.GENERATING):
        raise HTTPException(
            422,
            f"Cannot edit scene in state {scene.state.value}. "
            "Only DRAFT, REVIEW, LOCKED, and FAILED scenes are editable.",
        )

    # Track which fields changed for targeted ripple analysis
    changed_fields = []

    # Apply partial updates
    if req.title is not None:
        scene.title = req.title
        changed_fields.append("title")

    if req.narrative_beat is not None:
        scene.narrative.beat = req.narrative_beat
        changed_fields.append("narrative.beat")

    if req.narrative_desc is not None:
        scene.narrative.description = req.narrative_desc
        changed_fields.append("narrative.description")

    if req.emotional_arc is not None:
        scene.narrative.emotional_arc = req.emotional_arc
        changed_fields.append("narrative.emotional_arc")

    if req.conflict is not None:
        scene.narrative.conflict = req.conflict
        changed_fields.append("narrative.conflict")

    if req.visual_setting is not None:
        scene.visual.setting = req.visual_setting
        changed_fields.append("visual.setting")

    if req.visual_time is not None:
        scene.visual.time_of_day = req.visual_time
        changed_fields.append("visual.time_of_day")

    if req.camera_shot is not None:
        scene.visual.camera.shot_type = req.camera_shot
        changed_fields.append("visual.camera")

    if req.lighting_style is not None:
        scene.visual.lighting.style = req.lighting_style
        changed_fields.append("visual.lighting")

    if req.action_description is not None:
        scene.visual.action_description = req.action_description
        changed_fields.append("visual.action_description")

    if req.dialogue is not None:
        from app.narrative_engine.models.scene import DialogueLine
        scene.dialogue = [DialogueLine(**d) for d in req.dialogue]
        changed_fields.append("dialogue")

    if req.character_ids is not None:
        scene.character_ids = req.character_ids
        changed_fields.append("character_ids")

    if req.prop_ids is not None:
        scene.prop_ids = req.prop_ids
        changed_fields.append("prop_ids")

    if req.tags is not None:
        scene.metadata.tags = req.tags
        changed_fields.append("metadata.tags")

    if req.duration_estimate is not None:
        scene.metadata.duration_estimate = req.duration_estimate
        changed_fields.append("metadata.duration_estimate")

    if req.complexity_score is not None:
        scene.metadata.complexity_score = req.complexity_score
        changed_fields.append("metadata.complexity_score")

    if req.notes is not None:
        scene.metadata.notes = req.notes
        changed_fields.append("metadata.notes")

    # Version bump
    scene.version += 1

    # Audit
    from app.shared import AuditEntry
    scene.audit_log.append(AuditEntry(
        user_id="system",
        action="PATCH",
        details={"changed_fields": changed_fields},
    ))

    # Re-sync to graph
    engine.graph.upsert_scene(scene)

    # Ripple analysis
    ripple_result = analyzer.quick_check(scene_id, changed_fields)
    if ripple_result and ripple_result.get("conflicts"):
        # Return 409 with conflict details
        return {
            "status": "conflict",
            "scene": _scene_to_dict(scene),
            "ripple_analysis": ripple_result,
        }

    return {
        "status": "ok",
        "scene": _scene_to_dict(scene),
        "ripple_analysis": ripple_result,
    }


@router.get("/scripts/{script_id}/graph")
async def get_script_graph(script_id: str):
    """
    Return the dependency graph for a script/project as JSON.
    Includes all scenes, characters, props, and their relationships.
    """
    engine = get_engine()
    graph = engine.graph

    # Build node list
    nodes = []
    for sid, info in graph._scenes.items():
        nodes.append({
            "id": sid,
            "type": "scene",
            "title": info.get("title", ""),
            "state": info.get("state", ""),
        })
    for cid, char in graph._characters.items():
        nodes.append({
            "id": cid,
            "type": "character",
            "name": char.name,
        })
    for pid, prop in graph._props.items():
        nodes.append({
            "id": pid,
            "type": "prop",
            "name": prop.name,
        })

    # Build edge list
    edges = []
    type_map = {
        "FEATURES_CHARACTER": "CONTAINS",
        "USES_PROP": "REQUIRES",
        "DEPENDS_ON": "LEADS_TO",
    }
    for edge in graph._edges:
        edges.append({
            "source": edge["source"],
            "target": edge["target"],
            "type": type_map.get(edge["type"], edge["type"]),
        })

    # Stats
    stats = graph.get_graph_stats()

    return {
        "script_id": script_id,
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
        "orphan_scenes": graph.find_orphan_scenes(),
        "connected_components": len(graph.find_isolated_subgraphs()),
    }


@router.post("/scenes/{scene_id}/branch", status_code=status.HTTP_201_CREATED)
async def create_branch(scene_id: str, req: BranchRequest):
    """
    Create a story branch from a scene.
    Copies the scene and all downstream nodes into a new version branch.
    Returns the new scene with a fresh version ID.
    """
    engine = get_engine()

    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {scene_id} not found")

    branched = engine.create_branch(
        scene_id=scene_id,
        branch_name=req.branch_name,
        user_id=req.user_id,
    )

    return {
        "status": "created",
        "scene": _scene_to_dict(branched),
        "original_scene_id": scene_id,
        "branch_name": req.branch_name,
    }


@router.post("/scenes/{scene_id}/transition")
async def transition_scene(scene_id: str, req: TransitionRequest):
    """
    Attempt a state transition on a scene.
    Raises 422 with diagnostic details on invalid transitions.
    """
    engine = get_engine()

    try:
        engine.transition_scene(scene_id, req.target_state, req.user_id)
        scene = engine.get_scene(scene_id)
        return {
            "status": "ok",
            "scene": _scene_to_dict(scene),
            "valid_next_states": engine.get_valid_next_states(scene_id),
        }
    except StateTransitionError as e:
        raise HTTPException(422, detail=e.to_dict())
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


@router.get("/scenes/{scene_id}/valid-transitions")
async def get_valid_transitions(scene_id: str):
    """Get all valid next states for a scene."""
    engine = get_engine()
    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {scene_id} not found")
    return {
        "scene_id": scene_id,
        "current_state": scene.state.value,
        "valid_transitions": engine.get_valid_next_states(scene_id),
    }


@router.get("/scenes/{scene_id}/impact-analysis")
async def impact_analysis(scene_id: str):
    """
    Full ripple effect analysis for a scene.
    Returns detailed conflict report.
    """
    engine = get_engine()
    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {scene_id} not found")

    consistency = engine.check_scene_consistency(scene_id)
    return consistency


@router.get("/scenes/{scene_id}/graph")
async def get_scene_graph(scene_id: str):
    """
    Get the dependency graph centered on a specific scene.
    Returns upstream/downstream chains and co-appearances.
    """
    engine = get_engine()
    scene = engine.get_scene(scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {scene_id} not found")

    upstream = engine.get_upstream_scenes(scene_id)
    downstream = engine.get_downstream_scenes(scene_id)
    chains = engine.get_dependency_chains(scene_id)

    return {
        "scene_id": scene_id,
        "upstream": upstream,
        "downstream": downstream,
        "dependency_chains": chains,
        "character_co_appearances": engine.get_character_co_appearances(),
    }


@router.get("/consistency/global")
async def global_consistency_check():
    """Run consistency checks across all scenes."""
    engine = get_engine()
    return engine.check_global_consistency()


@router.get("/stats")
async def get_stats():
    """Get engine statistics."""
    engine = get_engine()
    return engine.get_stats()


# ── Helpers ────────────────────────────────────────────────────

def _scene_to_dict(scene) -> dict:
    """Serialize a SceneObject to a JSON-safe dict."""
    return {
        "id": str(scene.id),
        "title": scene.title,
        "state": scene.state.value,
        "version": scene.version,
        "branch": scene.branch,
        "created_at": scene.created_at.isoformat(),
        "updated_at": scene.updated_at.isoformat(),
        "narrative": {
            "beat": scene.narrative.beat,
            "description": scene.narrative.description,
            "emotional_arc": scene.narrative.emotional_arc,
            "conflict": scene.narrative.conflict,
            "outcome": scene.narrative.outcome,
        },
        "dialogue": [
            {
                "character_id": d.character_id,
                "text": d.text,
                "emotion": d.emotion,
                "tone": d.tone,
                "timing": d.timing,
            }
            for d in scene.dialogue
        ],
        "visual": {
            "setting": scene.visual.setting,
            "time_of_day": scene.visual.time_of_day,
            "weather": scene.visual.weather,
            "atmosphere": scene.visual.atmosphere,
            "camera": {
                "shot_type": scene.visual.camera.shot_type,
                "movement": scene.visual.camera.movement,
                "focus_point": scene.visual.camera.focus_point,
                "lens_mm": scene.visual.camera.lens_mm,
            },
            "lighting": {
                "style": scene.visual.lighting.style,
                "key_light": scene.visual.lighting.key_light,
                "mood": scene.visual.lighting.mood,
                "color_temperature": scene.visual.lighting.color_temperature,
            },
            "key_objects": scene.visual.key_objects,
            "action_description": scene.visual.action_description,
            "style_reference": scene.visual.style_reference,
        },
        "audio": {
            "music_style": scene.audio.music_style,
            "ambient": scene.audio.ambient,
            "sfx": scene.audio.sfx,
        },
        "character_ids": scene.character_ids,
        "prop_ids": scene.prop_ids,
        "depends_on": [str(d) for d in scene.depends_on],
        "metadata": {
            "genre": scene.metadata.genre,
            "tags": scene.metadata.tags,
            "duration_estimate": scene.metadata.duration_estimate,
            "complexity_score": scene.metadata.complexity_score,
            "notes": scene.metadata.notes,
        },
        "audit_log": [
            {
                "timestamp": e.timestamp.isoformat(),
                "user_id": e.user_id,
                "action": e.action,
                "details": e.details,
            }
            for e in scene.audit_log[-20:]  # last 20 entries
        ],
        "parent_version": scene.parent_version,
        "generated_video_url": scene.generated_video_url,
    }
