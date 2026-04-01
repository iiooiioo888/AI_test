"""
Milvus Embedding Pipeline — text → 768-dim vector → Milvus upsert/search.

Provides:
  - SceneEmbeddingPipeline: orchestrator for embed → store → query
  - EmbeddingProvider: wraps text-embedding model calls
  - MilvusClient: thin wrapper around pymilvus operations
  - ConflictDetector: semantic similarity based conflict flagging
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────

COLLECTION_NAME = "scene_embeddings"
EMBEDDING_DIM = 768
EMBEDDING_MODEL = "text-embedding-3-large"

# Index / search params
INDEX_PARAMS = {
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128},
}
SEARCH_PARAMS = {
    "metric_type": "COSINE",
    "params": {"nprobe": 16},
}


# ── Data Classes ───────────────────────────────────────────────

@dataclass
class SceneEmbedding:
    """A single scene's embedding record."""
    id: str                        # scene UUID
    embedding: list[float]         # 768-dim vector
    title: str = ""
    branch: str = "main"
    state: str = "draft"
    genre: str = ""
    updated_at: int = 0            # unix timestamp
    text_hash: str = ""            # content hash for change detection


@dataclass
class SimilarScene:
    """A search result with similarity score."""
    id: str
    title: str
    score: float
    branch: str = ""
    state: str = ""
    genre: str = ""


@dataclass
class ConflictResult:
    """Conflict detection output."""
    scene_id: str
    similar_scene_id: str
    similarity_score: float
    reason: str


# ── Embedding Provider ────────────────────────────────────────

class EmbeddingProvider:
    """
    Wraps text-embedding model calls.

    Supports:
      - OpenAI API (text-embedding-3-large → 768 dims)
      - Local sentence-transformers fallback
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dim: int = EMBEDDING_DIM,
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model or EMBEDDING_MODEL
        self.dim = dim
        self._client = None

    def _get_client(self):
        """Lazy-init the embedding client."""
        if self._client is not None:
            return self._client

        if self.provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("pip install openai  — required for OpenAI embeddings")
        elif self.provider == "local":
            try:
                from sentence_transformers import SentenceTransformer
                self._client = SentenceTransformer(self.model)
            except ImportError:
                raise ImportError("pip install sentence-transformers  — required for local embeddings")
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate a single embedding vector."""
        client = self._get_client()

        if self.provider == "openai":
            resp = client.embeddings.create(input=[text], model=self.model, dimensions=self.dim)
            return resp.data[0].embedding[: self.dim]

        elif self.provider == "local":
            vec = client.encode([text])[0]
            return vec.tolist()[: self.dim]

        raise ValueError(f"Unhandled provider: {self.provider}")

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Batch embedding with automatic chunking."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            client = self._get_client()

            if self.provider == "openai":
                resp = client.embeddings.create(input=chunk, model=self.model, dimensions=self.dim)
                all_embeddings.extend(e.embedding[: self.dim] for e in resp.data)

            elif self.provider == "local":
                vecs = client.encode(chunk)
                all_embeddings.extend(v.tolist()[: self.dim] for v in vecs)

            logger.debug("Embedded batch %d-%d / %d", i, i + len(chunk), len(texts))

        return all_embeddings


# ── Text Builder ───────────────────────────────────────────────

def build_embedding_text(scene_data: dict) -> str:
    """
    Combine scene fields into a single string for embedding.

    Expected keys in scene_data:
      - title, description, narrative_text
      - scene_data.dialogue (list of {character, text})
      - scene_data.visual (setting, atmosphere)
    """
    parts: list[str] = []

    if scene_data.get("title"):
        parts.append(scene_data["title"])
    if scene_data.get("description"):
        parts.append(scene_data["description"])
    if scene_data.get("narrative_text"):
        parts.append(scene_data["narrative_text"])

    # Dialogue
    sd = scene_data.get("scene_data", {})
    if isinstance(sd, dict):
        for d in sd.get("dialogue", [])[:10]:
            char = d.get("character", d.get("character_id", ""))
            text = d.get("text", "")
            if text:
                parts.append(f"{char}: {text}" if char else text)

        visual = sd.get("visual", {})
        if isinstance(visual, dict):
            if visual.get("setting"):
                parts.append(f"Setting: {visual['setting']}")
            if visual.get("atmosphere"):
                parts.append(f"Atmosphere: {visual['atmosphere']}")

    return " | ".join(parts) if parts else "Empty scene"


