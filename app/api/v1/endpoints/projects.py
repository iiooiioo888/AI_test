"""
項目管理端點
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/", summary="列出項目")
async def list_projects():
    """列出所有項目"""
    return []


@router.post("/", summary="創建項目")
async def create_project():
    """創建新項目"""
    return {"id": "project-001", "name": "New Project"}


@router.get("/{project_id}", summary="獲取項目詳情")
async def get_project(project_id: str):
    """獲取項目詳情"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found"
    )
