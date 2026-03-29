"""
視頻生成端點
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.services.video import (
    get_generation_engine,
    get_quality_evaluator,
    GenerationTask,
    GenerationConfig,
    GenerationModel,
    GenerationMode,
)
from app.services.auth.rbac import get_rbac_service, Permission

router = APIRouter()


@router.post(
    "/submit",
    summary="提交生成任務",
    description="提交視頻生成任務到隊列",
)
async def submit_generation_task(
    scene_id: str,
    model: str = "stable-video-diffusion",
    resolution: str = "1920x1080",
    duration: float = 5.0,
    # current_user: User = Depends(get_current_user),
):
    """提交視頻生成任務"""
    engine = get_generation_engine()
    
    # 創建任務
    task = GenerationTask(
        task_id=str(uuid.uuid4()),
        scene_id=scene_id,
        config=GenerationConfig(
            model=GenerationModel(model),
            resolution=resolution,
            duration=duration,
        ),
        positive_prompt="cinematic shot, masterpiece",
        negative_prompt="ugly, deformed, low quality",
    )
    
    # 提交任務
    task_id = await engine.submit_task(task)
    
    return {
        "task_id": task_id,
        "status": "queued",
        "queue_position": task.queue_position,
        "estimated_time": task.estimated_time,
    }


@router.get(
    "/tasks/{task_id}",
    summary="查詢任務狀態",
    description="查詢生成任務的當前狀態和進度",
)
async def get_task_status(task_id: str):
    """查詢任務狀態"""
    engine = get_generation_engine()
    task = engine.get_task_status(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    return {
        "task_id": task.task_id,
        "scene_id": task.scene_id,
        "status": task.status,
        "progress": task.progress,
        "gpu_id": task.gpu_id,
        "estimated_time": task.estimated_time,
        "actual_time": task.actual_time,
        "error_message": task.error_message,
        "quality_metrics": task.quality_metrics,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.post(
    "/tasks/{task_id}/cancel",
    summary="取消任務",
    description="取消進行中的生成任務",
)
async def cancel_task(task_id: str):
    """取消任務"""
    engine = get_generation_engine()
    success = await engine.cancel_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel task (already completed or not found)",
        )
    
    return {"message": "Task cancelled successfully"}


@router.get(
    "/queue",
    summary="查看隊列狀態",
    description="查看當前生成隊列的狀態",
)
async def get_queue_status():
    """查看隊列狀態"""
    engine = get_generation_engine()
    status_data = await engine.get_queue_status()
    
    return status_data


@router.post(
    "/evaluate",
    summary="質量評估",
    description="評估生成視頻的質量",
)
async def evaluate_video_quality(
    video_path: str,
    prompt: str,
    reference_images: Optional[list] = None,
):
    """質量評估"""
    evaluator = get_quality_evaluator()
    
    metrics = await evaluator.evaluate(video_path, prompt, reference_images)
    
    return {
        "overall_score": metrics.overall_score,
        "grade": evaluator.get_quality_grade(metrics),
        "vmaf_score": metrics.vmaf_score,
        "clip_score": metrics.clip_score,
        "motion_smoothness": metrics.motion_smoothness,
        "temporal_consistency": metrics.temporal_consistency,
        "character_consistency": metrics.character_consistency,
        "style_consistency": metrics.style_consistency,
        "issues": metrics.issues,
        "recommendations": metrics.recommendations,
        "should_retry": evaluator.should_retry(metrics),
    }
