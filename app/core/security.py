"""
企業級安全防護模塊
包含輸入驗證、XSS 防護、CSRF 防護、速率限制等
"""
import re
import hashlib
import secrets
import time
from typing import Optional, Dict, List, Any, Set
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import structlog

logger = structlog.get_logger()


# ============================================================================
# XSS 防護
# ============================================================================

class XSSProtection:
    """XSS 攻擊防護"""
    
    # 危險 HTML 標籤
    DANGEROUS_TAGS = {
        'script', 'iframe', 'object', 'embed', 'form', 'input', 'button',
        'textarea', 'select', 'style', 'link', 'meta', 'base', 'applet',
        'frame', 'frameset', 'layer', 'ilayer', 'bgsound', 'title', 'svg'
    }
    
    # 危險屬性
    DANGEROUS_ATTRIBUTES = {
        'onabort', 'onblur', 'onchange', 'onclick', 'ondblclick', 'onerror',
        'onfocus', 'onkeydown', 'onkeypress', 'onkeyup', 'onload', 'onmousedown',
        'onmousemove', 'onmouseout', 'onmouseover', 'onmouseup', 'onreset',
        'onresize', 'onscroll', 'onselect', 'onsubmit', 'onunload', 'oncontextmenu',
        'oninput', 'onsearch', 'onwheel', 'oncopy', 'oncut', 'onpaste',
        'formaction', 'xlink:href', 'href', 'src', 'data', 'action', 'formaction'
    }
    
    # 危險協議
    DANGEROUS_PROTOCOLS = {'javascript:', 'data:', 'vbscript:', 'file:'}
    
    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """
        清理 HTML，防止 XSS 攻擊
        
        Args:
            text: 輸入文本
            
        Returns:
            清理後的文本
        """
        if not text:
            return text
        
        # 移除危險標籤
        for tag in cls.DANGEROUS_TAGS:
            # 移除開始標籤
            text = re.sub(rf'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
            # 移除結束標籤
            text = re.sub(rf'</{tag}>', '', text, flags=re.IGNORECASE)
        
        # 移除危險屬性
        for attr in cls.DANGEROUS_ATTRIBUTES:
            text = re.sub(rf'\s*{attr}\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
            text = re.sub(rf'\s*{attr}\s*=\s*[^\s>]+', '', text, flags=re.IGNORECASE)
        
        # 移除危險協議
        for protocol in cls.DANGEROUS_PROTOCOLS:
            text = re.sub(rf'{protocol}[^"\'>\s]*', '', text, flags=re.IGNORECASE)
        
        # 轉義剩餘的 HTML 特殊字符
        text = cls._escape_html(text)
        
        return text
    
    @classmethod
    def _escape_html(cls, text: str) -> str:
        """轉義 HTML 特殊字符"""
        escape_map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;',
        }
        
        for char, escape in escape_map.items():
            text = text.replace(char, escape)
        
        return text
    
    @classmethod
    def validate_input(cls, text: str, max_length: int = 10000) -> bool:
        """
        驗證輸入是否安全
        
        Args:
            text: 輸入文本
            max_length: 最大長度
            
        Returns:
            bool: 是否安全
        """
        if not text:
            return True
        
        # 檢查長度
        if len(text) > max_length:
            return False
        
        # 檢查危險模式
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'on\w+\s*=',
            r'expression\s*\(',
            r'url\s*\(',
            r'eval\s*\(',
            r'document\.(cookie|location|write)',
            r'window\.(location|open|alert)',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("xss_attack_detected", pattern=pattern, input_length=len(text))
                return False
        
        return True


# ============================================================================
# CSRF 防護
# ============================================================================

class CSRFProtection:
    """CSRF 攻擊防護"""
    
    def __init__(self):
        self.tokens: Dict[str, Dict[str, Any]] = {}
        self.token_lifetime = timedelta(hours=1)
    
    def generate_token(self, user_id: str) -> str:
        """
        生成 CSRF Token
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            str: CSRF Token
        """
        token = secrets.token_urlsafe(32)
        
        self.tokens[token] = {
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + self.token_lifetime,
        }
        
        # 清理過期 token
        self._cleanup_expired_tokens()
        
        return token
    
    def validate_token(self, token: str, user_id: str) -> bool:
        """
        驗證 CSRF Token
        
        Args:
            token: Token 字符串
            user_id: 用戶 ID
            
        Returns:
            bool: 是否有效
        """
        if not token or token not in self.tokens:
            logger.warning("csrf_token_not_found", token=token[:8] if token else None)
            return False
        
        token_data = self.tokens[token]
        
        # 檢查用戶 ID 是否匹配
        if token_data['user_id'] != user_id:
            logger.warning("csrf_token_user_mismatch")
            return False
        
        # 檢查是否過期
        if datetime.utcnow() > token_data['expires_at']:
            logger.warning("csrf_token_expired")
            del self.tokens[token]
            return False
        
        return True
    
    def invalidate_token(self, token: str):
        """使 Token 失效"""
        if token in self.tokens:
            del self.tokens[token]
    
    def _cleanup_expired_tokens(self):
        """清理過期 Token"""
        now = datetime.utcnow()
        expired_tokens = [
            token for token, data in self.tokens.items()
            if now > data['expires_at']
        ]
        
        for token in expired_tokens:
            del self.tokens[token]


# ============================================================================
# 速率限制
# ============================================================================

class RateLimiter:
    """速率限制器"""
    
    def __init__(self):
        # 存儲請求記錄：{identifier: [(timestamp, count)]}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        
        # 默認限制
        self.default_limits = {
            'api': {'requests': 100, 'window': 60},  # 100 次/分鐘
            'auth': {'requests': 5, 'window': 300},  # 5 次/5 分鐘
            'upload': {'requests': 10, 'window': 3600},  # 10 次/小時
            'generation': {'requests': 20, 'window': 3600},  # 20 次/小時
        }
    
    def is_allowed(self, identifier: str, limit_type: str = 'api') -> bool:
        """
        檢查請求是否允許
        
        Args:
            identifier: 請求標識 (IP/用戶 ID)
            limit_type: 限制類型
            
        Returns:
            bool: 是否允許
        """
        if limit_type not in self.default_limits:
            limit_type = 'api'
        
        limit_config = self.default_limits[limit_type]
        max_requests = limit_config['requests']
        window_seconds = limit_config['window']
        
        now = time.time()
        window_start = now - window_seconds
        
        # 清理舊記錄
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if ts > window_start
        ]
        
        # 檢查是否超過限制
        if len(self.requests[identifier]) >= max_requests:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                limit_type=limit_type,
                current_count=len(self.requests[identifier]),
                max_requests=max_requests,
            )
            return False
        
        # 記錄請求
        self.requests[identifier].append(now)
        
        return True
    
    def get_remaining(self, identifier: str, limit_type: str = 'api') -> int:
        """
        獲取剩餘請求次數
        
        Args:
            identifier: 請求標識
            limit_type: 限制類型
            
        Returns:
            int: 剩餘次數
        """
        if limit_type not in self.default_limits:
            limit_type = 'api'
        
        limit_config = self.default_limits[limit_type]
        max_requests = limit_config['requests']
        window_seconds = limit_config['window']
        
        now = time.time()
        window_start = now - window_seconds
        
        # 清理舊記錄
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if ts > window_start
        ]
        
        return max(0, max_requests - len(self.requests[identifier]))
    
    def get_retry_after(self, identifier: str, limit_type: str = 'api') -> int:
        """
        獲取重試等待時間 (秒)
        
        Args:
            identifier: 請求標識
            limit_type: 限制類型
            
        Returns:
            int: 等待秒數
        """
        if not self.requests[identifier]:
            return 0
        
        limit_config = self.default_limits[limit_type]
        window_seconds = limit_config['window']
        
        oldest_request = min(self.requests[identifier])
        retry_after = int(oldest_request + window_seconds - time.time())
        
        return max(0, retry_after)


