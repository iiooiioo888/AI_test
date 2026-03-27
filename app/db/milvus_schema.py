"""
Milvus Schema — scene semantic vector storage.

768-dimensional vectors from text-embedding-3-large (OpenAI)
for similarity search and conflict detection.
"""
from __future__ import annotations

from typing import Optional


# ── Collection Schema Definition ───────────────────────────────
#
# Production setup uses pymilvus. This module defines the schema
# and provides helper functions for initialization.
#
# Requirements: pip install pymilvus>=2.4

COLLECTION_NAME = "scene_embeddings"

# Schema fields
SCHEMA_FIELDS = [
    {
        "name": "id",
        "dtype": "VARCHAR",
        "max_length": 36,
        "is_primary": True,
        "description": "Scene UUID",
    },
    {
        "name": "embedding",
        "dtype": "FLOAT_VECTOR",
        "dim": 768,
        "description": "Scene semantic embedding (text-embedding-3-large, 768 dims)",
    },
    {
        "name": "title",
        "dtype": "VARCHAR",
        "max_length": 500,
        "description": "Scene title for display",
    },
    {
        "name": "branch",
        "dtype": "VARCHAR",
        "max_length": 100,
        "description": "Version branch name",
    },
    {
        "name": "state",
        "dtype": "VARCHAR",
        "max_length": 20,
        "description": "Scene lifecycle state",
    },
    {
        "name": "genre",
        "dtype": "VARCHAR",
        "max_length": 50,
        "description": "Scene genre",
    },
    {
        "name": "updated_at",
        "dtype": "INT64",
        "description": "Unix timestamp of last update",
    },
]

# Index parameters
INDEX_PARAMS = {
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128},
}

# Search parameters
SEARCH_PARAMS = {
    "metric_type": "COSINE",
    "params": {"nprobe": 16},
}


def get_create_collection_code() -> str:
    """
    Returns Python code string to create the Milvus collection.
    Use this as a reference or exec in init scripts.
    """
    return '''
from pymilvus import (
    connections, Collection, FieldSchema,
    CollectionSchema, DataType, utility
)

def init_scene_embeddings(host="milvus", port="19530"):
    """Initialize Milvus collection for scene embeddings."""
    connections.connect(alias="default", host=host, port=port)

    # Check if collection exists
    if utility.has_collection("scene_embeddings"):
        print("Collection 'scene_embeddings' already exists")
        return Collection("scene_embeddings")

    # Define schema
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="branch", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="state", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="genre", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="updated_at", dtype=DataType.INT64),
    ]
    schema = CollectionSchema(fields=fields, description="Scene semantic embeddings")
    collection = Collection(name="scene_embeddings", schema=schema)

    # Create index on vector field
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }
    collection.create_index(field_name="embedding", index_params=index_params)

    # Scalar field indexes for filtering
    collection.create_index(field_name="state")
    collection.create_index(field_name="branch")
    collection.create_index(field_name="genre")

    print(f"Created collection 'scene_embeddings' with {len(fields)} fields")
    return collection


def search_similar_scenes(collection, query_embedding, top_k=5,
                          filters="", output_fields=None):
    """
    Search for scenes similar to the query embedding.

    Args:
        collection: Milvus Collection object
        query_embedding: 768-dim float list
        top_k: number of results
        filters: Milvus filter expression, e.g. "state == 'COMPLETED'"
        output_fields: fields to return

    Returns:
        List of {id, title, similarity_score, ...}
    """
    if output_fields is None:
        output_fields = ["id", "title", "branch", "state", "genre"]

    collection.load()
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
        limit=top_k,
        expr=filters or None,
        output_fields=output_fields,
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "id": hit.id,
            "score": hit.score,
            **{field: hit.entity.get(field) for field in output_fields},
        })
    return hits


def detect_conflicts_by_similarity(collection, scene_embedding,
                                    scene_id, threshold=0.85):
    """
    Detect potential conflicts via semantic similarity.
    Scenes with high similarity but different characters/props
    may have consistency issues.

    Args:
        collection: Milvus Collection
        scene_embedding: 768-dim float list
        scene_id: exclude this scene from results
        threshold: minimum similarity score to flag

    Returns:
        List of potentially conflicting scene IDs
    """
    similar = search_similar_scenes(
        collection, scene_embedding, top_k=20,
        filters=f'id != "{scene_id}"',
    )
    return [s for s in similar if s["score"] >= threshold]
'''


def get_embedding_text(scene) -> str:
    """
    Generate the text to embed for a scene.
    Combines narrative beat, description, dialogue, and visual setting.
    """
    parts = []

    if hasattr(scene, 'narrative'):
        if scene.narrative.beat:
            parts.append(scene.narrative.beat)
        if scene.narrative.description:
            parts.append(scene.narrative.description)

    if hasattr(scene, 'dialogue'):
        for d in scene.dialogue[:10]:  # limit dialogue for embedding
            parts.append(f"{d.character_id}: {d.text}")

    if hasattr(scene, 'visual'):
        if scene.visual.setting:
            parts.append(f"Setting: {scene.visual.setting}")
        if scene.visual.atmosphere:
            parts.append(f"Atmosphere: {scene.visual.atmosphere}")

    return " | ".join(parts) if parts else "Empty scene"
