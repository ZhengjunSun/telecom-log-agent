from __future__ import annotations

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install the API extra: pip install -e '.[api]'") from exc

from .workflow import IncidentWorkflow

app = FastAPI(title="Telecom Log Agent", version="0.1.0")
workflow = IncidentWorkflow()


class AnalyzeRequest(BaseModel):
    logs: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    return workflow.analyze(request.logs).to_dict()

