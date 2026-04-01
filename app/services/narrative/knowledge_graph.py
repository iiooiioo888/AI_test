"""
Neo4j 知識圖譜服務 — relationship names aligned with TASKS.md §1.

Relationships:
  LEADS_TO   — narrative sequence (Scene → Scene)
  CONTAINS   — scene contains character (Scene → Character)
  REQUIRES   — scene requires prop (Scene → Prop)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from neo4j import AsyncGraphDatabase, GraphDatabase
from neo4j.asyncio import AsyncDriver
import structlog

from app.db.neo4j_schema import CYPHER_QUERIES, Neo4jSchema
from app.core.config import settings

logger = structlog.get_logger()


class KnowledgeGraphService:
    """
    Neo4j 知識圖譜服務

    核心功能：
    1. 角色關係網絡存儲
    2. 場景依賴關係
    3. 漣漪效應分析
    4. 連貫性檢查
    """

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        """連接到 Neo4j"""
        if not self.driver:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            logger.info("neo4j_connected", uri=self.uri)

    async def disconnect(self):
        """斷開連接"""
        if self.driver:
            await self.driver.close()
            logger.info("neo4j_disconnected")

    async def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """執行 Cypher 查詢"""
        if not self.driver:
            await self.connect()

        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    # ========================================================================
    # 場景操作
    # ========================================================================

    async def create_scene(
        self,
        scene_id: str,
        title: str,
        description: str,
        project_id: str,
        status: str = "draft",
        branch: str = "main",
        version: str = "1.0.0",
        **kwargs,
    ):
        """創建場景節點"""
        query = """
        MERGE (s:Scene {id: $scene_id})
        SET s.title = $title,
            s.description = $description,
            s.projectId = $project_id,
            s.status = $status,
            s.branch = $branch,
            s.version = $version,
            s.createdAt = datetime($created_at),
            s.updatedAt = datetime($updated_at)
        RETURN s
        """
        params = {
            "scene_id": scene_id,
            "title": title,
            "description": description,
            "project_id": project_id,
            "status": status,
            "branch": branch,
            "version": version,
            "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow().isoformat()),
        }
        return await self.execute_query(query, params)

    async def link_scenes(self, from_scene_id: str, to_scene_id: str):
        """建立場景序列關係 (LEADS_TO)"""
        query = """
        MATCH (from:Scene {id: $from_id})
        MATCH (to:Scene {id: $to_id})
        MERGE (from)-[r:LEADS_TO]->(to)
        RETURN r
        """
        return await self.execute_query(query, {"from_id": from_scene_id, "to_id": to_scene_id})

    async def unlink_scenes(self, from_scene_id: str, to_scene_id: str):
        """移除場景序列關係"""
        query = """
        MATCH (from:Scene {id: $from_id})-[r:LEADS_TO]->(to:Scene {id: $to_id})
        DELETE r
        """
        return await self.execute_query(query, {"from_id": from_scene_id, "to_id": to_scene_id})

    # ========================================================================
    # 角色操作
    # ========================================================================

    async def create_character(
        self,
        character_id: str,
        name: str,
        appearance: str,
        project_id: str,
        **kwargs,
    ):
        """創建角色節點"""
        query = """
        MERGE (c:Character {id: $character_id})
        SET c.name = $name,
            c.appearance = $appearance,
            c.projectId = $project_id,
            c.description = $description,
            c.personality = $personality,
            c.updatedAt = datetime($updated_at)
        RETURN c
        """
        params = {
            "character_id": character_id,
            "name": name,
            "appearance": appearance,
            "project_id": project_id,
            "description": kwargs.get("description", ""),
            "personality": kwargs.get("personality", ""),
            "updated_at": datetime.utcnow().isoformat(),
        }
        return await self.execute_query(query, params)

    async def link_character_to_scene(
        self,
        character_id: str,
        scene_id: str,
        role: str = "supporting",
    ):
        """建立角色與場景的關係 (CONTAINS)"""
        query = """
        MATCH (c:Character {id: $character_id})
        MATCH (s:Scene {id: $scene_id})
        MERGE (s)-[r:CONTAINS]->(c)
        SET r.role = $role
        RETURN r
        """
        return await self.execute_query(query, {
            "character_id": character_id,
            "scene_id": scene_id,
            "role": role,
        })

    async def link_prop_to_scene(
        self,
        prop_id: str,
        scene_id: str,
        mandatory: bool = True,
    ):
        """建立道具與場景的關係 (REQUIRES)"""
        query = """
        MATCH (p:Prop {id: $prop_id})
        MATCH (s:Scene {id: $scene_id})
        MERGE (s)-[r:REQUIRES]->(p)
        SET r.mandatory = $mandatory
        RETURN r
        """
        return await self.execute_query(query, {
            "prop_id": prop_id,
            "scene_id": scene_id,
            "mandatory": mandatory,
        })

    async def create_character_relationship(
        self,
        from_char_id: str,
        to_char_id: str,
        relationship_type: str,
        strength: float = 0.5,
    ):
        """創建角色關係"""
        query = """
        MATCH (from:Character {id: $from_id})
        MATCH (to:Character {id: $to_id})
        MERGE (from)-[r:RELATED_TO {type: $type}]->(to)
        SET r.strength = $strength,
            r.updatedAt = datetime()
        RETURN r
        """
        return await self.execute_query(query, {
            "from_id": from_char_id,
            "to_id": to_char_id,
            "type": relationship_type,
            "strength": strength,
        })

    # ========================================================================
    # 漣漪效應分析
    # ========================================================================

    async def analyze_ripple_effect(self, scene_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """
        漣漪效應分析

        當場景修改時，找出所有受影響的場景

        Args:
            scene_id: 目標場景 ID
            max_depth: 最大遞歸深度

        Returns:
            影響分析結果
        """
        # 查詢 1: 找出所有後續場景 (通過 LEADS_TO 關係)
        next_scenes_query = """
        MATCH path = (s:Scene {id: $scene_id})-[:LEADS_TO*1..$max_depth]->(affected:Scene)
        WHERE affected.status <> 'completed'
        RETURN affected.id, affected.title, affected.status, length(path) as distance
        ORDER BY distance
        """
        next_scenes = await self.execute_query(next_scenes_query, {
            "scene_id": scene_id,
            "max_depth": max_depth,
        })

        # 查詢 2: 找出依賴此場景的其他場景
        dependencies_query = """
        MATCH (target:Scene {id: $scene_id})<-[:DEPENDS_ON*1..$max_depth]-(dependent:Scene)
        WHERE dependent.status <> 'completed'
        RETURN dependent.id, dependent.title, dependent.status, length(dependent) as distance
        ORDER BY distance
        """
        dependents = await self.execute_query(dependencies_query, {
            "scene_id": scene_id,
            "max_depth": max_depth,
        })

        # 查詢 3: 找出登場的角色 (通過 CONTAINS)
        characters_query = """
        MATCH (s:Scene {id: $scene_id})-[:CONTAINS]->(c:Character)
        RETURN c.id, c.name, c.appearance
        """
        characters = await self.execute_query(characters_query, {"scene_id": scene_id})

        # 查詢 4: 檢查角色死亡衝突 (後續場景中出現已標記死亡的角色)
        dead_char_conflict_query = """
        MATCH (changed:Scene {id: $scene_id})-[:LEADS_TO*1..$max_depth]->(affected:Scene)
        MATCH (affected)-[:CONTAINS]->(c:Character)
        WHERE c.status = 'dead'
        RETURN affected.id, affected.title, collect(c.name) AS dead_characters
        """
        dead_conflicts = await self.execute_query(dead_char_conflict_query, {
            "scene_id": scene_id,
            "max_depth": max_depth,
        })

        # 查詢 5: 檢查道具銷毀衝突
        destroyed_prop_query = """
        MATCH (changed:Scene {id: $scene_id})-[:LEADS_TO*1..$max_depth]->(affected:Scene)
        MATCH (changed)-[:REQUIRES]->(p:Prop)
        MATCH (affected)-[:REQUIRES]->(p)
        WHERE p.status = 'destroyed'
        RETURN affected.id, affected.title, collect(p.name) AS destroyed_props
        """
        prop_conflicts = await self.execute_query(destroyed_prop_query, {
            "scene_id": scene_id,
            "max_depth": max_depth,
        })

        return {
            "scene_id": scene_id,
            "affected_scenes": [
                {
                    "id": r["affected.id"],
                    "title": r["affected.title"],
                    "status": r["affected.status"],
                    "distance": r["distance"],
                }
                for r in next_scenes
            ],
            "dependent_scenes": [
                {
                    "id": r["dependent.id"],
                    "title": r["dependent.title"],
                    "status": r["dependent.status"],
                    "distance": r["distance"],
                }
                for r in dependents
            ],
            "characters": [
                {
                    "id": r["c.id"],
                    "name": r["c.name"],
                    "appearance": r["c.appearance"],
                }
                for r in characters
            ],
            "conflicts": {
                "dead_characters": [
                    {
                        "scene_id": r["affected.id"],
                        "scene_title": r["affected.title"],
                        "characters": r["dead_characters"],
                    }
                    for r in dead_conflicts
                ],
                "destroyed_props": [
                    {
                        "scene_id": r["affected.id"],
                        "scene_title": r["affected.title"],
                        "props": r["destroyed_props"],
                    }
                    for r in prop_conflicts
                ],
            },
            "total_affected": len(next_scenes) + len(dependents),
            "recommendations": self._generate_recommendations(next_scenes, dependents, dead_conflicts, prop_conflicts),
        }

    def _generate_recommendations(
        self,
        next_scenes: List,
        dependents: List,
        dead_conflicts: List,
        prop_conflicts: List,
    ) -> List[str]:
        """生成變更建議"""
        recommendations = []

        if len(next_scenes) > 5:
            recommendations.append("⚠️ 影響範圍較大，建議分批修改")

        if any(s.get("affected.status") == "locked" for s in next_scenes):
            recommendations.append("⚠️ 有已鎖定的場景受影響，需要解鎖後修改")

        if len(dependents) > 0:
            recommendations.append("📋 需要檢查依賴場景的連貫性")

        if dead_conflicts:
            names = set()
            for c in dead_conflicts:
                names.update(c.get("dead_characters", []))
            recommendations.append(f"💀 HIGH 衝突：角色 [{', '.join(names)}] 已標記死亡，但在後續場景中仍出現")

        if prop_conflicts:
            names = set()
            for c in prop_conflicts:
                names.update(c.get("destroyed_props", []))
            recommendations.append(f"🔧 MEDIUM 衝突：道具 [{', '.join(names)}] 已銷毀，但在後續場景中仍被使用")

        return recommendations

    # ========================================================================
    # 連貫性檢查
    # ========================================================================

    async def check_continuity(self, scene_id: str) -> Dict[str, Any]:
        """
        連貫性檢查

        檢查場景與前後場景的一致性

        Returns:
            檢查結果
        """
        issues = []
        warnings = []

        # 檢查 1: 角色一致性 (CONTAINS)
        characters_query = """
        MATCH (prev:Scene)-[:LEADS_TO]->(current:Scene {id: $scene_id})
        MATCH (current)-[:CONTAINS]->(c:Character)
        MATCH (prev)-[:CONTAINS]->(prev_c:Character)
        WHERE c.id = prev_c.id
        RETURN c.id, c.name, c.appearance as current_appearance,
               prev_c.appearance as prev_appearance
        """
        char_results = await self.execute_query(characters_query, {"scene_id": scene_id})

        for r in char_results:
            if r["current_appearance"] != r["prev_appearance"]:
                warnings.append({
                    "type": "character_appearance_mismatch",
                    "character_id": r["c.id"],
                    "character_name": r["c.name"],
                    "message": f"角色 {r['c.name']} 的外觀描述不一致",
                })

        # 檢查 2: 地點一致性
        location_query = """
        MATCH (prev:Scene)-[:LEADS_TO]->(current:Scene {id: $scene_id})
        MATCH (current)-[:SET_IN_LOCATION]->(loc:Location)
        MATCH (prev)-[:SET_IN_LOCATION]->(prev_loc:Location)
        WHERE loc.id = prev_loc.id
        RETURN loc.id, loc.name
        """
        loc_results = await self.execute_query(location_query, {"scene_id": scene_id})

        # 檢查 3: 場景序列完整性 (LEADS_TO)
        sequence_query = """
        MATCH (prev:Scene)-[:LEADS_TO]->(current:Scene {id: $scene_id})
        MATCH (current)-[:LEADS_TO]->(next:Scene)
        RETURN prev.id as prev_id, next.id as next_id
        """
        sequence_results = await self.execute_query(sequence_query, {"scene_id": scene_id})

        return {
            "scene_id": scene_id,
            "is_consistent": len(issues) == 0 and len(warnings) == 0,
            "issues": issues,
            "warnings": warnings,
            "checked_at": datetime.utcnow().isoformat(),
        }

    # ========================================================================
    # 角色關係網絡
    # ========================================================================

    async def get_character_network(self, project_id: str) -> Dict[str, Any]:
        """獲取角色關係網絡"""
        query = """
        MATCH (c:Character {projectId: $project_id})-[r:RELATED_TO]-(other:Character)
        RETURN c.id, c.name, r.type, r.strength, other.id, other.name
        """
        results = await self.execute_query(query, {"project_id": project_id})

        # 構建網絡圖
        nodes = {}
        edges = []

        for r in results:
            if r["c.id"] not in nodes:
                nodes[r["c.id"]] = {"id": r["c.id"], "name": r["c.name"]}
            if r["other.id"] not in nodes:
                nodes[r["other.id"]] = {"id": r["other.id"], "name": r["other.name"]}

            edges.append({
                "source": r["c.id"],
                "target": r["other.id"],
                "type": r["r.type"],
                "strength": r["r.strength"],
            })

        return {
            "project_id": project_id,
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_characters": len(nodes),
            "total_relationships": len(edges),
        }

    # ========================================================================
    # 統計與分析
    # ========================================================================

    async def get_scene_statistics(self, project_id: str) -> Dict[str, Any]:
        """獲取場景統計"""
        query = """
        MATCH (p:Project {id: $project_id})-[:HAS_SCENE]->(s:Scene)
        RETURN s.status, count(s) as count
        GROUP BY s.status
        """
        results = await self.execute_query(query, {"project_id": project_id})

        return {
            "project_id": project_id,
            "by_status": {r["s.status"]: r["count"] for r in results},
            "total_scenes": sum(r["count"] for r in results),
        }

    async def get_scene_graph(self, project_id: str) -> Dict[str, Any]:
        """
        Returns full scene graph for frontend rendering.
        Uses LEADS_TO / CONTAINS / REQUIRES.
        """
        query = Neo4jSchema.get_query("get_full_graph")
        results = await self.execute_query(query, {"project_id": project_id})

        nodes = {}
        edges = []

        for r in results:
            s = r.get("s", {})
            sid = s.get("id")
            if sid and sid not in nodes:
                nodes[sid] = {
                    "id": sid,
                    "type": "scene",
                    "title": s.get("title", ""),
                    "status": s.get("status", ""),
                }

            # LEADS_TO edge
            next_scene = r.get("next")
            if next_scene and next_scene.get("id"):
                nid = next_scene["id"]
                if nid not in nodes:
                    nodes[nid] = {
                        "id": nid,
                        "type": "scene",
                        "title": next_scene.get("title", ""),
                        "status": next_scene.get("status", ""),
                    }
                edges.append({"source": sid, "target": nid, "type": "LEADS_TO"})

            # CONTAINS edge
            c = r.get("c")
            if c and c.get("id"):
                cid = c["id"]
                if cid not in nodes:
                    nodes[cid] = {
                        "id": cid,
                        "type": "character",
                        "name": c.get("name", ""),
                    }
                edges.append({"source": sid, "target": cid, "type": "CONTAINS"})

            # REQUIRES edge
            pr = r.get("pr")
            if pr and pr.get("id"):
                pid = pr["id"]
                if pid not in nodes:
                    nodes[pid] = {
                        "id": pid,
                        "type": "prop",
                        "name": pr.get("name", ""),
                    }
                edges.append({"source": sid, "target": pid, "type": "REQUIRES"})

        return {
            "project_id": project_id,
            "nodes": list(nodes.values()),
            "edges": edges,
        }


# ============================================================================
# 單例模式
# ============================================================================

_knowledge_graph_instance: Optional[KnowledgeGraphService] = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """獲取知識圖譜服務單例"""
    global _knowledge_graph_instance
    if not _knowledge_graph_instance:
        _knowledge_graph_instance = KnowledgeGraphService()
    return _knowledge_graph_instance
