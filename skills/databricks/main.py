"""Databricks integration skill — SQL warehouses, Unity Catalog, and Jobs via the REST API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, apiToken, warehouseId).

Auth is a workspace Personal Access Token sent as "Authorization: Bearer {apiToken}". There is
no token endpoint. SQL statements run on the configured SQL warehouse via the Statement
Execution API with INLINE/JSON_ARRAY results. Rows are capped at 1000 with a truncation note
when results are cut off; a statement whose inline result would exceed the API's 25 MiB inline
limit fails outright rather than being truncated.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
api_token = params.get("apiToken") or ""
warehouse_id = params.get("warehouseId") or ""

ROW_CAP = 1000
CATALOG_LIST_CAP = 100  # max_results for Unity Catalog list endpoints


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Databricks REST API. Returns parsed JSON (or None)."""
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "User-Agent": "sophon-databricks-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("message") or parsed.get("error_code") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Databricks API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Databricks workspace: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def statement_summary(resp, fetch_chunks=False):
    """Shape a Statement Execution API response into columns + row objects."""
    status = resp.get("status") or {}
    state = status.get("state")
    statement_id = resp.get("statement_id")
    if state in ("PENDING", "RUNNING"):
        return {
            "statement_id": statement_id,
            "state": state,
            "hint": "Statement is still running. Poll it with databricks.get_statement.",
        }
    if state != "SUCCEEDED":
        err = status.get("error") or {}
        return {
            "statement_id": statement_id,
            "state": state,
            "error": err.get("message") or err.get("error_code") or f"Statement ended in state {state}",
        }
    manifest = resp.get("manifest") or {}
    columns = [c.get("name") for c in ((manifest.get("schema") or {}).get("columns") or [])]
    result = resp.get("result") or {}
    raw_rows = list(result.get("data_array") or [])
    unfetched_chunks = result.get("next_chunk_index") is not None
    if fetch_chunks:
        next_chunk = result.get("next_chunk_index")
        while next_chunk is not None and len(raw_rows) < ROW_CAP:
            chunk = request(
                "GET",
                f"/api/2.0/sql/statements/{urllib.parse.quote(str(statement_id), safe='')}"
                f"/result/chunks/{int(next_chunk)}",
            ) or {}
            raw_rows.extend(chunk.get("data_array") or [])
            next_chunk = chunk.get("next_chunk_index")
        unfetched_chunks = next_chunk is not None
    capped = len(raw_rows) > ROW_CAP
    if capped:
        raw_rows = raw_rows[:ROW_CAP]
    rows = [dict(zip(columns, row)) for row in raw_rows]
    out = {
        "statement_id": statement_id,
        "state": state,
        "row_count": len(rows),
        "total_row_count": manifest.get("total_row_count"),
        "columns": columns,
        "rows": rows,
    }
    if manifest.get("truncated") or capped or unfetched_chunks:
        out["truncated"] = True
        note = "Results were truncated by the row limit (max 1000 rows)."
        if unfetched_chunks:
            note += (" More result chunks exist; use databricks.get_statement with this"
                     " statement_id to fetch the remaining rows up to the row cap.")
        note += " Narrow the query or add a WHERE/LIMIT clause for complete data."
        out["note"] = note
    return out


# --- Tool handlers ---------------------------------------------------------

def execute_sql():
    statement = params.get("statement")
    if not statement:
        raise ValueError("statement required")
    row_limit = clamp(params.get("row_limit", ROW_CAP), ROW_CAP, ROW_CAP)
    resp = request("POST", "/api/2.0/sql/statements", data={
        "statement": statement,
        "warehouse_id": warehouse_id,
        # Kept safely below the sandbox timeoutSeconds (30) so slow statements still
        # return a statement_id + poll hint instead of the process being killed.
        "wait_timeout": "20s",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
        "row_limit": row_limit,
    })
    print(json.dumps(statement_summary(resp or {})))


def get_statement():
    statement_id = params.get("statement_id")
    if not statement_id:
        raise ValueError("statement_id required")
    resp = request(
        "GET", f"/api/2.0/sql/statements/{urllib.parse.quote(str(statement_id), safe='')}")
    print(json.dumps(statement_summary(resp or {}, fetch_chunks=True)))


def cancel_statement():
    statement_id = params.get("statement_id")
    if not statement_id:
        raise ValueError("statement_id required")
    request(
        "POST",
        f"/api/2.0/sql/statements/{urllib.parse.quote(str(statement_id), safe='')}/cancel")
    print(json.dumps({"statement_id": statement_id, "cancelled": True}))


