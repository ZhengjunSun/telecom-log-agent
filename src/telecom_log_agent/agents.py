from __future__ import annotations

from collections import Counter, defaultdict

from .models import Finding, LogEvent


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
    rules = {
        "heartbeat timeout": (
            "Control-plane connectivity degradation",
            "Check transport reachability and peer process health",
        ),
        "authentication rejected": (
            "Credential or clock synchronization failure",
            "Validate certificate lifetime, shared credentials, and NTP offset",
        ),
        "packet loss": (
            "Transport congestion or interface degradation",
            "Inspect interface counters, QoS queues, and recent route changes",
        ),
        "database pool exhausted": (
            "Downstream database saturation",
            "Inspect slow queries and connection pool utilization",
        ),
    }

    def run(self, events: list[LogEvent]) -> Finding:
        corpus = "\n".join(e.message.lower() for e in events)
        matched = [(needle, result) for needle, result in self.rules.items() if needle in corpus]
        if not matched:
            return Finding(self.name, "No deterministic runbook rule matched", 0.35)
        needle, (cause, action) = matched[0]
        return Finding(self.name, f"{cause}. Suggested check: {action}", 0.82, (needle,))


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

