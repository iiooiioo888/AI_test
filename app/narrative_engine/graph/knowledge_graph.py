"""
Neo4j Knowledge Graph Service

Stores character/plot/prop dependency relationships.
Implements ripple-effect analysis: when a scene changes,
propagate impact to all connected nodes.

Enhanced with:
- Transitive dependency resolution
- Orphan scene detection
- Dependency chain visualization
- Character relationship strength tracking
- Scene clustering by character co-appearance
"""
from __future__ import annotations

from collections import defaultdict
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
        # Prevent duplicate edges
        for edge in self._edges:
            if (edge["source"] == source and edge["target"] == target
                    and edge["type"] == rel_type):
                # Update properties on existing edge
                if properties:
                    edge["properties"].update(properties)
                return
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

    def get_ripple_report(self, node_id: str, max_depth: int = 5) -> dict:
        """
        Enhanced ripple analysis with node type breakdown and severity scoring.
        Returns detailed impact report.
        """
        ripple = self.get_ripple_effect(node_id, max_depth)

        # Classify affected nodes
        affected_scenes = []
        affected_characters = []
        affected_props = []

        all_nodes = []
        for depth, nodes in ripple.items():
            all_nodes.extend([(n, depth) for n in nodes])

        for nid, depth in all_nodes:
            if nid in self._scenes:
                affected_scenes.append({"id": nid, "depth": depth,
                                        "title": self._scenes[nid].get("title", "")})
            elif nid in self._characters:
                affected_characters.append({"id": nid, "depth": depth,
                                            "name": self._characters[nid].name})
            elif nid in self._props:
                affected_props.append({"id": nid, "depth": depth,
                                       "name": self._props[nid].name})

        # Severity: more distant impacts are less severe
        total = len(all_nodes)
        severity = "low"
        if total > 10 or any(d["depth"] > 3 for d in affected_scenes):
            severity = "high"
        elif total > 5:
            severity = "medium"

        return {
            "source_node": node_id,
            "severity": severity,
            "total_affected": total,
            "by_type": {
                "scenes": affected_scenes,
                "characters": affected_characters,
                "props": affected_props,
            },
            "depth_map": {str(k): v for k, v in ripple.items()},
        }

    # ── Transitive Dependencies ────────────────────────────────

    def get_transitive_dependencies(self, scene_id: str,
                                     max_depth: int = 10) -> list[list[str]]:
        """
        Find all dependency chains leading to this scene.
        Returns list of chains, each chain is a list of scene IDs from root to scene_id.
        Uses DFS to enumerate all paths.
        """
        chains: list[list[str]] = []

        # Find direct dependencies (scenes this scene depends on)
        direct_deps = self.get_scene_dependencies(scene_id)

        if not direct_deps:
            return [[scene_id]]

        for dep_id in direct_deps:
            parent_chains = self.get_transitive_dependencies(dep_id, max_depth - 1)
            for chain in parent_chains:
                chains.append(chain + [scene_id])

        if not chains:
            chains.append([scene_id])

        return chains

    def get_all_upstream(self, scene_id: str) -> set[str]:
        """
        Get all scenes upstream (transitive dependencies) of a scene.
        """
        visited = set()
        queue = [scene_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for dep_id in self.get_scene_dependencies(current):
                if dep_id not in visited:
                    queue.append(dep_id)

        visited.discard(scene_id)  # Remove self
        return visited

    def get_all_downstream(self, scene_id: str) -> set[str]:
        """
        Get all scenes downstream (transitive dependents) of a scene.
        """
        visited = set()
        queue = [scene_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            # Find scenes that depend on current
            for edge in self._edges:
                if edge["type"] == "DEPENDS_ON" and edge["target"] == current:
                    depender = edge["source"]
                    if depender not in visited:
                        queue.append(depender)

        visited.discard(scene_id)
        return visited

    # ── Orphan Detection ───────────────────────────────────────

    def find_orphan_scenes(self) -> list[dict]:
        """
        Find scenes with no incoming or outgoing dependencies
        and no characters/props. These are disconnected from the story.
        """
        orphans = []
        for sid, scene_info in self._scenes.items():
            has_dependencies = False
            for edge in self._edges:
                if edge["type"] == "DEPENDS_ON":
                    if edge["source"] == sid or edge["target"] == sid:
                        has_dependencies = True
                        break
            if not has_dependencies:
                has_characters = bool(scene_info.get("character_ids"))
                if not has_characters:
                    orphans.append({
                        "id": sid,
                        "title": scene_info.get("title", ""),
                        "state": scene_info.get("state", ""),
                        "reason": "No dependencies and no characters",
                    })
        return orphans

    def find_isolated_subgraphs(self) -> list[list[str]]:
        """
        Find connected components in the scene dependency graph.
        Useful for detecting story fragments that aren't connected.
        """
        scene_ids = set(self._scenes.keys())
        if not scene_ids:
            return []

        # Build adjacency for scenes only
        adj: dict[str, set[str]] = defaultdict(set)
        for edge in self._edges:
            if edge["type"] == "DEPENDS_ON":
                s, t = edge["source"], edge["target"]
                if s in scene_ids and t in scene_ids:
                    adj[s].add(t)
                    adj[t].add(s)

        visited = set()
        components = []

        for sid in scene_ids:
            if sid in visited:
                continue
            # BFS to find component
            component = []
            queue = [sid]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                for neighbor in adj.get(node, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            components.append(component)

        return components

    # ── Character Relationship Analysis ────────────────────────

    def get_character_co_appearances(self) -> dict[str, list[dict]]:
        """
        Find characters that appear in the same scenes.
        Returns {character_id: [{co_character_id, scene_ids, count}]}
        """
        # Build character → scenes map
        char_scenes: dict[str, set[str]] = defaultdict(set)
        for edge in self._edges:
            if edge["type"] == "FEATURES_CHARACTER":
                char_scenes[edge["target"]].add(edge["source"])

        # Find co-appearances
        char_ids = list(char_scenes.keys())
        co_appearances: dict[str, list[dict]] = defaultdict(list)

        for i, c1 in enumerate(char_ids):
            for c2 in char_ids[i + 1:]:
                shared = char_scenes[c1] & char_scenes[c2]
                if shared:
                    co_appearances[c1].append({
                        "co_character_id": c2,
                        "co_character_name": self._characters[c2].name if c2 in self._characters else c2,
                        "scene_ids": list(shared),
                        "count": len(shared),
                    })
                    co_appearances[c2].append({
                        "co_character_id": c1,
                        "co_character_name": self._characters[c1].name if c1 in self._characters else c1,
                        "scene_ids": list(shared),
                        "count": len(shared),
                    })

        return dict(co_appearances)

    def get_prop_usage_chain(self, prop_id: str) -> list[dict]:
        """
        Get the sequence of scenes where a prop appears (ordered by scene index).
        Useful for tracking object continuity.
        """
        scenes = []
        for edge in self._edges:
            if edge["type"] == "USES_PROP" and edge["target"] == prop_id:
                sid = edge["source"]
                if sid in self._scenes:
                    scenes.append(self._scenes[sid])
        return scenes

    # ── Character/Prop Queries ─────────────────────────────────

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

    def get_scene_dependents(self, scene_id: str) -> list[str]:
        """Return all scene IDs that depend on this scene."""
        return [
            e["source"] for e in self._edges
            if e["target"] == scene_id and e["type"] == "DEPENDS_ON"
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

        # Check for circular dependencies
        if self._has_circular_dependency(str(scene.id)):
            warnings.append(f"Circular dependency detected involving scene {scene.id}")

        return warnings

    def _has_circular_dependency(self, scene_id: str,
                                  visited: Optional[set] = None) -> bool:
        """DFS cycle detection in dependency graph."""
        if visited is None:
            visited = set()
        if scene_id in visited:
            return True
        visited.add(scene_id)
        for dep_id in self.get_scene_dependencies(scene_id):
            if self._has_circular_dependency(dep_id, visited.copy()):
                return True
        return False

    # ── Query Helpers ──────────────────────────────────────────

    def get_all_characters(self) -> list[Character]:
        return list(self._characters.values())

    def get_all_props(self) -> list[Prop]:
        return list(self._props.values())

    def get_edge_types(self) -> dict[str, int]:
        """Return count of each edge type."""
        counts: dict[str, int] = defaultdict(int)
        for edge in self._edges:
            counts[edge["type"]] += 1
        return dict(counts)

    def get_graph_stats(self) -> dict:
        return {
            "characters": len(self._characters),
            "props": len(self._props),
            "scenes": len(self._scenes),
            "edges": len(self._edges),
            "edge_types": self.get_edge_types(),
            "orphan_scenes": len(self.find_orphan_scenes()),
            "connected_components": len(self.find_isolated_subgraphs()),
        }
