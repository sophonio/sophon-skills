# Grafana

Interact with Grafana from Sophon: search dashboards, inspect a dashboard's full model, list
data sources and provisioned alert rules, and add annotations to mark events on your graphs.

Implemented with the Grafana HTTP API over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `grafana.search_dashboards` | none | Search dashboards by title (returns uid, folder) |
| `grafana.get_dashboard` | none | Get one dashboard's full model and metadata by uid |
| `grafana.list_datasources` | none | List data sources (id, uid, name, type) |
| `grafana.list_alert_rules` | none | List provisioned Grafana-managed alert rules |
| `grafana.create_annotation` | medium | Add an annotation, optionally on a dashboard/panel |

## Connection

Connect the **Grafana** integration with:

- **Grafana URL** — your instance base URL, e.g. `https://myorg.grafana.net` (or a self-hosted
  host such as `https://grafana.example.com`).
- **Service Account Token** — a [service account token](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
  (`glsa_...`). Grant it only the roles/permissions the tools you use require (Viewer is enough
  for the read tools; annotation write needs Editor).

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is
never written into the skill. Requests are authenticated with `Authorization: Bearer <token>`.

## Notes

- `grafana.create_annotation` writes to your Grafana instance — it is marked medium-risk so Sophon
  can gate it behind approval.
- `grafana.list_alert_rules` returns provisioned Grafana-managed alert rules via the provisioning
  API (`/api/v1/provisioning/alert-rules`).

## Trademarks

Grafana is a trademark of Grafana Labs. This is an unofficial, independently built integration and
is not affiliated with or endorsed by Grafana Labs.
