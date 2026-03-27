"""
Narrative Engine Service — orchestrates all sub-services.

Coordinates: Scene CRUD, State Machine, Knowledge Graph, CRDT,
consistency checking, novel adaptation, undo/redo, and version snapshots.
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
                     narrative: Optional[Narrative] = None,
                     character_ids: Optional[list[str]] = None,
                     prop_ids: Optional[list[str]] = None,
                     depends_on: Optional[list[UUID]] = None) -> SceneObject:
        scene = SceneObject(
            title=title,
            narrative=narrative or Narrative(),
            character_ids=character_ids or [],
            prop_ids=prop_ids or [],
            depends_on=depends_on or [],
        )
        scene.audit_log.append(AuditEntry(
            user_id=user_id,
            action="CREATE",
            details={"title": title},
        ))
        self._scenes[str(scene.id)] = scene
        self.graph.upsert_scene(scene)

        # Sync characters and props to graph
        for cid in scene.character_ids:
            if cid not in self.graph._characters:
                self.graph._characters[cid] = Character(id=cid, name=cid)
        for pid in scene.prop_ids:
            if pid not in self.graph._props:
                self.graph._props[pid] = Prop(id=pid, name=pid)

        return scene

    def get_scene(self, scene_id: str) -> Optional[SceneObject]:
        return self._scenes.get(scene_id)

    def list_scenes(self, state: Optional[SceneState] = None,
                    branch: Optional[str] = None) -> list[SceneObject]:
        scenes = list(self._scenes.values())
        if state:
            scenes = [s for s in scenes if s.state == state]
        if branch:
            scenes = [s for s in scenes if s.branch == branch]
        return scenes

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

        # Audit log
        scene.audit_log.append(AuditEntry(
            user_id=user_id,
            action="FIELD_UPDATE",
            details={"path": path, "value": str(value)[:200]},
        ))

        # Re-sync to graph
        self.graph.upsert_scene(scene)

        return True

    def delete_scene(self, scene_id: str, user_id: str) -> bool:
        if scene_id in self._scenes:
            del self._scenes[scene_id]
            # Remove from graph
            if scene_id in self.graph._scenes:
                del self.graph._scenes[scene_id]
            return True
        return False

    # ── State Transitions ──────────────────────────────────────

    def transition_scene(self, scene_id: str, new_state: SceneState,
                         user_id: str) -> bool:
        scene = self._scenes.get(scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        result = self.state_machine.transition(scene, new_state, user_id)
        if result:
            self.graph.upsert_scene(scene)
        return result

    def get_valid_next_states(self, scene_id: str) -> list[str]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return []
        return [s.value for s in self.state_machine.get_valid_transitions(scene.state)]

    # ── Undo / Redo ────────────────────────────────────────────

    def undo(self, user_id: str) -> Optional[dict]:
        """Undo the last field edit by this user."""
        return self.crdt.undo(user_id)

    def redo(self, user_id: str) -> Optional[dict]:
        """Redo the last undone edit by this user."""
        return self.crdt.redo(user_id)

    def can_undo(self, user_id: str) -> bool:
        return self.crdt.can_undo(user_id)

    def can_redo(self, user_id: str) -> bool:
        return self.crdt.can_redo(user_id)

    def get_undo_stack(self, user_id: str) -> list[dict]:
        return self.crdt.get_undo_stack(user_id)

    # ── Version Snapshots ──────────────────────────────────────

    def create_snapshot(self, description: str = "") -> dict:
        snapshot = self.crdt.create_snapshot(description)
        return {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp,
            "description": snapshot.description,
            "operations_count": snapshot.operations_count,
        }

    def get_snapshots(self) -> list[dict]:
        return self.crdt.get_snapshots()

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
        ripple = self.graph.get_ripple_report(scene_id)

        # Check dependency chains
        chains = self.graph.get_transitive_dependencies(scene_id)

        return {
            "scene_id": scene_id,
            "state": scene.state.value,
            "warnings": warnings,
            "ripple_impact": ripple,
            "dependency_chains": chains,
            "total_affected": ripple.get("total_affected", 0),
            "severity": ripple.get("severity", "low"),
        }

    def check_global_consistency(self) -> dict:
        """Check all scenes for consistency issues."""
        all_warnings = {}
        for sid, scene in self._scenes.items():
            warnings = self.graph.check_consistency(scene)
            if warnings:
                all_warnings[sid] = warnings

        orphans = self.graph.find_orphan_scenes()
        components = self.graph.find_isolated_subgraphs()

        return {
            "total_scenes": len(self._scenes),
            "scenes_with_issues": len(all_warnings),
            "issues": all_warnings,
            "orphan_scenes": orphans,
            "connected_components": len(components),
            "fragmented": len(components) > 1,
        }

    # ── Graph Queries ──────────────────────────────────────────

    def get_dependency_chains(self, scene_id: str) -> list[list[str]]:
        """Get all transitive dependency chains for a scene."""
        return self.graph.get_transitive_dependencies(scene_id)

    def get_upstream_scenes(self, scene_id: str) -> list[str]:
        """Get all scenes this scene transitively depends on."""
        return list(self.graph.get_all_upstream(scene_id))

    def get_downstream_scenes(self, scene_id: str) -> list[str]:
        """Get all scenes that transitively depend on this scene."""
        return list(self.graph.get_all_downstream(scene_id))

    def get_character_co_appearances(self) -> dict:
        """Get characters that appear in the same scenes."""
        return self.graph.get_character_co_appearances()

    def get_orphan_scenes(self) -> list[dict]:
        """Find scenes disconnected from the story."""
        return self.graph.find_orphan_scenes()

    # ── Story Arc Management ───────────────────────────────────

    def create_story_arc(self, title: str, **kwargs) -> StoryArc:
        arc = StoryArc(title=title, **kwargs)
        self._arcs[str(arc.id)] = arc
        return arc

    def get_story_arc(self, arc_id: str) -> Optional[StoryArc]:
        return self._arcs.get(arc_id)

    def list_story_arcs(self) -> list[StoryArc]:
        return list(self._arcs.values())

    def add_scene_to_arc(self, arc_id: str, scene_id: str,
                         position: Optional[int] = None) -> bool:
        """Add a scene to a story arc at a specific position."""
        arc = self._arcs.get(arc_id)
        if not arc:
            raise ValueError(f"Story arc {arc_id} not found")

        scene_uuid = UUID(scene_id) if isinstance(scene_id, str) else scene_id
        if scene_uuid in arc.scene_order:
            # Already in arc, reorder if position specified
            if position is not None:
                arc.scene_order.remove(scene_uuid)
                arc.scene_order.insert(position, scene_uuid)
            return True

        if position is not None:
            arc.scene_order.insert(position, scene_uuid)
        else:
            arc.scene_order.append(scene_uuid)
        return True

    def remove_scene_from_arc(self, arc_id: str, scene_id: str) -> bool:
        """Remove a scene from a story arc."""
        arc = self._arcs.get(arc_id)
        if not arc:
            return False

        scene_uuid = UUID(scene_id) if isinstance(scene_id, str) else scene_id
        if scene_uuid in arc.scene_order:
            arc.scene_order.remove(scene_uuid)
            return True
        return False

    def reorder_arc_scenes(self, arc_id: str,
                           scene_ids: list[str]) -> bool:
        """Reorder all scenes in an arc."""
        arc = self._arcs.get(arc_id)
        if not arc:
            return False

        arc.scene_order = [UUID(sid) if isinstance(sid, str) else sid
                           for sid in scene_ids]
        return True

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

    def list_branches(self) -> dict[str, list[str]]:
        """List all branches and their scene IDs."""
        branches: dict[str, list[str]] = {}
        for sid, scene in self._scenes.items():
            branches.setdefault(scene.branch, []).append(sid)
        return branches

    # ── Novel Adaptation ───────────────────────────────────────

    def adapt_from_text(self, text: str, title: str,
                        user_id: str, max_scenes: int = 20) -> StoryArc:
        """
        Parse raw text (novel/screenplay) into structured scenes.
        Uses intelligent paragraph splitting with dialogue detection.
        """
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        scenes = []

        for i, para in enumerate(paragraphs[:max_scenes]):
            # Detect dialogue patterns
            dialogue_lines = []
            narrative_text = para

            # Simple dialogue detection: lines starting with quotes
            lines = para.split("\n")
            clean_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(('"', "'", "「", "「", "「")):
                    # Extract character name if "Name: dialogue" pattern
                    if ":" in stripped[:30]:
                        parts = stripped.split(":", 1)
                        char_name = parts[0].strip().strip('"\'「「')
                        char_text = parts[1].strip().strip('"\'「「')
                        dialogue_lines.append({
                            "character_id": char_name.lower().replace(" ", "_"),
                            "text": char_text,
                        })
                    else:
                        clean_lines.append(stripped)
                else:
                    clean_lines.append(stripped)

            narrative_text = "\n".join(clean_lines)

            # Build scene
            scene = self.create_scene(
                title=f"{title} - Scene {i+1}",
                user_id=user_id,
                narrative=Narrative(
                    beat=narrative_text[:150] if narrative_text else para[:150],
                    description=narrative_text or para,
                ),
                character_ids=[d["character_id"] for d in dialogue_lines],
            )

            # Add dialogue to scene
            from app.narrative_engine.models.scene import DialogueLine
            for dl in dialogue_lines:
                scene.dialogue.append(DialogueLine(**dl))

            # Set up dependency chain (each scene depends on previous)
            if scenes:
                scene.depends_on = [scenes[-1].id]
                self.graph.upsert_scene(scene)

            scenes.append(scene)

        arc = self.create_story_arc(
            title=title,
            source_text=text[:5000],
            source_format="novel",
            scene_order=[s.id for s in scenes],
        )

        return arc

    # ── Conflict Detection ─────────────────────────────────────

    def get_conflict_log(self) -> list[dict]:
        return self.crdt.get_conflict_log()

    def get_field_history(self, scene_id: str, path: str) -> Optional[dict]:
        """Get the edit history for a specific field."""
        return self.crdt.get_field_diff(path)

    # ── Stats ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "scenes": len(self._scenes),
            "arcs": len(self._arcs),
            "graph": self.graph.get_graph_stats(),
            "crdt_operations": len(self.crdt.get_operation_log()),
            "conflicts": len(self.crdt.get_conflict_log()),
            "snapshots": len(self.crdt.get_snapshots()),
        }

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
