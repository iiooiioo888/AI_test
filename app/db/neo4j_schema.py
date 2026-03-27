"""
Neo4j 知識圖譜 Schema
用於存儲角色/情節/道具依賴關係，實現漣漪效應分析
"""

# Neo4j Cypher Schema 定義
NEO4J_SCHEMA = """
// ============================================================================
// Enterprise AI Video Production Platform - Neo4j Knowledge Graph Schema
// ============================================================================

// 節點標籤 (Node Labels)
// - Project: 項目
// - Scene: 場景
// - Character: 角色
// - Prop: 道具
// - Location: 地點
// - Prompt: 提示詞
// - User: 用戶

// ============================================================================
// 創建約束 (Constraints)
// ============================================================================

// 唯一性約束
CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT scene_id IF NOT EXISTS FOR (s:Scene) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT character_id IF NOT EXISTS FOR (c:Character) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT prop_id IF NOT EXISTS FOR (pr:Prop) REQUIRE pr.id IS UNIQUE;
CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT prompt_id IF NOT EXISTS FOR (pm:Prompt) REQUIRE pm.id IS UNIQUE;
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;

// 存在性約束 (確保關鍵屬性存在)
CREATE CONSTRAINT scene_title IF NOT EXISTS FOR (s:Scene) REQUIRE (s.title, s.status) IS NOT NULL;
CREATE CONSTRAINT character_name IF NOT EXISTS FOR (c:Character) REQUIRE (c.name) IS NOT NULL;

// ============================================================================
// 創建索引 (Indexes) - 優化查詢性能
// ============================================================================

CREATE INDEX scene_status_idx IF NOT EXISTS FOR (s:Scene) ON (s.status);
CREATE INDEX scene_branch_idx IF NOT EXISTS FOR (s:Scene) ON (s.branch);
CREATE INDEX scene_created_idx IF NOT EXISTS FOR (s:Scene) ON (s.createdAt);
CREATE INDEX character_project_idx IF NOT EXISTS FOR (c:Character) ON (c.projectId);
CREATE INDEX prop_project_idx IF NOT EXISTS FOR (pr:Prop) ON (pr.projectId);
CREATE INDEX location_project_idx IF NOT EXISTS FOR (l:Location) ON (l.projectId);
CREATE INDEX prompt_category_idx IF NOT EXISTS FOR (pm:Prompt) ON (pm.category);
CREATE INDEX prompt_tags_idx IF NOT EXISTS FOR (pm:Prompt) ON (pm.tags);

// 全文索引 - 搜索優化
CREATE INDEX scene_title_fulltext IF NOT EXISTS FOR (s:Scene) ON (s.title, s.description);
CREATE INDEX character_name_fulltext IF NOT EXISTS FOR (c:Character) ON (c.name, c.description);

// ============================================================================
// 關係類型 (Relationship Types)
// ============================================================================

// 項目結構關係
// (:Project)-[:HAS_SCENE]->(:Scene)
// (:Project)-[:HAS_CHARACTER]->(:Character)
// (:Project)-[:HAS_PROP]->(:Prop)
// (:Project)-[:HAS_LOCATION]->(:Location)

// 場景序列關係 (敘事順序)
// (:Scene)-[:NEXT]->(:Scene)
// (:Scene)-[:PREVIOUS]->(:Scene)

// 場景內容關係
// (:Scene)-[:FEATURES_CHARACTER]->(:Character)
// (:Scene)-[:USES_PROP]->(:Prop)
// (:Scene)-[:SET_IN_LOCATION]->(:Location)
// (:Scene)-[:USES_PROMPT]->(:Prompt)

// 角色關係 (知識圖譜核心)
// (:Character)-[:RELATED_TO]->(:Character)  {type: 'friend/enemy/family/etc'}
// (:Character)-[:APPEARS_IN]->(:Scene)

// 依賴關係 (漣漪效應分析)
// (:Scene)-[:DEPENDS_ON]->(:Scene)  // 場景依賴
// (:Scene)-[:DEPENDS_ON]->(:Character)  // 依賴角色設定
// (:Scene)-[:DEPENDS_ON]->(:Prop)  // 依賴道具
// (:Scene)-[:DEPENDS_ON]->(:Location)  // 依賴地點

// 版本控制關係
// (:Scene)-[:HAS_VERSION]->(:Scene)  // 版本歷史
// (:Scene)-[:BRANCHED_FROM]->(:Scene)  // 分支來源
// (:Scene)-[:MERGED_INTO]->(:Scene)  // 合併目標

// 用戶協作關係
// (:User)-[:CREATED]->(:Scene)
// (:User)-[:EDITED]->(:Scene)
// (:User)-[:OWNS]->(:Project)
// (:User)-[:MEMBER_OF]->(:Project) {role: 'admin/editor/viewer'}

// ============================================================================
// 示例數據插入
// ============================================================================

// 創建項目
MERGE (p:Project {
    id: 'proj-001',
    name: '英雄傳奇',
    status: 'active',
    createdAt: datetime('2026-03-27')
})

// 創建角色
MERGE (c1:Character {
    id: 'char-001',
    name: '李明',
    appearance: '黑色長髮，銳利的眼神，身穿青色長袍',
    personality: '勇敢，正義，堅毅',
    projectId: 'proj-001'
})

MERGE (c2:Character {
    id: 'char-002',
    name: '王芳',
    appearance: '長髮及腰，溫柔的笑容，身穿白色連衣裙',
    personality: '善良，聰明，體貼',
    projectId: 'proj-001'
})

// 創建角色關係
MERGE (c1)-[r:RELATED_TO {type: '盟友', strength: 0.9}]->(c2)

// 創建場景
MERGE (s1:Scene {
    id: 'scene-001',
    title: '英雄登場',
    description: '主角在黎明時分登上山巔',
    status: 'draft',
    branch: 'main',
    version: '1.0.0',
    duration: 8.0,
    createdAt: datetime('2026-03-27'),
    updatedAt: datetime('2026-03-27')
})

// 創建場景序列
MERGE (s2:Scene {
    id: 'scene-002',
    title: '遭遇敵人',
    status: 'draft',
    branch: 'main',
    version: '1.0.0'
})

MERGE (s1)-[:NEXT]->(s2)
MERGE (s2)-[:PREVIOUS]->(s1)

// 創建場景與角色的關係
MERGE (s1)-[:FEATURES_CHARACTER {importance: 'lead'}]->(c1)
MERGE (s2)-[:FEATURES_CHARACTER {importance: 'lead'}]->(c1)
MERGE (s2)-[:FEATURES_CHARACTER {importance: 'supporting'}]->(c2)

// 創建依賴關係 (用於漣漪效應分析)
MERGE (s2)-[:DEPENDS_ON]->(s1)  // 場景 2 依賴場景 1 的結尾
MERGE (s2)-[:DEPENDS_ON]->(c1)  // 場景 2 依賴角色 1 的設定

// 創建地點
MERGE (l1:Location {
    id: 'loc-001',
    name: '青雲山巔',
    environmentType: 'outdoor',
    timeOfDay: 'dawn',
    projectId: 'proj-001'
})

MERGE (s1)-[:SET_IN_LOCATION]->(l1)

// 創建用戶與協作關係
MERGE (u1:User {
    id: 'user-001',
    username: 'director_zhang',
    email: 'zhang@example.com',
    role: 'director'
})

MERGE (u1)-[:OWNS]->(p)
MERGE (u1)-[:CREATED]->(s1)
MERGE (u1)-[:MEMBER_OF {role: 'admin'}]->(p)

// ============================================================================
// 漣漪效應分析查詢 (Ripple Effect Analysis)
// ============================================================================

// 查詢 1: 當角色設定改變時，找出所有受影響的場景
// MATCH (c:Character {id: 'char-001'})<-[:FEATURES_CHARACTER]-(s:Scene)
// RETURN s.id, s.title, s.status

// 查詢 2: 當場景修改時，找出所有後續依賴的場景 (遞歸)
// MATCH path = (s:Scene {id: 'scene-001'})-[:NEXT*]->(affected:Scene)
// WHERE affected.status <> 'completed'
// RETURN path, length(path) as distance

// 查詢 3: 完整的依賴影響分析
// MATCH (target:Scene {id: 'scene-001'})
// MATCH (target)-[:DEPENDS_ON*]->(dependency)
// MATCH (dependency)<-[:DEPENDS_ON*]-(affected:Scene)
// WHERE affected <> target
// RETURN DISTINCT affected, dependency

// 查詢 4: 角色關係網絡可視化
// MATCH (c:Character {projectId: 'proj-001'})-[r:RELATED_TO]-(other:Character)
// RETURN c, r, other

// ============================================================================
// 連貫性檢查查詢 (Consistency Check)
// ============================================================================

// 檢查 1: 角色外觀一致性 (跨場景)
// MATCH (c:Character {id: 'char-001'})<-[:FEATURES_CHARACTER]-(s:Scene)
// RETURN s.id, s.sceneData.characterAppearance as appearance
// ORDER BY s.createdAt

// 檢查 2: 場景序列完整性
// MATCH (s:Scene {projectId: 'proj-001', branch: 'main'})
// WHERE NOT (s)-[:NEXT]->() AND s.status <> 'completed'
// RETURN s  // 找到序列斷點

// 檢查 3: 未使用的角色/道具
// MATCH (c:Character {projectId: 'proj-001'})
// WHERE NOT (c)<-[:FEATURES_CHARACTER]-()
// RETURN c  // 找到未使用的角色
"""