# ============================================================================
# SQL 注入防護
# ============================================================================

class SQLInjectionProtection:
    """SQL 注入防護"""
    
    # 危險 SQL 關鍵詞
    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT',
        'UPDATE', 'EXEC', 'EXECUTE', 'UNION', 'SELECT', 'FROM',
        'WHERE', 'HAVING', 'GROUP BY', 'ORDER BY', '--', ';',
        'xp_', 'sp_', '0x', 'CHAR(', 'CONCAT(', 'BENCHMARK(', 'SLEEP('
    }
    
    # 危險模式
    DANGEROUS_PATTERNS = [
        r"('\s*OR\s+'[^']*'\s*=\s*'[^']*')",  # ' OR 'a'='a
        r"('\s*OR\s+\d+\s*=\s*\d+)",  # ' OR 1=1
        r"(--\s*$)",  # 註釋
        r"(;\s*DROP\s+TABLE)",  # ; DROP TABLE
        r"(UNION\s+SELECT)",  # UNION SELECT
        r"(INTO\s+OUTFILE)",  # INTO OUTFILE
        r"(LOAD_FILE\s*\()",  # LOAD_FILE()
    ]
    
    @classmethod
    def validate_input(cls, text: str) -> bool:
        """
        驗證輸入是否包含 SQL 注入攻擊
        
        Args:
            text: 輸入文本
            
        Returns:
            bool: 是否安全
        """
        if not text:
            return True
        
        text_upper = text.upper()
        
        # 檢查危險關鍵詞組合
        keyword_count = sum(1 for kw in cls.DANGEROUS_KEYWORDS if kw in text_upper)
        if keyword_count >= 2:
            logger.warning("sql_injection_detected", keywords=keyword_count)
            return False
        
        # 檢查危險模式
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("sql_injection_pattern_detected", pattern=pattern)
                return False
        
        return True


