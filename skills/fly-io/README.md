# Fly.io

Manage [Fly.io](https://fly.io) Machines for an app through the [Fly Machines REST API](https://fly.io/docs/machines/api/), using an app-scoped API token. Pure Python standard library — no dependencies.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `fly.list_machines` | none | List the machines for an app, with state, region, and image. |
| `fly.get_machine` | none | Get a single machine by id. |
| `fly.start_machine` | medium | Start a stopped machine. |
| `fly.stop_machine` | medium | Stop a running machine. |
| `fly.restart_machine` | medium | Restart a machine. |
| `fly.destroy_machine` | high | Permanently destroy a machine. Not reversible. Accepts `force` to destroy while running. |

Every tool accepts an `appName` argument and falls back to the app configured on the connection. If neither is set, the call returns `{"error": "appName required (pass it or configure it on the connection)"}`.

Machine responses are trimmed to `id`, `name`, `state`, `region`, and `image`.

## Connection

Authenticate with a Fly API token (Bearer auth).

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `token` | secret | yes | A Fly API token — run `fly tokens create`. An app-scoped deploy token is recommended. |
| `appName` | text | yes | The Fly app these machines belong to, e.g. `my-app`. |

Requests go to `https://api.machines.dev/v1` with `Authorization: Bearer <token>`.

## Limitations

Image-building deploys are **not** supported. Building a machine from source needs a remote builder, which is outside the scope of this stdlib-only skill. Provision machines from a prebuilt image with the Fly CLI or the raw API, then manage their lifecycle (start / stop / restart / destroy) here.

## Trademarks

Fly.io is a trademark of Fly.io, Inc. This skill is an independent integration and is not affiliated with, endorsed by, or sponsored by Fly.io, Inc.