# Cypher 查詢模板
CYPHER_QUERIES = {
    # 漣漪效應分析
    "ripple_effect_character": """
        MATCH (c:Character {id: $character_id})<-[:FEATURES_CHARACTER]-(s:Scene)
        WHERE s.status IN ['draft', 'review', 'locked']
        RETURN s.id, s.title, s.status, s.branch
        ORDER BY s.createdAt
    """,
    
    "ripple_effect_scene": """
        MATCH path = (s:Scene {id: $scene_id})-[:NEXT*]->(affected:Scene)
        WHERE affected.status <> 'completed'
        RETURN affected.id, affected.title, affected.status, length(path) as distance
        ORDER BY distance
    """,
    
    # 依賴關係分析
    "get_dependencies": """
        MATCH (target:Scene {id: $scene_id})-[:DEPENDS_ON]->(dependency)
        RETURN dependency, labels(dependency)[0] as type
    """,
    
    "get_dependents": """
        MATCH (target:Scene {id: $scene_id})<-[:DEPENDS_ON]-(dependent:Scene)
        RETURN dependent.id, dependent.title, dependent.status
    """,
    
    # 連貫性檢查
    "check_character_consistency": """
        MATCH (c:Character {id: $character_id})<-[:FEATURES_CHARACTER]-(s:Scene)
        RETURN s.id, s.title, s.sceneData.characterAppearance as appearance
        ORDER BY s.createdAt
    """,
    
    "check_sequence_integrity": """
        MATCH (s:Scene {projectId: $project_id, branch: 'main'})
        WHERE NOT (s)-[:NEXT]->() AND s.status <> 'completed'
        RETURN s.id, s.title, s.status
    """,
    
    # 角色關係網絡
    "get_character_network": """
        MATCH (c:Character {projectId: $project_id})-[r:RELATED_TO]-(other:Character)
        RETURN c.id, c.name, r.type, r.strength, other.id, other.name
    """,
    
    # 場景統計
    "scene_statistics": """
        MATCH (p:Project {id: $project_id})-[:HAS_SCENE]->(s:Scene)
        RETURN s.status, count(s) as count
        GROUP BY s.status
    """,
    
    # 版本歷史
    "get_version_history": """
        MATCH (current:Scene {id: $scene_id})
        OPTIONAL MATCH (current)-[:HAS_VERSION*]-(ancestor)
        RETURN current, ancestor
        ORDER BY ancestor.version DESC
    """,
}


