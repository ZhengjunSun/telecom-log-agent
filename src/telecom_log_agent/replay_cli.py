from __future__ import annotations

import argparse
import json
from pathlib import Path

from .replay import IncidentReplayRunner, ReplayStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist and resume incident replays")
    parser.add_argument("--db", type=Path, default=Path("telecom-replay.db"))
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("path", type=Path)
    resume = commands.add_parser("resume")
    resume.add_argument("incident_id")
    decide = commands.add_parser("decide")
    decide.add_argument("incident_id")
    decide.add_argument("decision", choices=("approve", "reject"))
    decide.add_argument("--reviewer", required=True)
    events = commands.add_parser("events")
    events.add_argument("incident_id")
    args = parser.parse_args()

    store = ReplayStore(args.db)
    runner = IncidentReplayRunner(store)
    if args.command == "start":
        incident_id = store.submit(args.path.read_text(encoding="utf-8"))
        result = runner.run(incident_id)
    elif args.command == "resume":
        result = runner.run(args.incident_id)
    elif args.command == "decide":
        store.decide(args.incident_id, args.decision == "approve", args.reviewer)
        result = runner.run(args.incident_id)
    else:
        result = store.events(args.incident_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
