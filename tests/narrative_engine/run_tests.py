"""
Standalone test runner for Narrative Engine.
Bypasses app.py/app/ namespace conflict.
"""
import sys
import os

# Remove current dir from path to avoid app.py conflict
sys.path = [p for p in sys.path if p != '' and p != '.']
# Add project root so 'app' package resolves
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# Clear cached modules
for key in list(sys.modules.keys()):
    if key == 'app' or key.startswith('app.'):
        del sys.modules[key]

# Import directly
from app.narrative_engine.services.narrative_service import NarrativeEngine
from app.narrative_engine.models.scene import SceneObject, Narrative
from app.narrative_engine.models.character import Character, Prop, StoryArc
from app.narrative_engine.crdt.crdt_engine import CRDTEngine, FieldOperation
from app.narrative_engine.services.state_machine import StateMachineService, InvalidTransitionError
from app.shared import SceneState, Role


def test(name, fn):
    try:
        fn()
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def main():
    passed = 0
    total = 0

    # ── Scene CRUD ─────────────────────────────────────────────
    print("\n📦 Scene CRUD:")

    def test_create():
        e = NarrativeEngine()
        s = e.create_scene("Test", user_id="u1")
        assert s.title == "Test"
        assert s.state == SceneState.DRAFT

    def test_get():
        e = NarrativeEngine()
        s = e.create_scene("A", user_id="u1")
        assert e.get_scene(str(s.id)) is not None

    def test_list():
        e = NarrativeEngine()
        e.create_scene("S1", user_id="u1")
        e.create_scene("S2", user_id="u1")
        assert len(e.list_scenes()) == 2

    def test_delete():
        e = NarrativeEngine()
        s = e.create_scene("X", user_id="u1")
        assert e.delete_scene(str(s.id), "u1")

    for n, fn in [("create", test_create), ("get", test_get),
                  ("list", test_list), ("delete", test_delete)]:
        total += 1
        passed += test(n, fn)

    # ── State Machine ──────────────────────────────────────────
    print("\n🔄 State Machine:")

    def test_valid_trans():
        e = NarrativeEngine()
        s = e.create_scene("S", user_id="u1")
        assert e.transition_scene(str(s.id), SceneState.REVIEW, "u1")

    def test_full_lifecycle():
        e = NarrativeEngine()
        s = e.create_scene("S", user_id="u1")
        sid = str(s.id)
        for st in [SceneState.REVIEW, SceneState.LOCKED,
                   SceneState.QUEUED, SceneState.GENERATING,
                   SceneState.COMPLETED]:
            assert e.transition_scene(sid, st, "u1"), f"Failed: {st}"
        assert e.get_scene(sid).state == SceneState.COMPLETED

    def test_invalid_trans():
        e = NarrativeEngine()
        s = e.create_scene("S", user_id="u1")
        try:
            e.transition_scene(str(s.id), SceneState.COMPLETED, "u1")
            assert False, "Should have raised"
        except Exception:
            pass

    for n, fn in [("valid_trans", test_valid_trans),
                  ("full_lifecycle", test_full_lifecycle),
                  ("invalid_trans", test_invalid_trans)]:
        total += 1
        passed += test(n, fn)

    # ── Field Updates & RBAC ───────────────────────────────────
    print("\n🔐 Field Updates & RBAC:")

    def test_update():
        e = NarrativeEngine()
        s = e.create_scene("S", user_id="u1")
        e.update_scene_field(str(s.id), "narrative.beat", "New!", "u1", Role.WRITER)
        assert e.get_scene(str(s.id)).narrative.beat == "New!"

    def test_rbac():
        e = NarrativeEngine()
        s = e.create_scene("S", user_id="u1")
        try:
            e.update_scene_field(str(s.id), "state", "X", "u1", Role.VIEWER)
            assert False
        except PermissionError:
            pass

    for n, fn in [("update", test_update), ("rbac", test_rbac)]:
        total += 1
        passed += test(n, fn)

    # ── Knowledge Graph ────────────────────────────────────────
    print("\n🕸️ Knowledge Graph:")

    def test_graph():
        e = NarrativeEngine()
        c = Character(name="Alice", role_type="protagonist")
        e.graph.upsert_character(c)
        s = e.create_scene("S", user_id="u1")
        s.character_ids = [c.id]
        e.graph.upsert_scene(s)
        assert len(e.graph.get_character_scenes(c.id)) > 0

    def test_ripple():
        e = NarrativeEngine()
        s1 = e.create_scene("S1", user_id="u1")
        s2 = e.create_scene("S2", user_id="u1")
        s2.depends_on = [s1.id]
        e.graph.upsert_scene(s2)
        r = e.graph.get_ripple_effect(str(s1.id))
        assert len(r) >= 1

    for n, fn in [("graph", test_graph), ("ripple", test_ripple)]:
        total += 1
        passed += test(n, fn)

    # ── CRDT ───────────────────────────────────────────────────
    print("\n⚡ CRDT:")

    def test_crdt_lww():
        c = CRDTEngine()
        c.apply_operation(FieldOperation("a", "v1", "u1", timestamp=1.0))
        c.apply_operation(FieldOperation("a", "v2", "u2", timestamp=2.0))
        assert c.get_field_value("a") == "v2"

    def test_crdt_merge():
        c1 = CRDTEngine()
        c2 = CRDTEngine()
        c1.apply_operation(FieldOperation("x", 1, "u1", timestamp=1.0))
        c2.apply_operation(FieldOperation("x", 2, "u2", timestamp=2.0))
        c1.merge(c2)
        assert c1.get_field_value("x") == 2

    for n, fn in [("lww", test_crdt_lww), ("merge", test_crdt_merge)]:
        total += 1
        passed += test(n, fn)

    # ── Branching ──────────────────────────────────────────────
    print("\n🌿 Branching:")

    def test_branch():
        e = NarrativeEngine()
        s = e.create_scene("S", user_id="u1")
        b = e.create_branch(str(s.id), "feat", "u1")
        assert b.branch == "feat"
        assert b.parent_version == s.version

    total += 1
    passed += test("branch", test_branch)

    # ── Novel Adaptation ───────────────────────────────────────
    print("\n📖 Novel Adaptation:")

    def test_adapt():
        e = NarrativeEngine()
        text = "Alice walked in.\n\nBob looked up."
        arc = e.adapt_from_text(text, "Story", "u1")
        assert len(arc.scene_order) == 2

    total += 1
    passed += test("adapt", test_adapt)

    # ── Summary ────────────────────────────────────────────────
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️ {total - passed} failed")
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
