"""
場景狀態機單元測試
"""
import pytest
from datetime import datetime
from app.services.narrative.scene_state_machine import (
    SceneStateMachine,
    SceneStatus,
    StateMachineConfig,
    StateTransition,
)


class TestSceneStateMachine:
    """場景狀態機測試"""
    
    @pytest.fixture
    def state_machine(self):
        """創建狀態機實例"""
        return SceneStateMachine()
    
    def test_initial_state(self, state_machine):
        """測試初始狀態"""
        assert state_machine.transition_history == []
    
    def test_valid_transition_draft_to_review(self, state_machine):
        """測試合法轉換：DRAFT → REVIEW"""
        success, error = state_machine.transition(
            scene_id="scene-001",
            current_status=SceneStatus.DRAFT,
            target_status=SceneStatus.REVIEW,
            user_id="user-001",
            reason="Submit for review",
        )
        
        assert success is True
        assert error is None
        assert len(state_machine.transition_history) == 1
        
        transition = state_machine.transition_history[0]
        assert transition.from_status == SceneStatus.DRAFT
        assert transition.to_status == SceneStatus.REVIEW
        assert transition.user_id == "user-001"
        assert transition.reason == "Submit for review"
    
    def test_invalid_transition_draft_to_locked(self, state_machine):
        """測試非法轉換：DRAFT → LOCKED (跳過 REVIEW)"""
        success, error = state_machine.transition(
            scene_id="scene-001",
            current_status=SceneStatus.DRAFT,
            target_status=SceneStatus.LOCKED,
            user_id="user-001",
        )
        
        assert success is False
        assert error is not None
        assert "Illegal transition" in error
        assert len(state_machine.transition_history) == 0
    
    def test_complete_workflow(self):
        """測試完整工作流程"""
        sm = SceneStateMachine()
        scene_id = "scene-001"
        user_id = "user-001"
        
        # DRAFT → REVIEW
        success, _ = sm.transition(scene_id, SceneStatus.DRAFT, SceneStatus.REVIEW, user_id)
        assert success is True
        
        # REVIEW → LOCKED
        success, _ = sm.transition(scene_id, SceneStatus.REVIEW, SceneStatus.LOCKED, user_id)
        assert success is True
        
        # LOCKED → QUEUED
        success, _ = sm.transition(scene_id, SceneStatus.LOCKED, SceneStatus.QUEUED, user_id)
        assert success is True
        
        # QUEUED → GENERATING
        success, _ = sm.transition(scene_id, SceneStatus.QUEUED, SceneStatus.GENERATING, user_id)
        assert success is True
        
        # GENERATING → COMPLETED
        success, _ = sm.transition(scene_id, SceneStatus.GENERATING, SceneStatus.COMPLETED, user_id)
        assert success is True
        
        # COMPLETED 是終端狀態，不能再轉換
        success, error = sm.transition(scene_id, SceneStatus.COMPLETED, SceneStatus.DRAFT, user_id)
        assert success is False
        assert "Illegal transition" in error
    
    def test_failed_retry_workflow(self):
        """測試失敗重試流程"""
        sm = SceneStateMachine()
        scene_id = "scene-001"
        
        # ... 跳轉到 GENERATING
        for from_status, to_status in [
            (SceneStatus.DRAFT, SceneStatus.REVIEW),
            (SceneStatus.REVIEW, SceneStatus.LOCKED),
            (SceneStatus.LOCKED, SceneStatus.QUEUED),
            (SceneStatus.QUEUED, SceneStatus.GENERATING),
        ]:
            success, _ = sm.transition(scene_id, from_status, to_status, "user-001")
            assert success is True
        
        # GENERATING → FAILED
        success, _ = sm.transition(scene_id, SceneStatus.GENERATING, SceneStatus.FAILED, "user-001")
        assert success is True
        
        # FAILED → QUEUED (重試)
        success, _ = sm.transition(scene_id, SceneStatus.FAILED, SceneStatus.QUEUED, "user-001")
        assert success is True
        
        # FAILED → DRAFT (返回修改)
        # 先回到 FAILED
        sm.transition(scene_id, SceneStatus.QUEUED, SceneStatus.GENERATING, "user-001")
        sm.transition(scene_id, SceneStatus.GENERATING, SceneStatus.FAILED, "user-001")
        
        # FAILED → DRAFT
        success, _ = sm.transition(scene_id, SceneStatus.FAILED, SceneStatus.DRAFT, "user-001")
        assert success is True
    
    def test_get_available_transitions(self, state_machine):
        """測試獲取可用轉換"""
        available = state_machine.get_available_transitions(SceneStatus.DRAFT)
        assert available == [SceneStatus.REVIEW]
        
        available = state_machine.get_available_transitions(SceneStatus.REVIEW)
        assert SceneStatus.LOCKED in available
        assert SceneStatus.DRAFT in available
        
        available = state_machine.get_available_transitions(SceneStatus.COMPLETED)
        assert available == []
    
    def test_is_terminal_state(self, state_machine):
        """測試終端狀態檢查"""
        assert state_machine.is_terminal_state(SceneStatus.COMPLETED) is True
        assert state_machine.is_terminal_state(SceneStatus.DRAFT) is False
    
    def test_is_editable(self, state_machine):
        """測試可編輯狀態檢查"""
        assert state_machine.is_editable(SceneStatus.DRAFT) is True
        assert state_machine.is_editable(SceneStatus.FAILED) is True
        assert state_machine.is_editable(SceneStatus.LOCKED) is False
        assert state_machine.is_editable(SceneStatus.COMPLETED) is False
    
    def test_is_generating(self, state_machine):
        """測試生成中狀態檢查"""
        assert state_machine.is_generating(SceneStatus.QUEUED) is True
        assert state_machine.is_generating(SceneStatus.GENERATING) is True
        assert state_machine.is_generating(SceneStatus.DRAFT) is False
    
    def test_transition_history(self, state_machine):
        """測試轉換歷史記錄"""
        # 執行多次轉換
        state_machine.transition("scene-001", SceneStatus.DRAFT, SceneStatus.REVIEW, "user-001")
        state_machine.transition("scene-001", SceneStatus.REVIEW, SceneStatus.LOCKED, "user-002")
        
        history = state_machine.get_transition_history()
        assert len(history) == 2
        
        # 檢查歷史記錄內容
        assert history[0].from_status == SceneStatus.DRAFT
        assert history[0].to_status == SceneStatus.REVIEW
        assert history[0].user_id == "user-001"
        
        assert history[1].from_status == SceneStatus.REVIEW
        assert history[1].to_status == SceneStatus.LOCKED
        assert history[1].user_id == "user-002"
    
    def test_transition_with_metadata(self, state_machine):
        """測試帶元數據的轉換"""
        success, error = state_machine.transition(
            scene_id="scene-001",
            current_status=SceneStatus.GENERATING,
            target_status=SceneStatus.FAILED,
            user_id="system",
            reason="GPU out of memory",
            metadata={"error_code": "OOM", "gpu_id": 0},
        )
        
        assert success is True
        assert len(state_machine.transition_history) == 1
        
        transition = state_machine.transition_history[0]
        assert transition.metadata["error_code"] == "OOM"
        assert transition.metadata["gpu_id"] == 0


