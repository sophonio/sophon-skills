# ClickHouse Skill

ClickHouse integration for Sophon — run read-only SQL over the native HTTP interface, browse databases and tables, describe schemas, inspect partition-level storage stats, and insert rows as JSONEachRow. Works with ClickHouse Cloud and self-hosted servers using HTTP Basic auth.

Security model: every read tool sends `readonly=1` so the **server itself** rejects any write statement; database/table identifiers are strictly validated (`^[A-Za-z0-9_]+$`); dynamic values are passed via ClickHouse's typed `param_<name>` bindings (`{name:String}` placeholders), never string interpolation.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `clickhouse.query` | Low | Run a read-only SELECT (server-enforced via `readonly=1`), rows capped by limit |
| `clickhouse.list_databases` | None | List database names from `system.databases` |
| `clickhouse.list_tables` | None | List tables with engine, total rows, and total bytes from `system.tables` |
| `clickhouse.describe_table` | None | Describe a table's columns via `DESCRIBE TABLE` |
| `clickhouse.table_stats` | None | Partition-level part/row/byte sums from `system.parts` |
| `clickhouse.insert_rows` | Medium | Insert rows via `INSERT ... FORMAT JSONEachRow` |
| `clickhouse.ping` | None | Connectivity check — returns the server version |

`clickhouse.query` appends `LIMIT <limit>` (default 100, max 1000) when the statement has no explicit `LIMIT`; returned rows are always truncated client-side to the limit. If the only `LIMIT` sits inside a subquery, the outer query runs uncapped on the server — add an outer `LIMIT` on huge tables to avoid timeouts.

## Setup

1. Find your HTTP(S) interface URL:
   - **ClickHouse Cloud**: `https://<your-instance>.clickhouse.cloud:8443`
   - **Self-hosted**: `http://<host>:8123` by default, or `https://<host>:8443` if TLS is configured. Prefer HTTPS — credentials are sent with HTTP Basic auth.
2. Create a dedicated database user. A plain SELECT-only user is strongly recommended:

   ```sql
   CREATE USER sophon IDENTIFIED BY '<strong password>';
   GRANT SELECT ON *.* TO sophon;
   ```

   Notes:
   - Read tools always send `readonly=1` explicitly, so writes are rejected server-side regardless of the user's grants.
   - Avoid assigning a settings profile that forces `readonly = 1`: because the read tools pass `readonly=1` themselves, older ClickHouse releases treat that as a settings change in readonly mode and reject **every** read with `Code: 164 (Cannot modify 'readonly' setting in readonly mode)`. If you must use such a profile, the admin needs to mark the `readonly` setting `changeable_in_readonly` in the profile's constraints.
   - `clickhouse.insert_rows` needs a user with `INSERT` granted on the target tables and **without** a forced readonly profile — if you only need read access, skip that grant and the tool will simply fail server-side.
   - The listing tools read `system.databases`, `system.tables`, and `system.parts`; the user only sees objects it has access to.
3. (Optional) Pick a default database for the connection; tools accepting a `database` parameter can override it per call.
4. In Sophon, go to **Settings > Connections**, click **Connect** on the ClickHouse card, enter the server URL, username, password, and optional default database, then test the connection.

## Usage Examples

**Explore what's there:**
> "List the databases on ClickHouse, then show me the tables in `web` with their sizes"

**Query data:**
> "Query ClickHouse: top 10 pages by hits from web.pageviews in the last 7 days"

**Inspect a schema:**
> "Describe the columns of the web.events table and show its partition stats"

**Insert rows:**
> "Insert these two rows into web.events: ..."

## Requirements

- A ClickHouse server (ClickHouse Cloud, any tier, or self-hosted v21+) with the HTTP interface enabled and reachable from Sophon (default ports 8443/8123)
- A database user; plain SELECT-only grants recommended — see the readonly-profile caveat under Setup (INSERT grant only if you use `clickhouse.insert_rows`)
- Typed query parameters (`{name:String}`) require a modern ClickHouse version (v21+)

## Trademarks

ClickHouse is a trademark of ClickHouse, Inc. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by ClickHouse, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
