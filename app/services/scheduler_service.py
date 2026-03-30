"""
排程服務
定時任務、自動化工作流排程、資源調度、發布排程等
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import structlog
import json

logger = structlog.get_logger()


class TaskType(str, Enum):
    """任務類型"""
    SCRIPT_GENERATION = "script_generation"  # AI 腳本生成
    VIDEO_EDITING = "video_editing"  # 視頻剪輯
    VIDEO_RENDERING = "video_rendering"  # 視頻渲染
    ASSET_PROCESSING = "asset_processing"  # 資產處理
    PUBLISHING = "publishing"  # 發布任務
    EXPORT = "export"  # 導出任務
    BACKUP = "backup"  # 備份任務
    ANALYSIS = "analysis"  # 分析任務
    NOTIFICATION = "notification"  # 通知任務
    CUSTOM = "custom"  # 自定義任務


class TaskPriority(str, Enum):
    """任務優先級"""
    LOW = "low"  # 低優先級
    NORMAL = "normal"  # 普通優先級
    HIGH = "high"  # 高優先級
    URGENT = "urgent"  # 緊急優先級


class TaskStatus(str, Enum):
    """任務狀態"""
    PENDING = "pending"  # 等待中
    SCHEDULED = "scheduled"  # 已排程
    QUEUED = "queued"  # 隊列中
    RUNNING = "running"  # 運行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消
    RETRYING = "retrying"  # 重試中


class RecurrenceType(str, Enum):
    """重複類型"""
    NONE = "none"  # 不重複
    DAILY = "daily"  # 每天
    WEEKLY = "weekly"  # 每週
    MONTHLY = "monthly"  # 每月
    CUSTOM = "custom"  # 自定義


@dataclass
class ScheduledTask:
    """排程任務"""
    id: str
    name: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    
    # 排程信息
    scheduled_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: str = "UTC"
    
    # 重複設置
    recurrence: RecurrenceType = RecurrenceType.NONE
    recurrence_config: Optional[Dict[str, Any]] = None
    
    # 任務參數
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 執行配置
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 3600
    
    # 結果
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # 元數據
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "timezone": self.timezone,
            "recurrence": self.recurrence.value,
            "recurrence_config": self.recurrence_config,
            "parameters": self.parameters,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "result": self.result,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SchedulerService:
    """
    排程服務
    
    功能：
    1. AI 腳本生成排程
    2. AI 剪輯建議排程
    3. AI 受眾分析排程
    4. 智能資產管理排程
    5. 視頻渲染排程
    6. 發布排程
    7. 備份排程
    8. 資源調度排程
    9. 定時任務管理
    10. 任務依賴管理
    """
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._max_workers = 10
        
        # 任務回調
        self._callbacks: Dict[str, List] = {}
        
        # 啟動排程器
        asyncio.create_task(self._scheduler_loop())
    
    async def _scheduler_loop(self):
        """排程器主循環"""
        self._running = True
        
        while self._running:
            try:
                # 檢查是否有到期的任務
                await self._check_due_tasks()
                
                # 每 5 秒檢查一次
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error("scheduler_loop_error", error=str(e))
    
    async def _check_due_tasks(self):
        """檢查到期的任務"""
        now = datetime.utcnow()
        
        for task in self._tasks.values():
            if task.status == TaskStatus.SCHEDULED and task.scheduled_time <= now:
                # 任務到期，加入執行隊列
                await self._queue_task(task)
    
    async def _queue_task(self, task: ScheduledTask):
        """將任務加入執行隊列"""
        task.status = TaskStatus.QUEUED
        
        # 優先級數值 (越小優先級越高)
        priority_map = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
        }
        
        priority = priority_map.get(task.priority, 2)
        
        await self._task_queue.put((priority, task.id))
        
        logger.info(
            "task_queued",
            task_id=task.id,
            name=task.name,
            priority=task.priority.value,
        )
    
    async def _execute_task(self, task: ScheduledTask):
        """執行任務"""
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.utcnow()
        
        logger.info(
            "task_started",
            task_id=task.id,
            name=task.name,
            task_type=task.task_type.value,
        )
        
        try:
            # 根據任務類型執行
            result = await self._execute_by_type(task)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.end_time = datetime.utcnow()
            
            logger.info(
                "task_completed",
                task_id=task.id,
                name=task.name,
                duration=(task.end_time - task.start_time).total_seconds(),
            )
            
        except Exception as e:
            task.error_message = str(e)
            logger.error(
                "task_failed",
                task_id=task.id,
                name=task.name,
                error=str(e),
            )
            
            # 檢查是否重試
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                task.scheduled_time = datetime.utcnow() + timedelta(minutes=5)
                
                logger.info(
                    "task_retry_scheduled",
                    task_id=task.id,
                    retry_count=task.retry_count,
                )
            else:
                task.status = TaskStatus.FAILED
                task.end_time = datetime.utcnow()
        
        # 通知回調
        await self._notify_callbacks(task)
        
        # 處理重複任務
        if task.status == TaskStatus.COMPLETED and task.recurrence != RecurrenceType.NONE:
            await self._schedule_next_recurrence(task)
    
    async def _execute_by_type(self, task: ScheduledTask) -> Dict[str, Any]:
        """根據任務類型執行"""
        task_type = task.task_type
        
        if task_type == TaskType.SCRIPT_GENERATION:
            return await self._execute_script_generation(task)
        elif task_type == TaskType.VIDEO_EDITING:
            return await self._execute_video_editing(task)
        elif task_type == TaskType.VIDEO_RENDERING:
            return await self._execute_video_rendering(task)
        elif task_type == TaskType.ASSET_PROCESSING:
            return await self._execute_asset_processing(task)
        elif task_type == TaskType.PUBLISHING:
            return await self._execute_publishing(task)
        elif task_type == TaskType.EXPORT:
            return await self._execute_export(task)
        elif task_type == TaskType.BACKUP:
            return await self._execute_backup(task)
        elif task_type == TaskType.ANALYSIS:
            return await self._execute_analysis(task)
        else:
            return await self._execute_custom(task)
    
    async def _execute_script_generation(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行 AI 腳本生成"""
        from app.services.ai_assistant import get_ai_assistant_service
        
        ai_service = get_ai_assistant_service()
        
        # 從參數獲取腳本生成配置
        prompt = task.parameters.get("prompt", "")
        genre = task.parameters.get("genre", "drama")
        duration = task.parameters.get("duration", 300.0)
        
        # 調用 AI 腳本生成
        script = await ai_service.generate_script(
            prompt=prompt,
            genre=genre,
            duration=duration,
        )
        
        return {
            "script_id": script.id,
            "title": script.title,
            "scenes_count": len(script.scenes),
        }
    
    async def _execute_video_editing(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行 AI 剪輯建議"""
        from app.services.ai_assistant import get_ai_assistant_service
        
        ai_service = get_ai_assistant_service()
        
        project_id = task.parameters.get("project_id")
        clips = task.parameters.get("clips", [])
        
        # 獲取剪輯建議
        suggestions = await ai_service.analyze_and_suggest(project_id, clips)
        
        return {
            "suggestions_count": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
        }
    
    async def _execute_analysis(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行 AI 受眾分析"""
        from app.services.ai_assistant import get_ai_assistant_service
        
        ai_service = get_ai_assistant_service()
        
        script_id = task.parameters.get("script_id")
        platform = task.parameters.get("platform", "youtube")
        
        # 模擬分析結果
        return {
            "script_id": script_id,
            "platform": platform,
            "target_audience": "18-35",
            "engagement_prediction": 0.75,
        }
    
    async def _execute_asset_processing(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行智能資產管理"""
        from app.services.asset_manager import get_asset_manager_service
        
        asset_service = get_asset_manager_service()
        
        action = task.parameters.get("action", "process")
        asset_ids = task.parameters.get("asset_ids", [])
        
        processed_count = 0
        for asset_id in asset_ids:
            asset = asset_service.get_asset(asset_id)
            if asset:
                # 自動生成標籤
                tags = asset_service._auto_generate_tags(asset)
                asset.tags.extend(tags)
                processed_count += 1
        
        return {
            "processed_count": processed_count,
            "asset_ids": asset_ids,
        }
    
    async def _execute_video_rendering(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行視頻渲染"""
        # TODO: 實現視頻渲染邏輯
        return {
            "render_id": task.id,
            "status": "completed",
            "output_path": f"/output/{task.id}.mp4",
        }
    
    async def _execute_publishing(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行發布任務"""
        platform = task.parameters.get("platform", "youtube")
        video_path = task.parameters.get("video_path", "")
        
        # TODO: 實現發布邏輯
        return {
            "platform": platform,
            "video_path": video_path,
            "published_url": f"https://{platform}.com/watch?v={task.id}",
        }
    
    async def _execute_export(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行導出任務"""
        format = task.parameters.get("format", "mp4")
        quality = task.parameters.get("quality", "1080p")
        
        # TODO: 實現導出邏輯
        return {
            "format": format,
            "quality": quality,
            "output_path": f"/exports/{task.id}.{format}",
        }
    
    async def _execute_backup(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行備份任務"""
        backup_type = task.parameters.get("type", "full")
        
        # TODO: 實現備份邏輯
        return {
            "backup_type": backup_type,
            "backup_path": f"/backups/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        }
    
    async def _execute_custom(self, task: ScheduledTask) -> Dict[str, Any]:
        """執行自定義任務"""
        # 調用自定義回調
        callback = task.parameters.get("callback")
        if callback and callable(callback):
            return await callback(task.parameters)
        
        return {"status": "completed"}
    
    async def _notify_callbacks(self, task: ScheduledTask):
        """通知回調"""
        callbacks = self._callbacks.get(task.task_type.value, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error("callback_error", task_id=task.id, error=str(e))
    
    async def _schedule_next_recurrence(self, task: ScheduledTask):
        """安排下一次重複任務"""
        if task.recurrence == RecurrenceType.NONE:
            return
        
        # 計算下一次執行時間
        next_time = self._calculate_next_recurrence(task)
        
        # 創建新任務
        import uuid
        new_task = ScheduledTask(
            id=str(uuid.uuid4()),
            name=task.name,
            description=task.description,
            task_type=task.task_type,
            priority=task.priority,
            status=TaskStatus.SCHEDULED,
            scheduled_time=next_time,
            recurrence=task.recurrence,
            recurrence_config=task.recurrence_config,
            parameters=task.parameters,
            created_by=task.created_by,
        )
        
        self._tasks[new_task.id] = new_task
        
        logger.info(
            "recurrence_scheduled",
            task_id=task.id,
            next_task_id=new_task.id,
            next_time=next_time.isoformat(),
        )
    
    def _calculate_next_recurrence(self, task: ScheduledTask) -> datetime:
        """計算下一次重複時間"""
        now = datetime.utcnow()
        
        if task.recurrence == RecurrenceType.DAILY:
            return now + timedelta(days=1)
        elif task.recurrence == RecurrenceType.WEEKLY:
            return now + timedelta(weeks=1)
        elif task.recurrence == RecurrenceType.MONTHLY:
            return now + timedelta(days=30)
        elif task.recurrence == RecurrenceType.CUSTOM:
            config = task.recurrence_config or {}
            interval = config.get("interval", 1)
            unit = config.get("unit", "hours")
            
            if unit == "hours":
                return now + timedelta(hours=interval)
            elif unit == "days":
                return now + timedelta(days=interval)
            elif unit == "weeks":
                return now + timedelta(weeks=interval)
        
        return now
    
    # ========================================================================
    # 公共 API
    # ========================================================================
    
    async def schedule_task(
        self,
        name: str,
        task_type: TaskType,
        scheduled_time: datetime,
        parameters: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        recurrence: RecurrenceType = RecurrenceType.NONE,
        recurrence_config: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout_seconds: int = 3600,
    ) -> ScheduledTask:
        """
        排程任務
        
        Args:
            name: 任務名稱
            task_type: 任務類型
            scheduled_time: 排程時間
            parameters: 任務參數
            priority: 優先級
            recurrence: 重複類型
            recurrence_config: 重複配置
            max_retries: 最大重試次數
            timeout_seconds: 超時時間
            
        Returns:
            ScheduledTask: 排程任務
        """
        import uuid
        
        task = ScheduledTask(
            id=str(uuid.uuid4()),
            name=name,
            description=f"排程任務：{name}",
            task_type=task_type,
            priority=priority,
            status=TaskStatus.SCHEDULED,
            scheduled_time=scheduled_time,
            parameters=parameters or {},
            recurrence=recurrence,
            recurrence_config=recurrence_config,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        
        self._tasks[task.id] = task
        
        logger.info(
            "task_scheduled",
            task_id=task.id,
            name=name,
            scheduled_time=scheduled_time.isoformat(),
        )
        
        return task
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.RUNNING, TaskStatus.COMPLETED]:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.utcnow()
        
        logger.info("task_cancelled", task_id=task_id)
        return True
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """獲取任務"""
        return self._tasks.get(task_id)
    
    def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        limit: int = 50,
    ) -> List[ScheduledTask]:
        """獲取任務列表"""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        
        # 按排程時間排序
        tasks.sort(key=lambda t: t.scheduled_time, reverse=True)
        
        return tasks[:limit]
    
    def register_callback(self, task_type: str, callback):
        """註冊回調"""
        if task_type not in self._callbacks:
            self._callbacks[task_type] = []
        
        self._callbacks[task_type].append(callback)
        
        logger.info("callback_registered", task_type=task_type)
    
    async def start_workers(self, count: int = 10):
        """啟動工作線程"""
        self._max_workers = count
        
        for i in range(count):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info("workers_started", count=count)
    
    async def _worker(self, worker_id: int):
        """工作線程"""
        while self._running:
            try:
                # 從隊列獲取任務
                priority, task_id = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                
                task = self._tasks.get(task_id)
                if task:
                    await self._execute_task(task)
                
                self._task_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"worker_{worker_id}_error", error=str(e))
    
    def get_queue_status(self) -> Dict[str, Any]:
        """獲取隊列狀態"""
        return {
            "queue_size": self._task_queue.qsize(),
            "running_workers": len([w for w in self._workers if not w.done()]),
            "total_tasks": len(self._tasks),
            "scheduled_tasks": len([t for t in self._tasks.values() if t.status == TaskStatus.SCHEDULED]),
            "running_tasks": len([t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]),
            "completed_tasks": len([t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in self._tasks.values() if t.status == TaskStatus.FAILED]),
        }


# 全局服務實例
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """獲取排程服務單例"""
    global _scheduler_service
    if not _scheduler_service:
        _scheduler_service = SchedulerService()
    return _scheduler_service
