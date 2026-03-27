// ═══════════════════════════════════════════════════════════════
// Neo4j Initialization — AVP Narrative Engine
// ═══════════════════════════════════════════════════════════════
//
// Creates constraints, indexes, and sample data for the
// narrative knowledge graph.
//
// Execute: cat neo4j_init.cypher | cypher-shell -u neo4j -p password
// ═══════════════════════════════════════════════════════════════


// ── 1. Uniqueness Constraints ─────────────────────────────────

CREATE CONSTRAINT scene_id_unique IF NOT EXISTS
FOR (s:Scene) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT character_id_unique IF NOT EXISTS
FOR (c:Character) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT prop_id_unique IF NOT EXISTS
FOR (p:Prop) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT arc_id_unique IF NOT EXISTS
FOR (a:StoryArc) REQUIRE a.id IS UNIQUE;


// ── 2. Indexes for Performance ────────────────────────────────

CREATE INDEX scene_state_idx IF NOT EXISTS
FOR (s:Scene) ON (s.state);

CREATE INDEX scene_branch_idx IF NOT EXISTS
FOR (s:Scene) ON (s.branch);

CREATE INDEX scene_title_idx IF NOT EXISTS
FOR (s:Scene) ON (s.title);

CREATE INDEX character_name_idx IF NOT EXISTS
FOR (c:Character) ON (c.name);

CREATE INDEX prop_name_idx IF NOT EXISTS
FOR (p:Prop) ON (p.name);


// ── 3. Full-text Search Indexes ───────────────────────────────

CREATE FULLTEXT INDEX scene_content_ft IF NOT EXISTS
FOR (s:Scene) ON EACH [s.title, s.narrative_beat, s.narrative_desc];

CREATE FULLTEXT INDEX character_desc_ft IF NOT EXISTS
FOR (c:Character) ON EACH [c.name, c.description];


// ── 4. Sample Data (Development) ─────────────────────────────

// Characters
MERGE (c1:Character {id: 'c1'})
ON CREATE SET c1.name = '主角', c1.description = '攝影師，孤獨而敏銳的觀察者', c1.state = 'alive';

MERGE (c2:Character {id: 'c2'})
ON CREATE SET c2.name = '林薇', c2.description = '神秘女人，戴墨鏡的訪客', c2.state = 'alive';

MERGE (c3:Character {id: 'c3'})
ON CREATE SET c3.name = '老張', c3.description = '工廠守衛，知道太多秘密', c3.state = 'alive';

// Props
MERGE (p1:Prop {id: 'p1'})
ON CREATE SET p1.name = '相機', p1.description = '主角的徠卡相機', p1.state = 'intact';

MERGE (p2:Prop {id: 'p2'})
ON CREATE SET p2.name = '墨鏡', p2.description = '林薇的標誌性墨鏡', p2.state = 'intact';

MERGE (p3:Prop {id: 'p3'})
ON CREATE SET p3.name = '咖啡杯', p3.description = '印有特殊標記的咖啡杯', p3.state = 'intact';

MERGE (p4:Prop {id: 'p4'})
ON CREATE SET p4.name = '手電筒', p4.description = '老舊的手電筒', p4.state = 'intact';

MERGE (p5:Prop {id: 'p5'})
ON CREATE SET p5.name = '鐵門鑰匙', p5.description = '通往秘密區域的鑰匙', p4.state = 'intact';

// Scenes
MERGE (s1:Scene {id: 's1'})
ON CREATE SET s1.title = '序幕：城市甦醒',
              s1.state = 'COMPLETED',
              s1.version = 3,
              s1.branch = 'main',
              s1.narrative_beat = '黎明時分，攝影師在空曠的屋頂等待日出';

MERGE (s2:Scene {id: 's2'})
ON CREATE SET s2.title = '第一幕：咖啡邂逅',
              s2.state = 'LOCKED',
              s2.version = 2,
              s2.branch = 'main',
              s2.narrative_beat = '主角在咖啡館遇見神秘人物';

