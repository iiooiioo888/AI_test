// ── Neo4j Relationship Migration ──────────────────────────────
// Migrate old relationship names → TASKS.md §1 aligned names:
//   NEXT             → LEADS_TO
//   PREVIOUS         → (removed, bidirectional via LEADS_TO query)
//   FEATURES_CHARACTER → CONTAINS
//   USES_PROP        → REQUIRES
//
// Run once on existing data. Safe to re-run (MATCH before CREATE).
// ============================================================================

// ── Step 1: NEXT → LEADS_TO ──────────────────────────────────
// Preserve the order property if it exists, otherwise default to 0.

MATCH (a:Scene)-[old:NEXT]->(b:Scene)
MERGE (a)-[new:LEADS_TO]->(b)
SET new.order = COALESCE(old.order, 0)
DELETE old
RETURN count(new) AS leads_to_created;

// ── Step 2: Remove PREVIOUS (inverse of LEADS_TO, queryable) ─

MATCH ()-[old:PREVIOUS]->()
DELETE old
RETURN count(old) AS previous_removed;

// ── Step 3: FEATURES_CHARACTER → CONTAINS ────────────────────
// Preserve importance → role mapping.

MATCH (s:Scene)-[old:FEATURES_CHARACTER]->(c:Character)
MERGE (s)-[new:CONTAINS]->(c)
SET new.role = CASE old.importance
    WHEN 'lead'       THEN 'lead'
    WHEN 'supporting' THEN 'supporting'
    ELSE 'extra'
END
DELETE old
RETURN count(new) AS contains_created;

// ── Step 4: USES_PROP → REQUIRES ─────────────────────────────

MATCH (s:Scene)-[old:USES_PROP]->(p:Prop)
MERGE (s)-[new:REQUIRES]->(p)
SET new.mandatory = COALESCE(old.mandatory, true)
DELETE old
RETURN count(new) AS requires_created;

// ── Step 5: Verification ─────────────────────────────────────
// Confirm no old relationships remain.

MATCH ()-[old:NEXT]->()          RETURN 'NEXT' AS rel, count(old) AS remaining
UNION
MATCH ()-[old:PREVIOUS]->()      RETURN 'PREVIOUS' AS rel, count(old) AS remaining
UNION
MATCH ()-[old:FEATURES_CHARACTER]->() RETURN 'FEATURES_CHARACTER' AS rel, count(old) AS remaining
UNION
MATCH ()-[old:USES_PROP]->()     RETURN 'USES_PROP' AS rel, count(old) AS remaining;
// Expected: all remaining = 0
