"""
CRDT 協作編輯單元測試
"""
import pytest
from app.services.narrative.crdt_editor import (
    VectorClock,
    LWWRegister,
    ORSet,
    SceneCRDT,
    CRDTOperation,
    CollaborativeEditingService,
)


class TestVectorClock:
    """向量時鐘測試"""
    
    def test_increment(self):
        """測試時鐘增加"""
        vc = VectorClock()
        vc.increment("node-1")
        assert vc.clocks == {"node-1": 1}
        
        vc.increment("node-1")
        assert vc.clocks == {"node-1": 2}
        
        vc.increment("node-2")
        assert vc.clocks == {"node-1": 2, "node-2": 1}
    
    def test_merge(self):
        """測試時鐘合併"""
        vc1 = VectorClock(clocks={"node-1": 2, "node-2": 1})
        vc2 = VectorClock(clocks={"node-1": 1, "node-2": 3, "node-3": 1})
        
        vc1.merge(vc2)
        
        assert vc1.clocks["node-1"] == 2  # max(2, 1)
        assert vc1.clocks["node-2"] == 3  # max(1, 3)
        assert vc1.clocks["node-3"] == 1  # 新增
    
    def test_happens_before(self):
        """測試 happens-before 關係"""
        vc1 = VectorClock(clocks={"node-1": 1, "node-2": 2})
        vc2 = VectorClock(clocks={"node-1": 2, "node-2": 3})
        
        assert vc1.happens_before(vc2) is True
        assert vc2.happens_before(vc1) is False
    
    def test_concurrent(self):
        """測試並發關係"""
        vc1 = VectorClock(clocks={"node-1": 2, "node-2": 1})
        vc2 = VectorClock(clocks={"node-1": 1, "node-2": 2})
        
        # vc1 和 vc2 是並發的 (互不 happens-before)
        assert vc1.happens_before(vc2) is False
        assert vc2.happens_before(vc1) is False
        assert vc1.concurrent_with(vc2) is True


class TestLWWRegister:
    """Last-Writer-Wins Register 測試"""
    
    def test_set_and_get(self):
        """測試設置和獲取值"""
        reg = LWWRegister()
        
        reg.set("value1", timestamp=1.0, site_id="site-1")
        assert reg.get() == "value1"
        
        reg.set("value2", timestamp=2.0, site_id="site-1")
        assert reg.get() == "value2"
    
    def test_lww_with_later_timestamp(self):
        """測試較晚時間戳勝出"""
        reg = LWWRegister(value="initial", timestamp=1.0, site_id="site-1")
        
        # 較晚時間戳
        reg.set("newer", timestamp=2.0, site_id="site-2")
        assert reg.get() == "newer"
        
        # 較早時間戳 (不會覆蓋)
        reg.set("older", timestamp=0.5, site_id="site-3")
        assert reg.get() == "newer"
    
    def test_lww_with_same_timestamp(self):
        """測試相同時間戳時 site_id 大的勝出"""
        reg = LWWRegister(value="value1", timestamp=1.0, site_id="site-1")
        
        # 相同時間戳，site_id 較大
        reg.set("value2", timestamp=1.0, site_id="site-2")
        assert reg.get() == "value2"
        
        # 相同時間戳，site_id 較小 (不會覆蓋)
        reg.set("value3", timestamp=1.0, site_id="site-0")
        assert reg.get() == "value2"
    
    def test_merge(self):
        """測試合併"""
        reg1 = LWWRegister(value="value1", timestamp=1.0, site_id="site-1")
        reg2 = LWWRegister(value="value2", timestamp=2.0, site_id="site-2")
        
        reg1.merge(reg2)
        assert reg1.get() == "value2"  # reg2 時間戳較晚


class TestORSet:
    """Observed-Remove Set 測試"""
    
    def test_add_and_contains(self):
        """測試添加和包含"""
        orset = ORSet()
        
        tag1 = orset.add("element1", "site-1")
        assert orset.contains("element1") is True
        
        tag2 = orset.add("element2", "site-1")
        assert orset.contains("element2") is True
    
    def test_remove(self):
        """測試移除"""
        orset = ORSet()
        
        orset.add("element1", "site-1")
        assert orset.contains("element1") is True
        
        orset.remove("element1")
        assert orset.contains("element1") is False
    
    def test_add_after_remove(self):
        """測試移除後再次添加"""
        orset = ORSet()
        
        orset.add("element1", "site-1")
        orset.remove("element1")
        assert orset.contains("element1") is False
        
        # 再次添加
        orset.add("element1", "site-2")
        assert orset.contains("element1") is True
    
    def test_merge(self):
        """測試合併"""
        set1 = ORSet()
        set2 = ORSet()
        
        set1.add("a", "site-1")
        set1.add("b", "site-1")
        
        set2.add("c", "site-2")
        set2.add("b", "site-2")
        
        set1.merge(set2)
        
        assert set1.contains("a") is True
        assert set1.contains("b") is True
        assert set1.contains("c") is True
    
    def test_merge_with_removal(self):
        """測試合併包含移除"""
        set1 = ORSet()
        set2 = ORSet()
        
        set1.add("a", "site-1")
        set1.add("b", "site-1")
        
        set2.add("b", "site-2")
        set2.remove("b")  # set2 移除了 b
        
        set1.merge(set2)
        
        # b 被移除
        assert set1.contains("a") is True
        assert set1.contains("b") is False


