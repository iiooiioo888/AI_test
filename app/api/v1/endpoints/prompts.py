"""
提示詞管理端點
"""
from fastapi import APIRouter, HTTPException, status, Query

router = APIRouter()


@router.get("/", summary="列出提示詞")
async def list_prompts(
    project_id: str = Query(...),
    category: str = Query(None),
):
    """列出提示詞"""
    return []


@router.post("/", summary="創建提示詞")
async def create_prompt():
    """創建提示詞"""
    return {"id": "prompt-001"}


@router.get("/{prompt_id}", summary="獲取提示詞詳情")
async def get_prompt(prompt_id: str):
    """獲取提示詞詳情"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Prompt not found"
    )


@router.post("/optimize", summary="優化提示詞")
async def optimize_prompt():
    """使用 LLM 優化提示詞"""
    return {"optimized_prompt": ""}


@router.get("/search", summary="搜索提示詞")
async def search_prompts(query: str, limit: int = 10):
    """使用 Milvus 向量搜索提示詞"""
    return []
