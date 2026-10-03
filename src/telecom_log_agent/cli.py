from __future__ import annotations

import argparse
import json
from pathlib import Path

from .workflow import IncidentWorkflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze synthetic telecom logs")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    report = IncidentWorkflow().analyze(args.path.read_text(encoding="utf-8"))
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

