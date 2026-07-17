"""Snowflake integration skill — run SQL and browse the catalog via Snowflake's REST APIs.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (accountUrl, pat, warehouse, role).

Auth is a Programmatic Access Token (PAT) sent as a static bearer token together with
"X-Snowflake-Authorization-Token-Type: PROGRAMMATIC_ACCESS_TOKEN" — there is no token endpoint.
SQL runs through the SQL API (POST /api/v2/statements, async results polled by statement
handle); catalog browsing uses the REST v2 catalog GETs (databases/schemas/tables/warehouses).
Result rows arrive as arrays of strings aligned to resultSetMetaData.rowType and are mapped to
objects keyed by column name.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
account_url = (params.get("accountUrl") or "").rstrip("/")
pat = params.get("pat") or ""
warehouse = params.get("warehouse") or ""
role = params.get("role") or ""

MAX_ROWS = 1000            # cap on rows returned to the model
STATEMENT_TIMEOUT = 20     # default server-side statement timeout (seconds)
SYNC_TIMEOUT_MAX = 20      # longest synchronous wait that fits the 30s sandbox budget
MAX_STATEMENT_TIMEOUT = 3600  # cap on the server-side timeout for async submissions


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Snowflake REST API.

    Returns (http_status, parsed_json_or_None) — the SQL API signals a still-running
    statement with HTTP 202, so callers need the status alongside the body.
    """
    url = f"{account_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {pat}",
        "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
        "Accept": "application/json",
        "User-Agent": "sophon-snowflake-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("message") or parsed.get("error") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Snowflake API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Snowflake: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def quoted(value):
    """Percent-encode a path segment (statement handles, database/schema/table names)."""
    return urllib.parse.quote(str(value), safe="")


def sql_ident(name, exact=False):
    """Format an identifier for use inside a SQL statement.

    With exact=True the name is a stored spelling (echoed by the REST catalog) and is
    always double-quoted verbatim. Otherwise plain identifiers are left bare so they
    resolve case-insensitively, matching the REST catalog's resolution of unquoted
    names; anything with characters outside the plain-identifier set is quoted.
    """
    name = str(name)
    if not exact and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
        return name
    return '"' + name.replace('"', '""') + '"'


def rows_to_objects(row_type, data):
    """Map SQL API row arrays (strings aligned to rowType) to objects keyed by column name.

    Duplicate column names (e.g. SELECT a.id, b.id) are suffixed (_2, _3, ...) so later
    columns do not silently overwrite earlier ones in the resulting objects.
    """
    names = []
    seen = {}
    for c in (row_type or []):
        name = c.get("name")
        count = seen.get(name, 0) + 1
        seen[name] = count
        names.append(name if count == 1 else f"{name}_{count}")
    return [dict(zip(names, row)) for row in (data or [])[:MAX_ROWS]]


def statement_result(handle, body):
    """Shape a completed SQL API response: columns from rowType, rows capped at MAX_ROWS."""
    meta = (body or {}).get("resultSetMetaData") or {}
    row_type = meta.get("rowType") or []
    rows = rows_to_objects(row_type, (body or {}).get("data"))
    total = meta.get("numRows")
    total = total if isinstance(total, int) else len(rows)
    return {
        "statementHandle": (body or {}).get("statementHandle") or handle,
        "status": "complete",
        "columns": [{"name": c.get("name"), "type": c.get("type")} for c in row_type],
        "rows": rows,
        "rowCount": total,
        "truncated": total > len(rows),
    }


def statement_payload(statement, timeout):
    payload = {"statement": statement, "timeout": timeout, "warehouse": warehouse}
    if params.get("database"):
        payload["database"] = params["database"]
    if params.get("schema"):
        payload["schema"] = params["schema"]
    effective_role = params.get("role") or role
    if effective_role:
        payload["role"] = effective_role
    return payload


def database_summary(d):
    return {
        "name": d.get("name"),
        "owner": d.get("owner"),
        "kind": d.get("kind"),
        "comment": d.get("comment"),
        "created_on": d.get("created_on"),
    }


def schema_summary(s):
    return {
        "name": s.get("name"),
        "database": s.get("database_name"),
        "owner": s.get("owner"),
        "comment": s.get("comment"),
        "created_on": s.get("created_on"),
    }


def table_summary(t):
    return {
        "name": t.get("name"),
        "kind": t.get("kind") or t.get("table_type"),
        "rows": t.get("rows"),
        "bytes": t.get("bytes"),
        "comment": t.get("comment"),
        "created_on": t.get("created_on"),
    }


def column_summary(c):
    return {
        "name": c.get("name"),
        "datatype": c.get("datatype"),
        "nullable": c.get("nullable"),
        "default": c.get("default"),
        "comment": c.get("comment"),
    }


# --- Tool handlers ---------------------------------------------------------

def run_query():
    statement = params.get("statement")
    if not statement:
        raise ValueError("statement required")
    timeout = clamp(params.get("timeout", STATEMENT_TIMEOUT), STATEMENT_TIMEOUT,
                    MAX_STATEMENT_TIMEOUT)
    # A timeout beyond the synchronous window means the caller expects a long-running
    # statement: submit it with ?async=true so we get a 202 + handle immediately (well
    # inside the 30s sandbox budget) instead of blocking, and keep the generous
    # server-side timeout so Snowflake does not cancel the statement early.
    run_async = timeout > SYNC_TIMEOUT_MAX
    status, body = request("POST", "/api/v2/statements",
                           data=statement_payload(statement, timeout),
                           query={"async": "true"} if run_async else None)
    body = body or {}
    if status == 202:
        print(json.dumps({
            "statementHandle": body.get("statementHandle"),
            "status": "running",
            "hint": "poll with snowflake.get_statement",
        }))
        return
    print(json.dumps(statement_result(None, body)))


