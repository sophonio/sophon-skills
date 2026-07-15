"""SQL database skill — query PostgreSQL, MySQL/MariaDB, or SQLite.

Uses pure-Python drivers (pg8000, PyMySQL) plus the stdlib sqlite3 module, so it installs and
runs unchanged in the alpine Python sandbox with no compiled dependencies. `params` is injected
as a global by the Sophon runtime and carries the tool name, the tool arguments, and the
connection-card field values (dbType, host, port, database, username, password).
"""

import json
import re

tool_name = params.get("tool", "")
db_type = (params.get("dbType") or "").strip().lower()
host = params.get("host") or ""
port_raw = params.get("port") or ""
database = params.get("database") or ""
username = params.get("username") or ""
password = params.get("password") or ""

VALID_DB_TYPES = ("postgres", "mysql", "sqlite")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_.]+$")


def parse_port(default):
    """Return the configured port as an int, falling back to the driver default."""
    try:
        return int(str(port_raw).strip())
    except (TypeError, ValueError):
        return default


def connect():
    """Open a DB-API connection based on dbType. Raises RuntimeError on bad config."""
    if db_type == "postgres":
        import pg8000.dbapi
        return pg8000.dbapi.connect(
            user=username,
            password=password,
            host=host or "localhost",
            port=parse_port(5432),
            database=database,
        )
    if db_type == "mysql":
        import pymysql
        return pymysql.connect(
            host=host or "localhost",
            port=parse_port(3306),
            user=username,
            password=password,
            database=database,
        )
    if db_type == "sqlite":
        import sqlite3
        return sqlite3.connect(database)
    raise RuntimeError(
        f"Unsupported dbType '{db_type}'. Must be one of: postgres, mysql, sqlite."
    )


def to_jsonable(value):
    """Coerce a DB cell value into something json.dumps can serialize."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            return bytes(value).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return bytes(value).hex()
    return str(value)


# --- Tool handlers ---------------------------------------------------------

def list_tables(conn):
    cur = conn.cursor()
    try:
        if db_type == "postgres":
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                "ORDER BY table_name"
            )
        elif db_type == "mysql":
            cur.execute("SHOW TABLES")
        else:  # sqlite
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        tables = [to_jsonable(row[0]) for row in cur.fetchall()]
        print(json.dumps({"tables": tables, "count": len(tables)}))
    finally:
        cur.close()


def describe_table(conn):
    table = (params.get("table") or "").strip()
    if not table:
        raise ValueError("Missing required parameter: table")
    if not IDENTIFIER_RE.match(table):
        raise ValueError(
            "Invalid table name: only letters, digits, underscore and dot are allowed."
        )
    cur = conn.cursor()
    try:
        columns = []
        if db_type == "postgres":
            cur.execute(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = %s "
                "ORDER BY ordinal_position",
                (table,),
            )
            for row in cur.fetchall():
                columns.append({
                    "name": to_jsonable(row[0]),
                    "type": to_jsonable(row[1]),
                    "nullable": row[2] == "YES",
                    "default": to_jsonable(row[3]),
                })
        elif db_type == "mysql":
            # table validated against the identifier whitelist above.
            cur.execute(f"DESCRIBE `{table}`")
            for row in cur.fetchall():
                columns.append({
                    "name": to_jsonable(row[0]),
                    "type": to_jsonable(row[1]),
                    "nullable": row[2] == "YES",
                    "key": to_jsonable(row[3]),
                    "default": to_jsonable(row[4]),
                })
        else:  # sqlite
            cur.execute(f"PRAGMA table_info(\"{table}\")")
            for row in cur.fetchall():
                columns.append({
                    "name": to_jsonable(row[1]),
                    "type": to_jsonable(row[2]),
                    "nullable": row[3] == 0,
                    "default": to_jsonable(row[4]),
                    "primaryKey": bool(row[5]),
                })
        if not columns:
            raise RuntimeError(f"Table not found or has no columns: {table}")
        print(json.dumps({"table": table, "columns": columns}))
    finally:
        cur.close()


def run_query(conn):
    sql = params.get("sql") or ""
    if not sql.strip():
        raise ValueError("Missing required parameter: sql")

    try:
        limit = int(params.get("limit"))
    except (TypeError, ValueError):
        limit = 500
    limit = max(1, min(limit, 1000))

    cur = conn.cursor()
    try:
        cur.execute(sql)
        if cur.description is not None:
            # A result set was produced (SELECT / RETURNING / SHOW / PRAGMA).
            col_names = [d[0] for d in cur.description]
            fetched = cur.fetchmany(limit)
            rows = [[to_jsonable(cell) for cell in row] for row in fetched]
            print(json.dumps({
                "columns": col_names,
                "rows": rows,
                "rowCount": len(rows),
                "truncated": len(rows) >= limit,
            }))
        else:
            # No result set: an INSERT/UPDATE/DELETE/DDL. Commit the change.
            affected = cur.rowcount
            conn.commit()
            print(json.dumps({"rowsAffected": affected}))
    finally:
        cur.close()


HANDLERS = {
    "sql.list_tables": list_tables,
    "sql.describe_table": describe_table,
    "sql.run_query": run_query,
}

conn = None
try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif db_type not in VALID_DB_TYPES:
        print(json.dumps({
            "error": "Invalid or missing dbType: connect the SQL integration with "
                     "dbType set to one of postgres, mysql, or sqlite."
        }))
    elif not database:
        print(json.dumps({
            "error": "Missing database: provide a database name (or SQLite file path)."
        }))
    else:
        conn = connect()
        handler(conn)
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Database error: {type(e).__name__}: {e}"}))
finally:
    if conn is not None:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
