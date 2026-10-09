from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agents import KnowledgeAgent
from .parser import parse_logs
from .workflow import IncidentWorkflow


def baseline_diagnose(raw_logs: str) -> tuple[str, str | None]:
    """Single-event baseline: classify only the first highest-severity event."""
    events = parse_logs(raw_logs)
    weights = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "CRITICAL": 4}
    event = max(enumerate(events), key=lambda item: (weights[item[1].severity], -item[0]))[1]
    message = event.message.lower()
    for rule in KnowledgeAgent.rules:
        if rule.needle in message:
            return rule.code, event.node
    return "unknown", event.node


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("evaluation data must be a non-empty JSON array")
    return data


def evaluate(path: Path) -> dict[str, Any]:
    rows = []
    workflow = IncidentWorkflow()
    for case in load_cases(path):
        report = workflow.analyze(case["logs"])
        baseline_code, baseline_node = baseline_diagnose(case["logs"])
        expected_code = case["expected_diagnosis"]
        expected_node = case["expected_node"]
        rows.append(
            {
                "case_id": case["case_id"],
                "expected": expected_code,
                "baseline": baseline_code,
                "workflow": report.metadata["diagnosis_code"],
                "expected_node": expected_node,
                "baseline_node": baseline_node,
                "workflow_node": report.metadata["root_cause_node"],
                "baseline_correct": baseline_code == expected_code,
                "workflow_correct": report.metadata["diagnosis_code"] == expected_code,
                "workflow_node_correct": report.metadata["root_cause_node"] == expected_node,
            }
        )
    total = len(rows)
    return {
        "dataset": str(path),
        "cases": total,
        "baseline_diagnosis_accuracy": sum(r["baseline_correct"] for r in rows) / total,
        "workflow_diagnosis_accuracy": sum(r["workflow_correct"] for r in rows) / total,
        "workflow_node_accuracy": sum(r["workflow_node_correct"] for r in rows) / total,
        "results": rows,
    }