def get_statement():
    handle = params.get("statementHandle")
    if not handle:
        raise ValueError("statementHandle required")
    status, body = request("GET", f"/api/v2/statements/{quoted(handle)}")
    body = body or {}
    if status == 202:
        print(json.dumps({
            "statementHandle": body.get("statementHandle") or handle,
            "status": "running",
            "message": body.get("message"),
        }))
        return
    meta = body.get("resultSetMetaData") or {}
    partitions = meta.get("partitionInfo") or []
    data = list(body.get("data") or [])
    # Partition 0 comes with the response; stitch the rest until the row cap is reached.
    partition = 1
    while partition < len(partitions) and len(data) < MAX_ROWS:
        _, part = request("GET", f"/api/v2/statements/{quoted(handle)}",
                          query={"partition": partition})
        data.extend((part or {}).get("data") or [])
        partition += 1
    body["data"] = data
    print(json.dumps(statement_result(handle, body)))


def cancel_statement():
    handle = params.get("statementHandle")
    if not handle:
        raise ValueError("statementHandle required")
    _, body = request("POST", f"/api/v2/statements/{quoted(handle)}/cancel")
    print(json.dumps({
        "statementHandle": handle,
        "canceled": True,
        "message": (body or {}).get("message"),
    }))


def list_databases():
    limit = clamp(params.get("limit", 25), 25, 100)
    _, body = request("GET", "/api/v2/databases", query={"showLimit": limit})
    databases = [database_summary(d) for d in (body or [])[:limit]]
    print(json.dumps({"count": len(databases), "databases": databases}))


def list_schemas():
    database = params.get("database")
    if not database:
        raise ValueError("database required")
    limit = clamp(params.get("limit", 25), 25, 100)
    _, body = request("GET", f"/api/v2/databases/{quoted(database)}/schemas",
                      query={"showLimit": limit})
    schemas = [schema_summary(s) for s in (body or [])[:limit]]
    print(json.dumps({"count": len(schemas), "schemas": schemas}))


def list_tables():
    database = params.get("database")
    schema = params.get("schema")
    if not database or not schema:
        raise ValueError("database and schema required")
    limit = clamp(params.get("limit", 25), 25, 100)
    _, body = request(
        "GET",
        f"/api/v2/databases/{quoted(database)}/schemas/{quoted(schema)}/tables",
        query={"showLimit": limit},
    )
    tables = [table_summary(t) for t in (body or [])[:limit]]
    print(json.dumps({"count": len(tables), "tables": tables}))


def describe_table():
    database = params.get("database")
    schema = params.get("schema")
    table = params.get("table")
    if not database or not schema or not table:
        raise ValueError("database, schema, and table required")
    _, body = request(
        "GET",
        f"/api/v2/databases/{quoted(database)}/schemas/{quoted(schema)}"
        f"/tables/{quoted(table)}",
    )
    body = body or {}
    columns = [column_summary(c) for c in (body.get("columns") or [])]
    if not columns:
        # Fallback for accounts where the REST catalog omits columns: DESCRIBE TABLE.
        # Prefer the stored spellings echoed by the REST catalog (quoted verbatim) so
        # the DESCRIBE targets exactly the table the GET resolved; otherwise leave
        # plain user-supplied names bare so they resolve case-insensitively too.
        parts = []
        for echoed, given in ((body.get("database_name"), database),
                              (body.get("schema_name"), schema),
                              (body.get("name"), table)):
            parts.append(sql_ident(echoed, exact=True) if echoed else sql_ident(given))
        statement = "DESCRIBE TABLE " + ".".join(parts)
        _, desc = request("POST", "/api/v2/statements",
                          data=statement_payload(statement, STATEMENT_TIMEOUT))
        desc = desc or {}
        meta = desc.get("resultSetMetaData") or {}
        for r in rows_to_objects(meta.get("rowType") or [], desc.get("data")):
            columns.append({
                "name": r.get("name"),
                "datatype": r.get("type"),
                "nullable": r.get("null?") == "Y" if r.get("null?") is not None else None,
                "default": r.get("default"),
                "comment": r.get("comment"),
            })
    print(json.dumps({
        "name": body.get("name") or table,
        "database": body.get("database_name") or database,
        "schema": body.get("schema_name") or schema,
        "kind": body.get("kind") or body.get("table_type"),
        "rows": body.get("rows"),
        "bytes": body.get("bytes"),
        "comment": body.get("comment"),
        "columns": columns,
    }))


def list_warehouses():
    _, body = request("GET", "/api/v2/warehouses")
    warehouses = [{
        "name": w.get("name"),
        "state": w.get("state"),
        "type": w.get("type") or w.get("warehouse_type"),
        "size": w.get("size") or w.get("warehouse_size"),
        "auto_suspend": w.get("auto_suspend"),
        "auto_resume": w.get("auto_resume"),
        "owner": w.get("owner"),
        "comment": w.get("comment"),
    } for w in (body or [])]
    print(json.dumps({"count": len(warehouses), "warehouses": warehouses}))


HANDLERS = {
    "snowflake.query": run_query,
    "snowflake.get_statement": get_statement,
    "snowflake.cancel_statement": cancel_statement,
    "snowflake.list_databases": list_databases,
    "snowflake.list_schemas": list_schemas,
    "snowflake.list_tables": list_tables,
    "snowflake.describe_table": describe_table,
    "snowflake.list_warehouses": list_warehouses,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (account_url and pat and warehouse):
        print(json.dumps({"error": "Missing Snowflake credentials: connect the Snowflake integration first (accountUrl, pat, warehouse)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
