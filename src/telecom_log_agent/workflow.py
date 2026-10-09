from __future__ import annotations

import hashlib

from .agents import CriticAgent, KnowledgeAgent, PatternAgent, TopologyAgent
from .models import IncidentReport, LogEvent
from .parser import parse_logs


class IncidentWorkflow:
    """Deterministic orchestration core; an LLM can replace individual agents."""

    def __init__(self) -> None:
        self.pattern = PatternAgent()
        self.topology = TopologyAgent()
        self.knowledge = KnowledgeAgent()
        self.critic = CriticAgent()

    def analyze(self, raw_logs: str) -> IncidentReport:
        events = parse_logs(raw_logs)
        if not events:
            raise ValueError("at least one log event is required")
        findings = [
            self.pattern.run(events),
            self.topology.run(events),
            self.knowledge.run(events),
        ]
        diagnosis = self.knowledge.diagnose(events)
        findings.append(self.critic.run(findings))
        severity = self._severity(events)
        knowledge = findings[2].summary
        root_cause = knowledge.split(". Suggested check:", 1)[0]
        actions = self._actions(events, knowledge)
        digest = hashlib.sha256(raw_logs.encode()).hexdigest()[:10]
        return IncidentReport(
            incident_id=f"INC-{digest.upper()}",
            severity=severity,
            probable_root_cause=root_cause,
            timeline=[f"{e.timestamp} [{e.node}] {e.severity}: {e.message}" for e in events],
            findings=findings,
            recommended_actions=actions,
            requires_human_approval=severity in {"P1", "P2"},
            metadata={
                "event_count": len(events),
                "nodes": sorted({e.node for e in events}),
                "diagnosis_code": diagnosis.code,
                "root_cause_node": self._root_cause_node(events),
                "data_classification": "synthetic-demo",
            },
        )

    @staticmethod
    def _root_cause_node(events: list[LogEvent]) -> str | None:
        weights = {"CRITICAL": 4, "ERROR": 3, "WARN": 1, "INFO": 0, "DEBUG": 0}
        scores: dict[str, int] = {}
        for event in events:
            scores[event.node] = scores.get(event.node, 0) + weights[event.severity]
        return max(scores, key=scores.get) if any(scores.values()) else None

    @staticmethod
    def _severity(events: list[LogEvent]) -> str:
        levels = {"CRITICAL": 4, "ERROR": 3, "WARN": 2, "INFO": 1, "DEBUG": 0}
        score = sum(levels[e.severity] for e in events)
        critical = sum(e.severity == "CRITICAL" for e in events)
        if critical >= 2 or score >= 16:
            return "P1"
        if critical or score >= 9:
            return "P2"
        if score >= 4:
            return "P3"
        return "P4"

    @staticmethod
    def _actions(events: list[LogEvent], knowledge: str) -> list[str]:
        actions = ["Preserve the incident timeline and correlated node logs"]
        if "Suggested check:" in knowledge:
            actions.append(knowledge.split("Suggested check:", 1)[1].strip())
        actions.extend(
            [
                "Run the proposed check in read-only mode",
                "Require an operator approval before any network-changing remediation",
            ]
        )
        return actions
