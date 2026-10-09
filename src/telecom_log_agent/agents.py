from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import ClassVar

from .models import Finding, LogEvent


@dataclass(frozen=True)
class RunbookRule:
    code: str
    needle: str
    cause: str
    action: str


@dataclass(frozen=True)
class Diagnosis:
    code: str
    cause: str
    action: str
    evidence: tuple[str, ...]
    confidence: float


class PatternAgent:
    name = "pattern-agent"

    def run(self, events: list[LogEvent]) -> Finding:
        counts = Counter(event.template for event in events)
        template, count = counts.most_common(1)[0]
        return Finding(
            self.name,
            f"Most frequent event template occurred {count} times: {template}",
            min(0.55 + count / max(len(events), 1) * 0.35, 0.95),
            (template,),
        )


class TopologyAgent:
    name = "topology-agent"

    def run(self, events: list[LogEvent]) -> Finding:
        errors: dict[str, int] = defaultdict(int)
        for event in events:
            if event.severity in {"ERROR", "CRITICAL"}:
                errors[event.node] += 1
        if not errors:
            return Finding(self.name, "No node has a critical error concentration", 0.50)
        node = max(errors, key=errors.get)
        return Finding(
            self.name,
            f"Failure propagation appears to originate near node {node}",
            min(0.60 + errors[node] * 0.08, 0.96),
            tuple(e.message for e in events if e.node == node and e.severity in {"ERROR", "CRITICAL"})[:3],
        )


class KnowledgeAgent:
    name = "knowledge-agent"
    rules: ClassVar[tuple[RunbookRule, ...]] = (
        RunbookRule(
            "control_plane_connectivity",
            "heartbeat timeout",
            "Control-plane connectivity degradation",
            "Check transport reachability and peer process health",
        ),
        RunbookRule(
            "credential_or_clock",
            "authentication rejected",
            "Credential or clock synchronization failure",
            "Validate certificate lifetime, shared credentials, and NTP offset",
        ),
        RunbookRule(
            "transport_degradation",
            "packet loss",
            "Transport congestion or interface degradation",
            "Inspect interface counters, QoS queues, and recent route changes",
        ),
        RunbookRule(
            "database_saturation",
            "database pool exhausted",
            "Downstream database saturation",
            "Inspect slow queries and connection pool utilization",
        ),
    )

    def diagnose(self, events: list[LogEvent]) -> Diagnosis:
        matches: list[tuple[int, int, int, RunbookRule, tuple[str, ...]]] = []
        severity_weight = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "CRITICAL": 4}
        for order, rule in enumerate(self.rules):
            evidence = tuple(e.message for e in events if rule.needle in e.message.lower())
            if evidence:
                score = sum(
                    severity_weight[e.severity]
                    for e in events
                    if rule.needle in e.message.lower()
                )
                matches.append((len(evidence), score, -order, rule, evidence))
        if not matches:
            return Diagnosis(
                "unknown",
                "No deterministic runbook rule matched",
                "Escalate with the preserved evidence bundle",
                (),
                0.35,
            )
        hit_count, _, _, rule, evidence = max(matches, key=lambda item: item[:3])
        return Diagnosis(
            rule.code,
            rule.cause,
            rule.action,
            evidence[:3],
            min(0.68 + 0.07 * hit_count, 0.89),
        )

    def run(self, events: list[LogEvent]) -> Finding:
        diagnosis = self.diagnose(events)
        summary = diagnosis.cause
        if diagnosis.code != "unknown":
            summary += f". Suggested check: {diagnosis.action}"
        return Finding(self.name, summary, diagnosis.confidence, diagnosis.evidence)


class CriticAgent:
    name = "critic-agent"

    def run(self, findings: list[Finding]) -> Finding:
        well_supported = [f for f in findings if f.evidence and f.confidence >= 0.7]
        confidence = min(0.45 + 0.15 * len(well_supported), 0.90)
        return Finding(
            self.name,
            f"Evidence audit accepted {len(well_supported)}/{len(findings)} upstream findings",
            confidence,
            tuple(f.agent for f in well_supported),
        )
