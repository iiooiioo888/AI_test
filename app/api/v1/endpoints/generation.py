"""
視頻生成端點
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks

router = APIRouter()


@router.post("/submit", summary="提交生成任務")
async def submit_generation_task(background_tasks: BackgroundTasks):
    """提交視頻生成任務到隊列"""
    return {
        "task_id": "task-001",
        "status": "queued",
        "queue_position": 1,
    }


@router.get("/tasks/{task_id}", summary="查詢任務狀態")
async def get_task_status(task_id: str):
    """查詢生成任務狀態"""
    return {
        "task_id": task_id,
        "status": "processing",
        "progress": 45.0,
    }


@router.post("/tasks/{task_id}/cancel", summary="取消任務")
async def cancel_task(task_id: str):
    """取消生成任務"""
    return {"message": "Task cancelled"}


@router.get("/queue", summary="查看隊列狀態")
async def get_queue_status():
    """查看生成隊列狀態"""
    return {
        "queued": 5,
        "processing": 2,
        "estimated_wait_minutes": 15,
    }
