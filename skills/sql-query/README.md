# SQL Database

Query relational databases from Sophon: list tables, inspect a table's columns, and run arbitrary
SQL — reads or writes — against **PostgreSQL**, **MySQL/MariaDB**, or **SQLite**.

Implemented with pure-Python drivers ([pg8000](https://github.com/tlocke/pg8000),
[PyMySQL](https://github.com/PyMySQL/PyMySQL)) and the standard-library `sqlite3` module, so it
installs as wheels/pure-python and runs in the alpine sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `sql.list_tables` | none | List the tables in the connected database |
| `sql.describe_table` | none | Describe a table's columns and their types |
| `sql.run_query` | high | Execute arbitrary SQL (SELECT returns rows; other statements are committed) |

`sql.run_query` returns `{columns, rows, rowCount, truncated}` for statements that produce a result
set (rows capped to `min(limit or 500, 1000)`), and `{rowsAffected}` for INSERT/UPDATE/DELETE/DDL.

## Connection

Connect the **SQL Database** integration with:

- **Database Type** — one of `postgres`, `mysql` (also MariaDB), or `sqlite`.
- **Host** *(optional)* — server hostname or IP; defaults to `localhost`. Leave blank for SQLite.
- **Port** *(optional)* — defaults to `5432` for postgres and `3306` for mysql.
- **Database (or SQLite file path)** — the database name for postgres/mysql, or the file path for
  sqlite (resolved against the sandbox working directory `/workspace`).
- **Username** / **Password** — required for postgres/mysql; ignored for sqlite. The password is
  stored in Sophon's credential vault and supplied at call time.

## Notes

- `sql.run_query` is marked **high-risk** because it can run any statement the connection permits,
  including `UPDATE`, `DELETE`, `DROP`, and other irreversible changes — Sophon can gate it behind
  approval. Non-result statements are committed automatically.
- `sql.describe_table` restricts the table identifier to `[A-Za-z0-9_.]` to guard against SQL
  injection; on postgres the name is additionally passed as a bound parameter.

## Trademarks

PostgreSQL, MySQL, MariaDB, and SQLite are trademarks of their respective owners. This is an
unofficial, independently built integration and is not affiliated with or endorsed by them.
