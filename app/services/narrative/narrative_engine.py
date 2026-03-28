"""
敘事引擎 - 統一接口
整合狀態機、知識圖譜、CRDT、RBAC 為一體的敘事引擎
"""
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import structlog

from .scene_state_machine import SceneStateMachine, SceneStatus, SceneStateMachineService
from .knowledge_graph import KnowledgeGraphService, get_knowledge_graph_service
from .crdt_editor import CollaborativeEditingService, get_collaborative_service, CRDTOperation
from ..auth.rbac import RBACService, Permission, Role, get_rbac_service, UserContext

logger = structlog.get_logger()


class NarrativeEngine:
    """
    敘事引擎 - 企業級劇本管理核心
    
    整合功能：
    1. 場景生命周期管理 (狀態機)
    2. 依賴關係分析 (知識圖譜)
    3. 實時協作編輯 (CRDT)
    4. 權限控制 (RBAC)
    
    使用場景：
    - 創建/更新場景
    - 狀態轉換審核
    - 連貫性檢查
    - 漣漪效應分析
    - 多人協作編輯
    """
    
    def __init__(
        self,
        db_session=None,
        state_machine: Optional[SceneStateMachine] = None,
        knowledge_graph: Optional[KnowledgeGraphService] = None,
        crdt_service: Optional[CollaborativeEditingService] = None,
        rbac_service: Optional[RBACService] = None,
    ):
        self.db = db_session
        self.state_machine = state_machine or SceneStateMachine()
        self.knowledge_graph = knowledge_graph or get_knowledge_graph_service()
        self.crdt_service = crdt_service or get_collaborative_service()
        self.rbac_service = rbac_service or get_rbac_service()
    
    # ========================================================================
    # 場景創建與更新
    # ========================================================================
    
    async def create_scene(
        self,
        scene_data: Dict[str, Any],
        user_context: UserContext,
        project_id: str,
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        創建場景
        
        Args:
            scene_data: 場景數據
            user_context: 用戶上下文
            project_id: 項目 ID
            
        Returns:
            (success, error_message, scene_data)
        """
        # 1. 權限檢查
        if not self.rbac_service.check_permission(
            user_context.user_id,
            Permission.SCENE_CREATE,
            resource_type="project",
            resource_id=project_id,
        ):
            return False, "Insufficient permissions to create scene", None
        
        # 2. 創建場景節點 (Neo4j)
        scene_id = scene_data.get("id", f"scene-{datetime.utcnow().timestamp()}")
        await self.knowledge_graph.create_scene(
            scene_id=scene_id,
            title=scene_data.get("title", "Untitled"),
            description=scene_data.get("description", ""),
            project_id=project_id,
            status=SceneStatus.DRAFT.value,
        )
        
        # 3. 初始化 CRDT
        site_id = f"user-{user_context.user_id}"
        crdt = self.crdt_service.join_scene(scene_id, site_id, websocket=None)
        
        # 4. 應用初始數據
        if scene_data.get("title"):
            op = crdt.create_update_operation("scene.title", scene_data["title"])
        if scene_data.get("narrative_text"):
            op = crdt.create_update_operation("scene.narrative_text", scene_data["narrative_text"])
        
        # 5. 保存到 PostgreSQL (TODO)
        # scene = await self.db.scenes.create(...)
        
        logger.info(
            "scene_created",
            scene_id=scene_id,
            project_id=project_id,
            user_id=user_context.user_id,
        )
        
        return True, None, {"id": scene_id, **scene_data}
    
    async def update_scene(
        self,
        scene_id: str,
        updates: Dict[str, Any],
        user_context: UserContext,
    ) -> Tuple[bool, Optional[str]]:
        """
        更新場景 (通過 CRDT)
        
        Args:
            scene_id: 場景 ID
            updates: 更新內容
            user_context: 用戶上下文
            
        Returns:
            (success, error_message)
        """
        # 1. 權限檢查
        if not self.rbac_service.check_permission(
            user_context.user_id,
            Permission.SCENE_UPDATE,
            resource_type="scene",
            resource_id=scene_id,
        ):
            return False, "Insufficient permissions to update scene"
        
        # 2. 檢查場景狀態 (DRAFT 或 FAILED 才可編輯)
        # current_status = await self._get_scene_status(scene_id)
        # if not self.state_machine.is_editable(current_status):
        #     return False, f"Cannot edit scene in {current_status.value} status"
        
        # 3. 應用 CRDT 操作
        site_id = f"user-{user_context.user_id}"
        crdt = self.crdt_service.join_scene(scene_id, site_id, websocket=None)
        
        for field_path, value in updates.items():
            op = crdt.create_update_operation(f"scene.{field_path}", value)
            # TODO: 廣播給其他協作者
            # await self.crdt_service.broadcast_operation(scene_id, op, exclude_site=site_id)
        
        # 4. 更新 PostgreSQL (TODO)
        
        logger.info(
            "scene_updated",
            scene_id=scene_id,
            user_id=user_context.user_id,
            fields=list(updates.keys()),
        )
        
        return True, None
    
    # ========================================================================
    # 狀態轉換
    # ========================================================================
    
    async def transition_scene(
        self,
        scene_id: str,
        target_status: SceneStatus,
        user_context: UserContext,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        轉換場景狀態
        
        Args:
            scene_id: 場景 ID
            target_status: 目標狀態
            user_context: 用戶上下文
            reason: 轉換原因
            
        Returns:
            (success, error_message)
        """
        # 1. 獲取當前狀態
        # current_status = await self._get_scene_status(scene_id)
        current_status = SceneStatus.DRAFT  # TODO: 從數據庫獲取
        
        # 2. 驗證轉換合法性
        success, error = self.state_machine.transition(
            scene_id=scene_id,
            current_status=current_status,
            target_status=target_status,
            user_id=user_context.user_id,
            reason=reason,
        )
        
        if not success:
            return False, error
        
        # 3. 檢查特殊權限
        if (current_status, target_status) in self.state_machine.config.privileged_transitions:
            required_role = {
                (SceneStatus.REVIEW, SceneStatus.LOCKED): Role.DIRECTOR,
                (SceneStatus.LOCKED, SceneStatus.QUEUED): Role.DIRECTOR,
            }.get((current_status, target_status))
            
            if required_role and not user_context.has_role(required_role):
                return False, f"Required role: {required_role.value}"
        
        # 4. 執行轉換 (更新數據庫)
        # await self.db.scenes.update(scene_id, status=target_status.value)
        
        # 5. 觸發後續操作
        if target_status == SceneStatus.QUEUED:
            await self._auto_create_generation_task(scene_id)
        
        logger.info(
            "scene_status_changed",
            scene_id=scene_id,
            from_status=current_status.value,
            to_status=target_status.value,
            user_id=user_context.user_id,
        )
        
        return True, None
    
    async def _auto_create_generation_task(self, scene_id: str):
        """自動創建視頻生成任務"""
        # TODO: 實現
        logger.info("generation_task_created", scene_id=scene_id)
    
    # ========================================================================
    # 漣漪效應分析
    # ========================================================================
    
    async def analyze_impact(self, scene_id: str) -> Dict[str, Any]:
        """
        分析場景變更的影響範圍
        
        Args:
            scene_id: 場景 ID
            
        Returns:
            影響分析結果
        """
        # 從 Neo4j 獲取漣漪效應分析
        analysis = await self.knowledge_graph.analyze_ripple_effect(scene_id)
        
        # 添加狀態信息
        affected_scenes_with_status = []
        for scene in analysis["affected_scenes"]:
            # status = await self._get_scene_status(scene["id"])
            affected_scenes_with_status.append({
                **scene,
                "requires_update": True,
            })
        
        return {
            **analysis,
            "affected_scenes": affected_scenes_with_status,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    # ========================================================================
    # 連貫性檢查
    # ========================================================================
    
    async def check_scene_continuity(self, scene_id: str) -> Dict[str, Any]:
        """
        檢查場景連貫性
        
        Args:
            scene_id: 場景 ID
            
        Returns:
            檢查結果
        """
        return await self.knowledge_graph.check_continuity(scene_id)
    
    # ========================================================================
    # 協作編輯
    # ========================================================================
    
    async def join_collaboration(
        self,
        scene_id: str,
        user_id: str,
        websocket,
    ) -> Dict[str, Any]:
        """
        加入場景協作編輯
        
        Args:
            scene_id: 場景 ID
            user_id: 用戶 ID
            websocket: WebSocket 連接
            
        Returns:
            當前場景狀態
        """
        site_id = f"user-{user_id}"
        crdt = self.crdt_service.join_scene(scene_id, site_id, websocket)
        
        return crdt.get_state()
    
    async def leave_collaboration(self, scene_id: str, user_id: str):
        """離開協作編輯"""
        site_id = f"user-{user_id}"
        self.crdt_service.leave_scene(scene_id, site_id)
    
    async def receive_crdt_operation(
        self,
        scene_id: str,
        operation: Dict,
        user_id: str,
    ) -> bool:
        """
        接收 CRDT 操作
        
        Args:
            scene_id: 場景 ID
            operation: 操作數據
            user_id: 用戶 ID
            
        Returns:
            操作是否成功應用
        """
        return self.crdt_service.apply_remote_operation(scene_id, operation)
    
    # ========================================================================
    # 查詢與統計
    # ========================================================================
    
    async def get_scene_state(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """獲取場景當前狀態"""
        return self.crdt_service.get_scene_state(scene_id)
    
    async def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """獲取項目統計"""
        return await self.knowledge_graph.get_scene_statistics(project_id)
    
    async def get_character_network(self, project_id: str) -> Dict[str, Any]:
        """獲取角色關係網絡"""
        return await self.knowledge_graph.get_character_network(project_id)
    
    # ========================================================================
    # 工具方法
    # ========================================================================
    
    async def _get_scene_status(self, scene_id: str) -> SceneStatus:
        """獲取場景當前狀態"""
        # TODO: 從數據庫查詢
        return SceneStatus.DRAFT
    
    async def cleanup(self):
        """清理資源"""
        await self.knowledge_graph.disconnect()


# ============================================================================
# 工廠函數
# ============================================================================

_narrative_engine_instance: Optional[NarrativeEngine] = None


def get_narrative_engine(db_session=None) -> NarrativeEngine:
    """獲取敘事引擎單例"""
    global _narrative_engine_instance
    if not _narrative_engine_instance:
        _narrative_engine_instance = NarrativeEngine(db_session=db_session)
    return _narrative_engine_instance


async def create_narrative_engine(db_session=None) -> NarrativeEngine:
    """創建新的敘事引擎實例"""
    engine = NarrativeEngine(db_session=db_session)
    await engine.knowledge_graph.connect()
    return engine
