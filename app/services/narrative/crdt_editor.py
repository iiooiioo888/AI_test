"""
CRDT (Conflict-Free Replicated Data Type) 協作編輯服務
支持多人實時編輯場景，自動解決衝突
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import hashlib
import structlog

logger = structlog.get_logger()


@dataclass
class VectorClock:
    """
    向量時鐘
    用於追蹤分布式系統中的事件順序
    """
    clocks: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, node_id: str):
        """增加本地時鐘"""
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1
    
    def merge(self, other: 'VectorClock'):
        """合併另一個向量時鐘"""
        for node_id, timestamp in other.clocks.items():
            self.clocks[node_id] = max(self.clocks.get(node_id, 0), timestamp)
    
    def happens_before(self, other: 'VectorClock') -> bool:
        """檢查是否在另一個事件之前發生"""
        dominated = False
        for node_id in set(self.clocks.keys()) | set(other.clocks.keys()):
            self_time = self.clocks.get(node_id, 0)
            other_time = other.clocks.get(node_id, 0)
            if self_time > other_time:
                return False
            if self_time < other_time:
                dominated = True
        return dominated
    
    def concurrent_with(self, other: 'VectorClock') -> bool:
        """檢查是否並發"""
        return not self.happens_before(other) and not other.happens_before(self)


@dataclass
class CRDTOperation:
    """
    CRDT 操作
    表示一次編輯操作
    """
    id: str  # 操作唯一 ID
    site_id: str  # 操作來源站點 ID
    timestamp: VectorClock  # 向量時鐘
    operation_type: str  # 'insert', 'update', 'delete'
    field_path: str  # 字段路徑 (如 'scene.title')
    value: Any = None  # 新值 (insert/update)
    old_value: Any = None  # 舊值 (update/delete)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "site_id": self.site_id,
            "timestamp": dict(self.timestamp.clocks),
            "operation_type": self.operation_type,
            "field_path": self.field_path,
            "value": self.value,
            "old_value": self.old_value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CRDTOperation':
        return cls(
            id=data["id"],
            site_id=data["site_id"],
            timestamp=VectorClock(clocks=data["timestamp"]),
            operation_type=data["operation_type"],
            field_path=data["field_path"],
            value=data.get("value"),
            old_value=data.get("old_value"),
        )


class LWWRegister:
    """
    Last-Writer-Wins Register
    最简单的 CRDT 實現，用於單值字段
    """
    
    def __init__(self, value: Any = None, timestamp: float = 0, site_id: str = ""):
        self.value = value
        self.timestamp = timestamp
        self.site_id = site_id
    
    def set(self, value: Any, timestamp: float, site_id: str):
        """設置值"""
        if timestamp > self.timestamp or (timestamp == self.timestamp and site_id > self.site_id):
            self.value = value
            self.timestamp = timestamp
            self.site_id = site_id
    
    def get(self) -> Any:
        """獲取值"""
        return self.value
    
    def merge(self, other: 'LWWRegister'):
        """合併另一個 Register"""
        self.set(other.value, other.timestamp, other.site_id)


class ORSet:
    """
    Observed-Remove Set
    支持並發添加/刪除的集合 CRDT
    """
    
    def __init__(self):
        self.elements: Dict[Any, set] = {}  # element -> set of unique tags
        self.tombstones: Dict[Any, set] = {}  # element -> set of removed tags
        self.counter = 0
    
    def add(self, element: Any, site_id: str) -> str:
        """添加元素"""
        tag = f"{site_id}:{self.counter}"
        self.counter += 1
        
        if element not in self.elements:
            self.elements[element] = set()
        self.elements[element].add(tag)
        
        return tag
    
    def remove(self, element: Any):
        """移除元素"""
        if element in self.elements:
            if element not in self.tombstones:
                self.tombstones[element] = set()
            self.tombstones[element].update(self.elements[element])
            del self.elements[element]
    
    def contains(self, element: Any) -> bool:
        """檢查元素是否存在"""
        return element in self.elements and len(self.elements[element]) > 0
    
    def get_elements(self) -> List[Any]:
        """獲取所有元素"""
        return list(self.elements.keys())
    
    def merge(self, other: 'ORSet'):
        """合併另一個 ORSet"""
        # 合併所有添加
        for element, tags in other.elements.items():
            if element not in self.elements:
                self.elements[element] = set()
            self.elements[element].update(tags)
        
        # 合併所有刪除
        for element, tags in other.tombstones.items():
            if element not in self.tombstones:
                self.tombstones[element] = set()
            self.tombstones[element].update(tags)
        
        # 應用墓碑
        for element in list(self.elements.keys()):
            if element in self.tombstones:
                self.elements[element] -= self.tombstones[element]
                if not self.elements[element]:
                    del self.elements[element]


class SceneCRDT:
    """
    場景 CRDT
    將場景對象分解為多個 CRDT 字段，支持協作編輯
    """
    
    def __init__(self, scene_id: str, site_id: str):
        self.scene_id = scene_id
        self.site_id = site_id
        self.vector_clock = VectorClock()
        
        # 簡單字段使用 LWW Register
        self.title = LWWRegister()
        self.description = LWWRegister()
        self.narrative_text = LWWRegister()
        self.positive_prompt = LWWRegister()
        self.negative_prompt = LWWRegister()
        
        # 集合字段使用 ORSet
        self.tags = ORSet()
        self.characters = ORSet()  # character IDs
        self.props = ORSet()  # prop IDs
        
        # 操作歷史
        self.operation_log: List[CRDTOperation] = []
    
    def apply_operation(self, op: CRDTOperation) -> bool:
        """
        應用 CRDT 操作
        
        Args:
            op: CRDT 操作
            
        Returns:
            bool: 操作是否成功應用
        """
        # 1. 檢查操作是否已應用 (冪等性)
        if any(existing.id == op.id for existing in self.operation_log):
            logger.debug("operation_already_applied", op_id=op.id)
            return False
        
        # 2. 更新向量時鐘
        self.vector_clock.merge(op.timestamp)
        
        # 3. 根據字段路徑應用操作
        field_name = op.field_path.split('.')[-1]
        
        if op.operation_type == 'insert':
            self._apply_insert(field_name, op.value, op.timestamp, op.site_id)
        elif op.operation_type == 'update':
            self._apply_update(field_name, op.value, op.timestamp, op.site_id)
        elif op.operation_type == 'delete':
            self._apply_delete(field_name, op.timestamp, op.site_id)
        
        # 4. 記錄操作
        self.operation_log.append(op)
        
        logger.info("crdt_operation_applied", op_id=op.id, field=op.field_path)
        return True
    
    def _apply_insert(self, field_name: str, value: Any, timestamp: VectorClock, site_id: str):
        """應用插入操作"""
        if field_name == 'tags':
            self.tags.add(value, site_id)
        elif field_name in ['characters', 'props']:
            # 集合字段
            pass  # TODO: 實現複雜對象的插入
    
    def _apply_update(self, field_name: str, value: Any, timestamp: VectorClock, site_id: str):
        """應用更新操作"""
        ts = max(timestamp.clocks.values()) if timestamp.clocks else 0
        
        if field_name == 'title':
            self.title.set(value, ts, site_id)
        elif field_name == 'description':
            self.description.set(value, ts, site_id)
        elif field_name == 'narrative_text':
            self.narrative_text.set(value, ts, site_id)
        elif field_name == 'positive_prompt':
            self.positive_prompt.set(value, ts, site_id)
        elif field_name == 'negative_prompt':
            self.negative_prompt.set(value, ts, site_id)
    
    def _apply_delete(self, field_name: str, timestamp: VectorClock, site_id: str):
        """應用刪除操作"""
        if field_name == 'tags':
            pass  # TODO: 實現刪除
    
    def create_update_operation(
        self,
        field_path: str,
        value: Any,
        old_value: Optional[Any] = None,
    ) -> CRDTOperation:
        """創建更新操作"""
        self.vector_clock.increment(self.site_id)
        
        op = CRDTOperation(
            id=self._generate_op_id(),
            site_id=self.site_id,
            timestamp=VectorClock(clocks=dict(self.vector_clock.clocks)),
            operation_type='update',
            field_path=field_path,
            value=value,
            old_value=old_value,
        )
        
        # 本地應用
        self.apply_operation(op)
        
        return op
    
    def create_insert_operation(self, field_path: str, value: Any) -> CRDTOperation:
        """創建插入操作"""
        self.vector_clock.increment(self.site_id)
        
        op = CRDTOperation(
            id=self._generate_op_id(),
            site_id=self.site_id,
            timestamp=VectorClock(clocks=dict(self.vector_clock.clocks)),
            operation_type='insert',
            field_path=field_path,
            value=value,
        )
        
        self.apply_operation(op)
        
        return op
    
    def _generate_op_id(self) -> str:
        """生成操作唯一 ID"""
        data = f"{self.scene_id}:{self.site_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get_state(self) -> Dict[str, Any]:
        """獲取當前場景狀態"""
        return {
            "scene_id": self.scene_id,
            "title": self.title.get(),
            "description": self.description.get(),
            "narrative_text": self.narrative_text.get(),
            "positive_prompt": self.positive_prompt.get(),
            "negative_prompt": self.negative_prompt.get(),
            "tags": self.tags.get_elements(),
            "characters": self.characters.get_elements(),
            "props": self.props.get_elements(),
            "vector_clock": dict(self.vector_clock.clocks),
        }
    
    def merge(self, other: 'SceneCRDT'):
        """合併另一個場景 CRDT"""
        # 合併向量時鐘
        self.vector_clock.merge(other.vector_clock)
        
        # 合併所有字段
        self.title.merge(other.title)
        self.description.merge(other.description)
        self.narrative_text.merge(other.narrative_text)
        self.positive_prompt.merge(other.positive_prompt)
        self.negative_prompt.merge(other.negative_prompt)
        self.tags.merge(other.tags)
        self.characters.merge(other.characters)
        self.props.merge(other.props)
        
        # 合併操作歷史
        for op in other.operation_log:
            if not any(existing.id == op.id for existing in self.operation_log):
                self.operation_log.append(op)


class CollaborativeEditingService:
    """
    協作編輯服務
    管理多個用戶的實時協作
    """
    
    def __init__(self):
        # scene_id -> SceneCRDT
        self.scenes: Dict[str, SceneCRDT] = {}
        # scene_id -> {site_id -> WebSocket connection}
        self.connections: Dict[str, Dict[str, Any]] = {}
    
    def join_scene(self, scene_id: str, site_id: str, websocket) -> SceneCRDT:
        """用戶加入場景編輯"""
        if scene_id not in self.scenes:
            self.scenes[scene_id] = SceneCRDT(scene_id, site_id)
        
        if scene_id not in self.connections:
            self.connections[scene_id] = {}
        
        self.connections[scene_id][site_id] = websocket
        
        logger.info("user_joined_collaboration", scene_id=scene_id, site_id=site_id)
        return self.scenes[scene_id]
    
    def leave_scene(self, scene_id: str, site_id: str):
        """用戶離開場景編輯"""
        if scene_id in self.connections and site_id in self.connections[scene_id]:
            del self.connections[scene_id][site_id]
        
        logger.info("user_left_collaboration", scene_id=scene_id, site_id=site_id)
    
    async def broadcast_operation(self, scene_id: str, operation: CRDTOperation, exclude_site: str):
        """廣播操作給其他協作者"""
        if scene_id not in self.connections:
            return
        
        for site_id, websocket in self.connections[scene_id].items():
            if site_id != exclude_site:
                try:
                    await websocket.send_json(operation.to_dict())
                except Exception as e:
                    logger.error("broadcast_failed", site_id=site_id, error=str(e))
    
    def apply_remote_operation(self, scene_id: str, operation_dict: Dict) -> bool:
        """應用遠程操作"""
        if scene_id not in self.scenes:
            return False
        
        op = CRDTOperation.from_dict(operation_dict)
        return self.scenes[scene_id].apply_operation(op)
    
    def get_scene_state(self, scene_id: str) -> Optional[Dict]:
        """獲取場景當前狀態"""
        if scene_id not in self.scenes:
            return None
        return self.scenes[scene_id].get_state()


# 全局服務實例
_collaborative_service: Optional[CollaborativeEditingService] = None


def get_collaborative_service() -> CollaborativeEditingService:
    """獲取協作編輯服務單例"""
    global _collaborative_service
    if not _collaborative_service:
        _collaborative_service = CollaborativeEditingService()
    return _collaborative_service