def list_warehouses():
    resp = request("GET", "/api/2.0/sql/warehouses")
    warehouses = [{
        "id": w.get("id"),
        "name": w.get("name"),
        "state": w.get("state"),
        "size": w.get("size") or w.get("cluster_size"),
    } for w in (resp or {}).get("warehouses", [])]
    print(json.dumps({"count": len(warehouses), "warehouses": warehouses}))


def list_tables():
    catalog = params.get("catalog") or ""
    schema = params.get("schema") or ""
    if schema and not catalog:
        raise ValueError("catalog required when schema is provided")
    if not catalog:
        resp = request("GET", "/api/2.1/unity-catalog/catalogs",
                       query={"max_results": CATALOG_LIST_CAP}) or {}
        catalogs = [{
            "name": c.get("name"),
            "comment": c.get("comment"),
            "owner": c.get("owner"),
        } for c in resp.get("catalogs", [])[:CATALOG_LIST_CAP]]
        out = {"count": len(catalogs), "catalogs": catalogs}
        if resp.get("next_page_token"):
            out["truncated"] = True
        print(json.dumps(out))
        return
    if not schema:
        resp = request("GET", "/api/2.1/unity-catalog/schemas",
                       query={"catalog_name": catalog,
                              "max_results": CATALOG_LIST_CAP}) or {}
        schemas = [{
            "name": s.get("name"),
            "catalog_name": s.get("catalog_name"),
            "comment": s.get("comment"),
        } for s in resp.get("schemas", [])[:CATALOG_LIST_CAP]]
        out = {"count": len(schemas), "schemas": schemas}
        if resp.get("next_page_token"):
            out["truncated"] = True
        print(json.dumps(out))
        return
    resp = request("GET", "/api/2.1/unity-catalog/tables",
                   query={"catalog_name": catalog, "schema_name": schema,
                          "max_results": CATALOG_LIST_CAP}) or {}
    tables = [{
        "name": t.get("name"),
        "table_type": t.get("table_type"),
        "columns": [{
            "name": c.get("name"),
            "type": c.get("type_text") or c.get("type_name"),
        } for c in (t.get("columns") or [])],
    } for t in resp.get("tables", [])[:CATALOG_LIST_CAP]]
    out = {"count": len(tables), "tables": tables}
    if resp.get("next_page_token"):
        out["truncated"] = True
    print(json.dumps(out))


def list_jobs():
    limit = clamp(params.get("limit", 25), 25, 25)
    resp = request("GET", "/api/2.2/jobs/list", query={"limit": limit})
    jobs = [{
        "job_id": j.get("job_id"),
        "name": (j.get("settings") or {}).get("name"),
        "creator": j.get("creator_user_name"),
    } for j in (resp or {}).get("jobs", [])]
    print(json.dumps({"count": len(jobs), "jobs": jobs}))


def list_job_runs():
    limit = clamp(params.get("limit", 25), 25, 25)
    resp = request("GET", "/api/2.2/jobs/runs/list",
                   query={"limit": limit, "job_id": params.get("job_id")})
    runs = []
    for r in (resp or {}).get("runs", []):
        state = r.get("state") or {}
        status = r.get("status") or {}
        runs.append({
            "run_id": r.get("run_id"),
            "job_id": r.get("job_id"),
            "life_cycle_state": state.get("life_cycle_state") or status.get("state"),
            "result_state": state.get("result_state")
                or ((status.get("termination_details") or {}).get("code")),
            "start_time": r.get("start_time"),
            "duration_ms": r.get("run_duration") or r.get("execution_duration"),
        })
    print(json.dumps({"count": len(runs), "runs": runs}))


def run_job():
    job_id = params.get("job_id")
    if job_id in (None, ""):
        raise ValueError("job_id required")
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        raise ValueError("job_id must be an integer")
    resp = request("POST", "/api/2.2/jobs/run-now", data={"job_id": job_id})
    print(json.dumps({
        "job_id": job_id,
        "run_id": (resp or {}).get("run_id"),
        "started": True,
    }))


HANDLERS = {
    "databricks.execute_sql": execute_sql,
    "databricks.get_statement": get_statement,
    "databricks.cancel_statement": cancel_statement,
    "databricks.list_warehouses": list_warehouses,
    "databricks.list_tables": list_tables,
    "databricks.list_jobs": list_jobs,
    "databricks.list_job_runs": list_job_runs,
    "databricks.run_job": run_job,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_token and warehouse_id):
        print(json.dumps({"error": "Missing Databricks credentials: connect the Databricks integration first (baseUrl, apiToken, warehouseId)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
