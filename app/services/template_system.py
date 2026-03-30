"""
模板系統
支持場景模板、提示詞模板、項目模板等
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class TemplateType(str, Enum):
    """模板類型"""
    SCENE = "scene"
    PROMPT = "prompt"
    PROJECT = "project"
    CHARACTER = "character"
    WORKFLOW = "workflow"


class TemplateCategory(str, Enum):
    """模板分類"""
    ACTION = "action"  # 動作
    DRAMA = "drama"  # 劇情
    ROMANCE = "romance"  # 愛情
    COMEDY = "comedy"  # 喜劇
    HORROR = "horror"  # 恐怖
    SCI_FI = "sci_fi"  # 科幻
    FANTASY = "fantasy"  # 奇幻
    DOCUMENTARY = "documentary"  # 紀錄片
    COMMERCIAL = "commercial"  # 廣告
    EDUCATIONAL = "educational"  # 教育
    SOCIAL_MEDIA = "social_media"  # 社交媒體


@dataclass
class Template:
    """模板"""
    id: str
    name: str
    description: str
    type: TemplateType
    category: TemplateCategory
    content: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    
    # 統計
    usage_count: int = 0
    average_rating: float = 0.0
    rating_count: int = 0
    
    # 元數據
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_public: bool = False
    is_featured: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "category": self.category.value,
            "content": self.content,
            "tags": self.tags,
            "thumbnail_url": self.thumbnail_url,
            "preview_url": self.preview_url,
            "usage_count": self.usage_count,
            "average_rating": round(self.average_rating, 2),
            "rating_count": self.rating_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "is_public": self.is_public,
            "is_featured": self.is_featured,
        }


class TemplateService:
    """
    模板服務
    
    功能：
    1. 場景模板
    2. 提示詞模板
    3. 項目模板
    4. 角色模板
    5. 工作流模板
    6. 模板市場
    7. 模板評分
    8. 智能推薦
    """
    
    def __init__(self):
        self._templates: Dict[str, Template] = {}
        self._register_default_templates()
    
    def _register_default_templates(self):
        """註冊默認模板"""
        import uuid
        
        # 場景模板
        self._templates[str(uuid.uuid4())] = Template(
            id=str(uuid.uuid4()),
            name="英雄登場",
            description="經典的英雄登場場景，適合動作片、奇幻片",
            type=TemplateType.SCENE,
            category=TemplateCategory.ACTION,
            content={
                "title": "英雄登場",
                "description": "主角在戲劇性的場景中登場",
                "narrative_text": "晨光熹微，英雄獨自登上山巔，遠眺遠方的城池...",
                "positive_prompt": "cinematic shot, heroic figure, mountain peak, dawn lighting, masterpiece, dramatic atmosphere",
                "negative_prompt": "ugly, deformed, noisy, blurry, low quality, watermark",
                "duration": 8.0,
                "resolution": "1920x1080",
                "fps": 24,
            },
            tags=["英雄", "登場", "動作", "戲劇性"],
            is_public=True,
            is_featured=True,
        )
        
        # 提示詞模板
        self._templates[str(uuid.uuid4())] = Template(
            id=str(uuid.uuid4()),
            name="電影級畫質",
            description="專業電影級別的視覺效果提示詞",
            type=TemplateType.PROMPT,
            category=TemplateCategory.COMMERCIAL,
            content={
                "positive_prompt": "cinematic shot, masterpiece, film grain, color graded, professional photography, 8k, ultra detailed",
                "negative_prompt": "ugly, deformed, noisy, blurry, low quality, watermark, text, signature",
                "style": "cinematic",
                "guidance_scale": 7.5,
                "steps": 25,
            },
            tags=["電影級", "專業", "高質量"],
            is_public=True,
            is_featured=True,
        )
        
        # 社交媒體模板
        self._templates[str(uuid.uuid4())] = Template(
            id=str(uuid.uuid4()),
            name="Instagram 短視頻",
            description="適合 Instagram/TikTok 的豎屏短視頻",
            type=TemplateType.SCENE,
            category=TemplateCategory.SOCIAL_MEDIA,
            content={
                "title": "社交媒體短視頻",
                "description": "豎屏 9:16 比例，適合手機觀看",
                "positive_prompt": "vertical video, social media style, vibrant colors, engaging, trendy",
                "negative_prompt": "horizontal, boring, dull colors",
                "duration": 15.0,
                "resolution": "1080x1920",
                "aspect_ratio": "9:16",
                "fps": 30,
            },
            tags=["社交媒體", "豎屏", "短視頻"],
            is_public=True,
            is_featured=True,
        )
    
    def create_template(self, template: Template) -> Template:
        """創建模板"""
        self._templates[template.id] = template
        logger.info("template_created", template_id=template.id, name=template.name)
        return template
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """獲取模板"""
        return self._templates.get(template_id)
    
    def get_templates(
        self,
        template_type: Optional[TemplateType] = None,
        category: Optional[TemplateCategory] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Template]:
        """獲取模板列表"""
        templates = list(self._templates.values())
        
        # 過濾
        if template_type:
            templates = [t for t in templates if t.type == template_type]
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]
        
        # 排序 (按評分和使用次數)
        templates.sort(
            key=lambda t: (t.is_featured, t.average_rating, t.usage_count),
            reverse=True
        )
        
        return templates[offset:offset + limit]
    
    def search_templates(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Template]:
        """搜索模板"""
        query_lower = query.lower()
        
        results = []
        for template in self._templates.values():
            # 搜索名稱、描述、標籤
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)
        
        # 按相關性排序
        results.sort(
            key=lambda t: (
                query_lower in t.name.lower(),
                query_lower in t.description.lower(),
                t.usage_count,
            ),
            reverse=True
        )
        
        return results[:limit]
    
    def apply_template(
        self,
        template_id: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        應用模板
        
        Args:
            template_id: 模板 ID
            overrides: 覆蓋參數
            
        Returns:
            Dict: 合併後的數據
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # 複製模板內容
        result = template.content.copy()
        
        # 應用覆蓋
        if overrides:
            result.update(overrides)
        
        # 增加使用次數
        template.usage_count += 1
        
        logger.info(
            "template_applied",
            template_id=template_id,
            usage_count=template.usage_count,
        )
        
        return result
    
    def rate_template(
        self,
        template_id: str,
        rating: int,
        user_id: str,
    ):
        """評分模板"""
        template = self.get_template(template_id)
        if not template:
            return
        
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        # 更新平均評分
        total_rating = template.average_rating * template.rating_count
        template.rating_count += 1
        template.average_rating = (total_rating + rating) / template.rating_count
        
        logger.info(
            "template_rated",
            template_id=template_id,
            rating=rating,
            new_average=template.average_rating,
        )
    
    def get_featured_templates(self, limit: int = 10) -> List[Template]:
        """獲取推薦模板"""
        featured = [t for t in self._templates.values() if t.is_featured]
        featured.sort(key=lambda t: t.usage_count, reverse=True)
        return featured[:limit]
    
    def get_similar_templates(
        self,
        template_id: str,
        limit: int = 5,
    ) -> List[Template]:
        """獲取相似模板"""
        template = self.get_template(template_id)
        if not template:
            return []
        
        # 基於類型和標籤推薦
        similar = [
            t for t in self._templates.values()
            if t.id != template_id and
               t.type == template.type and
               any(tag in template.tags for tag in t.tags)
        ]
        
        similar.sort(key=lambda t: t.usage_count, reverse=True)
        return similar[:limit]


# 全局服務實例
_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """獲取模板服務單例"""
    global _template_service
    if not _template_service:
        _template_service = TemplateService()
    return _template_service
