# Grafana Loki

Query Grafana Loki logs with LogQL over the Loki HTTP API. Pure Python standard library (urllib) — no
third-party dependencies. Supports plain Loki, token/basic-auth proxied setups (e.g. Grafana Cloud),
and multi-tenant Loki via `X-Scope-OrgID`.

## Tools

| Name | Risk | Description |
|------|------|-------------|
| `loki.query` | none | Run an instant LogQL query and return matching streams or metric values. |
| `loki.query_range` | none | Run a LogQL query over a time range. |
| `loki.list_labels` | none | List all label names (optionally within a time range). |
| `loki.label_values` | none | List all values for a given label name (optionally within a time range). |

### `loki.query`
- `query` (required) — LogQL expression, e.g. `{app="api"} |= "error"`
- `limit` — max entries to return (default 100)
- `time` — optional evaluation timestamp (RFC3339 or Unix nanoseconds)

### `loki.query_range`
- `query` (required) — LogQL expression
- `start`, `end` (required) — range bounds (RFC3339 or Unix nanoseconds)
- `limit` — max entries to return (default 100)
- `step` — resolution step for metric queries (e.g. `15s`, `1m`)
- `direction` — `forward` or `backward` (default `backward`)

### `loki.list_labels`
- `start`, `end` — optional range bounds

### `loki.label_values`
- `label` (required) — label name, e.g. `app`, `namespace`, `job`
- `start`, `end` — optional range bounds

## Connection / Auth

Configure the Loki connection with these fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `host` | url | yes | Base URL, e.g. `http://loki:3100`. The `/loki/api/v1` paths are appended automatically. |
| `token` | secret | no | Bearer token for proxied/authenticated setups. |
| `username` | text | no | Basic auth username (used only when no bearer token is set). |
| `password` | secret | no | Basic auth password. |
| `orgId` | text | no | `X-Scope-OrgID` tenant header for multi-tenant Loki. |

Loki wraps responses as `{"status": "success", "data": {...}}`; a non-success status is returned as
`{"error": ...}`.

## Trademarks

Grafana and Loki are trademarks of Grafana Labs. This skill is an independent integration and is not
affiliated with or endorsed by Grafana Labs.
