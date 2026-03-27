"""
認證端點
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login", response_model=Token, summary="用戶登錄")
async def login(login_data: LoginRequest):
    """用戶登錄，返回 JWT Token"""
    # TODO: 驗證用戶憑據
    # TODO: 生成 JWT Token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@router.post("/logout", summary="用戶登出")
async def logout():
    """用戶登出"""
    return {"message": "Logged out successfully"}


@router.get("/me", summary="獲取當前用戶信息")
async def get_current_user_info():
    """獲取當前登錄用戶信息"""
    # TODO: 從 JWT Token 解析用戶信息
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )
