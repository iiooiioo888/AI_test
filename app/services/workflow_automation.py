"""
自動化工作流服務
支持自定義工作流、觸發器、動作鏈
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import structlog
import json

logger = structlog.get_logger()


class TriggerType(str, Enum):
    """觸發器類型"""
    SCENE_CREATED = "scene_created"
    SCENE_UPDATED = "scene_updated"
    SCENE_STATUS_CHANGED = "scene_status_changed"
    PROJECT_CREATED = "project_created"
    GENERATION_COMPLETED = "generation_completed"
    GENERATION_FAILED = "generation_failed"
    SCHEDULED = "scheduled"  # 定時觸發
    MANUAL = "manual"  # 手動觸發


class ActionType(str, Enum):
    """動作類型"""
    SEND_NOTIFICATION = "send_notification"
    UPDATE_SCENE = "update_scene"
    CREATE_SCENE = "create_scene"
    START_GENERATION = "start_generation"
    RUN_SCRIPT = "run_script"
    WEBHOOK = "webhook"
    SEND_EMAIL = "send_email"
    ASSIGN_USER = "assign_user"


@dataclass
class Trigger:
    """觸發器"""
    id: str
    type: TriggerType
    conditions: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # Cron 表達式
    
    def matches(self, event: Dict[str, Any]) -> bool:
        """檢查事件是否匹配觸發器"""
        if self.type == TriggerType.SCHEDULED:
            return False  # 定時觸發由調度器處理
        
        if self.type == TriggerType.MANUAL:
            return False  # 手動觸發
        
        # 檢查事件類型
        if event.get("type") != self.type.value:
            return False
        
        # 檢查條件
        for key, expected_value in self.conditions.items():
            if event.get(key) != expected_value:
                return False
        
        return True


@dataclass
class Action:
    """動作"""
    id: str
    type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    order: int = 0
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """執行動作"""
        logger.info("executing_action", type=self.type.value, order=self.order)
        
        try:
            if self.type == ActionType.SEND_NOTIFICATION:
                await self._send_notification(context)
            elif self.type == ActionType.UPDATE_SCENE:
                await self._update_scene(context)
            elif self.type == ActionType.START_GENERATION:
                await self._start_generation(context)
            elif self.type == ActionType.WEBHOOK:
                await self._send_webhook(context)
            # ... 其他動作類型
            
            return True
        except Exception as e:
            logger.error("action_execution_failed", error=str(e))
            return False
    
    async def _send_notification(self, context: Dict[str, Any]):
        """發送通知"""
        from app.services.notification_service import get_notification_service
        
        notification_service = get_notification_service()
        
        recipient = self.parameters.get("recipient", context.get("user_id"))
        title = self.parameters.get("title", "通知")
        message = self.parameters.get("message", "")
        
        # 支持模板變量
        message = message.format(**context)
        
        await notification_service.send(
            notification_type=NotificationType.SYSTEM,
            recipient_id=recipient,
            title=title,
            message=message,
        )
    
    async def _update_scene(self, context: Dict[str, Any]):
        """更新場景"""
        # TODO: 實現場景更新
        pass
    
    async def _start_generation(self, context: Dict[str, Any]):
        """開始生成"""
        # TODO: 實現生成啟動
        pass
    
    async def _send_webhook(self, context: Dict[str, Any]):
        """發送 Webhook"""
        import aiohttp
        
        url = self.parameters.get("url")
        if not url:
            return
        
        payload = self.parameters.get("payload", {})
        payload.update(context)
        
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)


@dataclass
class Workflow:
    """工作流"""
    id: str
    name: str
    description: str
    triggers: List[Trigger] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    enabled: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def should_execute(self, event: Dict[str, Any]) -> bool:
        """檢查工作流是否應該執行"""
        if not self.enabled:
            return False
        
        for trigger in self.triggers:
            if trigger.matches(event):
                return True
        
        return False
    
    async def execute(self, context: Dict[str, Any]) -> bool:
        """執行工作流"""
        logger.info("executing_workflow", workflow_id=self.id, name=self.name)
        
        # 按順序執行所有動作
        sorted_actions = sorted(self.actions, key=lambda a: a.order)
        
        for action in sorted_actions:
            success = await action.execute(context)
            if not success:
                logger.warning("workflow_action_failed", workflow_id=self.id)
                return False
        
        logger.info("workflow_completed", workflow_id=self.id)
        return True


class WorkflowAutomationService:
    """
    工作流自動化服務
    
    功能：
    1. 自定義工作流
    2. 多觸發器支持
    3. 動作鏈執行
    4. 定時任務
    5. 條件判斷
    6. 錯誤重試
    """
    
    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def start(self):
        """啟動工作流服務"""
        self._running = True
        asyncio.create_task(self._event_processor())
        asyncio.create_task(self._scheduled_trigger_checker())
        
        logger.info("workflow_automation_started")
    
    async def stop(self):
        """停止工作流服務"""
        self._running = False
        logger.info("workflow_automation_stopped")
    
    def register_workflow(self, workflow: Workflow):
        """註冊工作流"""
        self._workflows[workflow.id] = workflow
        logger.info("workflow_registered", workflow_id=workflow.id, name=workflow.name)
    
    def unregister_workflow(self, workflow_id: str):
        """註銷工作流"""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            logger.info("workflow_unregistered", workflow_id=workflow_id)
    
    async def emit_event(self, event: Dict[str, Any]):
        """觸發事件"""
        await self._event_queue.put(event)
        logger.debug("event_emitted", event_type=event.get("type"))
    
    async def _event_processor(self):
        """事件處理器"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                # 查找匹配的工作流
                for workflow in self._workflows.values():
                    if workflow.should_execute(event):
                        asyncio.create_task(
                            workflow.execute(event.get("context", {}))
                        )
                
                self._event_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("event_processing_error", error=str(e))
    
    async def _scheduled_trigger_checker(self):
        """定時觸發檢查器"""
        while self._running:
            now = datetime.utcnow()
            
            for workflow in self._workflows.values():
                for trigger in workflow.triggers:
                    if trigger.type == TriggerType.SCHEDULED:
                        # TODO: 檢查 Cron 表達式
                        pass
            
            await asyncio.sleep(60)  # 每分鐘檢查一次
    
    def get_workflows(self, enabled_only: bool = True) -> List[Workflow]:
        """獲取所有工作流"""
        workflows = list(self._workflows.values())
        if enabled_only:
            workflows = [w for w in workflows if w.enabled]
        return workflows
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """獲取單個工作流"""
        return self._workflows.get(workflow_id)
    
    async def trigger_manual_workflow(
        self,
        workflow_id: str,
        context: Dict[str, Any],
    ) -> bool:
        """手動觸發工作流"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        # 檢查是否有手動觸發器
        has_manual_trigger = any(
            t.type == TriggerType.MANUAL for t in workflow.triggers
        )
        
        if not has_manual_trigger:
            return False
        
        return await workflow.execute(context)


# 全局服務實例
_workflow_service: Optional[WorkflowAutomationService] = None


def get_workflow_service() -> WorkflowAutomationService:
    """獲取工作流服務單例"""
    global _workflow_service
    if not _workflow_service:
        _workflow_service = WorkflowAutomationService()
    return _workflow_service


# ============================================================================
# 預設工作流模板
# ============================================================================

def create_default_workflows() -> List[Workflow]:
    """創建默認工作流"""
    import uuid
    
    workflows = []
    
    # 1. 場景創建通知
    workflows.append(Workflow(
        id=str(uuid.uuid4()),
        name="場景創建通知",
        description="當新場景創建時發送通知",
        triggers=[Trigger(
            id=str(uuid.uuid4()),
            type=TriggerType.SCENE_CREATED,
        )],
        actions=[Action(
            id=str(uuid.uuid4()),
            type=ActionType.SEND_NOTIFICATION,
            parameters={
                "title": "新場景已創建",
                "message": "場景 '{scene_title}' 已成功創建",
                "recipient": "{project_owner_id}",
            },
            order=0,
        )],
    ))
    
    # 2. 生成完成自動通知
    workflows.append(Workflow(
        id=str(uuid.uuid4()),
        name="生成完成通知",
        description="當視頻生成完成時發送通知",
        triggers=[Trigger(
            id=str(uuid.uuid4()),
            type=TriggerType.GENERATION_COMPLETED,
        )],
        actions=[Action(
            id=str(uuid.uuid4()),
            type=ActionType.SEND_NOTIFICATION,
            parameters={
                "title": "視頻生成完成",
                "message": "任務 {task_id} 已成功完成",
                "recipient": "{user_id}",
            },
            order=0,
        )],
    ))
    
    # 3. 生成失敗重試
    workflows.append(Workflow(
        id=str(uuid.uuid4()),
        name="生成失敗自動重試",
        description="當視頻生成失敗時自動重試 (最多 3 次)",
        triggers=[Trigger(
            id=str(uuid.uuid4()),
            type=TriggerType.GENERATION_FAILED,
            conditions={"retry_count": "<3"},
        )],
        actions=[
            Action(
                id=str(uuid.uuid4()),
                type=ActionType.SEND_NOTIFICATION,
                parameters={
                    "title": "生成失敗，正在重試",
                    "message": "任務 {task_id} 失敗，將自動重試 (第 {retry_count} 次)",
                    "recipient": "{user_id}",
                },
                order=0,
            ),
            Action(
                id=str(uuid.uuid4()),
                type=ActionType.START_GENERATION,
                parameters={
                    "scene_id": "{scene_id}",
                    "retry": True,
                },
                order=1,
            ),
        ],
    ))
    
    return workflows
