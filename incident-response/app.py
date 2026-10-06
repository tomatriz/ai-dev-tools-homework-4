import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel


INCIDENT_DIR = Path(os.getenv("INCIDENT_DIR", "incidents"))
AGENT_COMMAND = os.getenv("INCIDENT_AGENT_COMMAND", "").strip()
app = FastAPI(title="Order Tracker Incident Responder")


class AlertPayload(BaseModel):
    alerts: list[dict] = []
    status: str | None = None


def _safe_slug(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in value)[:80]


def _write_incident(payload: dict) -> tuple[Path, Path]:
    INCIDENT_DIR.mkdir(parents=True, exist_ok=True)
    alert = (payload.get("alerts") or [{}])[0]
    labels = alert.get("labels") or {}
    name = _safe_slug(labels.get("alertname", "unknown-alert"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = INCIDENT_DIR / f"{stamp}-{name}.json"
    response = INCIDENT_DIR / f"{stamp}-{name}.md"
    evidence.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return evidence, response


def _prompt_for(payload: dict, evidence: Path) -> str:
    alert = (payload.get("alerts") or [{}])[0]
    labels = alert.get("labels") or {}
    annotations = alert.get("annotations") or {}
    return (
        "Investigate the Order Tracker alert using read-only evidence first. "
        "Run focused tests, make the smallest safe source fix only when the failure is reproducible, "
        "and never modify credentials, infrastructure permissions, or incident evidence. "
        f"Alert labels: {json.dumps(labels, sort_keys=True)}. "
        f"Annotations: {json.dumps(annotations, sort_keys=True)}. "
        f"Evidence: {evidence}. End with a one-line outcome."
    )


def run_responder(payload: dict, evidence: Path, response: Path) -> None:
    alert = (payload.get("alerts") or [{}])[0]
    labels = alert.get("labels") or {}
    if str(labels.get("test", "")).lower() == "true":
        response.write_text(
            "Test alert received and evidence saved. No production symptoms were present.\n\n"
            "No incident to fix; no source changes were made.\n",
            encoding="utf-8",
        )
        return

    if not AGENT_COMMAND:
        response.write_text(
            "Alert evidence was captured, but INCIDENT_AGENT_COMMAND is not configured.\n\n"
            "Escalated to the on-call engineer without changing source code.\n",
            encoding="utf-8",
        )
        return

    prompt = _prompt_for(payload, evidence)
    command = shlex.split(AGENT_COMMAND) + [prompt]
    try:
        completed = subprocess.run(
            command,
            cwd="/workspace",
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        output = (completed.stdout + "\n" + completed.stderr).strip()
        response.write_text(output + "\n", encoding="utf-8")
    except (OSError, subprocess.TimeoutExpired) as exc:
        response.write_text(
            f"Responder failed safely: {exc}\n\nEscalated to the on-call engineer.\n",
            encoding="utf-8",
        )


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/alerts", status_code=202)
def receive_alert(payload: AlertPayload, background_tasks: BackgroundTasks):
    data = payload.model_dump()
    evidence, response = _write_incident(data)
    background_tasks.add_task(run_responder, data, evidence, response)
    return {
        "status": "accepted",
        "evidence": evidence.name,
        "response": response.name,
    }
