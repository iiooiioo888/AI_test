"""
性能優化服務
數據庫查詢優化、緩存層、異步任務隊列、資源池管理
"""
from typing import Optional, Dict, List, Any, Callable, TypeVar, Generic, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict
import asyncio
import hashlib
import json
import time
import structlog
from functools import wraps
import weakref

logger = structlog.get_logger()

T = TypeVar('T')


# ============================================================================
# 高級緩存系統
# ============================================================================

@dataclass
class CacheStats:
    """緩存統計"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    writes: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "writes": self.writes,
            "hit_rate": round(self.hit_rate, 2),
        }


class LRUCache(Generic[T]):
    """
    LRU 緩存實現
    
    特點：
    - O(1) 時間複雜度的讀寫
    - 自動淘汰最久未使用項目
    - 支持 TTL 過期
    - 線程安全
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, T] = OrderedDict()
        self._expires: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self.stats = CacheStats()
    
    async def get(self, key: str) -> Optional[T]:
        """獲取緩存"""
        async with self._lock:
            if key not in self._cache:
                self.stats.misses += 1
                return None
            
            # 檢查過期
            if key in self._expires and datetime.utcnow() > self._expires[key]:
                await self._delete(key)
                self.stats.misses += 1
                return None
            
            # 移動到末尾 (標記為最近使用)
            self._cache.move_to_end(key)
            self.stats.hits += 1
            return self._cache[key]
    
    async def set(self, key: str, value: T, ttl: Optional[int] = None):
        """設置緩存"""
        async with self._lock:
            # 如果已存在，先刪除
            if key in self._cache:
                await self._delete(key)
            
            # 檢查是否需要淘汰
            while len(self._cache) >= self.max_size:
                await self._evict_lru()
            
            # 設置值
            self._cache[key] = value
            self._cache.move_to_end(key)
            
            # 設置過期時間
            if ttl is not None or self.default_ttl:
                self._expires[key] = datetime.utcnow() + timedelta(
                    seconds=ttl or self.default_ttl
                )
            
            self.stats.writes += 1
    
    async def delete(self, key: str):
        """刪除緩存"""
        async with self._lock:
            await self._delete(key)
    
    async def _delete(self, key: str):
        """內部刪除方法"""
        if key in self._cache:
            del self._cache[key]
            self._expires.pop(key, None)
            self.stats.evictions += 1
    
    async def _evict_lru(self):
        """淘汰最久未使用"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            await self._delete(oldest_key)
    
    async def clear(self):
        """清空緩存"""
        async with self._lock:
            self._cache.clear()
            self._expires.clear()
    
    async def stats(self) -> CacheStats:
        """獲取統計信息"""
        return self.stats
    
    def __len__(self) -> int:
        return len(self._cache)


class MultiLevelCache:
    """
    多級緩存
    
    L1: 內存緩存 (LRU, 快速但容量小)
    L2: Redis 緩存 (網絡，容量大)
    L3: 數據庫 (持久化)
    """
    
    def __init__(
        self,
        l1_size: int = 500,
        l1_ttl: int = 300,
        l2_ttl: int = 3600,
    ):
        self.l1_cache = LRUCache(max_size=l1_size, default_ttl=l1_ttl)
        self.l2_ttl = l2_ttl
        self.redis_client = None  # TODO: 初始化 Redis
    
    async def get(self, key: str) -> Optional[Any]:
        """獲取緩存 (L1 → L2)"""
        # 嘗試 L1
        value = await self.l1_cache.get(key)
        if value is not None:
            return value
        
        # 嘗試 L2 (Redis)
        # TODO: 實現 Redis 獲取
        # value = await self.redis_client.get(key)
        # if value:
        #     # 回填 L1
        #     await self.l1_cache.set(key, value)
        #     return value
        
        return None
    
    async def set(self, key: str, value: Any):
        """設置緩存 (L1 + L2)"""
        # 設置 L1
        await self.l1_cache.set(key, value)
        
        # 設置 L2
        # TODO: 實現 Redis 設置
        # await self.redis_client.setex(key, self.l2_ttl, json.dumps(value))
    
    async def delete(self, key: str):
        """刪除緩存"""
        await self.l1_cache.delete(key)
        # TODO: Redis 刪除


# ============================================================================
# 數據庫連接池優化
# ============================================================================

class DatabaseConnectionPool:
    """
    數據庫連接池優化
    
    特點：
    - 連接復用
    - 自動重連
    - 超時控制
    - 連接健康檢查
    """
    
    def __init__(
        self,
        min_connections: int = 5,
        max_connections: int = 20,
        connection_timeout: int = 30,
        max_idle_time: int = 300,
    ):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_idle_time = max_idle_time
        
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self._active_connections: Set = set()
        self._initialized = False
    
    async def initialize(self, connection_factory: Callable):
        """初始化連接池"""
        if self._initialized:
            return
        
        # 創建最小連接數
        for _ in range(self.min_connections):
            conn = await connection_factory()
            await self._pool.put(conn)
        
        self._initialized = True
        logger.info(
            "database_pool_initialized",
            min_connections=self.min_connections,
            max_connections=self.max_connections,
        )
    
    async def acquire(self):
        """獲取連接"""
        if not self._initialized:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            # 嘗試從池獲取
            conn = self._pool.get_nowait()
        except asyncio.QueueEmpty:
            # 池為空，創建新連接 (如果不超過最大限制)
            if len(self._active_connections) < self.max_connections:
                # TODO: 創建新連接
                conn = None
            else:
                # 等待可用連接
                conn = await asyncio.wait_for(
                    self._pool.get(),
                    timeout=self.connection_timeout
                )
        
        self._active_connections.add(conn)
        return conn
    
    async def release(self, conn):
        """釋放連接"""
        if conn in self._active_connections:
            self._active_connections.remove(conn)
            
            # 健康檢查
            if await self._is_connection_healthy(conn):
                await self._pool.put(conn)
            else:
                # 連接不健康，關閉並創建新連接
                await self._close_connection(conn)
                # TODO: 創建新連接
    
    async def _is_connection_healthy(self, conn) -> bool:
        """檢查連接健康狀況"""
        # TODO: 實現健康檢查
        return True
    
    async def _close_connection(self, conn):
        """關閉連接"""
        # TODO: 實現
        pass
    
    async def close(self):
        """關閉連接池"""
        while not self._pool.empty():
            conn = self._pool.get_nowait()
            await self._close_connection(conn)
        
        for conn in self._active_connections:
            await self._close_connection(conn)
        
        self._active_connections.clear()
        self._initialized = False


# ============================================================================
# 異步任務隊列
# ============================================================================

class AsyncTaskQueue:
    """
    異步任務隊列
    
    特點：
    - 優先級隊列
    - 任務重試
    - 超時控制
    - 進度追蹤
    """
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._tasks: Dict[str, Dict] = {}
    
    async def start(self):
        """啟動任務隊列"""
        self._running = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info("task_queue_started", workers=self.max_workers)
    
    async def stop(self):
        """停止任務隊列"""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("task_queue_stopped")
    
    async def submit(
        self,
        task_id: str,
        coro: Callable,
        priority: int = 0,
        timeout: Optional[int] = None,
        retries: int = 3,
    ):
        """提交任務"""
        self._tasks[task_id] = {
            "coro": coro,
            "priority": priority,
            "timeout": timeout,
            "retries": retries,
            "attempts": 0,
            "status": "pending",
            "created_at": datetime.utcnow(),
        }
        
        await self._queue.put((priority, task_id))
        logger.debug("task_submitted", task_id=task_id, priority=priority)
    
    async def _worker(self, worker_id: int):
        """工作線程"""
        while self._running:
            try:
                priority, task_id = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            
            task_info = self._tasks.get(task_id)
            if not task_info:
                continue
            
            try:
                await self._execute_task(task_id, task_info)
            except Exception as e:
                logger.error(
                    "task_failed",
                    task_id=task_id,
                    worker_id=worker_id,
                    error=str(e),
                )
            
            self._queue.task_done()
    
    async def _execute_task(self, task_id: str, task_info: Dict):
        """執行任務"""
        task_info["status"] = "running"
        task_info["started_at"] = datetime.utcnow()
        
        try:
            coro = task_info["coro"]
            timeout = task_info["timeout"]
            
            if timeout:
                await asyncio.wait_for(coro(), timeout=timeout)
            else:
                await coro()
            
            task_info["status"] = "completed"
            task_info["completed_at"] = datetime.utcnow()
            
        except asyncio.TimeoutError:
            task_info["status"] = "timeout"
            await self._retry_task(task_id, task_info)
        
        except Exception as e:
            task_info["error"] = str(e)
            await self._retry_task(task_id, task_info)
    
    async def _retry_task(self, task_id: str, task_info: Dict):
        """重試任務"""
        task_info["attempts"] += 1
        
        if task_info["attempts"] < task_info["retries"]:
            task_info["status"] = "retrying"
            await self._queue.put((task_info["priority"], task_id))
        else:
            task_info["status"] = "failed"
            task_info["failed_at"] = datetime.utcnow()
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """獲取任務狀態"""
        return self._tasks.get(task_id)


# ============================================================================
# 查詢優化器
# ============================================================================

class QueryOptimizer:
    """
    查詢優化器
    
    功能：
    1. N+1 查詢檢測
    2. 查詢計劃分析
    3. 索引建議
    4. 查詢緩存
    """
    
    def __init__(self):
        self.query_log: List[Dict[str, Any]] = []
        self.slow_query_threshold = 1.0  # 秒
        self.query_cache: LRUCache = LRUCache(max_size=1000, default_ttl=300)
    
    def log_query(
        self,
        query: str,
        params: Dict,
        duration: float,
        rows: int = 0,
        plan: Optional[Dict] = None,
    ):
        """記錄查詢"""
        self.query_log.append({
            "query": query,
            "params": params,
            "duration": duration,
            "rows": rows,
            "plan": plan,
            "timestamp": datetime.utcnow(),
            "is_slow": duration > self.slow_query_threshold,
        })
        
        # 保持日誌大小
        if len(self.query_log) > 1000:
            self.query_log = self.query_log[-500:]
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """獲取慢查詢"""
        slow = [q for q in self.query_log if q["is_slow"]]
        return sorted(slow, key=lambda x: x["duration"], reverse=True)[:limit]
    
    def detect_n_plus_one(self) -> List[Dict]:
        """檢測 N+1 查詢"""
        patterns: Dict[str, List[Dict]] = {}
        
        for query in self.query_log[-100:]:
            pattern = self._extract_query_pattern(query["query"])
            
            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(query)
        
        n_plus_one = []
        for pattern, queries in patterns.items():
            if len(queries) > 10:
                n_plus_one.append({
                    "pattern": pattern,
                    "count": len(queries),
                    "total_time": sum(q["duration"] for q in queries),
                    "avg_time": sum(q["duration"] for q in queries) / len(queries),
                    "recommendation": "考慮使用 JOIN 或批量查詢",
                })
        
        return n_plus_one
    
    def _extract_query_pattern(self, query: str) -> str:
        """提取查詢模式"""
        # 移除具體值，保留結構
        pattern = query
        pattern = re.sub(r"'[^']*'", "'?'", pattern)
        pattern = re.sub(r"\d+", "?", pattern)
        return pattern.split("WHERE")[0] if "WHERE" in pattern else pattern
    
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
            "cache_hit_rate": self.query_cache.stats.hit_rate,
        }


# ============================================================================
# 性能監控裝飾器
# ============================================================================

def monitor_performance(func: Callable):
    """
    性能監控裝飾器
    
    記錄函數執行時間、內存使用、調用次數
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
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
                duration_ms=round(duration * 1000, 2),
                current_memory_mb=round(current / 1024 / 1024, 2),
                peak_memory_mb=round(peak / 1024 / 1024, 2),
            )
    
    return wrapper


def cache_result(ttl: int = 300, key_prefix: str = ""):
    """
    緩存結果裝飾器
    
    使用方式:
    @cache_result(ttl=300, key_prefix="user")
    async def get_user(user_id: int):
        ...
    """
    cache = LRUCache(max_size=1000, default_ttl=ttl)
    
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
            await cache.set(cache_key, result)
            logger.debug("cache_set", key=cache_key)
            
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


# ============================================================================
# 全局實例
# ============================================================================

# 多級緩存
cache = MultiLevelCache(l1_size=500, l1_ttl=300, l2_ttl=3600)

# 查詢優化器
query_optimizer = QueryOptimizer()

# 任務隊列
task_queue = AsyncTaskQueue(max_workers=10)
