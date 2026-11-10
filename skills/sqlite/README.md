# SQLite database skill

Connect an uploaded SQLite file to Sophon, inspect its schema, and answer questions using SQLite SQL.
The Sophon agent chooses the connection, reads table metadata, writes a query, and explains the
returned rows. The skill itself does not call a language model or sample rows automatically.

## Tools

`sqlite.ping` tests connectivity; `sqlite.list_tables` and `sqlite.describe_table` expose
catalog metadata; `sqlite.query` runs a single SELECT with the read-only identity; and
`sqlite.execute` runs a single statement with the optional write identity and is high risk.

Every tool takes `connectionId` from `db.list_connections`. Queries return columns, rows,
`rowCount`, `truncated`, and `elapsedMs`; the default row limit is 100 and the maximum is 1,000.

## Connection

Create one or more named connections in Sophon's Connections settings. Server connections need
host, port, database or service name, verified TLS, and a database account with read-only grants.
To enable `sqlite.execute`, configure a separate write account. SQLite uses a managed uploaded
database file; Sophon mounts it read-only for read tools and writable only for the high-risk tool.
Credentials are stored in Sophon's vault, and only the selected role's credentials reach a call.

This integration supports password authentication in its first release. TLS verification is on
unless explicitly disabled for a trusted local server. The database server's own grants are the
final authority for which statements can run.

## Third-party software and trademarks

This skill uses the pinned Python dependencies in `manifest.json`. SQLite is a trademark
of its respective owner. This is an independent integration, not an official product of that owner.
