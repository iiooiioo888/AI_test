"""
通知服務
支持郵件、WebSocket、系統通知等多種通知方式
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import structlog
import json

logger = structlog.get_logger()


class NotificationType(str, Enum):
    """通知類型"""
    EMAIL = "email"
    WEBSOCKET = "websocket"
    SYSTEM = "system"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    """通知優先級"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """通知對象"""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    recipient_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "recipient_id": self.recipient_id,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


class NotificationService:
    """
    通知服務
    
    功能：
    1. 郵件通知
    2. WebSocket 實時通知
    3. 系統通知
    4. Slack/Discord 集成
    5. Webhook 回調
    6. 通知模板
    7. 批量通知
    """
    
    def __init__(self):
        self._websocket_connections: Dict[str, List] = {}
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._email_config = {}
        self._slack_config = {}
        self._templates: Dict[str, str] = {}
        
        # 註冊通知模板
        self._register_default_templates()
    
    def _register_default_templates(self):
        """註冊默認通知模板"""
        self._templates = {
            "scene_created": "場景 '{scene_title}' 已創建",
            "scene_updated": "場景 '{scene_title}' 已更新",
            "scene_status_changed": "場景 '{scene_title}' 狀態變更為 {status}",
            "generation_started": "視頻生成已開始 (任務 ID: {task_id})",
            "generation_completed": "視頻生成已完成 (任務 ID: {task_id})",
            "generation_failed": "視頻生成失敗 (任務 ID: {task_id}): {error}",
            "project_shared": "項目 '{project_name}' 已與您共享",
            "comment_added": "有新評論：{comment}",
            "mention": "您被 @{mentioned_by} 提及",
        }
    
    async def send(
        self,
        notification_type: NotificationType,
        recipient_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict] = None,
    ) -> Notification:
        """
        發送通知
        
        Args:
            notification_type: 通知類型
            recipient_id: 接收者 ID
            title: 標題
            message: 消息內容
            priority: 優先級
            data: 附加數據
            
        Returns:
            Notification: 通知對象
        """
        import uuid
        
        notification = Notification(
            id=str(uuid.uuid4()),
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            recipient_id=recipient_id,
            data=data or {},
        )
        
        # 加入隊列
        await self._notification_queue.put(notification)
        
        # 根據類型發送
        if notification_type == NotificationType.WEBSOCKET:
            await self._send_websocket(notification)
        elif notification_type == NotificationType.EMAIL:
            await self._send_email(notification)
        elif notification_type == NotificationType.SYSTEM:
            await self._save_system_notification(notification)
        
        logger.info(
            "notification_sent",
            type=notification_type.value,
            recipient=recipient_id,
            priority=priority.value,
        )
        
        return notification
    
    async def send_template(
        self,
        template_name: str,
        recipient_id: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        **kwargs,
    ) -> Notification:
        """
        使用模板發送通知
        
        Args:
            template_name: 模板名稱
            recipient_id: 接收者 ID
            priority: 優先級
            **kwargs: 模板參數
            
        Returns:
            Notification: 通知對象
        """
        if template_name not in self._templates:
            raise ValueError(f"Template not found: {template_name}")
        
        template = self._templates[template_name]
        message = template.format(**kwargs)
        
        return await self.send(
            notification_type=NotificationType.SYSTEM,
            recipient_id=recipient_id,
            title=template_name.replace("_", " ").title(),
            message=message,
            priority=priority,
            data=kwargs,
        )
    
    async def broadcast(
        self,
        title: str,
        message: str,
        recipient_ids: List[str],
        notification_type: NotificationType = NotificationType.SYSTEM,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ):
        """
        批量發送通知
        
        Args:
            title: 標題
            message: 消息
            recipient_ids: 接收者 ID 列表
            notification_type: 通知類型
            priority: 優先級
        """
        tasks = [
            self.send(notification_type, rid, title, message, priority)
            for rid in recipient_ids
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(
            "notification_broadcast",
            recipients=len(recipient_ids),
            type=notification_type.value,
        )
    
    async def _send_websocket(self, notification: Notification):
        """發送 WebSocket 通知"""
        connections = self._websocket_connections.get(notification.recipient_id, [])
        
        for ws in connections:
            try:
                await ws.send_json(notification.to_dict())
                notification.sent_at = datetime.utcnow()
            except Exception as e:
                logger.error("websocket_send_failed", error=str(e))
    
    async def _send_email(self, notification: Notification):
        """發送郵件通知"""
        # TODO: 實現郵件發送
        # await email_client.send(
        #     to=notification.recipient_id,
        #     subject=notification.title,
        #     body=notification.message,
        #     html=render_email_template(notification),
        # )
        notification.sent_at = datetime.utcnow()
    
    async def _save_system_notification(self, notification: Notification):
        """保存系統通知"""
        # TODO: 保存到數據庫
        # await db.notifications.insert(notification.to_dict())
        notification.sent_at = datetime.utcnow()
    
    def register_websocket(self, user_id: str, websocket):
        """註冊 WebSocket 連接"""
        if user_id not in self._websocket_connections:
            self._websocket_connections[user_id] = []
        
        self._websocket_connections[user_id].append(websocket)
        
        logger.info("websocket_registered", user_id=user_id)
    
    def unregister_websocket(self, user_id: str, websocket):
        """註銷 WebSocket 連接"""
        if user_id in self._websocket_connections:
            self._websocket_connections[user_id] = [
                ws for ws in self._websocket_connections[user_id]
                if ws != websocket
            ]
    
    async def mark_as_read(self, notification_id: str):
        """標記通知為已讀"""
        # TODO: 更新數據庫
        pass
    
    async def get_unread_count(self, user_id: str) -> int:
        """獲取未讀通知數量"""
        # TODO: 從數據庫查詢
        return 0
    
    async def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[Notification]:
        """獲取用戶通知"""
        # TODO: 從數據庫查詢
        return []


# 全局服務實例
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """獲取通知服務單例"""
    global _notification_service
    if not _notification_service:
        _notification_service = NotificationService()
    return _notification_service
