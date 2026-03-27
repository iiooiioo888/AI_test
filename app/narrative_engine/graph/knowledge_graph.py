"""
Neo4j Knowledge Graph Service

Stores character/plot/prop dependency relationships.
Implements ripple-effect analysis: when a scene changes,
propagate impact to all connected nodes.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.narrative_engine.models.character import Character, Prop
from app.narrative_engine.models.scene import SceneObject


class KnowledgeGraphService:
    """
    In-memory graph store (production: Neo4j driver).
    Maintains nodes and edges for dependency tracking.
    """

    def __init__(self):
        # Adjacency lists for the graph
        self._characters: dict[str, Character] = {}
        self._props: dict[str, Prop] = {}
        self._scenes: dict[str, dict] = {}  # scene_id → scene summary
        self._edges: list[dict] = []  # {source, target, type, properties}

    # ── Node Operations ────────────────────────────────────────

    def upsert_character(self, char: Character) -> str:
        self._characters[char.id] = char
        return char.id

    def upsert_prop(self, prop: Prop) -> str:
        self._props[prop.id] = prop
        return prop.id

    def upsert_scene(self, scene: SceneObject) -> str:
        sid = str(scene.id)
        self._scenes[sid] = {
            "id": sid,
            "title": scene.title,
            "state": scene.state.value,
            "character_ids": scene.character_ids,
            "prop_ids": scene.prop_ids,
        }
        # Auto-create edges from scene to characters/props
        for cid in scene.character_ids:
            self.add_edge(sid, cid, "FEATURES_CHARACTER")
        for pid in scene.prop_ids:
            self.add_edge(sid, pid, "USES_PROP")
        for dep_id in scene.depends_on:
            self.add_edge(sid, str(dep_id), "DEPENDS_ON")
        return sid

    # ── Edge Operations ────────────────────────────────────────

    def add_edge(self, source: str, target: str, rel_type: str,
                 properties: Optional[dict] = None) -> None:
        self._edges.append({
            "source": source,
            "target": target,
            "type": rel_type,
            "properties": properties or {},
        })

    # ── Ripple Effect Analysis ─────────────────────────────────

    def get_ripple_effect(self, node_id: str, max_depth: int = 5) -> dict:
        """
        BFS traversal to find all nodes affected by a change.
        Returns {depth: [node_ids]} for impact assessment.
        """
        visited = {node_id}
        queue = [(node_id, 0)]
        impact: dict[int, list[str]] = {0: [node_id]}

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for edge in self._edges:
                neighbor = None
                if edge["source"] == current:
                    neighbor = edge["target"]
                elif edge["target"] == current:
                    neighbor = edge["source"]

                if neighbor and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
                    impact.setdefault(depth + 1, []).append(neighbor)

        return impact

    def get_character_scenes(self, character_id: str) -> list[str]:
        """Return all scene IDs featuring a character."""
        return [
            e["source"] for e in self._edges
            if e["target"] == character_id and e["type"] == "FEATURES_CHARACTER"
        ]

    def get_scene_dependencies(self, scene_id: str) -> list[str]:
        """Return all scene IDs this scene depends on."""
        return [
            e["target"] for e in self._edges
            if e["source"] == scene_id and e["type"] == "DEPENDS_ON"
        ]

    def check_consistency(self, scene: SceneObject) -> list[str]:
        """
        Check if a scene's relationships are consistent with the graph.
        Returns list of warnings.
        """
        warnings = []
        for cid in scene.character_ids:
            if cid not in self._characters:
                warnings.append(f"Character {cid} not found in graph")
        for pid in scene.prop_ids:
            if pid not in self._props:
                warnings.append(f"Prop {pid} not found in graph")
        for dep_id in scene.depends_on:
            if str(dep_id) not in self._scenes:
                warnings.append(f"Dependency scene {dep_id} not found")
        return warnings

    # ── Query Helpers ──────────────────────────────────────────

    def get_all_characters(self) -> list[Character]:
        return list(self._characters.values())

    def get_all_props(self) -> list[Prop]:
        return list(self._props.values())

    def get_graph_stats(self) -> dict:
        return {
            "characters": len(self._characters),
            "props": len(self._props),
            "scenes": len(self._scenes),
            "edges": len(self._edges),
        }