# ============================================================================
# 文件上傳安全
# ============================================================================

class FileUploadSecurity:
    """文件上傳安全檢查"""
    
    # 允許的 MIME 類型
    ALLOWED_MIME_TYPES = {
        'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'video': ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'],
        'document': ['application/pdf', 'text/plain'],
    }
    
    # 允許的擴展名
    ALLOWED_EXTENSIONS = {
        'image': {'.jpg', '.jpeg', '.png', '.gif', '.webp'},
        'video': {'.mp4', '.mov', '.avi', '.webm', '.mkv'},
        'document': {'.pdf', '.txt'},
    }
    
    # 最大文件大小 (字節)
    MAX_FILE_SIZES = {
        'image': 10 * 1024 * 1024,  # 10MB
        'video': 500 * 1024 * 1024,  # 500MB
        'document': 5 * 1024 * 1024,  # 5MB
    }
    
    # 危險擴展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.sh', '.php', '.asp', '.aspx',
        '.jsp', '.cgi', '.pl', '.py', '.rb', '.js', '.html', '.htm'
    }
    
    @classmethod
    def validate_file(cls, filename: str, file_size: int, mime_type: str,
                      file_type: str = 'image') -> tuple[bool, Optional[str]]:
        """
        驗證上傳文件
        
        Args:
            filename: 文件名
            file_size: 文件大小
            mime_type: MIME 類型
            file_type: 文件類型 (image/video/document)
            
        Returns:
            (是否安全，錯誤信息)
        """
        # 檢查擴展名
        ext = cls._get_extension(filename).lower()
        
        if ext in cls.DANGEROUS_EXTENSIONS:
            return False, "不允許的文件類型"
        
        if file_type in cls.ALLOWED_EXTENSIONS:
            if ext not in cls.ALLOWED_EXTENSIONS[file_type]:
                return False, f"不允許的 {file_type} 文件擴展名"
        
        # 檢查文件大小
        if file_type in cls.MAX_FILE_SIZES:
            if file_size > cls.MAX_FILE_SIZES[file_type]:
                max_size_mb = cls.MAX_FILE_SIZES[file_type] / (1024 * 1024)
                return False, f"文件超過最大限制 {max_size_mb}MB"
        
        # 檢查 MIME 類型
        if file_type in cls.ALLOWED_MIME_TYPES:
            if mime_type and mime_type not in cls.ALLOWED_MIME_TYPES[file_type]:
                return False, "不允許的 MIME 類型"
        
        return True, None
    
    @classmethod
    def _get_extension(cls, filename: str) -> str:
        """獲取文件擴展名"""
        if '.' in filename:
            return '.' + filename.rsplit('.', 1)[1].lower()
        return ''
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        清理文件名，防止路徑遍歷攻擊
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 清理後的文件名
        """
        # 移除路徑信息
        filename = filename.replace('\\', '/').split('/')[-1]
        
        # 移除危險字符
        filename = re.sub(r'[^\w\.\-]', '_', filename)
        
        # 移除多個連續的點
        filename = re.sub(r'\.{2,}', '.', filename)
        
        # 限制長度
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250-len(ext)] + '.' + ext if ext else name[:255]
        
        return filename


# ============================================================================
# 密碼安全
# ============================================================================

class PasswordSecurity:
    """密碼安全檢查"""
    
    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, Optional[str]]:
        """
        驗證密碼強度
        
        Args:
            password: 密碼
            
        Returns:
            (是否有效，錯誤信息)
        """
        if not password:
            return False, "密碼不能為空"
        
        if len(password) < 8:
            return False, "密碼長度至少 8 位"
        
        if len(password) > 128:
            return False, "密碼長度不能超過 128 位"
        
        # 檢查是否包含大小寫字母、數字、特殊字符
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        strength = sum([has_upper, has_lower, has_digit, has_special])
        
        if strength < 3:
            return False, "密碼需要包含大小寫字母、數字和特殊字符中的至少 3 種"
        
        # 檢查常見弱密碼
        weak_passwords = {
            'password', '123456', '12345678', 'qwerty', 'abc123',
            '111111', '123123', 'admin', 'letmein', 'welcome'
        }
        
        if password.lower() in weak_passwords:
            return False, "密碼過於常見，請使用更安全的密碼"
        
        return True, None
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        哈希密碼
        
        Args:
            password: 原始密碼
            
        Returns:
            str: 哈希後的密碼
        """
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """
        驗證密碼
        
        Args:
            password: 原始密碼
            hashed: 哈希後的密碼
            
        Returns:
            bool: 是否匹配
        """
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False


