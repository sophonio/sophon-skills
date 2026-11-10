"""Sophon database skill entrypoint. Generated copies set ENGINE below.

The Sophon runtime injects ``params`` before evaluating this file. Credentials and
the mounted SQLite path are supplied by the named-connection runtime, never by the
language model's tool arguments.
"""

import base64
import datetime
import decimal
import json
import os
from pathlib import Path
import re
import ssl
import time

ENGINE = "__ENGINE__"
MAX_ROWS = 1000
MAX_BYTES = 1024 * 1024
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def required(name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required field: {name}")
    return value.strip()


def required_secret(name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required field: {name}")
    return value


def identifier(name):
    value = required(name)
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {name}: use an unquoted database identifier")
    return value


def positive_int(value, default, maximum):
    if value is None or value == "":
        return default
    number = int(value)
    if number < 1:
        raise ValueError("limit must be positive")
    return min(number, maximum)


def connect():
    if ENGINE == "sqlite":
        import sqlite3
        mode = "rw" if params.get("tool") == "sqlite.execute" else "ro"
        path = os.environ.get("SOPHON_DATABASE_PATH", "/database/database.sqlite")
        connection = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode={mode}", uri=True, timeout=10)
        connection.enable_load_extension(False)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    host = required("host")
    port = positive_int(params.get("port"),
                            {"postgres": 5432, "mssql": 1433, "oracle": 1521, "mysql": 3306}[ENGINE],
                            65535)
    username = required("username")
    password = required_secret("password")
    tls = params.get("tlsMode") != "disable"

    if ENGINE == "postgres":
        import pg8000.dbapi
        return pg8000.dbapi.connect(user=username, password=password, host=host,
                                    port=port, database=required("database"),
                                    ssl_context=ssl.create_default_context() if tls else False,
                                    timeout=10)
    if ENGINE == "mysql":
        import pymysql
        return pymysql.connect(host=host, port=port, user=username, password=password,
                               database=required("database"), connect_timeout=10,
                               read_timeout=20, write_timeout=20,
                               ssl=ssl.create_default_context() if tls else None,
                               ssl_disabled=not tls)
    if ENGINE == "mssql":
        import pytds
        return pytds.connect(server=host, port=port, database=required("database"),
                             user=username, password=password, login_timeout=10,
                             timeout=20, cafile="/etc/ssl/cert.pem" if tls else None,
                             validate_host=True)
    if ENGINE == "oracle":
        import oracledb
        return oracledb.connect(user=username, password=password, host=host, port=port,
                                service_name=required("serviceName"),
                                protocol="tcps" if tls else "tcp",
                                ssl_server_dn_match=True, tcp_connect_timeout=10)
    raise ValueError("Unsupported engine")


def bind(sql, values, cursor):
    cursor.execute(sql, values)


def catalog(sql, values=(), limit=100):
    connection = connect()
    try:
        cursor = connection.cursor()
        try:
            bind(sql, values, cursor)
            names = [item[0] for item in cursor.description]
            rows = cursor.fetchmany(limit + 1)
            return {"columns": names, "rows": [[jsonable(x) for x in row] for row in rows[:limit]],
                    "rowCount": min(len(rows), limit), "truncated": len(rows) > limit}
        finally:
            cursor.close()
    finally:
        connection.close()


def list_schemas():
    limit = positive_int(params.get("limit"), 100, 500)
    if ENGINE == "postgres":
        return catalog("SELECT schema_name FROM information_schema.schemata "
                       "WHERE schema_name NOT IN ('pg_catalog', 'information_schema') "
                       "AND schema_name NOT LIKE 'pg_toast%' ORDER BY schema_name", limit=limit)
    if ENGINE == "mssql":
        return catalog("SELECT name FROM sys.schemas WHERE name NOT IN ('sys', 'INFORMATION_SCHEMA') "
                       "ORDER BY name", limit=limit)
    if ENGINE == "oracle":
        return catalog("SELECT DISTINCT owner FROM all_tables ORDER BY owner", limit=limit)
    raise ValueError("This engine has no separate schema catalog")


def list_tables():
    limit = positive_int(params.get("limit"), 100, 500)
    if ENGINE == "postgres":
        schema = params.get("schema") or "public"
        return catalog("SELECT table_name, table_type FROM information_schema.tables "
                       "WHERE table_schema = %s ORDER BY table_name", (schema,), limit)
    if ENGINE == "mssql":
        schema = params.get("schema") or "dbo"
        return catalog("SELECT table_name, table_type FROM INFORMATION_SCHEMA.TABLES "
                       "WHERE table_schema = %s ORDER BY table_name", (schema,), limit)
    if ENGINE == "oracle":
        schema = params.get("schema") or required("username").upper()
        return catalog("SELECT table_name, 'TABLE' FROM all_tables WHERE owner = :1 "
                       "UNION ALL SELECT view_name, 'VIEW' FROM all_views WHERE owner = :2 "
                       "ORDER BY 1", (schema.upper(), schema.upper()), limit)
    if ENGINE == "mysql":
        return catalog("SELECT table_name, table_type FROM information_schema.tables "
                       "WHERE table_schema = DATABASE() ORDER BY table_name", limit=limit)
    return catalog("SELECT name, type FROM sqlite_master "
                   "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' "
                   "ORDER BY name", limit=limit)


def describe_table():
    table = identifier("table")
    if ENGINE == "postgres":
        schema = params.get("schema") or "public"
        columns = catalog("SELECT column_name, data_type, is_nullable, column_default "
                          "FROM information_schema.columns WHERE table_schema = %s "
                          "AND table_name = %s ORDER BY ordinal_position", (schema, table), 500)
        keys = catalog("SELECT kcu.column_name, tc.constraint_type, ccu.table_schema, "
                       "ccu.table_name, ccu.column_name FROM information_schema.table_constraints tc "
                       "JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name "
                       "AND tc.table_schema=kcu.table_schema "
                       "LEFT JOIN information_schema.constraint_column_usage ccu "
                       "ON ccu.constraint_name=tc.constraint_name AND ccu.table_schema=tc.table_schema "
                       "WHERE tc.table_schema=%s AND tc.table_name=%s "
                       "AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY')",
                       (schema, table), 500)
    elif ENGINE == "mssql":
        schema = params.get("schema") or "dbo"
        columns = catalog("SELECT column_name, data_type, is_nullable, column_default "
                          "FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema=%s AND table_name=%s "
                          "ORDER BY ordinal_position", (schema, table), 500)
        keys = catalog("SELECT kcu.column_name, tc.constraint_type, NULL, NULL, NULL "
                       "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc JOIN "
                       "INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu ON tc.constraint_name=kcu.constraint_name "
                       "AND tc.table_schema=kcu.table_schema WHERE tc.table_schema=%s "
                       "AND tc.table_name=%s AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY')",
                       (schema, table), 500)
    elif ENGINE == "oracle":
        schema = (params.get("schema") or required("username")).upper()
        table = table.upper()
        columns = catalog("SELECT c.column_name, c.data_type, c.nullable, c.data_default, m.comments "
                          "FROM all_tab_columns c LEFT JOIN all_col_comments m ON "
                          "m.owner=c.owner AND m.table_name=c.table_name AND m.column_name=c.column_name "
                          "WHERE c.owner=:1 AND c.table_name=:2 ORDER BY c.column_id",
                          (schema, table), 500)
        keys = catalog("SELECT cc.column_name, c.constraint_type, r.owner, r.table_name, rc.column_name "
                       "FROM all_constraints c JOIN all_cons_columns cc ON cc.owner=c.owner "
                       "AND cc.constraint_name=c.constraint_name LEFT JOIN all_constraints r ON "
                       "r.owner=c.r_owner AND r.constraint_name=c.r_constraint_name "
                       "LEFT JOIN all_cons_columns rc ON rc.owner=r.owner AND rc.constraint_name=r.constraint_name "
                       "AND rc.position=cc.position WHERE c.owner=:1 AND c.table_name=:2 "
                       "AND c.constraint_type IN ('P','R')", (schema, table), 500)
    elif ENGINE == "mysql":
        columns = catalog("SELECT column_name, column_type, is_nullable, column_default, column_comment "
                          "FROM information_schema.columns WHERE table_schema=DATABASE() "
                          "AND table_name=%s ORDER BY ordinal_position", (table,), 500)
        keys = catalog("SELECT column_name, constraint_name, referenced_table_schema, "
                       "referenced_table_name, referenced_column_name FROM information_schema.key_column_usage "
                       "WHERE table_schema=DATABASE() AND table_name=%s "
                       "AND (constraint_name='PRIMARY' OR referenced_table_name IS NOT NULL)", (table,), 500)
    else:
        columns = catalog(f'PRAGMA table_info("{table}")', limit=500)
        keys = catalog(f'PRAGMA foreign_key_list("{table}")', limit=500)
    if not columns["rows"]:
        raise ValueError("Table not found or not visible to this account")
    return {"schema": params.get("schema"), "table": table,
            "columns": columns, "keys": keys}


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, datetime.timedelta):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"base64": base64.b64encode(bytes(value)).decode("ascii")}
    return str(value)


