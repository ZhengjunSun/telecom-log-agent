from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the deterministic incident workflow")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset), indent=2))


if __name__ == "__main__":
    main()
