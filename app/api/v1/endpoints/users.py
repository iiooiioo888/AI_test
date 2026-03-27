"""
用戶管理端點
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/", summary="列出用戶")
async def list_users():
    """列出所有用戶"""
    return []


@router.get("/{user_id}", summary="獲取用戶詳情")
async def get_user(user_id: str):
    """獲取用戶詳情"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
