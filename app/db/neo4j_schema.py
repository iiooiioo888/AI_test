"""
Neo4j Knowledge Graph Schema — aligned with TASKS.md §1 naming convention.

Relationships:
  LEADS_TO   — narrative sequence (Scene → Scene)
  CONTAINS   — scene contains character (Scene → Character)
  REQUIRES   — scene requires prop (Scene → Prop)
"""

NEO4J_SCHEMA = """
// ============================================================================
// Enterprise AI Video Production Platform - Neo4j Knowledge Graph Schema
// Relationship naming aligned with TASKS.md §1 specification
// ============================================================================

// ── Node Labels ───────────────────────────────────────────────
// Project, Scene, Character, Prop, Location, Prompt, User

// ── Unique Constraints ────────────────────────────────────────
CREATE CONSTRAINT project_id IF NOT EXISTS
  FOR (p:Project) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT scene_id IF NOT EXISTS
  FOR (s:Scene) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT character_id IF NOT EXISTS
  FOR (c:Character) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT prop_id IF NOT EXISTS
  FOR (pr:Prop) REQUIRE pr.id IS UNIQUE;
CREATE CONSTRAINT location_id IF NOT EXISTS
  FOR (l:Location) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT prompt_id IF NOT EXISTS
  FOR (pm:Prompt) REQUIRE pm.id IS UNIQUE;
CREATE CONSTRAINT user_id IF NOT EXISTS
  FOR (u:User) REQUIRE u.id IS UNIQUE;

// ── Existence Constraints ─────────────────────────────────────
CREATE CONSTRAINT scene_title_not_null IF NOT EXISTS
  FOR (s:Scene) REQUIRE (s.title, s.status) IS NOT NULL;
CREATE CONSTRAINT character_name_not_null IF NOT EXISTS
  FOR (c:Character) REQUIRE c.name IS NOT NULL;

// ── Indexes ───────────────────────────────────────────────────
CREATE INDEX scene_status_idx IF NOT EXISTS
  FOR (s:Scene) ON (s.status);
CREATE INDEX scene_branch_idx IF NOT EXISTS
  FOR (s:Scene) ON (s.branch);
CREATE INDEX scene_created_idx IF NOT EXISTS
  FOR (s:Scene) ON (s.createdAt);
CREATE INDEX character_project_idx IF NOT EXISTS
  FOR (c:Character) ON (c.projectId);
CREATE INDEX prop_project_idx IF NOT EXISTS
  FOR (pr:Prop) ON (pr.projectId);
CREATE INDEX location_project_idx IF NOT EXISTS
  FOR (l:Location) ON (l.projectId);
CREATE INDEX prompt_category_idx IF NOT EXISTS
  FOR (pm:Prompt) ON (pm.category);

// ── Fulltext Indexes ──────────────────────────────────────────
CREATE FULLTEXT INDEX scene_fulltext IF NOT EXISTS
  FOR (s:Scene) ON EACH [s.title, s.description];
CREATE FULLTEXT INDEX character_fulltext IF NOT EXISTS
  FOR (c:Character) ON EACH [c.name, c.description];

// ── Relationship Types (TASKS.md §1 aligned) ─────────────────
//
//   LEADS_TO      (Scene)-[:LEADS_TO {order}]->(Scene)
//     Narrative sequence — one scene leads to the next.
//
//   CONTAINS      (Scene)-[:CONTAINS {role}]->(Character)
//     A scene contains (features) a character.
//     Properties: role = "lead" | "supporting" | "extra"
//
//   REQUIRES      (Scene)-[:REQUIRES {mandatory}]->(Prop)
//     A scene requires a prop.
//     Properties: mandatory = true | false
//
// Additional relationships retained for richer graph queries:
//
//   SET_IN_LOCATION   (Scene)->(Location)
//   DEPENDS_ON        (Scene)->(Scene | Character | Prop | Location)
//   RELATED_TO        (Character)->(Character) {type, strength}
//   HAS_VERSION       (Scene)->(Scene)
//   BRANCHED_FROM     (Scene)->(Scene)
//   HAS_SCENE         (Project)->(Scene)
//   HAS_CHARACTER     (Project)->(Character)
//   HAS_PROP          (Project)->(Prop)
//   OWNS / MEMBER_OF  (User)->(Project)
//   CREATED / EDITED  (User)->(Scene)
"""