MERGE (s3:Scene {id: 's3'})
ON CREATE SET s3.title = '第二幕：追逐真相',
              s3.state = 'REVIEW',
              s3.version = 1,
              s3.branch = 'main',
              s3.narrative_beat = '主角跟蹤線索來到廢棄工廠';

MERGE (s4:Scene {id: 's4'})
ON CREATE SET s4.title = '第三幕：真相大白',
              s4.state = 'DRAFT',
              s4.version = 1,
              s4.branch = 'main',
              s4.narrative_beat = '所有線索匯聚，真相終於揭曉';


// ── 5. Relationships ──────────────────────────────────────────

// LEADS_TO: Scene story order
MATCH (s1:Scene {id: 's1'}), (s2:Scene {id: 's2'})
MERGE (s1)-[:LEADS_TO {order: 1}]->(s2);

MATCH (s2:Scene {id: 's2'}), (s3:Scene {id: 's3'})
MERGE (s2)-[:LEADS_TO {order: 2}]->(s3);

MATCH (s3:Scene {id: 's3'}), (s4:Scene {id: 's4'})
MERGE (s3)-[:LEADS_TO {order: 3}]->(s4);

// CONTAINS: Scene → Character
MATCH (s1:Scene {id: 's1'}), (c1:Character {id: 'c1'})
MERGE (s1)-[:CONTAINS {role: 'protagonist'}]->(c1);

MATCH (s2:Scene {id: 's2'}), (c1:Character {id: 'c1'})
MERGE (s2)-[:CONTAINS {role: 'protagonist'}]->(c1);

MATCH (s2:Scene {id: 's2'}), (c2:Character {id: 'c2'})
MERGE (s2)-[:CONTAINS {role: 'guest'}]->(c2);

MATCH (s3:Scene {id: 's3'}), (c1:Character {id: 'c1'})
MERGE (s3)-[:CONTAINS {role: 'protagonist'}]->(c1);

MATCH (s4:Scene {id: 's4'}), (c1:Character {id: 'c1'})
MERGE (s4)-[:CONTAINS {role: 'protagonist'}]->(c1);

MATCH (s4:Scene {id: 's4'}), (c2:Character {id: 'c2'})
MERGE (s4)-[:CONTAINS {role: 'key_witness'}]->(c2);

// REQUIRES: Scene → Prop
MATCH (s1:Scene {id: 's1'}), (p1:Prop {id: 'p1'})
MERGE (s1)-[:REQUIRES {importance: 'critical'}]->(p1);

MATCH (s2:Scene {id: 's2'}), (p2:Prop {id: 'p2'})
MERGE (s2)-[:REQUIRES {importance: 'symbolic'}]->(p2);

MATCH (s2:Scene {id: 's2'}), (p3:Prop {id: 'p3'})
MERGE (s2)-[:REQUIRES {importance: 'background'}]->(p3);

MATCH (s3:Scene {id: 's3'}), (p4:Prop {id: 'p4'})
MERGE (s3)-[:REQUIRES {importance: 'critical'}]->(p4);

MATCH (s3:Scene {id: 's3'}), (p5:Prop {id: 'p5'})
MERGE (s3)-[:REQUIRES {importance: 'critical'}]->(p5);


// ── 6. Verification Queries ───────────────────────────────────
// Run these to verify the graph:
//
// // All story chains (LEADS_TO paths)
// MATCH path = (s:Scene)-[:LEADS_TO*]->(s2:Scene)
// RETURN [n IN nodes(path) | n.title] AS chain;
//
// // Characters per scene
// MATCH (s:Scene)-[:CONTAINS]->(c:Character)
// RETURN s.title, collect(c.name) AS characters;
//
// // Props per scene
// MATCH (s:Scene)-[:REQUIRES]->(p:Prop)
// RETURN s.title, collect(p.name) AS props;
//
// // Ripple from s2
// MATCH path = (s:Scene {id: 's2'})-[:LEADS_TO*]->(downstream)
// RETURN downstream.title, downstream.state;