def content_hash(text: str) -> str:
    """SHA-256 hash for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── Milvus Client Wrapper ─────────────────────────────────────

class MilvusClient:
    """Thin wrapper around pymilvus for collection lifecycle + CRUD."""

    def __init__(self, host: str = "milvus", port: str = "19530", alias: str = "default"):
        self.host = host
        self.port = port
        self.alias = alias
        self._connected = False

    def connect(self):
        """Connect to Milvus server."""
        if self._connected:
            return
        from pymilvus import connections
        connections.connect(alias=self.alias, host=self.host, port=self.port)
        self._connected = True
        logger.info("Connected to Milvus at %s:%s", self.host, self.port)

    def ensure_collection(self):
        """Create collection + indexes if they don't exist."""
        from pymilvus import (
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
            utility,
        )

        self.connect()

        if utility.has_collection(COLLECTION_NAME):
            logger.info("Collection '%s' already exists", COLLECTION_NAME)
            return Collection(COLLECTION_NAME)

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="branch", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="state", dtype=DataType.VARCHAR, max_length=20),
            FieldSchema(name="genre", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="updated_at", dtype=DataType.INT64),
            FieldSchema(name="text_hash", dtype=DataType.VARCHAR, max_length=16),
        ]

        schema = CollectionSchema(fields=fields, description="Scene semantic embeddings")
        collection = Collection(name=COLLECTION_NAME, schema=schema)

        # Vector index
        collection.create_index(field_name="embedding", index_params=INDEX_PARAMS)

        # Scalar indexes for filtering
        for scalar_field in ("state", "branch", "genre"):
            try:
                collection.create_index(field_name=scalar_field)
            except Exception:
                pass  # some pymilvus versions auto-index scalars

        logger.info("Created collection '%s' with %d fields", COLLECTION_NAME, len(fields))
        return collection

    def get_collection(self):
        """Get existing collection (auto-creates if missing)."""
        from pymilvus import Collection
        self.connect()
        return self.ensure_collection()

    def upsert(self, records: list[SceneEmbedding]) -> int:
        """
        Upsert a batch of scene embeddings.

        Returns the number of rows affected.
        """
        collection = self.get_collection()
        collection.load()

        data = [
            [r.id for r in records],
            [r.embedding for r in records],
            [r.title for r in records],
            [r.branch for r in records],
            [r.state for r in records],
            [r.genre for r in records],
            [r.updated_at for r in records],
            [r.text_hash for r in records],
        ]

        mr = collection.upsert(data)
        logger.info("Upserted %d scene embeddings", len(records))
        return mr.insert_count if hasattr(mr, "insert_count") else len(records)

    def delete(self, scene_ids: list[str]):
        """Delete embeddings by scene IDs."""
        collection = self.get_collection()
        collection.delete(f'id in {scene_ids}')
        logger.info("Deleted %d scene embeddings", len(scene_ids))

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: str = "",
        output_fields: Optional[list[str]] = None,
    ) -> list[SimilarScene]:
        """Search for similar scenes by embedding vector."""
        from pymilvus import Collection

        collection = self.get_collection()
        collection.load()

        if output_fields is None:
            output_fields = ["id", "title", "branch", "state", "genre"]

        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=SEARCH_PARAMS,
            limit=top_k,
            expr=filters or None,
            output_fields=output_fields,
        )

        hits: list[SimilarScene] = []
        for hit in results[0]:
            entity = hit.entity
            hits.append(SimilarScene(
                id=hit.id,
                title=entity.get("title", ""),
                score=round(hit.score, 4),
                branch=entity.get("branch", ""),
                state=entity.get("state", ""),
                genre=entity.get("genre", ""),
            ))
        return hits


# ── Conflict Detector ──────────────────────────────────────────

class ConflictDetector:
    """Flag semantically similar scenes as potential conflicts."""

    def __init__(self, milvus: MilvusClient, threshold: float = 0.85):
        self.milvus = milvus
        self.threshold = threshold

    def detect(
        self,
        scene_id: str,
        embedding: list[float],
        top_k: int = 20,
    ) -> list[ConflictResult]:
        """
        Find scenes with high cosine similarity to the given scene,
        excluding the scene itself.
        """
        similar = self.milvus.search(
            query_embedding=embedding,
            top_k=top_k,
            filters=f'id != "{scene_id}"',
        )

        conflicts: list[ConflictResult] = []
        for s in similar:
            if s.score >= self.threshold:
                conflicts.append(ConflictResult(
                    scene_id=scene_id,
                    similar_scene_id=s.id,
                    similarity_score=s.score,
                    reason=f"Semantic similarity {s.score:.2f} ≥ {self.threshold}",
                ))
        return conflicts


