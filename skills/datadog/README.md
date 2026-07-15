# Datadog

Datadog integration for Sophon. Query metric timeseries and list, inspect, mute, and unmute
monitors through the Datadog REST API (v1). Pure Python standard library — no dependencies.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `datadog.query_metrics` | none | Query a metrics timeseries over a Unix-timestamp range. |
| `datadog.list_monitors` | none | List monitors, optionally filtered by name and tags. |
| `datadog.get_monitor` | none | Get a single monitor by id. |
| `datadog.mute_monitor` | medium | Mute a monitor (suppresses alert notifications), optionally until a time. |
| `datadog.unmute_monitor` | medium | Unmute a monitor to resume alert notifications. |

## Connection fields

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `apiKey` | secret | yes | Datadog API key. |
| `appKey` | secret | yes | Datadog Application key. |
| `site` | text | no | Your Datadog site, e.g. `datadoghq.com`, `datadoghq.eu`, `us5.datadoghq.com`. Defaults to `datadoghq.com`. |

The API base URL is built as `https://api.{site}` and every request is authenticated with the
`DD-API-KEY` and `DD-APPLICATION-KEY` headers. Create keys at
https://docs.datadoghq.com/account_management/api-app-keys/

## Trademarks

Datadog is a trademark of Datadog, Inc. This skill is an independent integration and is not
affiliated with, endorsed by, or sponsored by Datadog.
