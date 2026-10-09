import tempfile
from pathlib import Path

import pytest

from telecom_log_agent.replay import IncidentReplayRunner, ReplayStore

P1_LOGS = (
    "2026-01-01T00:00:01Z AMF-01 CRITICAL heartbeat timeout peer=10.0.0.1\n"
    "2026-01-01T00:00:02Z AMF-01 CRITICAL heartbeat timeout peer=10.0.0.1"
)


def test_persisted_analysis_recovers_without_running_twice() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "replay.db"
        store = ReplayStore(path)
        incident_id = store.submit(P1_LOGS)
        runner = IncidentReplayRunner(store)
        with pytest.raises(RuntimeError, match="injected interruption"):
            runner.run(incident_id, interrupt_after_analysis=True)

        restarted_store = ReplayStore(path)
        restarted = IncidentReplayRunner(restarted_store)
        waiting = restarted.run(incident_id)
        assert waiting["status"] == "waiting_approval"
        assert waiting["analysis_runs"] == 1

        restarted_store.decide(incident_id, True, "operator@example.test")
        completed = restarted.run(incident_id)
        assert completed["status"] == "completed"
        assert completed["analysis_runs"] == 1
        assert [event["event"] for event in restarted_store.events(incident_id)] == [
            "submitted",
            "analysis_completed",
            "process_interrupted",
            "approval_requested",
            "approval_decided",
            "replay_completed",
        ]


def test_rejection_is_terminal() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ReplayStore(Path(directory) / "replay.db")
        incident_id = store.submit(P1_LOGS)
        runner = IncidentReplayRunner(store)
        assert runner.run(incident_id)["status"] == "waiting_approval"
        store.decide(incident_id, False, "operator@example.test")
        assert runner.run(incident_id)["status"] == "rejected"
        assert runner.run(incident_id)["status"] == "rejected"
