# Snowflake Skill

Snowflake data warehouse integration for Sophon — run SQL through the Snowflake SQL API and browse databases, schemas, tables, and warehouses through the REST catalog, authenticated with a Programmatic Access Token (PAT).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `snowflake.query` | High | Execute an arbitrary SQL statement on the configured warehouse |
| `snowflake.get_statement` | None | Poll a statement by handle and fetch its stitched results |
| `snowflake.cancel_statement` | Low | Cancel a running statement |
| `snowflake.list_databases` | None | List visible databases |
| `snowflake.list_schemas` | None | List schemas in a database |
| `snowflake.list_tables` | None | List tables in a schema with row counts and sizes |
| `snowflake.describe_table` | None | Get a table's columns, datatypes, and comments |
| `snowflake.list_warehouses` | None | List virtual warehouses with state and size |

## Setup

1. Make sure your Snowflake user meets the PAT prerequisites: the user must be subject to a **network policy**, and if an **authentication policy** applies to the user it must allowlist `PROGRAMMATIC_ACCESS_TOKEN` as an authentication method. Your account admin may need to set these up first.
2. Generate a Programmatic Access Token, either:
   - in **Snowsight**: open your user menu > **Settings** > **Authentication** > **Programmatic access tokens** > **Generate new token**, or
   - in SQL: `ALTER USER my_user ADD PROGRAMMATIC ACCESS TOKEN my_token ROLE_RESTRICTION = 'ANALYST_ROLE';`
3. We recommend setting a `ROLE_RESTRICTION` so the token can only act as a single, least-privileged role. Note the expiry: tokens default to 15 days and can be issued for at most 365 days — plan to rotate the token before it expires.
4. Copy the token secret when it is shown — Snowflake displays it only once.
5. In Sophon, open **Settings > Connections**, click **Connect** on the Snowflake card, and fill in:
   - **Account URL** — e.g. `https://myorg-myaccount.snowflakecomputing.com`
   - **Programmatic Access Token** — the token secret from step 4
   - **Warehouse** — the virtual warehouse to run statements on (e.g. `COMPUTE_WH`)
   - **Role** (optional) — must match the token's role restriction if one is set
6. Test the connection.

## Usage Examples

> "Run this on Snowflake: SELECT COUNT(*) FROM SALES.PUBLIC.ORDERS WHERE created_at > CURRENT_DATE - 7"

> "List the databases in our Snowflake account, then show me the schemas in ANALYTICS"

> "Describe the table ANALYTICS.MARTS.FCT_REVENUE — what columns does it have?"

> "Check whether statement 01b2c3d4-0000-1234-0000-000000000000 has finished and show the results"

> "Which Snowflake warehouses do we have and which ones are running?"

## Requirements

- A Snowflake account reachable at `https://<account>.snowflakecomputing.com` with the SQL API enabled (available on all editions)
- A user that satisfies the PAT prerequisites above (network policy required; authentication policy, if any, must allow `PROGRAMMATIC_ACCESS_TOKEN`)
- A role with `USAGE` on the configured warehouse and appropriate privileges on the databases/schemas/tables you want to query
- Identifier caveat: Snowflake identifiers created with double quotes are **case-sensitive** — pass database, schema, and table names exactly as stored (unquoted identifiers are stored uppercase)
- Results are capped at 1000 rows per call; the response's `truncated` flag tells you when more rows exist
- Long-running queries: pass a `timeout` above 20 seconds to `snowflake.query` to submit the statement asynchronously — it returns a statement handle immediately, which you poll with `snowflake.get_statement` (timeout max 3600 seconds)

## Trademarks

Snowflake is a trademark of Snowflake Inc. This project is not affiliated with or endorsed by Snowflake Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
