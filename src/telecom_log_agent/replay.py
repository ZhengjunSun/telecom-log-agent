from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .workflow import IncidentWorkflow


class ReplayStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._database() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents(
                    incident_id TEXT PRIMARY KEY,
                    raw_logs TEXT NOT NULL,
                    status TEXT NOT NULL,
                    report_json TEXT,
                    decision TEXT,
                    reviewer TEXT,
                    analysis_runs INTEGER NOT NULL DEFAULT 0,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS replay_events(
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _database(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def submit(self, raw_logs: str) -> str:
        incident_id = "REPLAY-" + hashlib.sha256(raw_logs.encode()).hexdigest()[:12].upper()
        now = time.time()
        with self._database() as db:
            inserted = db.execute(
                "INSERT OR IGNORE INTO incidents(incident_id,raw_logs,status,updated_at) "
                "VALUES(?,?,'queued',?)",
                (incident_id, raw_logs, now),
            ).rowcount
            if inserted:
                self._event(db, incident_id, "submitted", {})
        return incident_id

    def get(self, incident_id: str) -> dict[str, Any]:
        with self._database() as db:
            row = db.execute(
                "SELECT * FROM incidents WHERE incident_id=?", (incident_id,)
            ).fetchone()
        if row is None:
            raise KeyError(incident_id)
        result = dict(row)
        result["report"] = json.loads(result.pop("report_json")) if result["report_json"] else None
        return result

    def save_report(self, incident_id: str, report: dict[str, Any]) -> None:
        with self._database() as db:
            db.execute(
                "UPDATE incidents SET report_json=?,status='analyzed',"
                "analysis_runs=analysis_runs+1,updated_at=? WHERE incident_id=?",
                (json.dumps(report), time.time(), incident_id),
            )
            self._event(db, incident_id, "analysis_completed", {})

    def transition(self, incident_id: str, status: str, event: str) -> None:
        with self._database() as db:
            current = db.execute(
                "SELECT status FROM incidents WHERE incident_id=?", (incident_id,)
            ).fetchone()
            if current is None:
                raise KeyError(incident_id)
            if current["status"] == status:
                return
            db.execute(
                "UPDATE incidents SET status=?,updated_at=? WHERE incident_id=?",
                (status, time.time(), incident_id),
            )
            self._event(db, incident_id, event, {})

    def decide(self, incident_id: str, approved: bool, reviewer: str) -> None:
        with self._database() as db:
            row = db.execute(
                "SELECT status,decision FROM incidents WHERE incident_id=?", (incident_id,)
            ).fetchone()
            if row is None:
                raise KeyError(incident_id)
            if row["status"] != "waiting_approval" or row["decision"] is not None:
                raise ValueError("incident is not awaiting a decision")
            decision = "approved" if approved else "rejected"
            db.execute(
                "UPDATE incidents SET decision=?,reviewer=?,status='analyzed',updated_at=? "
                "WHERE incident_id=?",
                (decision, reviewer, time.time(), incident_id),
            )
            self._event(
                db,
                incident_id,
                "approval_decided",
                {"decision": decision, "reviewer": reviewer},
            )

    def record_failure(self, incident_id: str, reason: str) -> None:
        with self._database() as db:
            self._event(db, incident_id, "process_interrupted", {"reason": reason})

    def events(self, incident_id: str) -> list[dict[str, Any]]:
        with self._database() as db:
            rows = db.execute(
                "SELECT event_id,event,payload_json,created_at FROM replay_events "
                "WHERE incident_id=? ORDER BY event_id",
                (incident_id,),
            ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "event": row["event"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _event(
        db: sqlite3.Connection, incident_id: str, event: str, payload: dict[str, Any]
    ) -> None:
        db.execute(
            "INSERT INTO replay_events(incident_id,event,payload_json,created_at) VALUES(?,?,?,?)",
            (incident_id, event, json.dumps(payload), time.time()),
        )


class IncidentReplayRunner:
    def __init__(
        self, store: ReplayStore, workflow: IncidentWorkflow | None = None
    ) -> None:
        self.store = store
        self.workflow = workflow or IncidentWorkflow()

    def run(self, incident_id: str, *, interrupt_after_analysis: bool = False) -> dict[str, Any]:
        state = self.store.get(incident_id)
        if state["status"] in {"completed", "rejected"}:
            return state
        if state["report"] is None:
            report = self.workflow.analyze(state["raw_logs"]).to_dict()
            self.store.save_report(incident_id, report)
            if interrupt_after_analysis:
                self.store.record_failure(incident_id, "injected-after-analysis")
                raise RuntimeError("injected interruption after persisted analysis")
            state = self.store.get(incident_id)
        report = state["report"]
        if report["requires_human_approval"]:
            if state["decision"] is None:
                self.store.transition(incident_id, "waiting_approval", "approval_requested")
            elif state["decision"] == "rejected":
                self.store.transition(incident_id, "rejected", "replay_rejected")
            else:
                self.store.transition(incident_id, "completed", "replay_completed")
        else:
            self.store.transition(incident_id, "completed", "replay_completed")
        return self.store.get(incident_id)