class Neo4jSchema:
    """Neo4j Schema 管理類"""
    
    @staticmethod
    def get_schema() -> str:
        """返回完整的 Schema 定義"""
        return NEO4J_SCHEMA
    
    @staticmethod
    def get_query(name: str) -> str:
        """獲取預定義的 Cypher 查詢"""
        return CYPHER_QUERIES.get(name, "")
    
    @staticmethod
    def validate_relationship(source_label: str, target_label: str, rel_type: str) -> bool:
        """驗證關係是否合法"""
        valid_relationships = {
            ('Project', 'Scene'): ['HAS_SCENE'],
            ('Project', 'Character'): ['HAS_CHARACTER'],
            ('Project', 'Prop'): ['HAS_PROP'],
            ('Project', 'Location'): ['HAS_LOCATION'],
            ('Scene', 'Scene'): ['NEXT', 'PREVIOUS', 'HAS_VERSION', 'BRANCHED_FROM', 'MERGED_INTO', 'DEPENDS_ON'],
            ('Scene', 'Character'): ['FEATURES_CHARACTER', 'DEPENDS_ON'],
            ('Scene', 'Prop'): ['USES_PROP', 'DEPENDS_ON'],
            ('Scene', 'Location'): ['SET_IN_LOCATION', 'DEPENDS_ON'],
            ('Scene', 'Prompt'): ['USES_PROMPT'],
            ('Character', 'Character'): ['RELATED_TO'],
            ('Character', 'Scene'): ['APPEARS_IN'],
            ('User', 'Project'): ['OWNS', 'MEMBER_OF'],
            ('User', 'Scene'): ['CREATED', 'EDITED'],
        }
        
        return valid_relationships.get((source_label, target_label), []).count(rel_type) > 0
