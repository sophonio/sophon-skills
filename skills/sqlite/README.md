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

SQLite needs no credentials, so this skill declares no connection form. It opens the database
file that Sophon's named-connection runtime mounts at `SOPHON_DATABASE_PATH` (default
`/database/database.sqlite`): read-only for the read tools, writable only for the high-risk
`sqlite.execute`.

That runtime, and the `db.list_connections` tool that supplies `connectionId`, are not available in
Sophon yet. Until they are, every call that reaches the database returns
`OperationalError: unable to open database file`.

## Third-party software and trademarks

This skill uses the pinned Python dependencies in `manifest.json`. SQLite is a trademark
of its respective owner. This is an independent integration, not an official product of that owner.
