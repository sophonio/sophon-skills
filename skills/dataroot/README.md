# Dataroot Skill

Dataroot integration for Sophon — discover the organizations you belong to, their connections and data sources, inspect a data source's schema/table/column metadata, list organization members, and check the signed-in account, via the Dataroot REST API. Dataroot is a Buildersoft LLC product (the same maker as Sophon).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `dataroot.list_organizations` | None | List the organizations the account belongs to (id and name) |
| `dataroot.list_connections` | None | List an organization's connections, with status and data-source count |
| `dataroot.list_data_sources` | None | List an organization's data sources (all connections, or one) — no secrets |
| `dataroot.get_data_source` | None | Get one data source's details and settings (secret values masked) |
| `dataroot.get_data_source_metadata` | None | Get a data source's schema/table/column metadata (summarized, capped) |
| `dataroot.list_members` | None | List an organization's members |
| `dataroot.whoami` | None | Return the signed-in account's profile and monthly quota |

Every tool that targets an organization accepts the **organization name or id** (e.g. `"Acme"` or the org's uuid) and resolves it automatically.

## Setup

1. Make sure you have a **Dataroot account** that is a member of at least one organization.
2. Find your **Dataroot API base URL** — for example `https://api.dev.dataroot.at` (no trailing slash). This is the environment your account lives in.
3. In Sophon, open **Settings > Connections**, click **Connect** on the Dataroot card, and enter:
   - **Base URL** — your Dataroot API base URL
   - **Email Address** — your Dataroot login email
   - **Password** — your Dataroot login password
4. Test the connection.

The skill logs in with your email and password to obtain a short-lived access token for each call; the password is never stored by the skill. Every organization-scoped call sends the resolved organization id in the required `X-Organization-Id` header.

## Usage Examples

> "Show me all data sources of the Acme organization"

> "List the connections in Acme and how many data sources each has"

> "What tables and columns are in data source `<id>`?"

> "Get the details of data source `<id>` in connection `<id>`"

> "Who are the members of the Beta organization?"

> "Which Dataroot organizations can I access, and who am I signed in as?"

## Requirements

- A Dataroot account with membership in one or more organizations; what you can see is determined by that account's access.
- The correct Dataroot **Base URL** for your environment.
- Secret data-source settings (database passwords, S3/GCS/Azure/AWS access keys, credential JSON, OAuth secrets, trust-store passwords) are **masked** (`***`) in `get_data_source` output; structural fields (host, port, database, username, schema, warehouse, role, region) remain visible.
- `list_data_sources` aggregates across an organization's connections and caps how many connections it scans (reporting `truncated: true` when it stops early); pass a `connectionId` to target a single connection.
- This version is **read-only**. Natural-language querying, dashboards, and direct SQL execution are not included.

## Trademarks

Dataroot is a product and trademark of Buildersoft LLC.

## License

Copyright © 2026 Buildersoft LLC. **All rights reserved.** This skill is a proprietary Buildersoft LLC product — it is **free to use** but is **not** open-source and is **not** licensed under the MIT License. See [LICENSE](LICENSE) for the full terms.
