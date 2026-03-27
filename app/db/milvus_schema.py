"""
Milvus 向量數據庫 Schema
用於提示詞 RAG 檢索、相似度搜索、智能推薦
"""

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)
from typing import Optional


# Milvus 集合定義
MILVUS_COLLECTIONS = {
    # 提示詞向量庫
    "prompts": {
        "description": "提示詞嵌入向量庫，用於 RAG 檢索與相似度搜索",
        "fields": [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
            FieldSchema(name="prompt_id", dtype=DataType.VARCHAR, max_length=100),  # PostgreSQL ID
            FieldSchema(name="project_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8000),  # 提示詞內容
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=50),  # style, character, scene
            FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=1000),  # JSON 數組字符串
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),  # sentence-transformers
            FieldSchema(name="success_rate", dtype=DataType.FLOAT),  # 一次成功率
            FieldSchema(name="reuse_count", dtype=DataType.INT64),  # 復用次數
            FieldSchema(name="quality_score", dtype=DataType.FLOAT),  # 質量評分
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
        ],
        "indexes": [
            {
                "field_name": "embedding",
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
            {
                "field_name": "category",
                "index_type": "INVERTED",
            },
            {
                "field_name": "project_id",
                "index_type": "INVERTED",
            },
        ],
    },
    
    # 場景向量庫 (用於場景相似度檢索)
    "scenes": {
        "description": "場景敘事文本嵌入向量庫，用於場景推薦與連貫性分析",
        "fields": [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
            FieldSchema(name="scene_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="project_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="narrative_text", dtype=DataType.VARCHAR, max_length=8000),
            FieldSchema(name="positive_prompt", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
            FieldSchema(name="status", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="branch", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
        ],
        "indexes": [
            {
                "field_name": "embedding",
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
            {
                "field_name": "project_id",
                "index_type": "INVERTED",
            },
            {
                "field_name": "status",
                "index_type": "INVERTED",
            },
        ],
    },
    
    # 角色向量庫
    "characters": {
        "description": "角色描述嵌入向量庫，用於角色一致性檢查與推薦",
        "fields": [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
            FieldSchema(name="character_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="project_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="appearance", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
        ],
        "indexes": [
            {
                "field_name": "embedding",
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
            {
                "field_name": "project_id",
                "index_type": "INVERTED",
            },
        ],
    },
    
    # 風格參考庫 (LoRA/Style 向量)
    "style_references": {
        "description": "風格參考向量庫，用於風格相似度檢索與推薦",
        "fields": [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
            FieldSchema(name="style_name", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),  # cinematic, anime, realistic
            FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="prompt_template", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
            FieldSchema(name="lora_name", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="usage_count", dtype=DataType.INT64),
            FieldSchema(name="avg_quality", dtype=DataType.FLOAT),
        ],
        "indexes": [
            {
                "field_name": "embedding",
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
            {
                "field_name": "category",
                "index_type": "INVERTED",
            },
        ],
    },
}


class MilvusSchema:
    """Milvus Schema 管理類"""
    
    def __init__(self, host: str = "localhost", port: int = 19530):
        self.host = host
        self.port = port
        self.connections = None
    
    def connect(self) -> bool:
        """連接到 Milvus"""
        try:
            self.connections = connections.connect(
                host=self.host,
                port=self.port
            )
            return True
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")
            return False
    
    def create_collection(self, collection_name: str) -> Optional[Collection]:
        """創建集合"""
        if collection_name not in MILVUS_COLLECTIONS:
            print(f"Unknown collection: {collection_name}")
            return None
        
        config = MILVUS_COLLECTIONS[collection_name]
        
        # 如果集合已存在，先刪除
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
        
        # 創建 schema
        fields = [FieldSchema(**field) for field in config["fields"]]
        schema = CollectionSchema(fields=fields, description=config["description"])
        
        # 創建集合
        collection = Collection(name=collection_name, schema=schema)
        
        # 創建索引
        for index_config in config["indexes"]:
            collection.create_index(
                field_name=index_config["field_name"],
                index_params=index_config,
            )
        
        # 加載到內存
        collection.load()
        
        return collection
    
    def create_all_collections(self) -> dict:
        """創建所有集合"""
        results = {}
        for collection_name in MILVUS_COLLECTIONS:
            collection = self.create_collection(collection_name)
            results[collection_name] = collection is not None
        return results
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """獲取集合"""
        if not utility.has_collection(collection_name):
            return None
        
        collection = Collection(collection_name)
        collection.load()
        return collection
    
    def search_similar(
        self,
        collection_name: str,
        embedding: list,
        limit: int = 10,
        filter_expr: Optional[str] = None
    ) -> list:
        """搜索相似向量"""
        collection = self.get_collection(collection_name)
        if not collection:
            return []
        
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 100},
        }
        
        results = collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=limit,
            expr=filter_expr,
            output_fields=["id", "prompt_id", "content", "category", "success_rate", "quality_score"],
        )
        
        return results[0] if results else []
    
    def insert_prompt(
        self,
        prompt_id: str,
        project_id: str,
        content: str,
        embedding: list,
        category: str = "general",
        tags: list = None,
        success_rate: float = 0.0,
        reuse_count: int = 0,
        quality_score: float = 0.0,
    ) -> bool:
        """插入提示詞向量"""
        collection = self.get_collection("prompts")
        if not collection:
            return False
        
        import json
        from datetime import datetime
        
        data = [{
            "id": prompt_id,
            "prompt_id": prompt_id,
            "project_id": project_id,
            "content": content[:7999],  # 限制長度
            "category": category,
            "tags": json.dumps(tags or []),
            "embedding": embedding,
            "success_rate": success_rate,
            "reuse_count": reuse_count,
            "quality_score": quality_score,
            "created_at": datetime.utcnow().isoformat(),
        }]
        
        collection.insert(data)
        collection.flush()
        return True
    
    def drop_all_collections(self):
        """刪除所有集合 (開發環境使用)"""
        for collection_name in MILVUS_COLLECTIONS:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)


# 初始化示例
def init_milvus():
    """初始化 Milvus 數據庫"""
    milvus = MilvusSchema()
    if milvus.connect():
        print("Connected to Milvus")
        results = milvus.create_all_collections()
        print(f"Collections created: {results}")
        return milvus
    return None


if __name__ == "__main__":
    # 測試初始化
    init_milvus()
