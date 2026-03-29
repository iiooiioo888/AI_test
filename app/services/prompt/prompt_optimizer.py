"""
提示詞優化服務
使用 LLM 進行提示詞重寫、優化、質量評估
"""
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class OptimizedPrompt(BaseModel):
    """優化後的提示詞"""
    original_prompt: str
    optimized_prompt: str
    negative_prompt: str
    improvements: List[str] = Field(default_factory=list)
    quality_score: float = Field(0.0, ge=0.0, le=1.0)
    estimated_tokens: int = 0
    model_used: str = ""
    optimized_at: datetime = Field(default_factory=datetime.utcnow)


class PromptQualityMetrics(BaseModel):
    """提示詞質量指標"""
    clarity_score: float = Field(0.0, ge=0.0, le=1.0)  # 清晰度
    specificity_score: float = Field(0.0, ge=0.0, le=1.0)  # 具體性
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)  # 完整性
    consistency_score: float = Field(0.0, ge=0.0, le=1.0)  # 一致性
    overall_score: float = Field(0.0, ge=0.0, le=1.0)  # 總分
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class PromptOptimizerService:
    """
    提示詞優化服務
    
    功能：
    1. 提示詞重寫 (LLM)
    2. 負向提示詞生成
    3. 質量評估
    4. 成本估算
    
    設計理由：
    - 企業級應用需要高質量提示詞
    - 自動化優化減少人工干預
    - 質量評估確保輸出穩定性
    """
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        # TODO: 初始化 LLM 客戶端
        # self.client = openai.Client()
    
    async def optimize_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        style: str = "cinematic",
    ) -> OptimizedPrompt:
        """
        優化提示詞
        
        Args:
            prompt: 原始提示詞
            context: 上下文信息 (場景、角色等)
            style: 風格類型 (cinematic, anime, realistic)
            
        Returns:
            OptimizedPrompt: 優化結果
        """
        # 1. 分析原始提示詞
        analysis = self._analyze_prompt(prompt)
        
        # 2. 構建優化請求
        system_prompt = self._build_system_prompt(style)
        user_prompt = self._build_user_prompt(prompt, analysis, context)
        
        # 3. 調用 LLM (TODO: 實際實現)
        # response = await self._call_llm(system_prompt, user_prompt)
        
        # 模擬優化結果
        optimized = self._mock_optimize(prompt, style)
        
        # 4. 質量評估
        quality = self.evaluate_quality(optimized.optimized_prompt)
        
        logger.info(
            "prompt_optimized",
            original_length=len(prompt),
            optimized_length=len(optimized.optimized_prompt),
            quality_score=quality.overall_score,
        )
        
        return OptimizedPrompt(
            original_prompt=prompt,
            optimized_prompt=optimized.optimized_prompt,
            negative_prompt=optimized.negative_prompt,
            improvements=optimized.improvements,
            quality_score=quality.overall_score,
            estimated_tokens=self._count_tokens(optimized.optimized_prompt),
            model_used=self.llm_provider,
        )
    
    def _analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """分析提示詞結構"""
        # 檢查是否包含關鍵元素
        has_subject = any(word in prompt.lower() for word in ["man", "woman", "person", "character"])
        has_action = any(word in prompt.lower() for word in ["running", "walking", "standing", "sitting"])
        has_environment = any(word in prompt.lower() for word in ["street", "room", "forest", "city"])
        has_lighting = any(word in prompt.lower() for word in ["sunlight", "moonlight", "neon", "dark"])
        has_style = any(word in prompt.lower() for word in ["cinematic", "realistic", "anime", "3d"])
        
        return {
            "has_subject": has_subject,
            "has_action": has_action,
            "has_environment": has_environment,
            "has_lighting": has_lighting,
            "has_style": has_style,
            "word_count": len(prompt.split()),
            "missing_elements": self._identify_missing_elements(
                has_subject, has_action, has_environment, has_lighting, has_style
            ),
        }
    
    def _identify_missing_elements(
        self,
        has_subject: bool,
        has_action: bool,
        has_environment: bool,
        has_lighting: bool,
        has_style: bool,
    ) -> List[str]:
        """識別缺失的元素"""
        missing = []
        if not has_subject:
            missing.append("subject (主角/對象)")
        if not has_action:
            missing.append("action (動作/行為)")
        if not has_environment:
            missing.append("environment (環境/場景)")
        if not has_lighting:
            missing.append("lighting (光照)")
        if not has_style:
            missing.append("style (風格)")
        return missing
    
    def _build_system_prompt(self, style: str) -> str:
        """構建系統提示詞"""
        style_guidelines = {
            "cinematic": "電影級視覺，注重構圖、光影、色彩分级",
            "anime": "日式動畫風格，注重線條、色彩、表情",
            "realistic": "照片級真實，注重細節、質感、光影",
            "3d": "3D 渲染風格，注重材質、光照、景深",
        }
        
        return f"""你是一位專業的 AI 視頻提示詞工程師。
你的任務是將用戶的簡單描述轉換為高質量的視頻生成提示詞。

{style_guidelines.get(style, "")}

輸出格式要求：
1. 主體描述 (誰/什麼)
2. 動作/狀態 (在做什麼)
3. 環境/場景 (在哪裡)
4. 光照/氣氛 (光線如何)
5. 風格/質感 (視覺風格)
6. 攝影/構圖 (鏡頭語言)

使用英文輸出，因為視頻生成模型對英文理解更好。"""
    
    def _build_user_prompt(
        self,
        original: str,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """構建用戶提示詞"""
        missing = analysis.get("missing_elements", [])
        
        prompt = f"""原始描述：{original}

請優化這個描述，使其適合 AI 視頻生成。"""
        
        if missing:
            prompt += f"\n\n建議補充：{', '.join(missing)}"
        
        if context:
            if context.get("character"):
                prompt += f"\n角色信息：{context['character']}"
            if context.get("location"):
                prompt += f"\n地點信息：{context['location']}"
            if context.get("time"):
                prompt += f"\n時間：{context['time']}"
        
        return prompt
    
    def _mock_optimize(self, prompt: str, style: str) -> OptimizedPrompt:
        """模擬優化 (TODO: 替換為真實 LLM 調用)"""
        # 風格模板
        style_templates = {
            "cinematic": "cinematic shot, masterpiece, film grain, color graded",
            "anime": "anime style, studio ghibli, makoto shinkai, vibrant colors",
            "realistic": "photorealistic, 8k, highly detailed, professional photography",
            "3d": "3d render, octane render, unreal engine 5, ray tracing",
        }
        
        base_template = "{subject}, {action}, {environment}, {lighting}, {style}"
        
        # 簡單分析並填充
        optimized = prompt
        if style in style_templates:
            optimized += f", {style_templates[style]}"
        
        # 添加通用優化詞
        optimized += ", professional, high quality, detailed"
        
        # 生成負向提示詞
        negative = "ugly, deformed, noisy, blurry, low quality, watermark, text"
        
        return OptimizedPrompt(
            original_prompt=prompt,
            optimized_prompt=optimized,
            negative_prompt=negative,
            improvements=[
                "添加了風格關鍵詞",
                "增強了質量描述",
                "生成了負向提示詞",
            ],
            quality_score=0.85,
        )
    
    def evaluate_quality(self, prompt: str) -> PromptQualityMetrics:
        """
        評估提示詞質量
        
        Returns:
            PromptQualityMetrics: 質量指標
        """
        # 清晰度：句子是否通順
        clarity = self._evaluate_clarity(prompt)
        
        # 具體性：是否有足夠細節
        specificity = self._evaluate_specificity(prompt)
        
        # 完整性：是否包含關鍵元素
        completeness = self._evaluate_completeness(prompt)
        
        # 一致性：是否有矛盾描述
        consistency = self._evaluate_consistency(prompt)
        
        # 總分
        overall = (clarity + specificity + completeness + consistency) / 4
        
        return PromptQualityMetrics(
            clarity_score=clarity,
            specificity_score=specificity,
            completeness_score=completeness,
            consistency_score=consistency,
            overall_score=overall,
            issues=self._identify_issues(prompt),
            suggestions=self._generate_suggestions(prompt),
        )
    
    def _evaluate_clarity(self, prompt: str) -> float:
        """評估清晰度"""
        # 簡單指標：句子長度、語法結構
        words = prompt.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        
        # 理想平均詞長 4-6 個字母
        if 4 <= avg_word_length <= 6:
            return 0.9
        elif 3 <= avg_word_length <= 7:
            return 0.7
        else:
            return 0.5
    
    def _evaluate_specificity(self, prompt: str) -> float:
        """評估具體性"""
        # 檢查形容詞和細節詞
        detail_words = ["detailed", "intricate", "elaborate", "complex", "fine", "rich"]
        count = sum(1 for word in detail_words if word in prompt.lower())
        
        return min(1.0, count / 3.0)
    
    def _evaluate_completeness(self, prompt: str) -> float:
        """評估完整性"""
        elements = {
            "subject": any(w in prompt.lower() for w in ["man", "woman", "person", "girl", "boy"]),
            "action": any(w in prompt.lower() for w in ["walking", "running", "standing", "sitting"]),
            "environment": any(w in prompt.lower() for w in ["street", "room", "city", "forest"]),
            "lighting": any(w in prompt.lower() for w in ["light", "sun", "moon", "neon", "dark"]),
        }
        
        present = sum(1 for v in elements.values() if v)
        return present / len(elements)
    
    def _evaluate_consistency(self, prompt: str) -> float:
        """評估一致性"""
        # 檢查是否有矛盾詞
        contradictions = [
            ("bright", "dark"),
            ("day", "night"),
            ("summer", "winter"),
            ("indoor", "outdoor"),
        ]
        
        prompt_lower = prompt.lower()
        for word1, word2 in contradictions:
            if word1 in prompt_lower and word2 in prompt_lower:
                return 0.5  # 發現矛盾
        
        return 1.0
    
    def _identify_issues(self, prompt: str) -> List[str]:
        """識別問題"""
        issues = []
        
        if len(prompt.split()) < 10:
            issues.append("提示詞過短，可能缺乏細節")
        
        if len(prompt) > 1000:
            issues.append("提示詞過長，可能超出模型限制")
        
        if prompt.count(",") < 3:
            issues.append("建議使用更多逗號分隔不同元素")
        
        return issues
    
    def _generate_suggestions(self, prompt: str) -> List[str]:
        """生成建議"""
        suggestions = []
        
        if "lighting" not in prompt.lower() and "light" not in prompt.lower():
            suggestions.append("添加光照描述 (如：cinematic lighting, natural light)")
        
        if "style" not in prompt.lower() and "cinematic" not in prompt.lower():
            suggestions.append("指定視覺風格 (如：cinematic, realistic, anime)")
        
        if "quality" not in prompt.lower() and "masterpiece" not in prompt.lower():
            suggestions.append("添加質量關鍵詞 (如：masterpiece, high quality)")
        
        return suggestions
    
    def _count_tokens(self, text: str) -> int:
        """估算 token 數量"""
        # 簡單估算：英文單詞數 * 1.3
        words = text.split()
        return int(len(words) * 1.3)
    
    async def batch_optimize(
        self,
        prompts: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[OptimizedPrompt]:
        """批量優化提示詞"""
        results = []
        for prompt in prompts:
            result = await self.optimize_prompt(prompt, context)
            results.append(result)
        return results


# 全局服務實例
_prompt_optimizer_instance: Optional[PromptOptimizerService] = None


def get_prompt_optimizer() -> PromptOptimizerService:
    """獲取提示詞優化器單例"""
    global _prompt_optimizer_instance
    if not _prompt_optimizer_instance:
        _prompt_optimizer_instance = PromptOptimizerService()
    return _prompt_optimizer_instance
