# Databricks Skill

Databricks workspace integration for Sophon — run SQL on a SQL warehouse, browse Unity Catalog, and list and trigger Lakeflow Jobs via the Databricks REST API.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `databricks.execute_sql` | High | Execute an arbitrary SQL statement on the configured SQL warehouse |
| `databricks.get_statement` | None | Get the status and results of a submitted SQL statement |
| `databricks.cancel_statement` | Low | Cancel a running SQL statement |
| `databricks.list_warehouses` | None | List SQL warehouses (id, name, state, size) |
| `databricks.list_tables` | None | Browse Unity Catalog: catalogs, schemas, or tables with columns |
| `databricks.list_jobs` | None | List jobs (job_id, name, creator) |
| `databricks.list_job_runs` | None | List recent job runs with state and duration |
| `databricks.run_job` | High | Trigger a job to run now |

## Setup

1. Sign in to your Databricks workspace and note its URL (e.g. `https://adb-123.4.azuredatabricks.net` on Azure or `https://xyz.cloud.databricks.com` on AWS/GCP).
2. Create a Personal Access Token: click your profile avatar > **Settings > Developer > Access tokens > Generate new token**. Copy the token immediately — it is shown only once.
   - PATs are self-serve, but tokens are automatically revoked after 90 days of inactivity, so long-idle connections may need a new token.
   - Workspace admins can disable personal access token authentication entirely. If PATs are disabled in your workspace, ask an admin to enable them for your user, or use machine-to-machine OAuth (a service principal exchanging its client ID/secret at `/oidc/v1/token` for a short-lived access token) — this skill does not implement the OAuth flow itself.
3. Find your SQL Warehouse ID: **SQL Warehouses >** select a warehouse **> Connection details** — the ID is the last path segment of the HTTP path (and shown as "ID").
4. In Sophon, open **Settings > Connections**, click **Connect** on the Databricks card, and fill in the Workspace URL, Personal Access Token, and SQL Warehouse ID, then test the connection.

## Usage Examples

> "Run this SQL on Databricks: SELECT country, count(*) FROM main.sales.orders GROUP BY country"

> "What tables are in the main catalog's analytics schema, and what columns do they have?"

> "List my Databricks SQL warehouses and tell me which ones are running."

> "Show the last runs of the nightly-etl job — did any fail?"

> "Trigger job 429 on Databricks now."

## Requirements

- A Databricks workspace on AWS, Azure, or GCP with at least one SQL warehouse (SQL statement execution requires a SQL warehouse, not an all-purpose cluster).
- A Personal Access Token for a user (or service principal) with **CAN USE** permission on the SQL warehouse, `USE CATALOG`/`USE SCHEMA`/`SELECT` privileges on the data being queried, and view/run permissions on any jobs you list or trigger.
- `databricks.list_tables` requires Unity Catalog to be enabled on the workspace.
- Inline SQL results are capped at 1000 rows; truncated results include a note, and `databricks.get_statement` can fetch remaining result chunks up to the row cap. Statements whose inline result exceeds the Databricks 25 MiB inline limit fail outright (they are not truncated) — narrow the query or add a LIMIT clause.

## Trademarks

Databricks is a trademark of Databricks, Inc. This project is not affiliated with or endorsed by Databricks, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
