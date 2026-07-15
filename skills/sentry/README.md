# Sentry

Sentry integration for Sophon. List projects, browse and inspect error issues and their
individual events, and triage issues (resolve, ignore, reassign) through the Sentry REST API
(v0). Pure Python standard library — no dependencies.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `sentry.list_projects` | none | List all projects in the organization. |
| `sentry.list_issues` | none | List issues for a project, with optional search query and stats period. |
| `sentry.get_issue` | none | Get a single issue by id. |
| `sentry.list_events` | none | List recent events (occurrences) for an issue. |
| `sentry.update_issue` | medium | Update an issue's status and/or reassign it. |

## Connection fields

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `token` | secret | yes | Auth/user token with `event:read` and `project:read` (and `event:write` to update issues). Create one at https://sentry.io/settings/account/api/auth-tokens/ |
| `organization` | text | yes | Your organization slug, e.g. `my-org-slug`. |
| `host` | url | no | Override for self-hosted Sentry. Defaults to `https://sentry.io`. |

The API base URL is built as `{host}/api/0` and every request is authenticated with
`Authorization: Bearer {token}`.

## Trademarks

Sentry is a trademark of Functional Software, Inc. This skill is an independent integration and
is not affiliated with, endorsed by, or sponsored by Sentry.
