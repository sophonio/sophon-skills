# Alertmanager

Manage Prometheus Alertmanager from Sophon: list alerts and silences, inspect cluster status, and
create or expire silences — all through the Alertmanager v2 REST API.

Implemented over the Python standard library (`urllib`, no dependencies), so it runs in the sandbox
unchanged. The `/api/v2` path is appended to your configured server URL automatically.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `alertmanager.list_alerts` | none | List alerts, filterable by active / silenced / inhibited state |
| `alertmanager.list_silences` | none | List all silences (active, pending, expired) |
| `alertmanager.get_status` | none | Get cluster status, version, and config metadata |
| `alertmanager.create_silence` | medium | Create a silence suppressing alerts matching the matchers |
| `alertmanager.expire_silence` | medium | Expire (delete) an existing silence by id |

## Connection

Connect the **Alertmanager** integration with:

- **Server URL** *(required)* — base URL of the Alertmanager server, e.g. `http://alertmanager:9093`.
- **Bearer Token** *(optional)* — sent as `Authorization: Bearer …` for proxied/authenticated setups.
- **Basic Auth Username / Password** *(optional)* — used for HTTP basic auth when no bearer token is
  set. A plain Alertmanager server usually needs no auth at all.

Credentials are stored in Sophon's credential vault and supplied to the skill at call time; they are
never written into the skill.

## Notes

- `list_alerts`, `list_silences`, and `get_status` are read-only (`none` risk).
- `create_silence` requires `matchers` (array of `{name, value, isRegex}`), `startsAt`, `endsAt`,
  `createdBy`, and `comment`; times are RFC3339, e.g. `2026-07-15T00:00:00Z`.
- On an Alertmanager error the tool returns `{"error": "..."}`.

## Trademarks

Prometheus and Alertmanager are trademarks of The Linux Foundation. This is an unofficial,
independently built integration and is not affiliated with or endorsed by the Prometheus project or
the Linux Foundation.
