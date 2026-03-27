"""
場景數據模型 - JSON 結構化存儲
遵循企業級 AVP 規格，支持場景生命周期與全局連貫性檢查
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class SceneStatus(str, Enum):
    """場景区生命周期狀態機"""
    DRAFT = "draft"           # 草稿 - 可編輯
    REVIEW = "review"         # 審核中 - 等待審批
    LOCKED = "locked"         # 已鎖定 - 不可修改
    QUEUED = "queued"         # 已排隊 - 等待生成
    GENERATING = "generating" # 生成中 - 正在渲染
    COMPLETED = "completed"   # 已完成 - 生成成功
    FAILED = "failed"         # 失敗 - 需要重試或修改


class Character(BaseModel):
    """角色定義"""
    id: str = Field(..., description="角色唯一標識")
    name: str = Field(..., description="角色名稱")
    description: str = Field(..., description="角色描述")
    appearance: str = Field(..., description="外貌特徵")
    personality: str = Field("", description="性格特點")
    relationships: List[str] = Field(default_factory=list, description="與其他角色的關係 ID")
    locked_features: Dict[str, Any] = Field(default_factory=dict, description="鎖定特徵 (FaceID, LoRA 等)")


class Prop(BaseModel):
    """道具/物件定義"""
    id: str = Field(..., description="道具唯一標識")
    name: str = Field(..., description="道具名稱")
    description: str = Field(..., description="道具描述")
    type: Literal["weapon", "vehicle", "furniture", "clothing", "other"] = Field(..., description="道具類型")
    importance: int = Field(1, ge=1, le=5, description="重要性等級 (1-5)")


class Location(BaseModel):
    """場景地點定義"""
    id: str = Field(..., description="地點唯一標識")
    name: str = Field(..., description="地點名稱")
    description: str = Field(..., description="地點描述")
    environment_type: str = Field(..., description="環境類型 (室內/室外/奇幻等)")
    lighting: str = Field("natural", description="光照條件")
    weather: Optional[str] = Field(None, description="天氣條件")
    time_of_day: Literal["dawn", "morning", "noon", "afternoon", "dusk", "night"] = Field("noon", description="時間")


class CameraSetup(BaseModel):
    """攝影機設置"""
    angle: str = Field("eye_level", description="攝影角度")
    movement: str = Field("static", description="攝影機運動")
    focal_length: float = Field(35.0, description="焦距 (mm)")
    aperture: float = Field(2.8, description="光圈")
    depth_of_field: str = Field("medium", description="景深")


class SceneObject(BaseModel):
    """
    核心場景對象 - JSON 結構化存儲
    支持版本控制、分支管理、全局連貫性檢查
    """
    # 基礎識別
    id: str = Field(..., description="場景唯一標識 (UUID)")
    version: str = Field("1.0.0", description="語義化版本號")
    branch: str = Field("main", description="分支名稱 (支持多版本)")
    
    # 內容定義
    title: str = Field(..., description="場景標題")
    description: str = Field(..., description="場景描述")
    narrative_text: str = Field(..., description="敘事文本/劇本")
    
    # 場景元素
    characters: List[Character] = Field(default_factory=list, description="登場角色")
    props: List[Prop] = Field(default_factory=list, description="場景道具")
    location: Optional[Location] = Field(None, description="場景地點")
    
    # 技術參數
    camera: Optional[CameraSetup] = Field(None, description="攝影機設置")
    duration: float = Field(5.0, ge=0.1, le=300.0, description="場景時長 (秒)")
    aspect_ratio: str = Field("16:9", description="畫幅比例")
    resolution: str = Field("1920x1080", description="解析度")
    fps: int = Field(24, ge=24, le=60, description="幀率")
    
    # 提示詞工程
    positive_prompt: str = Field(..., description="正向提示詞")
    negative_prompt: str = Field("", description="負向提示詞")
    prompt_weights: Dict[str, float] = Field(default_factory=dict, description="提示詞權重")
    style_lora: Optional[str] = Field(None, description="風格 LoRA 模型")
    character_lora: Optional[str] = Field(None, description="角色 LoRA 模型")
    
    # 狀態機
    status: SceneStatus = Field(SceneStatus.DRAFT, description="場景狀態")
    previous_scene_id: Optional[str] = Field(None, description="前一場景 ID (用於連貫性)")
    next_scene_id: Optional[str] = Field(None, description="下一場景 ID")
    
    # 依賴關係 (漣漪效應分析)
    dependencies: List[str] = Field(default_factory=list, description="依賴的場景/角色/道具 ID")
    dependents: List[str] = Field(default_factory=list, description="被哪些場景依賴")
    
    # 生成結果
    generated_video_url: Optional[str] = Field(None, description="生成視頻 URL")
    generated_thumbnail_url: Optional[str] = Field(None, description="縮略圖 URL")
    quality_metrics: Optional[Dict[str, float]] = Field(None, description="質量指標 (VMAF, CLIP Score 等)")
    
    # 協作與審計
    created_by: str = Field(..., description="創建者 ID")
    updated_by: str = Field(..., description="最後更新者 ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")
    locked_by: Optional[str] = Field(None, description="鎖定者 ID")
    locked_at: Optional[datetime] = Field(None, description="鎖定時間")
    
    # 元數據
    tags: List[str] = Field(default_factory=list, description="標籤")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定義元數據")
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        """驗證語義化版本號"""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('版本號必須符合語義化版本規範 (semver)')
        return v
    
    @field_validator('updated_at')
    @classmethod
    def validate_updated_at(cls, v, info):
        """確保 updated_at >= created_at"""
        if 'created_at' in info.data and v < info.data['created_at']:
            raise ValueError('更新時間不能早於創建時間')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "scene-001",
                "version": "1.0.0",
                "branch": "main",
                "title": "英雄登場",
                "description": "主角在黎明時分登上山巔",
                "narrative_text": "晨光熹微，英雄獨自登上山巔，遠眺遠方的城池...",
                "characters": [
                    {
                        "id": "char-001",
                        "name": "李明",
                        "description": "年輕的武者",
                        "appearance": "黑色長髮，銳利的眼神，身穿青色長袍"
                    }
                ],
                "location": {
                    "id": "loc-001",
                    "name": "青雲山巔",
                    "description": "雲霧繚繞的山頂",
                    "environment_type": "outdoor",
                    "time_of_day": "dawn"
                },
                "status": "draft",
                "positive_prompt": "cinematic shot, heroic figure, mountain peak, dawn lighting, masterpiece",
                "negative_prompt": "ugly, deformed, noisy, blurry, low quality",
                "duration": 8.0,
                "resolution": "1920x1080",
                "fps": 24
            }
        }


class SceneDiff(BaseModel):
    """場景差異比對結果 (用於 CRDT 協作)"""
    field_path: str = Field(..., description="字段路徑")
    old_value: Any = Field(None, description="舊值")
    new_value: Any = Field(None, description="新值")
    operation: Literal["create", "update", "delete"] = Field(..., description="操作類型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="操作時間")
    user_id: str = Field(..., description="操作者 ID")


class SceneBranch(BaseModel):
    """場景分支管理"""
    id: str = Field(..., description="分支唯一標識")
    name: str = Field(..., description="分支名稱")
    base_version: str = Field(..., description="基礎版本")
    created_from: str = Field(..., description="從哪個分支創建")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    created_by: str = Field(..., description="創建者")
    merged: bool = Field(False, description="是否已合併")
    merged_at: Optional[datetime] = Field(None, description="合併時間")
