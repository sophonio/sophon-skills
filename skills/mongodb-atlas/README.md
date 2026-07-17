# MongoDB Atlas Skill

MongoDB Atlas control-plane integration for Sophon — inspect projects, clusters, alerts, metrics, events, and database users through the Atlas Administration API v2 using a service account. Control-plane/ops only: the Atlas Data API (document CRUD) reached end-of-life in September 2025, so this skill has no collection-data tools.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `atlas.list_projects` | None | List Atlas projects (groups) with id, name, cluster count, created |
| `atlas.list_clusters` | None | List clusters in a project (state, version, instance size, paused) |
| `atlas.get_cluster` | None | Get one cluster's configuration and SRV connection string |
| `atlas.list_alerts` | None | List OPEN alerts for a project |
| `atlas.acknowledge_alert` | Low | Acknowledge an alert until a date-time, with optional comment |
| `atlas.get_process_metrics` | None | Get CPU, connections, and opcounter time series for a process |
| `atlas.list_events` | None | List recent project activity events with the acting user/API key |
| `atlas.list_database_users` | None | List database users (username, roles, auth database — no secrets) |

## Setup

1. In MongoDB Atlas, have an **Organization Owner** open **Organization Settings > Service Accounts** and create a new service account for Sophon.
2. Assign read-mostly organization access: the **Organization Read Only** role is enough for listing projects.
3. Grant the service account access to the project(s) you want to operate on, with **Project Read Only** plus **Project Alert Acknowledger** (needed only for `atlas.acknowledge_alert`).
4. Copy the **Client ID** and **Client Secret** — the secret is shown only once at creation.
5. **IP access list caveat:** organizations default to *"Require IP Access List for the Atlas Administration API"*. Either add Sophon's egress IP addresses to the service account's API access list, or relax that organization setting. Otherwise every call fails with a 403 `IP_ADDRESS_NOT_ON_ACCESS_LIST` error (the skill surfaces this with a hint when it happens).
6. In Sophon, open **Settings > Connections**, click **Connect** on the MongoDB Atlas card, enter the Client ID and Client Secret, optionally set a default Project (group) ID, and test the connection.

The skill authenticates with the OAuth2 client-credentials grant (`POST https://cloud.mongodb.com/api/oauth/token`); tokens live about one hour and are minted fresh on each invocation.

## Usage Examples

> "List my Atlas projects and how many clusters each one has"

> "Show the clusters in my Atlas project — are any paused or upgrading?"

> "Get the connection string and instance size for cluster Cluster0"

> "Any open Atlas alerts? Acknowledge the disk space one until tomorrow with a note that we're scaling up"

> "Pull the last hour of CPU and connection metrics for cluster0-shard-00-00.ab1cd.mongodb.net:27017"

## Requirements

- A MongoDB Atlas organization with Service Accounts (creating one requires the Organization Owner role)
- Service account roles: Organization Read Only (or Project Read Only per project), plus Project Alert Acknowledger for acknowledging alerts
- Sophon's egress IPs on the service account's API access list (or the org-level API IP access list requirement disabled)
- Control-plane operations only — no document reads/writes (the Atlas Data API was retired in September 2025)

## Trademarks

MongoDB and MongoDB Atlas are trademarks of MongoDB, Inc. This project is not affiliated with or endorsed by MongoDB, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
