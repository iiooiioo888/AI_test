"""
Enterprise AI Video Production Platform (AVP)
主應用入口
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.router import api_router
from app.utils.metrics import Metrics


# 配置結構化日誌
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(settings, 'LOG_LEVEL', 'INFO').upper()
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命周期管理"""
    # 啟動時初始化
    logger.info("AVP Platform starting up", version=settings.APP_VERSION)
    
    # 初始化數據庫連接
    # await init_databases()
    
    # 初始化 GPU 資源池
    # await init_gpu_pool()
    
    logger.info("AVP Platform ready")
    
    yield
    
    # 關閉時清理
    logger.info("AVP Platform shutting down")
    # await cleanup_databases()
    # await cleanup_gpu_pool()


# 創建 FastAPI 應用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="企業級 AI 視頻生產平台 - 端到端視頻生成系統",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus 監控
metrics = Metrics()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """請求日誌中間件"""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        "request_processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    
    # 記錄 Prometheus 指標
    metrics.request_duration.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).observe(duration)
    
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """驗證錯誤處理"""
    logger.warning("validation_error", errors=exc.errors())
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "請求參數驗證失敗",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用異常處理"""
    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "服務器內部錯誤",
        },
    )


# 健康檢查端點
@app.get("/health", tags=["Health"])
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """就緒檢查"""
    # TODO: 檢查數據庫連接、GPU 資源等
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "gpu_pool": "ok",
            "storage": "ok",
        }
    }


# 註冊 API 路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# 根路徑
@app.get("/", tags=["Root"])
async def root():
    """根路徑"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8888,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
    )