# ============================================================================
# 審計日誌
# ============================================================================

class SecurityAuditLogger:
    """安全審計日誌"""
    
    @staticmethod
    def log_security_event(event_type: str, user_id: Optional[str] = None,
                           ip_address: Optional[str] = None,
                           details: Optional[Dict] = None):
        """
        記錄安全事件
        
        Args:
            event_type: 事件類型
            user_id: 用戶 ID
            ip_address: IP 地址
            details: 詳細信息
        """
        logger.info(
            "security_event",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    @classmethod
    def log_login_attempt(cls, user_id: str, success: bool, ip_address: str):
        """記錄登錄嘗試"""
        cls.log_security_event(
            event_type="login_attempt",
            user_id=user_id,
            ip_address=ip_address,
            details={"success": success},
        )
    
    @classmethod
    def log_permission_denied(cls, user_id: str, action: str, resource: str):
        """記錄權限拒絕"""
        cls.log_security_event(
            event_type="permission_denied",
            user_id=user_id,
            details={"action": action, "resource": resource},
        )
    
    @classmethod
    def log_suspicious_activity(cls, user_id: Optional[str], activity_type: str,
                                details: Dict):
        """記錄可疑活動"""
        cls.log_security_event(
            event_type="suspicious_activity",
            user_id=user_id,
            details={**details, "activity_type": activity_type},
        )


# ============================================================================
# 全局實例
# ============================================================================

xss_protection = XSSProtection()
csrf_protection = CSRFProtection()
rate_limiter = RateLimiter()
sql_injection_protection = SQLInjectionProtection()
file_upload_security = FileUploadSecurity()
password_security = PasswordSecurity()
security_audit = SecurityAuditLogger()
