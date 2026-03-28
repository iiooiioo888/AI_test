"""
場景区生命周期狀態機
嚴格的狀態轉換規則與審計追蹤
"""
from enum import Enum
from typing import Optional, Dict, List, Set
from datetime import datetime
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class SceneStatus(str, Enum):
    """場景区生命周期狀態"""
    DRAFT = "draft"           # 草稿 - 可編輯
    REVIEW = "review"         # 審核中 - 等待審批
    LOCKED = "locked"         # 已鎖定 - 不可修改
    QUEUED = "queued"         # 已排隊 - 等待生成
    GENERATING = "generating" # 生成中 - 正在渲染
    COMPLETED = "completed"   # 已完成 - 生成成功
    FAILED = "failed"         # 失敗 - 需要重試或修改


class StateTransition(BaseModel):
    """狀態轉換記錄"""
    from_status: SceneStatus
    to_status: SceneStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    reason: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class StateMachineConfig(BaseModel):
    """狀態機配置"""
    # 定義合法的狀態轉換
    allowed_transitions: Dict[SceneStatus, List[SceneStatus]] = {
        SceneStatus.DRAFT: [SceneStatus.REVIEW],
        SceneStatus.REVIEW: [SceneStatus.LOCKED, SceneStatus.DRAFT],
        SceneStatus.LOCKED: [SceneStatus.QUEUED],
        SceneStatus.QUEUED: [SceneStatus.GENERATING],
        SceneStatus.GENERATING: [SceneStatus.COMPLETED, SceneStatus.FAILED],
        SceneStatus.FAILED: [SceneStatus.QUEUED, SceneStatus.DRAFT],
        SceneStatus.COMPLETED: [],  # 終端狀態，不可轉換
    }
    
    # 需要特殊權限的轉換
    privileged_transitions: Set[tuple] = {
        (SceneStatus.REVIEW, SceneStatus.LOCKED),  # 只有審核員可以
        (SceneStatus.LOCKED, SceneStatus.QUEUED),  # 只有導演可以
    }
    
    # 自動轉換 (由系統觸發)
    automatic_transitions: Set[tuple] = {
        (SceneStatus.QUEUED, SceneStatus.GENERATING),
        (SceneStatus.GENERATING, SceneStatus.COMPLETED),
        (SceneStatus.GENERATING, SceneStatus.FAILED),
    }


