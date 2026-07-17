"""ClickHouse integration skill — query and inspect a ClickHouse server over its HTTP interface.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, username, password, database).

Auth is HTTP Basic (base64 of username:password) against the native HTTP interface
(e.g. https://host:8443 for ClickHouse Cloud, http://host:8123 self-hosted). Security model:
read tools always send readonly=1 so the SERVER rejects any write statement; database/table
identifiers are strictly validated (^[A-Za-z0-9_]+$); dynamic values travel as typed
param_<name> bindings ({name:String} placeholders) — never string interpolation.
"""

import base64
import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").strip().rstrip("/")
username = params.get("username") or ""
password = params.get("password") or ""
database = params.get("database") or ""

IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")


def ident(value, what):
    """Strictly validate a ClickHouse identifier (database/table name)."""
    v = str(value or "")
    if not v:
        raise ValueError(f"{what} required")
    if not IDENT_RE.match(v):
        raise ValueError(f"Invalid {what}: only letters, digits, and underscores are allowed")
    return v


def request(method, query=None, body=None):
    """Make an authenticated request to the ClickHouse HTTP interface. Returns raw text or None."""
    url = f"{base_url}/"
    clean = {k: v for k, v in (query or {}).items() if v not in (None, "")}
    if clean:
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "User-Agent": "sophon-clickhouse-skill",
    }
    data = body.encode() if isinstance(body, str) else body
    if data is not None:
        headers["Content-Type"] = "text/plain; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return raw if raw.strip() else None
    except urllib.error.HTTPError as e:
        detail = (e.read().decode(errors="replace") if e.fp else "").strip()
        msg = detail
        try:
            parsed = json.loads(detail)
            if isinstance(parsed, dict):
                msg = parsed.get("exception") or parsed.get("error") or detail
        except (ValueError, TypeError):
            pass
        msg = " ".join(str(msg).split())[:500]
        if e.code == 429:
            retry = e.headers.get("Retry-After")
            if retry:
                msg = (f"{msg} " if msg else "rate limited ") + f"(retry after {retry}s)"
        raise RuntimeError(f"ClickHouse API error {e.code}: {msg or e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach ClickHouse: {e.reason}") from e