class TestStateMachineConfig:
    """狀態機配置測試"""
    
    def test_default_config(self):
        """測試默認配置"""
        config = StateMachineConfig()
        
        # 檢查所有狀態都有定義
        assert SceneStatus.DRAFT in config.allowed_transitions
        assert SceneStatus.REVIEW in config.allowed_transitions
        assert SceneStatus.LOCKED in config.allowed_transitions
        assert SceneStatus.QUEUED in config.allowed_transitions
        assert SceneStatus.GENERATING in config.allowed_transitions
        assert SceneStatus.COMPLETED in config.allowed_transitions
        assert SceneStatus.FAILED in config.allowed_transitions
    
    def test_custom_config(self):
        """測試自定義配置"""
        custom_transitions = {
            SceneStatus.DRAFT: [SceneStatus.REVIEW, SceneStatus.LOCKED],  # 允許直接鎖定
        }
        
        config = StateMachineConfig(allowed_transitions=custom_transitions)
        sm = SceneStateMachine(config)
        
        # 測試自定義轉換
        success, error = sm.transition(
            scene_id="scene-001",
            current_status=SceneStatus.DRAFT,
            target_status=SceneStatus.LOCKED,
            user_id="user-001",
        )
        
        assert success is True  # 自定義配置允許直接鎖定


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
