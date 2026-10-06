import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

module_path = Path(__file__).parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("incident_responder_app", module_path)
responder = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(responder)


def test_test_alert_saves_evidence_and_response(tmp_path, monkeypatch):
    monkeypatch.setattr(responder, "INCIDENT_DIR", tmp_path)
    with TestClient(responder.app) as client:
        result = client.post(
            "/alerts",
            json={
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "ResponderTest", "test": "true"},
                        "annotations": {"summary": "Test notification; no incident to fix"},
                    }
                ]
            },
        )
    assert result.status_code == 202
    body = result.json()
    assert json.loads((tmp_path / body["evidence"]).read_text())["alerts"][0]["status"] == "firing"
    answer = (tmp_path / body["response"]).read_text()
    assert answer.rstrip().endswith("No incident to fix; no source changes were made.")
