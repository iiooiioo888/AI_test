"""
RAG (Retrieval-Augmented Generation) 檢索服務
從 Milvus 向量庫檢索歷史成功案例
"""
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import structlog

logger = structlog.get_logger()


class RetrievalResult(BaseModel):
    """檢索結果"""
    prompt_id: str
    content: str
    similarity_score: float
    success_rate: float
    reuse_count: int
    quality_score: float
    category: str
    tags: List[str]
    metadata: Dict[str, Any]


class RAGRetrieverService:
    """
    RAG 檢索服務
    
    功能：
    1. 向量相似度搜索
    2. 歷史成功案例檢索
    3. 智能推薦
    4. 檢索結果重排序
    
    設計理由：
    - 利用歷史成功案例提高生成質量
    - 向量搜索找到語義相似的提示詞
    - 多維度排序 (相似度 + 成功率 + 質量)
    """
    
    def __init__(self, milvus_host: str = "localhost", milvus_port: int = 19530):
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = "prompts"
        self.embedding_model = None  # TODO: 初始化嵌入模型
    
    async def connect(self):
        """連接到 Milvus"""
        # TODO: 實現 Milvus 連接
        logger.info("rag_connected", host=self.milvus_host, port=self.milvus_port)
    
    async def disconnect(self):
        """斷開連接"""
        logger.info("rag_disconnected")
    
    async def search_similar_prompts(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        搜索相似提示詞
        
        Args:
            query: 查詢文本
            limit: 返回數量
            filters: 過濾條件 (category, tags 等)
            
        Returns:
            List[RetrievalResult]: 檢索結果
        """
        # 1. 生成查詢向量
        # query_embedding = await self._generate_embedding(query)
        query_embedding = self._mock_embedding(query)  # TODO: 替換為真實嵌入
        
        # 2. 執行向量搜索
        # results = await self._milvus_search(query_embedding, limit, filters)
        results = self._mock_search_results(query, limit)  # TODO: 替換為真實搜索
        
        logger.info(
            "rag_search_completed",
            query_length=len(query),
            results_count=len(results),
        )
        
        return results
    
    async def recommend_prompts(
        self,
        scene_context: Dict[str, Any],
        limit: int = 5,
    ) -> List[RetrievalResult]:
        """
        智能推薦提示詞
        
        Args:
            scene_context: 場景上下文 (title, description, characters 等)
            limit: 返回數量
            
        Returns:
            List[RetrievalResult]: 推薦結果
        """
        # 1. 從場景提取關鍵信息
        query_parts = []
        if scene_context.get("title"):
            query_parts.append(scene_context["title"])
        if scene_context.get("description"):
            query_parts.append(scene_context["description"])
        if scene_context.get("narrative_text"):
            query_parts.append(scene_context["narrative_text"][:200])
        
        query = " ".join(query_parts)
        
        # 2. 搜索相似提示詞
        results = await self.search_similar_prompts(query, limit=limit * 2)
        
        # 3. 重排序 (考慮成功率、復用次數)
        reranked = self._rerank_results(results, scene_context)
        
        return reranked[:limit]
    
    def _rerank_results(
        self,
        results: List[RetrievalResult],
        context: Dict[str, Any],
    ) -> List[RetrievalResult]:
        """重排序結果"""
        # 綜合評分 = 相似度 * 0.4 + 成功率 * 0.3 + 質量 * 0.2 + 復用次數歸一化 * 0.1
        for result in results:
            reuse_score = min(1.0, result.reuse_count / 100.0)  # 歸一化
            composite_score = (
                result.similarity_score * 0.4 +
                result.success_rate * 0.3 +
                result.quality_score * 0.2 +
                reuse_score * 0.1
            )
            result.metadata["composite_score"] = composite_score
        
        # 按綜合評分排序
        return sorted(results, key=lambda r: r.metadata.get("composite_score", 0), reverse=True)
    
    async def get_prompt_history(self, prompt_id: str) -> List[Dict[str, Any]]:
        """獲取提示詞使用歷史"""
        # TODO: 從 PostgreSQL 查詢 prompt_usage_history
        return []
    
    async def record_usage(
        self,
        prompt_id: str,
        scene_id: str,
        user_id: str,
        result_quality: float,
        user_feedback: Optional[int] = None,
    ):
        """記錄提示詞使用"""
        # TODO: 寫入 prompt_usage_history 表
        logger.info(
            "prompt_usage_recorded",
            prompt_id=prompt_id,
            scene_id=scene_id,
            user_id=user_id,
            result_quality=result_quality,
        )
    
    def _mock_embedding(self, text: str) -> List[float]:
        """模擬嵌入向量 (TODO: 替換為真實模型)"""
        # 使用簡單的 hash 模擬 768 維向量
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # 重複 hash 值填充到 768 維
        embedding = []
        while len(embedding) < 768:
            embedding.extend([b / 255.0 for b in hash_bytes])
        return embedding[:768]
    
    def _mock_search_results(self, query: str, limit: int) -> List[RetrievalResult]:
        """模擬搜索結果 (TODO: 替換為真實搜索)"""
        # 返回一些示例提示詞
        examples = [
            {
                "prompt_id": "prompt-001",
                "content": "cinematic shot, heroic figure standing on mountain peak at dawn, dramatic lighting, epic atmosphere",
                "similarity_score": 0.92,
                "success_rate": 0.87,
                "reuse_count": 45,
                "quality_score": 0.89,
                "category": "scene",
                "tags": ["cinematic", "hero", "mountain", "dawn"],
            },
            {
                "prompt_id": "prompt-002",
                "content": "anime style, young warrior with sword, cherry blossoms falling, sunset background, studio ghibli inspired",
                "similarity_score": 0.85,
                "success_rate": 0.91,
                "reuse_count": 67,
                "quality_score": 0.93,
                "category": "character",
                "tags": ["anime", "warrior", "sakura", "sunset"],
            },
            {
                "prompt_id": "prompt-003",
                "content": "photorealistic city street at night, neon lights, rain reflections, cyberpunk atmosphere, blade runner style",
                "similarity_score": 0.78,
                "success_rate": 0.84,
                "reuse_count": 32,
                "quality_score": 0.86,
                "category": "environment",
                "tags": ["cyberpunk", "city", "night", "neon"],
            },
        ]
        
        return [
            RetrievalResult(
                prompt_id=ex["prompt_id"],
                content=ex["content"],
                similarity_score=ex["similarity_score"],
                success_rate=ex["success_rate"],
                reuse_count=ex["reuse_count"],
                quality_score=ex["quality_score"],
                category=ex["category"],
                tags=ex["tags"],
                metadata={},
            )
            for ex in examples[:limit]
        ]


# 全局服務實例
_rag_retriever_instance: Optional[RAGRetrieverService] = None


def get_rag_retriever() -> RAGRetrieverService:
    """獲取 RAG 檢索器單例"""
    global _rag_retriever_instance
    if not _rag_retriever_instance:
        _rag_retriever_instance = RAGRetrieverService()
    return _rag_retriever_instance
