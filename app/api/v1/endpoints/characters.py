"""
角色管理端點
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/", summary="列出角色")
async def list_characters(project_id: str):
    """列出項目中的所有角色"""
    return []


@router.post("/", summary="創建角色")
async def create_character():
    """創建新角色"""
    return {"id": "char-001", "name": "New Character"}


@router.get("/{character_id}", summary="獲取角色詳情")
async def get_character(character_id: str):
    """獲取角色詳情"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found"
    )


@router.get("/{character_id}/relationships", summary="獲取角色關係")
async def get_character_relationships(character_id: str):
    """獲取角色關係網絡（從 Neo4j）"""
    return {
        "character_id": character_id,
        "relationships": []
    }
