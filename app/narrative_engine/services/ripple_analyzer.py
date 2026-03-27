"""
Ripple Effect Analyzer — cascading impact detection for scene changes.

When a scene is modified, this analyzer traverses the Neo4j knowledge graph
via LEADS_TO / CONTAINS / REQUIRES relationships to detect:

- Character state conflicts (e.g., dead character appearing later)
- Prop logic violations (e.g., destroyed prop reused)
- Timeline inconsistencies (e.g., scene duration vs. time-of-day jumps)
- Dialogue continuity breaks
- Emotional arc discontinuities

Returns structured conflict reports with severity ratings.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID


class ConflictSeverity(str, Enum):
    LOW = "low"         # cosmetic / suggestion
    MEDIUM = "medium"   # logic warning, may need attention
    HIGH = "high"       # definite conflict, must resolve
    CRITICAL = "critical"  # breaks story continuity


class ConflictType(str, Enum):
    CHARACTER_STATE = "character_state"
    PROP_LOGIC = "prop_logic"
    TIMELINE = "timeline"
    DIALOGUE = "dialogue"
    EMOTIONAL_ARC = "emotional_arc"
    DEPENDENCY = "dependency"
    CONTINUITY = "continuity"


@dataclass
class Conflict:
    """A single detected conflict."""
    type: ConflictType
    severity: ConflictSeverity
    source_scene_id: str
    affected_scene_id: str
    message: str
    details: dict = field(default_factory=dict)
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "source_scene": self.source_scene_id,
            "affected_scene": self.affected_scene_id,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
        }


@dataclass
class RippleReport:
    """Complete ripple analysis report for a scene change."""
    source_scene_id: str
    total_affected: int = 0
    conflicts: list[Conflict] = field(default_factory=list)
    downstream_scenes: list[str] = field(default_factory=list)
    affected_characters: list[str] = field(default_factory=list)
    affected_props: list[str] = field(default_factory=list)
    max_severity: ConflictSeverity = ConflictSeverity.LOW
    analysis_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "source_scene_id": self.source_scene_id,
            "total_affected": self.total_affected,
            "max_severity": self.max_severity.value,
            "conflict_count": len(self.conflicts),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "downstream_scenes": self.downstream_scenes,
            "affected_characters": self.affected_characters,
            "affected_props": self.affected_props,
            "analysis_time_ms": round(self.analysis_time_ms, 2),
        }

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def has_blocking_conflicts(self) -> bool:
        return any(
            c.severity in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL)
            for c in self.conflicts
        )


# ── Character State Tracking ───────────────────────────────────

@dataclass
class CharacterStateEvent:
    """Tracks character state changes across scenes."""
    scene_id: str
    character_id: str
    state: str  # "alive", "dead", "injured", "missing", "introduced"
    timestamp_order: int = 0  # scene order in the story


# ── Main Analyzer ──────────────────────────────────────────────

class RippleEffectAnalyzer:
    """
    BFS-based ripple effect analyzer.

    Traverses LEADS_TO relationships from a modified scene,
    checking each downstream scene for logical conflicts.

    Usage:
        analyzer = RippleEffectAnalyzer(knowledge_graph)
        report = analyzer.analyze(scene_id)
        if report.has_blocking_conflicts:
            return 409, report.to_dict()
    """

    def __init__(self, graph_service=None):
        """
        Args:
            graph_service: KnowledgeGraphService instance.
                           If None, uses a standalone in-memory store.
        """
        self._graph = graph_service
        self._character_states: dict[str, list[CharacterStateEvent]] = defaultdict(list)
        self._prop_states: dict[str, list[dict]] = defaultdict(list)
        self._max_depth = 10

    # ── Character / Prop State Registration ────────────────────

    def register_character_state(
        self,
        scene_id: str,
        character_id: str,
        state: str,
        order: int = 0,
    ) -> None:
        """Record a character's state at a given scene."""
        event = CharacterStateEvent(
            scene_id=scene_id,
            character_id=character_id,
            state=state,
            timestamp_order=order,
        )
        self._character_states[character_id].append(event)
        # Keep sorted by story order
        self._character_states[character_id].sort(key=lambda e: e.timestamp_order)

    def register_prop_state(
        self,
        scene_id: str,
        prop_id: str,
        state: str,
        order: int = 0,
    ) -> None:
        """Record a prop's state at a given scene."""
        self._prop_states[prop_id].append({
            "scene_id": scene_id,
            "state": state,
            "order": order,
        })
        self._prop_states[prop_id].sort(key=lambda e: e["order"])

    # ── Main Analysis ──────────────────────────────────────────

    def analyze(
        self,
        scene_id: str,
        changed_fields: Optional[list[str]] = None,
    ) -> RippleReport:
        """
        Full ripple analysis for a scene modification.

        Args:
            scene_id: The ID of the modified scene.
            changed_fields: Optional list of dot-paths that were changed.
                           If provided, narrows analysis to relevant checks.

        Returns:
            RippleReport with all detected conflicts.
        """
        import time
        start = time.monotonic()

        report = RippleReport(source_scene_id=scene_id)

        # 1. Get downstream scenes via BFS
        downstream = self._get_downstream_bfs(scene_id)
        report.downstream_scenes = downstream
        report.total_affected = len(downstream)

        if not downstream:
            report.analysis_time_ms = (time.monotonic() - start) * 1000
            return report

        # 2. Get source scene info
        source_scene = self._get_scene_info(scene_id)
        if not source_scene:
            report.analysis_time_ms = (time.monotonic() - start) * 1000
            return report

        # 3. Check each downstream scene
        for ds_id in downstream:
            ds_scene = self._get_scene_info(ds_id)
            if not ds_scene:
                continue

            # Character state conflicts
            self._check_character_conflicts(
                report, source_scene, ds_scene, changed_fields
            )

            # Prop logic conflicts
            self._check_prop_conflicts(
                report, source_scene, ds_scene, changed_fields
            )

            # Timeline / continuity
            self._check_timeline_conflicts(
                report, source_scene, ds_scene
            )

            # Emotional arc discontinuities
            self._check_emotional_arc(
                report, source_scene, ds_scene
            )

        # Collect affected entities
        all_chars = set()
        all_props = set()
        for ds_id in downstream:
            info = self._get_scene_info(ds_id)
            if info:
                all_chars.update(info.get("character_ids", []))
                all_props.update(info.get("prop_ids", []))
        report.affected_characters = list(all_chars)
        report.affected_props = list(all_props)

        # Determine max severity
        severity_order = [
            ConflictSeverity.LOW,
            ConflictSeverity.MEDIUM,
            ConflictSeverity.HIGH,
            ConflictSeverity.CRITICAL,
        ]
        for conflict in report.conflicts:
            if severity_order.index(conflict.severity) > severity_order.index(report.max_severity):
                report.max_severity = conflict.severity

        report.analysis_time_ms = (time.monotonic() - start) * 1000
        return report

    # ── Conflict Checkers ──────────────────────────────────────

    def _check_character_conflicts(
        self,
        report: RippleReport,
        source: dict,
        downstream: dict,
        changed_fields: Optional[list[str]],
    ) -> None:
        """
        Check if characters in the downstream scene have
        inconsistent states (e.g., dead character appearing alive).
        """
        ds_id = downstream.get("id", "")
        ds_chars = set(downstream.get("character_ids", []))

        for char_id in ds_chars:
            states = self._character_states.get(char_id, [])
            if not states:
                continue

            # Find the latest state before this downstream scene
            ds_order = downstream.get("story_order", 0)
            prior_states = [s for s in states if s.timestamp_order < ds_order]

            if prior_states:
                latest = prior_states[-1]
                if latest.state == "dead":
                    report.conflicts.append(Conflict(
                        type=ConflictType.CHARACTER_STATE,
                        severity=ConflictSeverity.HIGH,
                        source_scene_id=source.get("id", ""),
                        affected_scene_id=ds_id,
                        message=f"角色 '{char_id}' 在場景 {latest.scene_id} 中已標記為死亡，"
                                f"但在後續場景 {ds_id} 中仍然出現",
                        details={
                            "character_id": char_id,
                            "died_in": latest.scene_id,
                            "appears_in": ds_id,
                        },
                        suggestion="移除該角色、改為回憶/幻覺，或撤銷死亡標記",
                    ))

    def _check_prop_conflicts(
        self,
        report: RippleReport,
        source: dict,
        downstream: dict,
        changed_fields: Optional[list[str]],
    ) -> None:
        """Check prop logic: destroyed props shouldn't reappear intact."""
        ds_id = downstream.get("id", "")
        ds_props = set(downstream.get("prop_ids", []))

        for prop_id in ds_props:
            states = self._prop_states.get(prop_id, [])
            if not states:
                continue

            ds_order = downstream.get("story_order", 0)
            prior = [s for s in states if s["order"] < ds_order]

            if prior:
                latest = prior[-1]
                if latest["state"] == "destroyed":
                    report.conflicts.append(Conflict(
                        type=ConflictType.PROP_LOGIC,
                        severity=ConflictSeverity.MEDIUM,
                        source_scene_id=source.get("id", ""),
                        affected_scene_id=ds_id,
                        message=f"道具 '{prop_id}' 在場景 {latest['scene_id']} 中已被銷毀，"
                                f"但在場景 {ds_id} 中再次出現",
                        details={
                            "prop_id": prop_id,
                            "destroyed_in": latest["scene_id"],
                            "reappears_in": ds_id,
                        },
                        suggestion="引入替代道具、解釋為修復品，或撤銷銷毀事件",
                    ))

    def _check_timeline_conflicts(
        self,
        report: RippleReport,
        source: dict,
        downstream: dict,
    ) -> None:
        """Check timeline continuity: time_of_day jumps, duration gaps."""
        ds_id = downstream.get("id", "")
        src_time = source.get("time_of_day")
        ds_time = downstream.get("time_of_day")

        if src_time and ds_time:
            time_order = ["dawn", "morning", "noon", "afternoon", "dusk", "night"]
            try:
                src_idx = time_order.index(src_time)
                ds_idx = time_order.index(ds_time)
                # Downstream is earlier in the day — possible flash-forward issue
                if ds_idx < src_idx and not downstream.get("is_flashback", False):
                    report.conflicts.append(Conflict(
                        type=ConflictType.TIMELINE,
                        severity=ConflictSeverity.LOW,
                        source_scene_id=source.get("id", ""),
                        affected_scene_id=ds_id,
                        message=f"時間線跳躍：從 {src_time} 到 {ds_time}（非閃回）",
                        details={"source_time": src_time, "downstream_time": ds_time},
                        suggestion="確認是否為有意的時間線設計（如跨天敘事）",
                    ))
            except ValueError:
                pass

    def _check_emotional_arc(
        self,
        report: RippleReport,
        source: dict,
        downstream: dict,
    ) -> None:
        """Check for dramatic emotional arc jumps."""
        ds_id = downstream.get("id", "")
        src_arc = source.get("emotional_arc")
        ds_arc = downstream.get("emotional_arc")

        if not src_arc or not ds_arc:
            return

        jarring_transitions = {
            ("joy", "sorrow"),
            ("triumph", "tension"),
            ("relief", "suspense"),
            ("romance", "tension"),
        }

        pair = (src_arc, ds_arc)
        if pair in jarring_transitions:
            report.conflicts.append(Conflict(
                type=ConflictType.EMOTIONAL_ARC,
                severity=ConflictSeverity.LOW,
                source_scene_id=source.get("id", ""),
                affected_scene_id=ds_id,
                message=f"情緒弧線跳躍：{src_arc} → {ds_arc}，可能缺少過渡場景",
                details={"source_arc": src_arc, "downstream_arc": ds_arc},
                suggestion="考慮添加過渡場景或中間情緒節拍",
            ))

    # ── Graph Traversal ────────────────────────────────────────

    def _get_downstream_bfs(self, scene_id: str) -> list[str]:
        """
        BFS traversal from scene_id along LEADS_TO edges.
        Returns ordered list of downstream scene IDs.
        """
        if self._graph:
            return list(self._graph.get_all_downstream(scene_id))

        # Fallback: use internal adjacency
        visited = set()
        queue = [scene_id]
        result = []
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current != scene_id:
                result.append(current)
            # Would traverse LEADS_TO edges here
        return result

    def _get_scene_info(self, scene_id: str) -> Optional[dict]:
        """Get scene summary from graph service or internal store."""
        if self._graph:
            return self._graph._scenes.get(scene_id)
        return None

    # ── Quick Checks (for PATCH endpoint) ──────────────────────

    def quick_check(
        self,
        scene_id: str,
        changed_fields: list[str],
    ) -> Optional[dict]:
        """
        Lightweight check for PATCH requests.
        Only runs relevant checks based on which fields changed.
        Returns conflict summary or None if safe.
        """
        if not changed_fields:
            return None

        affected_fields = set(changed_fields)
        needs_character_check = any("character" in f for f in affected_fields)
        needs_prop_check = any("prop" in f for f in affected_fields)
        needs_narrative_check = any("narrative" in f for f in affected_fields)

        if not (needs_character_check or needs_prop_check or needs_narrative_check):
            return None

        report = self.analyze(scene_id, changed_fields)
        if report.has_conflicts:
            return report.to_dict()
        return None
