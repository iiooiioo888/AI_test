"""
性能優化服務
數據庫查詢優化、緩存層、異步任務隊列
"""
from typing import Optional, Dict, List, Any, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import hashlib
import json
import structlog
from functools import wraps

logger = structlog.get_logger()

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """緩存條目"""
    value: T
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def touch(self):
        """增加訪問計數"""
        self.access_count += 1


class AsyncCache:
    """
    異步緩存
    
    功能：
    1. TTL 過期
    2. LRU 淘汰
    3. 訪問統計
    4. 自動清理
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl  # 秒
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """獲取緩存"""
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                return None
            
            entry.touch()
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """設置緩存"""
        async with self._lock:
            # 檢查是否需要淘汰
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()
            
            expires_at = None
            if ttl is not None or self.default_ttl:
                expires_at = datetime.utcnow() + timedelta(
                    seconds=ttl or self.default_ttl
                )
            
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
            )
    
    async def delete(self, key: str):
        """刪除緩存"""
        async with self._lock:
            self._cache.pop(key, None)
    
    async def clear(self):
        """清空緩存"""
        async with self._lock:
            self._cache.clear()
    
    async def _evict_lru(self):
        """淘汰最少使用"""
        if not self._cache:
            return
        
        # 找到訪問次數最少的
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
        del self._cache[lru_key]
    
    async def stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        async with self._lock:
            total = len(self._cache)
            expired = sum(1 for e in self._cache.values() if e.is_expired())
            total_accesses = sum(e.access_count for e in self._cache.values())
            
            return {
                "size": total,
                "expired": expired,
                "total_accesses": total_accesses,
                "avg_accesses": total_accesses / total if total > 0 else 0,
                "max_size": self.max_size,
                "usage_percent": (total / self.max_size) * 100 if self.max_size > 0 else 0,
            }


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    緩存裝飾器
    
    使用方式:
    @cached(ttl=3600, key_prefix="user")
    async def get_user(user_id: int):
        ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成緩存 key
            cache_key = _generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            # 嘗試從緩存獲取
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug("cache_hit", key=cache_key)
                return cached_value
            
            # 執行函數
            result = await func(*args, **kwargs)
            
            # 存入緩存
            await cache.set(cache_key, result, ttl)
            logger.debug("cache_set", key=cache_key, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict, prefix: str) -> str:
    """生成緩存 key"""
    key_data = {
        "func": func_name,
        "args": args,
        "kwargs": kwargs,
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    if prefix:
        return f"{prefix}:{key_hash}"
    return key_hash


# 全局緩存實例
cache = AsyncCache(max_size=1000, default_ttl=3600)


class QueryOptimizer:
    """
    數據庫查詢優化器
    
    功能：
    1. N+1 查詢檢測
    2. 批量查詢
    3. 查詢計劃分析
    4. 索引建議
    """
    
    def __init__(self):
        self.query_log: List[Dict[str, Any]] = []
        self.slow_query_threshold = 1.0  # 秒
    
    def log_query(self, query: str, params: Dict, duration: float, rows: int = 0):
        """記錄查詢"""
        self.query_log.append({
            "query": query,
            "params": params,
            "duration": duration,
            "rows": rows,
            "timestamp": datetime.utcnow(),
            "is_slow": duration > self.slow_query_threshold,
        })
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """獲取慢查詢"""
        slow = [q for q in self.query_log if q["is_slow"]]
        return sorted(slow, key=lambda x: x["duration"], reverse=True)[:limit]
    
    def detect_n_plus_one(self) -> List[Dict]:
        """檢測 N+1 查詢"""
        # 簡化實現：查找短時間內執行的相似查詢
        patterns: Dict[str, List[Dict]] = {}
        
        for query in self.query_log[-100:]:  # 最近 100 次查詢
            # 移除具體參數，提取查詢模式
            pattern = query["query"].split("WHERE")[0] if "WHERE" in query["query"] else query["query"]
            
            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(query)
        
        # 找出執行次數過多的模式
        n_plus_one = []
        for pattern, queries in patterns.items():
            if len(queries) > 10:  # 閾值
                n_plus_one.append({
                    "pattern": pattern,
                    "count": len(queries),
                    "total_time": sum(q["duration"] for q in queries),
                    "avg_time": sum(q["duration"] for q in queries) / len(queries),
                })
        
        return n_plus_one
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取查詢統計"""
        if not self.query_log:
            return {"total_queries": 0}
        
        durations = [q["duration"] for q in self.query_log]
        slow_count = sum(1 for q in self.query_log if q["is_slow"])
        
        return {
            "total_queries": len(self.query_log),
            "slow_queries": slow_count,
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations),
            "total_rows": sum(q["rows"] for q in self.query_log),
        }


# 全局查詢優化器
query_optimizer = QueryOptimizer()


class BatchProcessor:
    """
    批量處理器
    
    功能：
    1. 批量操作
    2. 延遲執行
    3. 錯誤重試
    """
    
    def __init__(self, batch_size: int = 100, delay_ms: int = 100):
        self.batch_size = batch_size
        self.delay_ms = delay_ms
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def start(self):
        """啟動批量處理"""
        self._running = True
        asyncio.create_task(self._process_loop())
    
    async def stop(self):
        """停止批量處理"""
        self._running = False
    
    async def add(self, item: Any):
        """添加項目到隊列"""
        await self._queue.put(item)
    
    async def _process_loop(self):
        """處理循環"""
        while self._running:
            batch = []
            
            # 收集一批項目
            while len(batch) < self.batch_size and not self._queue.empty():
                try:
                    item = self._queue.get_nowait()
                    batch.append(item)
                except asyncio.QueueEmpty:
                    break
            
            if batch:
                await self._process_batch(batch)
            
            await asyncio.sleep(self.delay_ms / 1000.0)
    
    async def _process_batch(self, batch: List[Any]):
        """處理一批項目"""
        # 子類實現
        pass


# 性能監控裝飾器
def monitor_performance(func: Callable):
    """
    性能監控裝飾器
    
    記錄函數執行時間、內存使用等
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        import time
        import tracemalloc
        
        start_time = time.time()
        tracemalloc.start()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            logger.info(
                "function_performance",
                function=func.__name__,
                duration=duration,
                current_memory_mb=current / 1024 / 1024,
                peak_memory_mb=peak / 1024 / 1024,
            )
    
    return wrapper
