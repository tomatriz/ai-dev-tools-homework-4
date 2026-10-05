# Order Tracker — AI Dev Tools Zoomcamp Homework 4

This solution adds end-to-end observability and bounded automatic incident response to the course starter app.

## Run

Requirements: Docker with Compose. Python 3.11+ and `uv` are needed for local tests.

```bash
docker compose up --build -d --wait
curl http://localhost:8000/healthz
```

Open the app at <http://localhost:8000> and Grafana at <http://localhost:3000>. Grafana is preconfigured with Prometheus, Loki, Tempo, the **Order Tracker** dashboard, a 5xx alert, and a webhook contact point for the responder.

Run tests:

```bash
uv sync
uv run pytest -q
```

## Homework flow and answers

1. `GET /healthz` returns `{'status':'ok'}`.
2. `GET /api/orders/standard-1001` records HTTP status **200**.
3. `GET /api/orders/standard-1002` is missing and records HTTP status **404** in Grafana.
4. Because no 5xx response occurs for the missing standard order, the 5xx alert is **Normal** (`noDataState: OK`).
5. The test webhook saves evidence and ends with: **No incident to fix; no source changes were made.**
6. The original express-delivery calculation tried to use a day that does not exist in that month. The fixed calculation uses `timedelta(days=2)`.

## Telemetry

`GET /api/orders/{order_id}` emits a span, structured log, and `http.server.requests` metric with `http.route`, `http.request.method`, and `http.response.status_code`. Signals flow through the OpenTelemetry Collector to Prometheus, Loki, and Tempo. The Grafana dashboard displays request counts by route/status and recent 5xx responses.

## Incident responder

Grafana sends alert webhooks to `POST /alerts` on port 8001. The service persists the complete alert payload and a Markdown response in `incidents/`. Test notifications are handled without changing code. Real alerts invoke the headless command in `INCIDENT_AGENT_COMMAND`; if it is unset or fails, the responder escalates safely.

Example headless command (adapt it to the coding agent installed on the Docker host):

```bash
INCIDENT_AGENT_COMMAND="codex exec --sandbox workspace-write --skip-git-repo-check" docker compose up --build -d --wait
```

The agent prompt requires evidence-first investigation, focused tests, the smallest source fix, and a one-line outcome. It explicitly forbids changes to credentials, infrastructure permissions, and incident evidence.

## Useful checks

```bash
curl -i http://localhost:8000/api/orders/standard-1001
curl -i http://localhost:8000/api/orders/standard-1002
curl -X POST http://localhost:8001/alerts -H "Content-Type: application/json" -d '{"alerts":[{"status":"firing","labels":{"alertname":"ResponderTest","test":"true"},"annotations":{"summary":"Test notification; no incident to fix"}}]}'
curl -i http://localhost:8000/api/orders/express-1002
```
