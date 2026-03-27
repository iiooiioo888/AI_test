"""
Narrative Engine Service — orchestrates all sub-services.

Coordinates: Scene CRUD, State Machine, Knowledge Graph, CRDT,
consistency checking, and novel adaptation.
"""
from __future__ import annotations

import json
from typing import Optional
from uuid import UUID, uuid4

from app.narrative_engine.models.scene import SceneObject, Narrative
from app.narrative_engine.models.character import Character, Prop, StoryArc
from app.narrative_engine.graph.knowledge_graph import KnowledgeGraphService
from app.narrative_engine.services.state_machine import StateMachineService
from app.narrative_engine.crdt.crdt_engine import CRDTEngine, FieldOperation
from app.shared import SceneState, Role, FIELD_PERMISSIONS, AuditEntry


class NarrativeEngine:
    """
    Main orchestrator for the narrative pipeline.
    """

    def __init__(self):
        self.graph = KnowledgeGraphService()
        self.state_machine = StateMachineService()
        self.crdt = CRDTEngine()
        self._scenes: dict[str, SceneObject] = {}
        self._arcs: dict[str, StoryArc] = {}

    # ── Scene CRUD ──────────────────────────────────────────────

    def create_scene(self, title: str, user_id: str,
                     narrative: Optional[Narrative] = None) -> SceneObject:
        scene = SceneObject(
            title=title,
            narrative=narrative or Narrative(),
        )
        scene.audit_log.append(AuditEntry(
            user_id=user_id,
            action="CREATE",
            details={"title": title},
        ))
        self._scenes[str(scene.id)] = scene
        self.graph.upsert_scene(scene)
        return scene

    def get_scene(self, scene_id: str) -> Optional[SceneObject]:
        return self._scenes.get(scene_id)

    def list_scenes(self) -> list[SceneObject]:
        return list(self._scenes.values())

    def update_scene_field(self, scene_id: str, path: str,
                           value, user_id: str, role: Role = Role.WRITER) -> bool:
        """
        Field-level update with RBAC permission check and CRDT merge.
        """
        # RBAC check
        if not self._check_field_permission(path, role):
            raise PermissionError(
                f"Role {role.value} cannot edit field: {path}"
            )

        scene = self._scenes.get(scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        # State check: only DRAFT and REVIEW scenes can be edited
        if scene.state not in (SceneState.DRAFT, SceneState.REVIEW):
            raise ValueError(
                f"Cannot edit scene in state {scene.state.value}. "
                f"Only DRAFT and REVIEW scenes are editable."
            )

        # Apply via CRDT
        op = FieldOperation(path=path, value=value, user_id=user_id)
        self.crdt.apply_operation(op)

        # Also apply directly to the scene model
        self._set_scene_field(scene, path, value)
        scene.version += 1
        scene.updated_at = __import__("datetime").datetime.utcnow()

        return True

    def delete_scene(self, scene_id: str, user_id: str) -> bool:
        if scene_id in self._scenes:
            del self._scenes[scene_id]
            return True
        return False

    # ── State Transitions ──────────────────────────────────────

    def transition_scene(self, scene_id: str, new_state: SceneState,
                         user_id: str) -> bool:
        scene = self._scenes.get(scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")
        return self.state_machine.transition(scene, new_state, user_id)

    def get_valid_next_states(self, scene_id: str) -> list[str]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return []
        return [s.value for s in self.state_machine.get_valid_transitions(scene.state)]

    # ── Consistency Checking ───────────────────────────────────

    def check_scene_consistency(self, scene_id: str) -> dict:
        """
        Full consistency check for a scene:
        - Graph integrity (characters/props exist)
        - State transition validity
        - Dependency chain
        - Ripple effect analysis
        """
        scene = self._scenes.get(scene_id)
        if not scene:
            return {"error": "Scene not found"}

        warnings = self.graph.check_consistency(scene)
        ripple = self.graph.get_ripple_effect(scene_id)

        return {
            "scene_id": scene_id,
            "state": scene.state.value,
            "warnings": warnings,
            "ripple_impact": {str(k): v for k, v in ripple.items()},
            "total_affected": sum(len(v) for v in ripple.values()),
        }

    def check_global_consistency(self) -> dict:
        """Check all scenes for consistency issues."""
        all_warnings = {}
        for sid, scene in self._scenes.items():
            warnings = self.graph.check_consistency(scene)
            if warnings:
                all_warnings[sid] = warnings
        return {
            "total_scenes": len(self._scenes),
            "scenes_with_issues": len(all_warnings),
            "issues": all_warnings,
        }

    # ── Story Arc Management ───────────────────────────────────

    def create_story_arc(self, title: str, **kwargs) -> StoryArc:
        arc = StoryArc(title=title, **kwargs)
        self._arcs[str(arc.id)] = arc
        return arc

    def get_story_arc(self, arc_id: str) -> Optional[StoryArc]:
        return self._arcs.get(arc_id)

    # ── Version Branching ──────────────────────────────────────

    def create_branch(self, scene_id: str, branch_name: str,
                      user_id: str) -> SceneObject:
        """Create a new version branch from a scene."""
        scene = self._scenes.get(scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        import copy
        branched = copy.deepcopy(scene)
        branched.id = uuid4()
        branched.branch = branch_name
        branched.parent_version = scene.version
        branched.state = SceneState.DRAFT
        branched.audit_log = [AuditEntry(
            user_id=user_id,
            action="BRANCH",
            details={"from_scene": scene_id, "branch": branch_name},
        )]

        new_id = str(branched.id)
        self._scenes[new_id] = branched
        self.graph.upsert_scene(branched)
        return branched

    # ── Novel Adaptation (Stub) ────────────────────────────────

    def adapt_from_text(self, text: str, title: str,
                        user_id: str) -> StoryArc:
        """
        Parse raw text (novel/screenplay) into structured scenes.
        This is a stub — production would call an LLM for parsing.
        """
        # Simple paragraph-based scene splitting
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        scenes = []

        for i, para in enumerate(paragraphs[:20]):  # cap at 20 scenes
            scene = self.create_scene(
                title=f"{title} - Scene {i+1}",
                user_id=user_id,
                narrative=Narrative(
                    beat=para[:100],
                    description=para,
                ),
            )
            scenes.append(scene)

        arc = self.create_story_arc(
            title=title,
            source_text=text[:5000],  # store preview
            source_format="novel",
            scene_order=[s.id for s in scenes],
        )

        return arc

    # ── Helpers ────────────────────────────────────────────────

    def _check_field_permission(self, path: str, role: Role) -> bool:
        allowed = FIELD_PERMISSIONS.get(role, set())
        if "*" in allowed:
            return True
        return any(path.startswith(prefix) for prefix in allowed)

    @staticmethod
    def _set_scene_field(scene: SceneObject, path: str, value) -> None:
        """Set a nested field on a scene by dot-path."""
        keys = path.split(".")
        obj = scene
        for k in keys[:-1]:
            obj = getattr(obj, k)
        setattr(obj, keys[-1], value)

    def get_stats(self) -> dict:
        return {
            "scenes": len(self._scenes),
            "arcs": len(self._arcs),
            "graph": self.graph.get_graph_stats(),
            "crdt_operations": len(self.crdt.get_operation_log()),
        }