# ── Cypher Query Templates ─────────────────────────────────────

CYPHER_QUERIES = {
    # ── LEADS_TO queries ──────────────────────────────────────
    "get_next_scenes": """
        MATCH (s:Scene {id: $scene_id})-[:LEADS_TO*1..$max_depth]->(downstream:Scene)
        RETURN downstream.id AS id,
               downstream.title AS title,
               downstream.status AS status,
               length AS distance
        ORDER BY distance
    """,

    "get_previous_scenes": """
        MATCH (upstream:Scene)-[:LEADS_TO*1..$max_depth]->(s:Scene {id: $scene_id})
        RETURN upstream.id AS id,
               upstream.title AS title,
               upstream.status AS status,
               length AS distance
        ORDER BY distance
    """,

    "link_scene_sequence": """
        MATCH (a:Scene {id: $from_id}), (b:Scene {id: $to_id})
        MERGE (a)-[r:LEADS_TO]->(b)
        SET r.order = $order
        RETURN r
    """,

    # ── CONTAINS queries ──────────────────────────────────────
    "get_scene_characters": """
        MATCH (s:Scene {id: $scene_id})-[r:CONTAINS]->(c:Character)
        RETURN c.id AS id,
               c.name AS name,
               c.appearance AS appearance,
               r.role AS role
    """,

    "add_character_to_scene": """
        MATCH (s:Scene {id: $scene_id}), (c:Character {id: $character_id})
        MERGE (s)-[r:CONTAINS]->(c)
        SET r.role = $role
        RETURN r
    """,

    "get_character_scenes": """
        MATCH (s:Scene)-[:CONTAINS]->(c:Character {id: $character_id})
        RETURN s.id AS id, s.title AS title, s.status AS status
        ORDER BY s.createdAt
    """,

    # ── REQUIRES queries ──────────────────────────────────────
    "get_scene_props": """
        MATCH (s:Scene {id: $scene_id})-[r:REQUIRES]->(p:Prop)
        RETURN p.id AS id,
               p.name AS name,
               p.type AS type,
               r.mandatory AS mandatory
    """,

    "add_prop_to_scene": """
        MATCH (s:Scene {id: $scene_id}), (p:Prop {id: $prop_id})
        MERGE (s)-[r:REQUIRES]->(p)
        SET r.mandatory = $mandatory
        RETURN r
    """,

    # ── Ripple Effect Analysis ────────────────────────────────
    "ripple_downstream": """
        MATCH (changed:Scene {id: $scene_id})-[:LEADS_TO*1..]->(affected:Scene)
        WHERE affected.status IN ['draft', 'review']
        OPTIONAL MATCH (changed)-[:CONTAINS]->(c:Character)
        OPTIONAL MATCH (affected)-[:CONTAINS]->(c)
          WHERE c.status = 'dead'
        RETURN affected.id AS id,
               affected.title AS title,
               affected.status AS status,
               length AS distance,
               collect(DISTINCT c.name) AS dead_characters
        ORDER BY distance
    """,

    "ripple_prop_conflict": """
        MATCH (changed:Scene {id: $scene_id})-[:LEADS_TO*1..]->(affected:Scene)
        MATCH (changed)-[:REQUIRES]->(p:Prop)
        MATCH (affected)-[:REQUIRES]->(p)
        WHERE p.status = 'destroyed'
        RETURN affected.id AS id,
               p.name AS destroyed_prop,
               affected.title AS title
    """,

    # ── Consistency Checks ────────────────────────────────────
    "check_sequence_gaps": """
        MATCH (s:Scene {projectId: $project_id, branch: 'main'})
        WHERE NOT (s)-[:LEADS_TO]->() AND s.status <> 'completed'
        RETURN s.id AS id, s.title AS title, s.status AS status
    """,

    "find_unused_characters": """
        MATCH (c:Character {projectId: $project_id})
        WHERE NOT ()-[:CONTAINS]->(c)
        RETURN c.id AS id, c.name AS name
    """,

    "find_unused_props": """
        MATCH (p:Prop {projectId: $project_id})
        WHERE NOT ()-[:REQUIRES]->(p)
        RETURN p.id AS id, p.name AS name
    """,

    "character_co_appearances": """
        MATCH (s:Scene)-[:CONTAINS]->(c1:Character),
              (s)-[:CONTAINS]->(c2:Character)
        WHERE c1.id < c2.id
        RETURN c1.id AS char1_id, c1.name AS char1_name,
               c2.id AS char2_id, c2.name AS char2_name,
               count(s) AS co_appearances
        ORDER BY co_appearances DESC
    """,

    # ── Graph Export (for frontend rendering) ─────────────────
    "get_full_graph": """
        MATCH (p:Project {id: $project_id})-[:HAS_SCENE]->(s:Scene)
        OPTIONAL MATCH (s)-[leads:LEADS_TO]->(next:Scene)
        OPTIONAL MATCH (s)-[cont:CONTAINS]->(c:Character)
        OPTIONAL MATCH (s)-[req:REQUIRES]->(pr:Prop)
        RETURN s, leads, next, cont, c, req, pr
    """,

    # ── Orphan / Subgraph Detection ───────────────────────────
    "find_orphan_scenes": """
        MATCH (s:Scene {projectId: $project_id})
        WHERE NOT (s)-[:LEADS_TO]-()
          AND NOT ()-[:LEADS_TO]->(s)
        RETURN s.id AS id, s.title AS title
    """,

    "find_isolated_subgraphs": """
        MATCH (s:Scene {projectId: $project_id})
        WITH collect(s) AS scenes
        UNWIND scenes AS scene
        MATCH path = (scene)-[:LEADS_TO*]-(connected)
        RETURN scene.id AS root, collect(DISTINCT connected.id) AS component
    """,
}


