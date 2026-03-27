"""
API v1 路由匯總
"""
from fastapi import APIRouter
from .endpoints import (
    auth,
    users,
    projects,
    scenes,
    characters,
    prompts,
    generation,
    health,
)

api_router = APIRouter()

# 認證與用戶
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# 項目管理
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])

# 核心業務 - 場景管理
api_router.include_router(scenes.router, prefix="/scenes", tags=["Scenes"])

# 知識圖譜 - 角色/道具/地點
api_router.include_router(characters.router, prefix="/characters", tags=["Characters"])

# 提示詞工程
api_router.include_router(prompts.router, prefix="/prompts", tags=["Prompts"])

# 視頻生成
api_router.include_router(generation.router, prefix="/generation", tags=["Generation"])

# 健康檢查
api_router.include_router(health.router, prefix="/health", tags=["Health"])