class TestSceneCRDT:
    """場景 CRDT 測試"""
    
    def test_create_update_operation(self):
        """測試創建更新操作"""
        crdt = SceneCRDT(scene_id="scene-001", site_id="site-1")
        
        op = crdt.create_update_operation("scene.title", "New Title", old_value="Old Title")
        
        assert op.operation_type == "update"
        assert op.field_path == "scene.title"
        assert op.value == "New Title"
        assert op.old_value == "Old Title"
        assert op.site_id == "site-1"
    
    def test_apply_update_operation(self):
        """測試應用更新操作"""
        crdt = SceneCRDT(scene_id="scene-001", site_id="site-1")
        
        op = crdt.create_update_operation("scene.title", "Title V1")
        state = crdt.get_state()
        assert state["title"] == "Title V1"
        
        op2 = crdt.create_update_operation("scene.title", "Title V2")
        state = crdt.get_state()
        assert state["title"] == "Title V2"
    
    def test_idempotency(self):
        """測試冪等性 (同一操作不重複應用)"""
        crdt = SceneCRDT(scene_id="scene-001", site_id="site-1")
        
        op = crdt.create_update_operation("scene.title", "Title V1")
        
        # 再次應用同一操作
        result = crdt.apply_operation(op)
        assert result is False  # 應該返回 False (已應用)
    
    def test_merge_concurrent_updates(self):
        """測試合併並發更新"""
        crdt1 = SceneCRDT(scene_id="scene-001", site_id="site-1")
        crdt2 = SceneCRDT(scene_id="scene-001", site_id="site-2")
        
        # 兩個站點並發更新不同字段
        crdt1.create_update_operation("scene.title", "Title from Site 1")
        crdt2.create_update_operation("scene.description", "Desc from Site 2")
        
        # 合併
        crdt1.merge(crdt2)
        
        state = crdt1.get_state()
        assert state["title"] == "Title from Site 1"
        assert state["description"] == "Desc from Site 2"
    
    def test_get_state(self):
        """測試獲取狀態"""
        crdt = SceneCRDT(scene_id="scene-001", site_id="site-1")
        
        crdt.create_update_operation("scene.title", "Test Title")
        crdt.create_update_operation("scene.description", "Test Description")
        crdt.create_update_operation("scene.narrative_text", "Test Narrative")
        
        state = crdt.get_state()
        
        assert state["scene_id"] == "scene-001"
        assert state["title"] == "Test Title"
        assert state["description"] == "Test Description"
        assert state["narrative_text"] == "Test Narrative"
        assert "vector_clock" in state


class TestCollaborativeEditingService:
    """協作編輯服務測試"""
    
    def test_join_and_leave_scene(self):
        """測試加入和離開場景"""
        service = CollaborativeEditingService()
        
        # 加入
        crdt = service.join_scene("scene-001", "site-1", websocket=None)
        assert crdt is not None
        assert "scene-001" in service.scenes
        assert "scene-001" in service.connections
        
        # 離開
        service.leave_scene("scene-001", "site-1")
        assert "site-1" not in service.connections["scene-001"]
    
    def test_get_scene_state(self):
        """測試獲取場景狀態"""
        service = CollaborativeEditingService()
        
        service.join_scene("scene-001", "site-1", None)
        service.scenes["scene-001"].create_update_operation("scene.title", "Test")
        
        state = service.get_scene_state("scene-001")
        assert state is not None
        assert state["title"] == "Test"
    
    def test_apply_remote_operation(self):
        """測試應用遠程操作"""
        service = CollaborativeEditingService()
        service.join_scene("scene-001", "site-1", None)
        
        # 創建操作
        crdt = service.scenes["scene-001"]
        op = crdt.create_update_operation("scene.title", "Remote Title")
        
        # 應用遠程操作
        result = service.apply_remote_operation("scene-001", op.to_dict())
        assert result is True
        
        # 驗證狀態
        state = service.get_scene_state("scene-001")
        assert state["title"] == "Remote Title"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
