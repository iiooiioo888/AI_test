"""
Tests for the Narrative Engine — Scene, State Machine, Knowledge Graph, CRDT.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from app.narrative_engine.services.narrative_service import NarrativeEngine
from app.narrative_engine.models.scene import SceneObject, Narrative
from app.narrative_engine.models.character import Character, Prop
from app.narrative_engine.crdt.crdt_engine import CRDTEngine, FieldOperation
from app.narrative_engine.services.state_machine import StateMachineService, InvalidTransitionError
from app.shared import SceneState, Role


@pytest.fixture
def engine():
    return NarrativeEngine()


# ── Scene CRUD ──────────────────────────────────────────────────

class TestSceneCRUD:
    def test_create_scene(self, engine):
        scene = engine.create_scene("Test Scene", user_id="user1")
        assert scene.title == "Test Scene"
        assert scene.state == SceneState.DRAFT
        assert scene.version == 1

    def test_get_scene(self, engine):
        scene = engine.create_scene("Scene A", user_id="user1")
        fetched = engine.get_scene(str(scene.id))
        assert fetched is not None
        assert fetched.title == "Scene A"

    def test_list_scenes(self, engine):
        engine.create_scene("S1", user_id="u1")
        engine.create_scene("S2", user_id="u1")
        assert len(engine.list_scenes()) == 2

    def test_delete_scene(self, engine):
        scene = engine.create_scene("Doomed", user_id="u1")
        assert engine.delete_scene(str(scene.id), "u1")
        assert engine.get_scene(str(scene.id)) is None


# ── State Machine ───────────────────────────────────────────────

class TestStateMachine:
    def test_valid_transition_draft_to_review(self, engine):
        scene = engine.create_scene("S1", user_id="u1")
        assert engine.transition_scene(str(scene.id), SceneState.REVIEW, "u1")
        assert engine.get_scene(str(scene.id)).state == SceneState.REVIEW

    def test_full_lifecycle(self, engine):
        scene = engine.create_scene("S1", user_id="u1")
        sid = str(scene.id)
        for state in [SceneState.REVIEW, SceneState.LOCKED,
                      SceneState.QUEUED, SceneState.GENERATING,
                      SceneState.COMPLETED]:
            assert engine.transition_scene(sid, state, "u1")
        assert engine.get_scene(sid).state == SceneState.COMPLETED

    def test_invalid_transition(self, engine):
        scene = engine.create_scene("S1", user_id="u1")
        with pytest.raises(Exception):
            engine.transition_scene(str(scene.id), SceneState.COMPLETED, "u1")

    def test_valid_transitions_query(self, engine):
        scene = engine.create_scene("S1", user_id="u1")
        valid = engine.get_valid_next_states(str(scene.id))
        assert "REVIEW" in valid


# ── Field Updates & RBAC ────────────────────────────────────────

class TestFieldUpdates:
    def test_update_narrative_beat(self, engine):
        scene = engine.create_scene("S1", user_id="u1")
        engine.update_scene_field(
            str(scene.id), "narrative.beat", "New beat", "u1", Role.WRITER
        )
        updated = engine.get_scene(str(scene.id))
        assert updated.narrative.beat == "New beat"

    def test_rbac_denied(self, engine):
        scene = engine.create_scene("S1", user_id="u1")
        with pytest.raises(PermissionError):
            engine.update_scene_field(
                str(scene.id), "state", "LOCKED", "u1", Role.VIEWER
            )


# ── Knowledge Graph ─────────────────────────────────────────────

class TestKnowledgeGraph:
    def test_character_and_scene(self, engine):
        char = Character(name="Alice", role_type="protagonist")
        engine.graph.upsert_character(char)
        scene = engine.create_scene("S1", user_id="u1",
                                     narrative=Narrative(beat="Alice enters"))
        # Manually add character to scene for graph
        scene.character_ids = [char.id]
        engine.graph.upsert_scene(scene)
        scenes = engine.graph.get_character_scenes(char.id)
        assert len(scenes) > 0

    def test_ripple_effect(self, engine):
        s1 = engine.create_scene("S1", user_id="u1")
        s2 = engine.create_scene("S2", user_id="u1")
        s2.depends_on = [s1.id]
        engine.graph.upsert_scene(s2)
        ripple = engine.graph.get_ripple_effect(str(s1.id))
        assert len(ripple) >= 1


# ── CRDT ────────────────────────────────────────────────────────

class TestCRDT:
    def test_apply_and_resolve(self):
        crdt = CRDTEngine()
        op1 = FieldOperation("narrative.beat", "Beat v1", "user1", timestamp=1.0)
        op2 = FieldOperation("narrative.beat", "Beat v2", "user2", timestamp=2.0)
        crdt.apply_operation(op1)
        crdt.apply_operation(op2)
        assert crdt.get_field_value("narrative.beat") == "Beat v2"

    def test_merge(self):
        crdt1 = CRDTEngine()
        crdt2 = CRDTEngine()
        crdt1.apply_operation(FieldOperation("a", 1, "u1", timestamp=1.0))
        crdt2.apply_operation(FieldOperation("a", 2, "u2", timestamp=2.0))
        crdt1.merge(crdt2)
        assert crdt1.get_field_value("a") == 2


# ── Branching ───────────────────────────────────────────────────

class TestBranching:
    def test_create_branch(self, engine):
        scene = engine.create_scene("S1", user_id="u1")
        branched = engine.create_branch(str(scene.id), "feature-x", "u1")
        assert branched.branch == "feature-x"
        assert branched.parent_version == scene.version


# ── Novel Adaptation ────────────────────────────────────────────

class TestAdaptation:
    def test_adapt_text(self, engine):
        text = "Alice walked into the room.\n\nBob looked up surprised."
        arc = engine.adapt_from_text(text, "Test Story", "u1")
        assert len(arc.scene_order) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