# ── Schema Management Class ────────────────────────────────────

class Neo4jSchema:
    """Neo4j Schema manager with TASKS.md §1 aligned relationship names."""

    # Canonical relationship names (single source of truth)
    REL_LEADS_TO = "LEADS_TO"
    REL_CONTAINS = "CONTAINS"
    REL_REQUIRES = "REQUIRES"

    # Valid relationship matrix
    VALID_RELATIONSHIPS = {
        ("Project",  "Scene"):     ["HAS_SCENE"],
        ("Project",  "Character"): ["HAS_CHARACTER"],
        ("Project",  "Prop"):      ["HAS_PROP"],
        ("Project",  "Location"):  ["HAS_LOCATION"],
        ("Scene",    "Scene"):     ["LEADS_TO", "HAS_VERSION", "BRANCHED_FROM", "MERGED_INTO", "DEPENDS_ON"],
        ("Scene",    "Character"): ["CONTAINS", "DEPENDS_ON"],
        ("Scene",    "Prop"):      ["REQUIRES", "DEPENDS_ON"],
        ("Scene",    "Location"):  ["SET_IN_LOCATION", "DEPENDS_ON"],
        ("Scene",    "Prompt"):    ["USES_PROMPT"],
        ("Character","Character"): ["RELATED_TO"],
        ("Character","Scene"):     ["APPEARS_IN"],
        ("User",     "Project"):   ["OWNS", "MEMBER_OF"],
        ("User",     "Scene"):     ["CREATED", "EDITED"],
    }

    @staticmethod
    def get_schema() -> str:
        """Return the full Cypher schema definition."""
        return NEO4J_SCHEMA

    @staticmethod
    def get_query(name: str) -> str:
        """Get a predefined Cypher query template by name."""
        return CYPHER_QUERIES.get(name, "")

    @staticmethod
    def validate_relationship(source_label: str, target_label: str, rel_type: str) -> bool:
        """Check whether a relationship type is valid between two node labels."""
        valid = Neo4jSchema.VALID_RELATIONSHIPS.get((source_label, target_label), [])
        return rel_type in valid