# ── Pipeline Orchestrator ──────────────────────────────────────

class SceneEmbeddingPipeline:
    """
    End-to-end pipeline: scene dict → embed → upsert → search/conflicts.

    Usage:
        pipeline = SceneEmbeddingPipeline(
            embedding_provider=EmbeddingProvider(provider="openai", api_key="sk-..."),
            milvus=MilvusClient(host="milvus"),
        )
        pipeline.initialize()

        # Upsert a single scene
        record = pipeline.build_record(scene_dict)
        pipeline.upsert([record])

        # Search
        results = pipeline.search("主角在雨中奔跑", top_k=5)

        # Detect conflicts
        conflicts = pipeline.detect_conflicts(scene_id, record.embedding)
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        milvus: Optional[MilvusClient] = None,
        conflict_threshold: float = 0.85,
    ):
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.milvus = milvus or MilvusClient()
        self.detector = ConflictDetector(self.milvus, threshold=conflict_threshold)

    def initialize(self):
        """Connect to Milvus and ensure collection exists."""
        self.milvus.ensure_collection()
        logger.info("SceneEmbeddingPipeline initialized")

    # ── Build ─────────────────────────────────────────────────

    def build_record(self, scene: dict) -> SceneEmbedding:
        """
        Build a SceneEmbedding from a scene dict (same shape as DB row).

        Embeds the combined text fields and attaches metadata.
        """
        text = build_embedding_text(scene)
        vec = self.embedding_provider.embed(text)

        return SceneEmbedding(
            id=scene["id"],
            embedding=vec,
            title=scene.get("title", ""),
            branch=scene.get("branch", "main"),
            state=scene.get("status", scene.get("state", "draft")),
            genre=scene.get("genre", ""),
            updated_at=int(time.time()),
            text_hash=content_hash(text),
        )

    def build_records_batch(self, scenes: list[dict]) -> list[SceneEmbedding]:
        """Batch-build embedding records with a single API call."""
        texts = [build_embedding_text(s) for s in scenes]
        hashes = [content_hash(t) for t in texts]
        embeddings = self.embedding_provider.embed_batch(texts)
        now = int(time.time())

        records: list[SceneEmbedding] = []
        for scene, vec, h in zip(scenes, embeddings, hashes):
            records.append(SceneEmbedding(
                id=scene["id"],
                embedding=vec,
                title=scene.get("title", ""),
                branch=scene.get("branch", "main"),
                state=scene.get("status", scene.get("state", "draft")),
                genre=scene.get("genre", ""),
                updated_at=now,
                text_hash=h,
            ))
        return records

    # ── Upsert / Delete ───────────────────────────────────────

    def upsert(self, records: list[SceneEmbedding]) -> int:
        """Upsert embedding records into Milvus."""
        return self.milvus.upsert(records)

    def upsert_scenes(self, scenes: list[dict]) -> int:
        """Convenience: embed + upsert from raw scene dicts."""
        records = self.build_records_batch(scenes)
        return self.upsert(records)

    def delete(self, scene_ids: list[str]):
        """Remove scene embeddings."""
        self.milvus.delete(scene_ids)

    # ── Search ────────────────────────────────────────────────

    def search(self, query_text: str, top_k: int = 5, filters: str = "") -> list[SimilarScene]:
        """Text → embedding → similarity search."""
        vec = self.embedding_provider.embed(query_text)
        return self.milvus.search(vec, top_k=top_k, filters=filters)

    def find_similar(self, scene_id: str, embedding: list[float], top_k: int = 5) -> list[SimilarScene]:
        """Find scenes similar to a known scene by its embedding."""
        return self.milvus.search(
            embedding,
            top_k=top_k,
            filters=f'id != "{scene_id}"',
        )

    # ── Conflict Detection ────────────────────────────────────

    def detect_conflicts(
        self,
        scene_id: str,
        embedding: list[float],
    ) -> list[ConflictResult]:
        """Run conflict detection against all other scenes."""
        return self.detector.detect(scene_id, embedding)

    def detect_conflicts_for_scene(self, scene: dict) -> list[ConflictResult]:
        """Embed + detect conflicts in one call."""
        record = self.build_record(scene)
        return self.detect_conflicts(record.id, record.embedding)