class SceneStateMachine:
    """
    場景区生命周期狀態機
    
    狀態轉換流程：
    DRAFT → REVIEW → LOCKED → QUEUED → GENERATING → COMPLETED
                ↓         ↓                      ↓
              DRAFT     DRAFT                  FAILED → QUEUED
    
    設計理由：
    1. DRAFT: 允許自由編輯，協作階段
    2. REVIEW: 鎖定編輯，等待審核
    3. LOCKED: 審核通過，內容凍結
    4. QUEUED: 加入生成隊列
    5. GENERATING: GPU 正在渲染
    6. COMPLETED: 生成成功
    7. FAILED: 生成失敗，可重試或返回修改
    
    潛在風險：
    - 狀態不一致：需要事務保證
    - 並發轉換：需要分布式鎖
    - 審計遺失：需要預寫日誌
    """
    
    def __init__(self, config: Optional[StateMachineConfig] = None):
        self.config = config or StateMachineConfig()
        self.transition_history: List[StateTransition] = []
    
    def can_transition(self, from_status: SceneStatus, to_status: SceneStatus) -> bool:
        """
        檢查狀態轉換是否合法
        
        Args:
            from_status: 當前狀態
            to_status: 目標狀態
            
        Returns:
            bool: 是否允許轉換
        """
        allowed = self.config.allowed_transitions.get(from_status, [])
        return to_status in allowed
    
    def transition(
        self,
        scene_id: str,
        current_status: SceneStatus,
        target_status: SceneStatus,
        user_id: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        執行狀態轉換
        
        Args:
            scene_id: 場景 ID
            current_status: 當前狀態
            target_status: 目標狀態
            user_id: 操作用戶 ID
            reason: 轉換原因
            metadata: 附加元數據
            
        Returns:
            (success, error_message)
        """
        # 1. 驗證轉換合法性
        if not self.can_transition(current_status, target_status):
            error_msg = f"Illegal transition: {current_status.value} → {target_status.value}"
            logger.warning("state_transition_rejected", scene_id=scene_id, error=error_msg)
            return False, error_msg
        
        # 2. 檢查是否需要特殊權限
        if (current_status, target_status) in self.config.privileged_transitions:
            # TODO: 檢查用戶權限
            # if not user_has_permission(user_id, target_status):
            #     return False, "Insufficient permissions"
            pass
        
        # 3. 創建轉換記錄
        transition = StateTransition(
            from_status=current_status,
            to_status=target_status,
            user_id=user_id,
            reason=reason,
            metadata=metadata or {},
        )
        
        # 4. 記錄歷史
        self.transition_history.append(transition)
        
        # 5. 記錄審計日誌
        logger.info(
            "state_transition_executed",
            scene_id=scene_id,
            from_status=current_status.value,
            to_status=target_status.value,
            user_id=user_id,
            reason=reason,
        )
        
        return True, None
    
    def get_transition_history(self, scene_id: Optional[str] = None) -> List[StateTransition]:
        """獲取狀態轉換歷史"""
        if scene_id:
            # TODO: 從數據庫查詢特定場景的歷史
            pass
        return self.transition_history
    
    def get_available_transitions(self, current_status: SceneStatus) -> List[SceneStatus]:
        """獲取當前狀態可轉換的所有目標狀態"""
        return self.config.allowed_transitions.get(current_status, [])
    
    def is_terminal_state(self, status: SceneStatus) -> bool:
        """檢查是否為終端狀態"""
        return len(self.config.allowed_transitions.get(status, [])) == 0
    
    def is_editable(self, status: SceneStatus) -> bool:
        """檢查狀態是否允許編輯"""
        return status in [SceneStatus.DRAFT, SceneStatus.FAILED]
    
    def is_generating(self, status: SceneStatus) -> bool:
        """檢查是否正在生成"""
        return status in [SceneStatus.QUEUED, SceneStatus.GENERATING]


# ============================================================================
# 狀態機服務 (與數據庫集成)
# ============================================================================

class SceneStateMachineService:
    """
    場景区生命周期服務
    封裝狀態機與數據庫操作
    """
    
    def __init__(self, db_session, state_machine: Optional[SceneStateMachine] = None):
        self.db = db_session
        self.state_machine = state_machine or SceneStateMachine()
    
    async def update_scene_status(
        self,
        scene_id: str,
        target_status: SceneStatus,
        user_id: str,
        reason: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        更新場景狀態 (帶事務)
        
        Args:
            scene_id: 場景 ID
            target_status: 目標狀態
            user_id: 用戶 ID
            reason: 原因
            
        Returns:
            (success, error_message)
        """
        # 1. 查詢當前場景
        # scene = await self.db.scenes.find_by_id(scene_id)
        # if not scene:
        #     return False, "Scene not found"
        
        # current_status = SceneStatus(scene.status)
        
        # 2. 驗證轉換
        # success, error = self.state_machine.transition(
        #     scene_id=scene_id,
        #     current_status=current_status,
        #     target_status=target_status,
        #     user_id=user_id,
        #     reason=reason,
        # )
        
        # if not success:
        #     return False, error
        
        # 3. 更新數據庫 (事務)
        # async with self.db.transaction():
        #     await self.db.scenes.update(
        #         scene_id,
        #         status=target_status.value,
        #         updated_by=user_id,
        #         updated_at=datetime.utcnow(),
        #     )
        
        #     # 如果是 LOCKED → QUEUED，創建生成任務
        #     if target_status == SceneStatus.QUEUED:
        #         await self._create_generation_task(scene_id)
        
        # 4. 觸發事件
        # await self._emit_status_changed_event(scene_id, target_status)
        
        return True, None
    
    async def _create_generation_task(self, scene_id: str):
        """創建視頻生成任務"""
        # TODO: 實現
        pass
    
    async def _emit_status_changed_event(self, scene_id: str, new_status: SceneStatus):
        """觸發狀態變更事件"""
        # TODO: 發布到消息隊列
        pass


# ============================================================================
# 自動狀態機 (用於生成任務)
# ============================================================================

class AutoStateMachine(SceneStateMachine):
    """
    自動狀態機
    用於系統自動觸發的狀態轉換 (如生成完成)
    """
    
    async def auto_complete(self, scene_id: str, user_id: str = "system"):
        """自動完成生成"""
        return self.transition(
            scene_id=scene_id,
            current_status=SceneStatus.GENERATING,
            target_status=SceneStatus.COMPLETED,
            user_id=user_id,
            reason="Generation completed successfully",
        )
    
    async def auto_fail(
        self,
        scene_id: str,
        error_message: str,
        user_id: str = "system",
    ):
        """自動標記失敗"""
        return self.transition(
            scene_id=scene_id,
            current_status=SceneStatus.GENERATING,
            target_status=SceneStatus.FAILED,
            user_id=user_id,
            reason=f"Generation failed: {error_message}",
            metadata={"error": error_message},
        )
