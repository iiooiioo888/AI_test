# 🕐 AVP Platform - 排程系統使用指南

**更新日期:** 2026-03-30 22:45  
**版本:** v2.3  
**GitHub:** https://github.com/iiooiioo888/AI_test

---

## 📋 目錄

1. [排程系統概述](#排程系統概述)
2. [任務類型](#任務類型)
3. [優先級](#優先級)
4. [任務狀態](#任務狀態)
5. [重複任務](#重複任務)
6. [使用示例](#使用示例)
7. [API 參考](#api 參考)
8. [最佳實踐](#最佳實踐)

---

## 排程系統概述

AVP Platform 排程系統提供強大的定時任務管理功能，支持：

- ✅ **10 種任務類型** - AI 腳本/剪輯/分析/資產/渲染/發布等
- ✅ **4 級優先級** - Low/Normal/High/Urgent
- ✅ **8 種任務狀態** - 完整生命周期管理
- ✅ **重複任務** - 每日/每週/每月/自定義
- ✅ **自動重試** - 失敗自動重試最多 3 次
- ✅ **超時控制** - 可配置任務超時時間
- ✅ **回調通知** - 任務完成通知
- ✅ **多工作線程** - 10 個並發工作線程
- ✅ **任務隊列** - 優先級隊列管理
- ✅ **實時狀態** - 實時查詢隊列狀態

---

## 任務類型

### TaskType 列舉

```python
class TaskType(str, Enum):
    SCRIPT_GENERATION = "script_generation"    # AI 腳本生成
    VIDEO_EDITING = "video_editing"            # 視頻剪輯
    VIDEO_RENDERING = "video_rendering"        # 視頻渲染
    ASSET_PROCESSING = "asset_processing"      # 資產處理
    PUBLISHING = "publishing"                  # 發布任務
    EXPORT = "export"                          # 導出任務
    BACKUP = "backup"                          # 備份任務
    ANALYSIS = "analysis"                      # 分析任務
    NOTIFICATION = "notification"              # 通知任務
    CUSTOM = "custom"                          # 自定義任務
```

### 各類型說明

| 類型 | 說明 | 典型用途 |
|------|------|---------|
| **script_generation** | AI 腳本生成 | 定時生成劇本 |
| **video_editing** | 視頻剪輯 | 批量剪輯任務 |
| **video_rendering** | 視頻渲染 | 排隊渲染 |
| **asset_processing** | 資產處理 | 批量標籤生成 |
| **publishing** | 發布任務 | 定時發布視頻 |
| **export** | 導出任務 | 批量導出 |
| **backup** | 備份任務 | 定時備份 |
| **analysis** | 分析任務 | 受眾分析 |
| **notification** | 通知任務 | 定時通知 |
| **custom** | 自定義 | 特殊需求 |

---

## 優先級

### TaskPriority 列舉

```python
class TaskPriority(str, Enum):
    LOW = "low"        # 低優先級
    NORMAL = "normal"  # 普通優先級
    HIGH = "high"      # 高優先級
    URGENT = "urgent"  # 緊急優先級
```

### 優先級說明

| 優先級 | 說明 | 適用場景 |
|--------|------|---------|
| **LOW** | 低優先級 | 備份、歸檔等非緊急任務 |
| **NORMAL** | 普通優先級 | 一般任務 |
| **HIGH** | 高優先級 | 客戶緊急需求 |
| **URGENT** | 緊急優先級 | 系統關鍵任務 |

---

## 任務狀態

### TaskStatus 列舉

```python
class TaskStatus(str, Enum):
    PENDING = "pending"      # 等待中
    SCHEDULED = "scheduled"  # 已排程
    QUEUED = "queued"        # 隊列中
    RUNNING = "running"      # 運行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失敗
    CANCELLED = "cancelled"  # 已取消
    RETRYING = "retrying"    # 重試中
```

### 狀態流程圖

```
PENDING → SCHEDULED → QUEUED → RUNNING → COMPLETED
                                    ↓
                                  FAILED → RETRYING → QUEUED
                                    ↓
                                CANCELLED
```

---

## 重複任務

### RecurrenceType 列舉

```python
class RecurrenceType(str, Enum):
    NONE = "none"      # 不重複
    DAILY = "daily"    # 每天
    WEEKLY = "weekly"  # 每週
    MONTHLY = "monthly"# 每月
    CUSTOM = "custom"  # 自定義
```

### 重複配置

```python
# 每天執行
recurrence=RecurrenceType.DAILY

# 每週執行
recurrence=RecurrenceType.WEEKLY

# 每月執行
recurrence=RecurrenceType.MONTHLY

# 自定義 (每 6 小時)
recurrence=RecurrenceType.CUSTOM,
recurrence_config={
    "interval": 6,
    "unit": "hours",
}
```

---

## 使用示例

### 1. AI 腳本生成排程

```python
from app.services.scheduler_service import (
    get_scheduler_service,
    TaskType,
    TaskPriority,
    RecurrenceType,
)
from datetime import datetime, timedelta

scheduler = get_scheduler_service()

# 示例 1: 定時生成腳本 (明天上午 10 點)
task = await scheduler.schedule_task(
    name="生成動作片腳本",
    task_type=TaskType.SCRIPT_GENERATION,
    scheduled_time=datetime.utcnow() + timedelta(days=1, hours=10),
    parameters={
        "prompt": "一個關於英雄救世的故事",
        "genre": "action",
        "duration": 300.0,
    },
    priority=TaskPriority.NORMAL,
)

print(f"任務 ID: {task.id}")
print(f"排程時間：{task.scheduled_time}")

# 示例 2: 每天自动生成腳本
task = await scheduler.schedule_task(
    name="每日腳本生成",
    task_type=TaskType.SCRIPT_GENERATION,
    scheduled_time=datetime.utcnow().replace(hour=9, minute=0),
    parameters={
        "prompt": "每日創意腳本",
        "genre": "drama",
        "duration": 180.0,
    },
    recurrence=RecurrenceType.DAILY,
)
```

### 2. AI 剪輯建議排程

```python
# 定時分析剪輯建議
task = await scheduler.schedule_task(
    name="分析項目剪輯建議",
    task_type=TaskType.VIDEO_EDITING,
    scheduled_time=datetime.utcnow() + timedelta(hours=1),
    parameters={
        "project_id": "proj-001",
        "clips": [...],  # 片段列表
    },
    priority=TaskPriority.HIGH,
)
```

### 3. AI 受眾分析排程

```python
# 每週分析受眾
task = await scheduler.schedule_task(
    name="每週受眾分析",
    task_type=TaskType.ANALYSIS,
    scheduled_time=datetime.utcnow().replace(hour=8, minute=0),
    parameters={
        "script_id": "script-001",
        "platform": "youtube",
    },
    recurrence=RecurrenceType.WEEKLY,
)
```

### 4. 智能資產管理排程

```python
# 批量處理資產 (每 6 小時)
task = await scheduler.schedule_task(
    name="資產標籤處理",
    task_type=TaskType.ASSET_PROCESSING,
    scheduled_time=datetime.utcnow(),
    parameters={
        "action": "process",
        "asset_ids": ["asset-001", "asset-002", ...],
    },
    recurrence=RecurrenceType.CUSTOM,
    recurrence_config={
        "interval": 6,
        "unit": "hours",
    },
)
```

### 5. 視頻渲染排程

```python
# 排隊渲染 (夜間渲染)
task = await scheduler.schedule_task(
    name="夜間批量渲染",
    task_type=TaskType.VIDEO_RENDERING,
    scheduled_time=datetime.utcnow().replace(hour=2, minute=0),
    parameters={
        "project_id": "proj-001",
        "quality": "4k",
        "format": "mp4",
    },
    priority=TaskPriority.NORMAL,
)
```

### 6. 發布排程

```python
# 定時發布到多個平台
platforms = ["youtube", "tiktok", "instagram"]

for platform in platforms:
    task = await scheduler.schedule_task(
        name=f"發布到{platform}",
        task_type=TaskType.PUBLISHING,
        scheduled_time=datetime.utcnow() + timedelta(days=1),
        parameters={
            "platform": platform,
            "video_path": "/output/final.mp4",
            "title": "視頻標題",
            "description": "視頻描述",
        },
        priority=TaskPriority.HIGH if platform == "youtube" else TaskPriority.NORMAL,
    )
```

### 7. 備份排程

```python
# 每天備份
task = await scheduler.schedule_task(
    name="每日備份",
    task_type=TaskType.BACKUP,
    scheduled_time=datetime.utcnow().replace(hour=3, minute=0),
    parameters={
        "type": "full",
        "backup_path": "/backups",
    },
    recurrence=RecurrenceType.DAILY,
)

# 每週完整備份
task = await scheduler.schedule_task(
    name="每週完整備份",
    task_type=TaskType.BACKUP,
    scheduled_time=datetime.utcnow().replace(hour=2, minute=0),
    parameters={
        "type": "full",
        "include_assets": True,
        "include_projects": True,
    },
    recurrence=RecurrenceType.WEEKLY,
)
```

### 8. 任務管理

```python
# 獲取任務
task = scheduler.get_task(task_id)
print(f"任務狀態：{task.status}")
print(f"排程時間：{task.scheduled_time}")

# 獲取任務列表
tasks = scheduler.get_tasks(
    status=TaskStatus.SCHEDULED,
    task_type=TaskType.SCRIPT_GENERATION,
    limit=50,
)

# 取消任務
success = await scheduler.cancel_task(task_id)
if success:
    print("任務已取消")

# 獲取隊列狀態
status = scheduler.get_queue_status()
print(f"隊列大小：{status['queue_size']}")
print(f"運行中任務：{status['running_tasks']}")
print(f"已完成任務：{status['completed_tasks']}")
```

### 9. 回調通知

```python
# 註冊回調函數
def on_script_completed(task):
    print(f"腳本生成完成：{task.result}")

def on_task_failed(task):
    print(f"任務失敗：{task.error_message}")

# 註冊到對應任務類型
scheduler.register_callback("script_generation", on_script_completed)
scheduler.register_callback("video_editing", on_script_completed)
scheduler.register_callback("script_generation", on_task_failed)
```

### 10. 複雜排程場景

```python
# 場景：完整工作流排程
# 1. 早上 9 點：生成腳本
# 2. 早上 10 點：分析剪輯建議
# 3. 中午 12 點：開始渲染
# 4. 下午 6 點：發布到平台

base_time = datetime.utcnow().replace(hour=9, minute=0)

# 腳本生成
await scheduler.schedule_task(
    name="生成腳本",
    task_type=TaskType.SCRIPT_GENERATION,
    scheduled_time=base_time,
    parameters={"prompt": "...", "genre": "action"},
)

# 剪輯建議 (1 小時後)
await scheduler.schedule_task(
    name="剪輯建議",
    task_type=TaskType.VIDEO_EDITING,
    scheduled_time=base_time + timedelta(hours=1),
    parameters={"project_id": "proj-001"},
)

# 開始渲染 (3 小時後)
await scheduler.schedule_task(
    name="渲染視頻",
    task_type=TaskType.VIDEO_RENDERING,
    scheduled_time=base_time + timedelta(hours=3),
    parameters={"quality": "4k"},
)

# 發布 (9 小時後)
await scheduler.schedule_task(
    name="發布視頻",
    task_type=TaskType.PUBLISHING,
    scheduled_time=base_time + timedelta(hours=9),
    parameters={"platform": "youtube"},
)
```

---

## API 參考

### schedule_task

```python
async def schedule_task(
    name: str,                              # 任務名稱
    task_type: TaskType,                    # 任務類型
    scheduled_time: datetime,               # 排程時間
    parameters: Optional[Dict] = None,      # 任務參數
    priority: TaskPriority = NORMAL,        # 優先級
    recurrence: RecurrenceType = NONE,      # 重複類型
    recurrence_config: Optional[Dict] = None,  # 重複配置
    max_retries: int = 3,                   # 最大重試
    timeout_seconds: int = 3600,            # 超時時間
) -> ScheduledTask
```

### cancel_task

```python
async def cancel_task(task_id: str) -> bool
```

### get_task

```python
def get_task(task_id: str) -> Optional[ScheduledTask]
```

### get_tasks

```python
def get_tasks(
    status: Optional[TaskStatus] = None,
    task_type: Optional[TaskType] = None,
    limit: int = 50,
) -> List[ScheduledTask]
```

### get_queue_status

```python
def get_queue_status() -> Dict[str, Any]
```

### register_callback

```python
def register_callback(task_type: str, callback)
```

---

## 最佳實踐

### 1. 合理設置優先級

```python
# ✅ 好的做法
TaskPriority.URGENT  # 僅用於關鍵任務
TaskPriority.HIGH    # 客戶緊急需求
TaskPriority.NORMAL  # 一般任務
TaskPriority.LOW     # 備份等不緊急任務

# ❌ 避免：所有任務都用 HIGH
```

### 2. 設置合理的超時時間

```python
# 根據任務類型設置
timeout_seconds=300      # 簡單任務 (5 分鐘)
timeout_seconds=3600     # 一般任務 (1 小時)
timeout_seconds=7200     # 複雜任務 (2 小時)
```

### 3. 使用重複任務

```python
# ✅ 好的做法：每天備份
recurrence=RecurrenceType.DAILY

# ✅ 好的做法：每週分析
recurrence=RecurrenceType.WEEKLY

# ❌ 避免：手動創建大量重複任務
```

### 4. 監控隊列狀態

```python
# 定期檢查隊列
status = scheduler.get_queue_status()

if status['queue_size'] > 100:
    print("警告：隊列積壓")

if status['failed_tasks'] > 10:
    print("警告：大量任務失敗")
```

### 5. 使用回調通知

```python
# 註冊回調，實時獲取任務狀態
scheduler.register_callback("script_generation", on_completed)
scheduler.register_callback("video_rendering", on_completed)
```

### 6. 錯誤處理

```python
try:
    task = await scheduler.schedule_task(...)
except Exception as e:
    logger.error(f"排程失敗：{e}")
    # 發送通知或重試
```

---

## 性能建議

### 並發控制

```python
# 默認 10 個工作線程
await scheduler.start_workers(count=10)

# 高負載時增加
await scheduler.start_workers(count=20)

# 低負載時減少
await scheduler.start_workers(count=5)
```

### 任務分組

```python
# 將相關任務分組處理
batch_tasks = []
for i in range(10):
    task = await scheduler.schedule_task(
        name=f"批量任務-{i}",
        task_type=TaskType.ASSET_PROCESSING,
        scheduled_time=datetime.utcnow() + timedelta(minutes=i),
    )
    batch_tasks.append(task)
```

---

**更新日期:** 2026-03-30 22:45  
**版本:** v2.3  
**GitHub:** https://github.com/iiooiioo888/AI_test
