# Vercel

Read-only access to the [Vercel](https://vercel.com) REST API: inspect deployments, projects, and
environment-variable metadata. Pure Python standard library — no third-party dependencies.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `vercel.list_deployments` | none | List recent deployments, optionally filtered by `projectId` and `state`. |
| `vercel.get_deployment` | none | Get a single deployment by id or URL. |
| `vercel.list_projects` | none | List projects in the current scope. |
| `vercel.get_project` | none | Get a single project by id or name. |
| `vercel.list_env` | none | List a project's environment variable keys and targets (never the decrypted values). |

## Connection

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `token` | secret | yes | A Vercel access token with read access. Create one at https://vercel.com/account/tokens |
| `teamId` | text | no | Team id for team-scoped resources. Leave blank to use your personal scope. |

When `teamId` is set it is merged into the query string of every request. Authentication uses the
`Authorization: Bearer <token>` header against `https://api.vercel.com`.

## Security

`vercel.list_env` returns only environment variable **keys** and their **targets** — it never
returns decrypted secret values.

## Trademarks

Vercel is a trademark of Vercel, Inc. This skill is an independent integration and is not affiliated
with or endorsed by Vercel, Inc.