def validate_sql(sql, read_only):
    import sqlglot
    from sqlglot import exp
    dialect = {"postgres": "postgres", "mssql": "tsql", "oracle": "oracle",
               "mysql": "mysql", "sqlite": "sqlite"}[ENGINE]
    try:
        statements = [item for item in sqlglot.parse(sql, read=dialect, error_level="RAISE") if item]
    except Exception as exc:
        raise ValueError("SQL could not be parsed as a single statement") from exc
    if len(statements) != 1:
        raise ValueError("Exactly one SQL statement is required")
    if read_only:
        statement = statements[0]
        if not isinstance(statement, (exp.Select, exp.Union, exp.Except, exp.Intersect)):
            raise ValueError("Read query must be a SELECT statement")
        forbidden = {"insert", "update", "delete", "merge", "create", "drop", "alter",
                     "into", "command", "copy", "grant", "revoke"}
        if any(type(node).__name__.lower() in forbidden for node in statement.walk()):
            raise ValueError("Read query contains a write operation")


def run_sql(write=False):
    sql = required("sql")
    validate_sql(sql, not write)
    limit = positive_int(params.get("limit"), 100, MAX_ROWS)
    start = time.monotonic()
    connection = connect()
    try:
        if not write and ENGINE in ("postgres", "mysql", "oracle"):
            setup = connection.cursor()
            try:
                setup.execute("START TRANSACTION READ ONLY" if ENGINE == "mysql"
                              else "SET TRANSACTION READ ONLY")
            finally:
                setup.close()
        cursor = connection.cursor()
        try:
            cursor.execute(sql)
            if cursor.description is not None:
                names = [item[0] for item in cursor.description]
                rows = cursor.fetchmany(limit + 1)
                result = {"columns": names, "rows": [[jsonable(x) for x in row] for row in rows[:limit]],
                          "rowCount": min(len(rows), limit), "truncated": len(rows) > limit}
                while result["rows"] and len(json.dumps(result, default=str).encode("utf-8")) > MAX_BYTES:
                    result["rows"].pop()
                    result["rowCount"] -= 1
                    result["truncated"] = True
            else:
                result = {"rowsAffected": cursor.rowcount}
            if write:
                connection.commit()
            else:
                connection.rollback()
            result["elapsedMs"] = int((time.monotonic() - start) * 1000)
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    finally:
        connection.close()


def ping():
    result = catalog("SELECT 1", limit=1)
    return {"ok": result["rows"] == [[1]]}


def dispatch():
    tool = params.get("tool", "")
    handlers = {
        f"{ENGINE}.ping": ping,
        f"{ENGINE}.list_tables": list_tables,
        f"{ENGINE}.describe_table": describe_table,
        f"{ENGINE}.query": lambda: run_sql(False),
        f"{ENGINE}.execute": lambda: run_sql(True),
    }
    if ENGINE in ("postgres", "mssql", "oracle"):
        handlers[f"{ENGINE}.list_schemas"] = list_schemas
    handler = handlers.get(tool)
    if handler is None:
        return {"error": f"Unknown tool: {tool}"}
    try:
        return handler()
    except Exception as exc:
        message = str(exc)
        for key in ("password", "username", "host"):
            secret = params.get(key)
            if isinstance(secret, str) and secret:
                message = message.replace(secret, "[redacted]")
        return {"error": f"{type(exc).__name__}: {message}"}


print(json.dumps(dispatch(), default=str))
