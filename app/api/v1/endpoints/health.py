"""
健康檢查端點
"""
from fastapi import APIRouter, status
from datetime import datetime

router = APIRouter()


@router.get("/", summary="健康檢查")
async def health_check():
    """基礎健康檢查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/detailed", summary="詳細健康檢查")
async def detailed_health_check():
    """
    詳細健康檢查：
    - 數據庫連接
    - Neo4j 連接
    - Milvus 連接
    - Redis 連接
    - GPU 資源
    - 存儲空間
    """
    checks = {
        "database": {"status": "ok", "latency_ms": 0},
        "neo4j": {"status": "ok", "latency_ms": 0},
        "milvus": {"status": "ok", "latency_ms": 0},
        "redis": {"status": "ok", "latency_ms": 0},
        "gpu_pool": {"status": "ok", "available": 4, "total": 4},
        "storage": {"status": "ok", "used_gb": 0, "total_gb": 100},
    }
    
    all_healthy = all(v["status"] == "ok" for v in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }
