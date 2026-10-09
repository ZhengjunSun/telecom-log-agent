from pathlib import Path

from telecom_log_agent.evaluation import baseline_diagnose, evaluate

DATASET = Path(__file__).parents[1] / "evals" / "incidents.json"


def test_single_event_baseline_prefers_highest_severity() -> None:
    logs = (
        "2026-01-01T00:00:01Z UPF-01 ERROR packet loss 40 percent\n"
        "2026-01-01T00:00:02Z AMF-01 CRITICAL heartbeat timeout peer=10.0.0.1"
    )
    assert baseline_diagnose(logs) == ("control_plane_connectivity", "AMF-01")


def test_published_evaluation_is_reproducible() -> None:
    result = evaluate(DATASET)
    assert result["cases"] == 8
    assert result["baseline_diagnosis_accuracy"] == 0.625
    assert result["workflow_diagnosis_accuracy"] == 1.0
    assert result["workflow_node_accuracy"] == 1.0
