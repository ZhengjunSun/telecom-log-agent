from telecom_log_agent.parser import parse_line, template_for
from telecom_log_agent.workflow import IncidentWorkflow

SAMPLE = """2026-01-01T00:00:01Z AMF-01 ERROR heartbeat timeout peer=10.0.0.1 elapsed=3000ms
2026-01-01T00:00:02Z AMF-01 CRITICAL heartbeat timeout peer=10.0.0.1 elapsed=6000ms
2026-01-01T00:00:03Z SMF-02 ERROR session update failed code=504"""


def test_template_normalizes_variables() -> None:
    assert template_for("peer 10.0.0.1 waited 3000ms") == "peer <*> waited <*>ms"


def test_parse_line() -> None:
    event = parse_line("2026-01-01T00:00:00Z N1 INFO ready")
    assert event.node == "N1"
    assert event.template == "ready"


def test_workflow_is_auditable_and_requires_approval() -> None:
    report = IncidentWorkflow().analyze(SAMPLE)
    assert report.severity == "P2"
    assert report.requires_human_approval is True
    assert report.metadata["data_classification"] == "synthetic-demo"
    assert {f.agent for f in report.findings} == {
        "pattern-agent",
        "topology-agent",
        "knowledge-agent",
        "critic-agent",
    }
