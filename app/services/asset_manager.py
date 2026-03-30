"""
資產管理服務
素材庫、音樂庫、音效庫、圖片庫、3D 模型庫等
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class AssetType(str, Enum):
    """資產類型"""
    VIDEO = "video"
    AUDIO = "audio"
    MUSIC = "music"
    SFX = "sfx"  # 音效
    IMAGE = "image"
    MODEL_3D = "model_3d"
    FONT = "font"
    TEMPLATE = "template"
    PRESET = "preset"


class AssetCategory(str, Enum):
    """資產分類"""
    ACTION = "action"
    DRAMA = "drama"
    COMEDY = "comedy"
    ROMANCE = "romance"
    HORROR = "horror"
    SCI_FI = "sci_fi"
    DOCUMENTARY = "documentary"
    COMMERCIAL = "commercial"
    SOCIAL_MEDIA = "social_media"
    EDUCATIONAL = "educational"


@dataclass
class Asset:
    """資產"""
    id: str
    name: str
    description: str
    type: AssetType
    category: AssetCategory
    file_path: str
    file_size: int  # 字節
    duration: Optional[float] = None  # 音頻/視頻時長
    resolution: Optional[str] = None  # 視頻/圖片解析度
    tags: List[str] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    
    # 元數據
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # 統計
    usage_count: int = 0
    download_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    
    # 授權
    license: str = "standard"
    is_public: bool = False
    is_premium: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "category": self.category.value,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "duration": self.duration,
            "resolution": self.resolution,
            "tags": self.tags,
            "thumbnail_url": self.thumbnail_url,
            "preview_url": self.preview_url,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "usage_count": self.usage_count,
            "download_count": self.download_count,
            "rating": round(self.rating, 2),
            "license": self.license,
            "is_public": self.is_public,
            "is_premium": self.is_premium,
        }


class AssetManagerService:
    """
    資產管理服務
    
    功能：
    1. 素材庫管理 (視頻/圖片)
    2. 音樂庫管理
    3. 音效庫管理
    4. 3D 模型庫
    5. 字體庫
    6. 模板庫
    7. 預設庫
    8. 智能標籤
    9. 智能搜索
    10. 收藏夾管理
    """
    
    def __init__(self):
        self._assets: Dict[str, Asset] = {}
        self._collections: Dict[str, Dict] = {}
        self._register_default_assets()
    
    def _register_default_assets(self):
        """註冊默認資產"""
        import uuid
        
        # 默認音樂
        self._assets[str(uuid.uuid4())] = Asset(
            id=str(uuid.uuid4()),
            name="史詩背景音樂",
            description="適合動作場面的史詩音樂",
            type=AssetType.MUSIC,
            category=AssetCategory.ACTION,
            file_path="/music/epic_001.mp3",
            file_size=5 * 1024 * 1024,
            duration=180.0,
            tags=["史詩", "動作", "背景音樂", "激昂"],
            is_public=True,
        )
        
        # 默認音效
        self._assets[str(uuid.uuid4())] = Asset(
            id=str(uuid.uuid4()),
            name="爆炸音效",
            description="大型爆炸音效",
            type=AssetType.SFX,
            category=AssetCategory.ACTION,
            file_path="/sfx/explosion_001.wav",
            file_size=2 * 1024 * 1024,
            duration=3.0,
            tags=["爆炸", "音效", "動作"],
            is_public=True,
        )
        
        # 默認圖片
        self._assets[str(uuid.uuid4())] = Asset(
            id=str(uuid.uuid4()),
            name="城市夜景背景",
            description="現代城市夜景",
            type=AssetType.IMAGE,
            category=AssetCategory.SCI_FI,
            file_path="/images/city_night_001.jpg",
            file_size=3 * 1024 * 1024,
            resolution="1920x1080",
            tags=["城市", "夜景", "背景", "現代"],
            thumbnail_url="/thumbnails/city_night_001.jpg",
            is_public=True,
        )
    
    # ========================================================================
    # 資產 CRUD
    # ========================================================================
    
    def add_asset(self, asset: Asset) -> Asset:
        """添加資產"""
        self._assets[asset.id] = asset
        logger.info("asset_added", asset_id=asset.id, name=asset.name, type=asset.type.value)
        return asset
    
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """獲取資產"""
        return self._assets.get(asset_id)
    
    def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> Asset:
        """更新資產"""
        asset = self.get_asset(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")
        
        for key, value in updates.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        
        asset.updated_at = datetime.utcnow()
        logger.info("asset_updated", asset_id=asset_id)
        return asset
    
    def delete_asset(self, asset_id: str):
        """刪除資產"""
        if asset_id in self._assets:
            del self._assets[asset_id]
            logger.info("asset_deleted", asset_id=asset_id)
    
    # ========================================================================
    # 搜索與過濾
    # ========================================================================
    
    def search_assets(
        self,
        query: str,
        asset_type: Optional[AssetType] = None,
        category: Optional[AssetCategory] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Asset]:
        """搜索資產"""
        query_lower = query.lower()
        
        results = []
        for asset in self._assets.values():
            # 過濾公開資產
            if is_public and not asset.is_public:
                continue
            
            # 過濾類型
            if asset_type and asset.type != asset_type:
                continue
            
            # 過濾分類
            if category and asset.category != category:
                continue
            
            # 搜索文本
            if query and not (
                query_lower in asset.name.lower() or
                query_lower in asset.description.lower() or
                any(query_lower in tag.lower() for tag in asset.tags)
            ):
                continue
            
            # 過濾標籤
            if tags and not any(tag in asset.tags for tag in tags):
                continue
            
            results.append(asset)
        
        # 排序 (按相關性、使用次數、評分)
        results.sort(key=lambda a: (a.usage_count, a.rating), reverse=True)
        
        return results[offset:offset + limit]
    
    def get_assets_by_type(
        self,
        asset_type: AssetType,
        limit: int = 50,
    ) -> List[Asset]:
        """按類型獲取資產"""
        assets = [a for a in self._assets.values() if a.type == asset_type]
        assets.sort(key=lambda a: a.usage_count, reverse=True)
        return assets[:limit]
    
    def get_featured_assets(self, limit: int = 20) -> List[Asset]:
        """獲取推薦資產"""
        featured = [a for a in self._assets.values() if a.is_public]
        featured.sort(key=lambda a: (a.is_premium, a.rating, a.usage_count), reverse=True)
        return featured[:limit]
    
    # ========================================================================
    # 收藏夾管理
    # ========================================================================
    
    def create_collection(
        self,
        name: str,
        description: str = "",
        user_id: str = "",
    ) -> Dict[str, Any]:
        """創建收藏夾"""
        import uuid
        
        collection = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "user_id": user_id,
            "asset_ids": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        self._collections[collection["id"]] = collection
        logger.info("collection_created", collection_id=collection["id"], name=name)
        return collection
    
    def add_to_collection(
        self,
        collection_id: str,
        asset_id: str,
    ):
        """添加資產到收藏夾"""
        collection = self._collections.get(collection_id)
        if not collection:
            raise ValueError(f"Collection not found: {collection_id}")
        
        if asset_id not in collection["asset_ids"]:
            collection["asset_ids"].append(asset_id)
            collection["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info("asset_added_to_collection", collection_id=collection_id, asset_id=asset_id)
    
    def remove_from_collection(
        self,
        collection_id: str,
        asset_id: str,
    ):
        """從收藏夾移除資產"""
        collection = self._collections.get(collection_id)
        if not collection:
            return
        
        if asset_id in collection["asset_ids"]:
            collection["asset_ids"].remove(asset_id)
            collection["updated_at"] = datetime.utcnow().isoformat()
    
    def get_collection(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """獲取收藏夾"""
        return self._collections.get(collection_id)
    
    def get_user_collections(self, user_id: str) -> List[Dict[str, Any]]:
        """獲取用戶收藏夾"""
        return [
            c for c in self._collections.values()
            if c["user_id"] == user_id
        ]
    
    # ========================================================================
    # 使用統計
    # ========================================================================
    
    def record_usage(self, asset_id: str):
        """記錄資產使用"""
        asset = self.get_asset(asset_id)
        if asset:
            asset.usage_count += 1
            logger.debug("asset_usage_recorded", asset_id=asset_id, count=asset.usage_count)
    
    def record_download(self, asset_id: str):
        """記錄下載"""
        asset = self.get_asset(asset_id)
        if asset:
            asset.download_count += 1
            logger.debug("asset_download_recorded", asset_id=asset_id, count=asset.download_count)
    
    def rate_asset(self, asset_id: str, rating: int, user_id: str):
        """評分資產"""
        asset = self.get_asset(asset_id)
        if not asset:
            return
        
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        # 更新平均評分
        total_rating = asset.rating * asset.rating_count
        asset.rating_count += 1
        asset.rating = (total_rating + rating) / asset.rating_count
        
        logger.info(
            "asset_rated",
            asset_id=asset_id,
            rating=rating,
            new_rating=asset.rating,
        )
    
    # ========================================================================
    # 批量操作
    # ========================================================================
    
    def bulk_upload(
        self,
        assets: List[Asset],
        auto_tag: bool = True,
    ) -> Dict[str, Any]:
        """批量上傳資產"""
        success_count = 0
        failed_count = 0
        errors = []
        
        for asset in assets:
            try:
                # 自動標籤
                if auto_tag:
                    asset.tags.extend(self._auto_generate_tags(asset))
                
                self.add_asset(asset)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"asset": asset.name, "error": str(e)})
        
        return {
            "total": len(assets),
            "successful": success_count,
            "failed": failed_count,
            "errors": errors[:10],
        }
    
    def _auto_generate_tags(self, asset: Asset) -> List[str]:
        """自動生成標籤"""
        tags = []
        
        # 基於類型
        tags.append(asset.type.value)
        tags.append(asset.category.value)
        
        # 基於名稱
        name_words = asset.name.lower().split()
        tags.extend([w for w in name_words if len(w) > 3])
        
        return list(set(tags))
    
    # ========================================================================
    # 導出/導入
    # ========================================================================
    
    def export_collection(
        self,
        collection_id: str,
        format: str = "json",
    ) -> str:
        """導出收藏夾"""
        collection = self.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection not found: {collection_id}")
        
        # 獲取所有資產
        assets = [
            self.get_asset(aid).to_dict()
            for aid in collection["asset_ids"]
            if self.get_asset(aid)
        ]
        
        import json
        return json.dumps({
            "collection": collection,
            "assets": assets,
        }, ensure_ascii=False, indent=2)
    
    def import_assets(
        self,
        json_data: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """導入資產"""
        import json
        
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}
        
        assets_data = data.get("assets", [])
        
        success_count = 0
        for asset_data in assets_data:
            try:
                asset = Asset(
                    id=asset_data.get("id", ""),
                    name=asset_data.get("name", ""),
                    description=asset_data.get("description", ""),
                    type=AssetType(asset_data.get("type", "video")),
                    category=AssetCategory(asset_data.get("category", "action")),
                    file_path=asset_data.get("file_path", ""),
                    file_size=asset_data.get("file_size", 0),
                    tags=asset_data.get("tags", []),
                    created_by=user_id,
                )
                self.add_asset(asset)
                success_count += 1
            except Exception as e:
                logger.error("asset_import_failed", error=str(e))
        
        return {
            "total": len(assets_data),
            "successful": success_count,
        }


# 全局服務實例
_asset_manager_service: Optional[AssetManagerService] = None


def get_asset_manager_service() -> AssetManagerService:
    """獲取資產管理服務單例"""
    global _asset_manager_service
    if not _asset_manager_service:
        _asset_manager_service = AssetManagerService()
    return _asset_manager_service
