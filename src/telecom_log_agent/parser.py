from __future__ import annotations

import re

from .models import LogEvent

LINE = re.compile(
    r"^(?P<ts>\S+)\s+(?P<node>[A-Za-z0-9_-]+)\s+"
    r"(?P<severity>DEBUG|INFO|WARN|ERROR|CRITICAL)\s+(?P<message>.+)$"
)
VARIABLE = re.compile(
    r"(?:\b\d{1,3}(?:\.\d{1,3}){3}\b|\b0x[0-9a-fA-F]+\b|\d+(?:\.\d+)?)"
)


def template_for(message: str) -> str:
    """Approximate Drain-style normalization without external services."""
    return VARIABLE.sub("<*>", message)


def parse_line(line: str) -> LogEvent:
    match = LINE.match(line.strip())
    if not match:
        raise ValueError(f"unsupported log format: {line!r}")
    data = match.groupdict()
    return LogEvent(
        timestamp=data["ts"],
        node=data["node"],
        severity=data["severity"],
        message=data["message"],
        template=template_for(data["message"]),
    )


def parse_logs(text: str) -> list[LogEvent]:
    return [parse_line(line) for line in text.splitlines() if line.strip()]