def run_select(sql, bind=None):
    """Run a read-only statement with FORMAT JSON and return the {meta, data, rows} envelope.

    Always sends readonly=1 so the server itself rejects any write statement. Dynamic values
    go through ClickHouse's typed param_<name> query parameters, never string interpolation.
    """
    qp = {"query": f"{sql} FORMAT JSON"}
    if database:
        qp["database"] = database
    for key, value in (bind or {}).items():
        qp[f"param_{key}"] = value
    qp["readonly"] = "1"
    raw = request("GET", query=qp)
    try:
        env = json.loads(raw or "")
    except ValueError:
        raise RuntimeError("ClickHouse returned a non-JSON response; expected FORMAT JSON output")
    return env if isinstance(env, dict) else {}


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def to_int(value):
    """ClickHouse FORMAT JSON quotes 64-bit integers as strings; coerce to int when possible."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_db():
    return str(params.get("database") or database or "default")


# --- Tool handlers ---------------------------------------------------------

def query():
    sql = str(params.get("sql") or "").strip().rstrip(";").strip()
    if not sql:
        raise ValueError("sql required")
    if re.search(r"\bFORMAT\s+\w+\s*$", sql, re.IGNORECASE):
        raise ValueError("Do not include a FORMAT clause; results are always returned as FORMAT JSON")
    limit = clamp(params.get("limit", 100), 100, 1000)
    if not re.search(r"\bLIMIT\s+\d", sql, re.IGNORECASE):
        # Append on a NEW LINE so a trailing `--` line comment cannot swallow the cap.
        # If LIMIT only appears in a subquery or string literal, no outer cap is appended
        # and the server may return more rows; rows[:limit] below still bounds the output.
        sql = f"{sql}\nLIMIT {limit}"
    env = run_select(sql)
    rows = env.get("data") or []
    truncated = len(rows) > limit
    rows = rows[:limit]
    result = {
        "columns": [{"name": m.get("name"), "type": m.get("type")} for m in env.get("meta") or []],
        "count": len(rows),
        "rows": rows,
    }
    if truncated:
        result["truncated"] = True
    print(json.dumps(result))


def list_databases():
    env = run_select("SELECT name FROM system.databases ORDER BY name")
    names = [d.get("name") for d in env.get("data") or []]
    print(json.dumps({"count": len(names), "databases": names}))


def list_tables():
    db = resolve_db()
    env = run_select(
        "SELECT name, engine, total_rows, total_bytes FROM system.tables "
        "WHERE database = {db:String} ORDER BY name",
        bind={"db": db},
    )
    tables = [{
        "name": t.get("name"),
        "engine": t.get("engine"),
        "totalRows": to_int(t.get("total_rows")),
        "totalBytes": to_int(t.get("total_bytes")),
    } for t in env.get("data") or []]
    print(json.dumps({"database": db, "count": len(tables), "tables": tables}))


def describe_table():
    db = ident(resolve_db(), "database")
    table = ident(params.get("table"), "table")
    env = run_select(f"DESCRIBE TABLE {db}.{table}")
    columns = [{
        "name": c.get("name"),
        "type": c.get("type"),
        "defaultType": c.get("default_type") or None,
        "defaultExpression": c.get("default_expression") or None,
        "comment": c.get("comment") or None,
    } for c in env.get("data") or []]
    print(json.dumps({"database": db, "table": table, "count": len(columns), "columns": columns}))


def table_stats():
    db = ident(resolve_db(), "database")
    table = ident(params.get("table"), "table")
    env = run_select(
        "SELECT partition, count() AS parts, sum(rows) AS rows, "
        "sum(data_compressed_bytes) AS compressed_bytes, "
        "sum(data_uncompressed_bytes) AS uncompressed_bytes "
        "FROM system.parts WHERE database = {db:String} AND table = {table:String} "
        "AND active GROUP BY partition ORDER BY partition",
        bind={"db": db, "table": table},
    )
    partitions = [{
        "partition": p.get("partition"),
        "parts": to_int(p.get("parts")),
        "rows": to_int(p.get("rows")),
        "compressedBytes": to_int(p.get("compressed_bytes")),
        "uncompressedBytes": to_int(p.get("uncompressed_bytes")),
    } for p in env.get("data") or []]
    total_rows = sum(p["rows"] or 0 for p in partitions)
    print(json.dumps({"database": db, "table": table, "count": len(partitions),
                      "totalRows": total_rows, "partitions": partitions}))


def insert_rows():
    db = ident(resolve_db(), "database")
    table = ident(params.get("table"), "table")
    rows = params.get("rows")
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
        raise ValueError("rows must be a non-empty array of JSON objects")
    lines = "\n".join(json.dumps(r) for r in rows)
    request("POST", body=f"INSERT INTO {db}.{table} FORMAT JSONEachRow\n{lines}")
    print(json.dumps({"inserted": len(rows), "database": db, "table": table}))


def ping():
    env = run_select("SELECT version()")
    data = env.get("data") or []
    version = None
    if data and isinstance(data[0], dict):
        version = next(iter(data[0].values()), None)
    print(json.dumps({"ok": True, "version": version}))


HANDLERS = {
    "clickhouse.query": query,
    "clickhouse.list_databases": list_databases,
    "clickhouse.list_tables": list_tables,
    "clickhouse.describe_table": describe_table,
    "clickhouse.table_stats": table_stats,
    "clickhouse.insert_rows": insert_rows,
    "clickhouse.ping": ping,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and username and password):
        print(json.dumps({"error": "Missing ClickHouse credentials: connect the ClickHouse integration first (baseUrl, username, password)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
