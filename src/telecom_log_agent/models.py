from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LogEvent:
    timestamp: str
    node: str
    severity: str
    message: str
    template: str = ""


@dataclass(frozen=True)
class Finding:
    agent: str
    summary: str
    confidence: float
    evidence: tuple[str, ...] = ()


@dataclass
class IncidentReport:
    incident_id: str
    severity: str
    probable_root_cause: str
    timeline: list[str]
    findings: list[Finding]
    recommended_actions: list[str]
    requires_human_approval: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

