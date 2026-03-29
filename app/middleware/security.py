"""
安全中間件
提供請求過濾、速率限制、安全頭部等功能
"""
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import time
import structlog

from app.core.security import (
    xss_protection,
    rate_limiter,
    sql_injection_protection,
    security_audit,
)

logger = structlog.get_logger()


class SecurityMiddleware:
    """安全中間件"""
    
    def __init__(self, app):
        self.app = app
        
        # 安全頭部
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'X-Download-Options': 'noopen',
            'X-Permitted-Cross-Domain-Policies': 'none',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none';"
            ),
        }
    
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        
        request = Request(scope, receive)
        
        # 1. IP 黑名單檢查
        client_ip = self._get_client_ip(request)
        if self._is_ip_blocked(client_ip):
            security_audit.log_suspicious_activity(
                user_id=None,
                activity_type="blocked_ip",
                details={"ip": client_ip},
            )
            return await self._send_error_response(send, status.HTTP_403_FORBIDDEN, "Access denied")
        
        # 2. 速率限制檢查
        if not rate_limiter.is_allowed(client_ip, 'api'):
            retry_after = rate_limiter.get_retry_after(client_ip)
            security_audit.log_suspicious_activity(
                user_id=None,
                activity_type="rate_limit_exceeded",
                details={"ip": client_ip, "retry_after": retry_after},
            )
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "請求過於頻繁，請稍後再試",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
            return await response(scope, receive, send)
        
        # 3. 記錄請求開始時間
        start_time = time.time()
        
        # 4. 添加安全頭部到響應
        async def send_with_security_headers(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                for header_name, header_value in self.security_headers.items():
                    headers.append((
                        header_name.lower().encode('latin-1'),
                        header_value.encode('latin-1')
                    ))
                message['headers'] = headers
            await send(message)
        
        # 5. 處理請求
        try:
            return await self.app(scope, receive, send_with_security_headers)
        finally:
            # 6. 記錄請求日誌
            duration = time.time() - start_time
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=scope.get('response_status_code'),
                client_ip=client_ip,
                duration_ms=round(duration * 1000, 2),
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """獲取客戶端 IP"""
        # 檢查 X-Forwarded-For
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # 檢查 X-Real-IP
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # 使用直接連接的 IP
        if request.client:
            return request.client.host
        
        return 'unknown'
    
    def _is_ip_blocked(self, ip: str) -> bool:
        """檢查 IP 是否在黑名單中"""
        # TODO: 實現 IP 黑名單
        blocked_ips = set()
        return ip in blocked_ips
    
    async def _send_error_response(self, send, status_code: int, message: str):
        """發送錯誤響應"""
        response = JSONResponse(
            status_code=status_code,
            content={"error": "access_denied", "message": message},
        )
        await response({}, lambda: None, send)


# ============================================================================
# 安全裝飾器
# ============================================================================

from functools import wraps
from fastapi import Depends, HTTPException, status, Request


def rate_limit(limit_type: str = 'api'):
    """
    速率限制裝飾器
    
    使用方式:
    @router.post("/login", dependencies=[Depends(rate_limit('auth'))])
    """
    async def dependency(request: Request):
        client_ip = request.client.host if request.client else 'unknown'
        
        if not rate_limiter.is_allowed(client_ip, limit_type):
            retry_after = rate_limiter.get_retry_after(client_ip, limit_type)
            security_audit.log_suspicious_activity(
                user_id=None,
                activity_type="rate_limit_exceeded",
                details={"ip": client_ip, "type": limit_type},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="請求過於頻繁，請稍後再試",
                headers={"Retry-After": str(retry_after)},
            )
    
    return dependency


def validate_input(max_length: int = 10000):
    """
    輸入驗證裝飾器
    
    使用方式:
    @router.post("/scene", dependencies=[Depends(validate_input())])
    """
    async def dependency(request: Request):
        # 驗證請求體
        body = await request.body()
        if body:
            try:
                text = body.decode('utf-8')
                if not xss_protection.validate_input(text, max_length):
                    security_audit.log_suspicious_activity(
                        user_id=None,
                        activity_type="xss_attack_detected",
                        details={"ip": request.client.host, "length": len(text)},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="輸入包含不安全內容",
                    )
                
                if not sql_injection_protection.validate_input(text):
                    security_audit.log_suspicious_activity(
                        user_id=None,
                        activity_type="sql_injection_detected",
                        details={"ip": request.client.host},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="輸入包含不安全內容",
                    )
            except UnicodeDecodeError:
                pass  # 二進制數據，跳過文本驗證
    
    return dependency


def require_csrf_token():
    """
    CSRF Token 驗證裝飾器
    
    使用方式:
    @router.post("/update", dependencies=[Depends(require_csrf_token())])
    """
    from app.core.security import csrf_protection
    
    async def dependency(request: Request):
        # 從請求頭或表單獲取 token
        token = request.headers.get('X-CSRF-Token')
        
        if not token:
            # 嘗試從表單獲取
            try:
                form = await request.form()
                token = form.get('csrf_token')
            except Exception:
                pass
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="缺少 CSRF Token",
            )
        
        # TODO: 驗證 token (需要用戶上下文)
        # if not csrf_protection.validate_token(token, user_id):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="CSRF Token 無效",
        #     )
    
    return dependency


# ============================================================================
# 安全工具函數
# ============================================================================

def generate_csrf_token(user_id: str) -> str:
    """生成 CSRF Token"""
    from app.core.security import csrf_protection
    return csrf_protection.generate_token(user_id)


def validate_csrf_token(token: str, user_id: str) -> bool:
    """驗證 CSRF Token"""
    from app.core.security import csrf_protection
    return csrf_protection.validate_token(token, user_id)


def check_rate_limit(identifier: str, limit_type: str = 'api') -> dict:
    """
    檢查速率限制
    
    Returns:
        dict: {'allowed': bool, 'remaining': int, 'retry_after': int}
    """
    allowed = rate_limiter.is_allowed(identifier, limit_type)
    remaining = rate_limiter.get_remaining(identifier, limit_type)
    retry_after = rate_limiter.get_retry_after(identifier, limit_type)
    
    return {
        'allowed': allowed,
        'remaining': remaining,
        'retry_after': retry_after,
    }
