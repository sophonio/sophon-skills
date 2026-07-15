# Prometheus

Query a Prometheus server from Sophon: run instant and range PromQL queries, list active alerts and
scrape targets, and enumerate label values — all through the Prometheus HTTP API.

Implemented over the Python standard library (`urllib`, no dependencies), so it runs in the sandbox
unchanged. The `/api/v1` path is appended to your configured server URL automatically.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `prometheus.query` | none | Run an instant PromQL query at a single point in time |
| `prometheus.query_range` | none | Run a PromQL query over a time range at a fixed step |
| `prometheus.list_alerts` | none | List currently active alerts |
| `prometheus.list_targets` | none | List active scrape targets and their health |
| `prometheus.label_values` | none | List all values for a given label name |

## Connection

Connect the **Prometheus** integration with:

- **Server URL** *(required)* — base URL of the Prometheus server, e.g. `http://prometheus:9090`.
- **Bearer Token** *(optional)* — sent as `Authorization: Bearer …` for proxied/authenticated
  setups such as Grafana Cloud.
- **Basic Auth Username / Password** *(optional)* — used for HTTP basic auth when no bearer token is
  set. A plain Prometheus server usually needs no auth at all.

Credentials are stored in Sophon's credential vault and supplied to the skill at call time; they are
never written into the skill.

## Notes

- All tools are read-only (`none` risk) — this skill never modifies the server.
- Responses return the raw Prometheus `data` payload (result type + result) for queries, and
  trimmed summaries for alerts and targets.
- On a Prometheus error (bad PromQL, unknown label) the tool returns `{"error": "..."}`.

## Trademarks

Prometheus is a trademark of The Linux Foundation. This is an unofficial, independently built
integration and is not affiliated with or endorsed by the Prometheus project or the Linux Foundation.
