"""Offline mock-HTTP integration tests for the databricks skill."""
import sys

from mockhttp import run_tool, resp, err, check

BASE = {
    "baseUrl": "https://adb-123.4.azuredatabricks.net",
    "apiToken": "dapiSECRETTOKEN123",
    "warehouseId": "wh-abc123",
}

ok = True


def params(tool, **kw):
    p = dict(BASE)
    p["tool"] = tool
    p.update(kw)
    return p


# ---------------------------------------------------------------- 1. list_warehouses (auth exactness + shaping)
out, ex = run_tool("databricks", params("databricks.list_warehouses"), [
    resp(200, body={"warehouses": [
        {"id": "wh-1", "name": "Main", "state": "RUNNING", "cluster_size": "Small",
         "creator_name": "someone@x.co", "jdbc_url": "jdbc:spark://secret"},
        {"id": "wh-2", "name": "ETL", "state": "STOPPED", "size": "Medium",
         "creator_name": "other@x.co"},
    ]}),
])
ok &= check("warehouses: one request", len(ex) == 1, repr(ex))
ok &= check("warehouses: exact URL",
            ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.0/sql/warehouses", ex[0].url)
ok &= check("warehouses: GET", ex[0].method == "GET", ex[0].method)
ok &= check("warehouses: Bearer PAT byte-exact",
            ex[0].headers.get("authorization") == "Bearer dapiSECRETTOKEN123", str(ex[0].headers))
ok &= check("warehouses: Accept json", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("warehouses: no body on GET", ex[0].body is None, str(ex[0].body))
ok &= check("warehouses: count", out.get("count") == 2, str(out)[:200])
ok &= check("warehouses: trimmed fields present",
            out["warehouses"][0] == {"id": "wh-1", "name": "Main", "state": "RUNNING",
                                     "size": "Small"}, str(out["warehouses"][0]))
ok &= check("warehouses: raw fields absent",
            "creator_name" not in str(out) and "jdbc_url" not in str(out), str(out)[:300])

# ---------------------------------------------------------------- 2. list_tables (no args -> catalogs)
out, ex = run_tool("databricks", params("databricks.list_tables"), [
    resp(200, body={"catalogs": [
        {"name": "main", "comment": "prod", "owner": "admins", "metastore_id": "m1",
         "created_at": 123},
    ], "next_page_token": "tok-next"}),
])
ok &= check("catalogs: URL + max_results",
            ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.1/unity-catalog/catalogs"
            "?max_results=100", ex[0].url)
ok &= check("catalogs: count and shape",
            out.get("count") == 1 and out["catalogs"][0] == {"name": "main", "comment": "prod",
                                                            "owner": "admins"}, str(out)[:250])
ok &= check("catalogs: truncated flag on next_page_token", out.get("truncated") is True,
            str(out)[:250])
ok &= check("catalogs: raw fields absent", "metastore_id" not in str(out), str(out)[:250])

# ---------------------------------------------------------------- 3. list_tables (catalog + schema -> tables)
out, ex = run_tool("databricks",
                   params("databricks.list_tables", catalog="main", schema="default"), [
    resp(200, body={"tables": [
        {"name": "orders", "table_type": "MANAGED", "storage_location": "s3://bucket/x",
         "columns": [{"name": "id", "type_text": "bigint", "type_name": "LONG", "position": 0},
                     {"name": "ts", "type_name": "TIMESTAMP"}]},
    ]}),
])
ok &= check("tables: query carries catalog_name+schema_name+max_results",
            "catalog_name=main" in ex[0].url and "schema_name=default" in ex[0].url
            and "max_results=100" in ex[0].url
            and ex[0].url.startswith(
                "https://adb-123.4.azuredatabricks.net/api/2.1/unity-catalog/tables?"),
            ex[0].url)
ok &= check("tables: column shaping prefers type_text",
            out["tables"][0]["columns"] == [{"name": "id", "type": "bigint"},
                                            {"name": "ts", "type": "TIMESTAMP"}],
            str(out)[:300])
ok &= check("tables: count + raw fields absent",
            out.get("count") == 1 and "storage_location" not in str(out), str(out)[:300])

# ---------------------------------------------------------------- 4. list_jobs
out, ex = run_tool("databricks", params("databricks.list_jobs"), [
    resp(200, body={"jobs": [
        {"job_id": 42, "creator_user_name": "eve@x.co",
         "settings": {"name": "nightly-etl", "email_notifications": {"on_failure": ["a@b.c"]}}},
    ]}),
])
ok &= check("jobs: URL with default limit",
            ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.2/jobs/list?limit=25",
            ex[0].url)
ok &= check("jobs: shaping",
            out == {"count": 1, "jobs": [{"job_id": 42, "name": "nightly-etl",
                                          "creator": "eve@x.co"}]}, str(out)[:250])

# ---------------------------------------------------------------- 5. list_job_runs with job_id filter
out, ex = run_tool("databricks", params("databricks.list_job_runs", job_id=42, limit=5), [
    resp(200, body={"runs": [
        {"run_id": 900, "job_id": 42, "start_time": 1750000000000, "execution_duration": 6100,
         "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"}},
    ]}),
])
ok &= check("job_runs: query carries limit and job_id",
            "limit=5" in ex[0].url and "job_id=42" in ex[0].url
            and ex[0].url.startswith(
                "https://adb-123.4.azuredatabricks.net/api/2.2/jobs/runs/list?"), ex[0].url)
ok &= check("job_runs: shaping",
            out["runs"][0] == {"run_id": 900, "job_id": 42, "life_cycle_state": "TERMINATED",
                               "result_state": "SUCCESS", "start_time": 1750000000000,
                               "duration_ms": 6100}, str(out)[:300])

# ---------------------------------------------------------------- 6. execute_sql: POST body exactness (must-verify)
out, ex = run_tool("databricks",
                   params("databricks.execute_sql",
                          statement="SELECT id, name FROM main.default.users", row_limit=50), [
    resp(200, body={
        "statement_id": "stmt-1", "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": "id"}, {"name": "name"}]},
                     "total_row_count": 2},
        "result": {"data_array": [["1", "Ann"], ["2", "Bo"]]},
    }),
])
ok &= check("execute_sql: POST to /api/2.0/sql/statements",
            ex[0].method == "POST"
            and ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.0/sql/statements",
            repr(ex[0]))
ok &= check("execute_sql: content-type json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("execute_sql: exact body (statement/warehouse_id/wait_timeout/INLINE/row_limit)",
            ex[0].json == {"statement": "SELECT id, name FROM main.default.users",
                           "warehouse_id": "wh-abc123", "wait_timeout": "20s",
                           "disposition": "INLINE", "format": "JSON_ARRAY", "row_limit": 50},
            str(ex[0].body))
ok &= check("execute_sql: rows zipped into objects",
            out["rows"] == [{"id": "1", "name": "Ann"}, {"id": "2", "name": "Bo"}]
            and out["row_count"] == 2 and out["columns"] == ["id", "name"]
            and out["state"] == "SUCCEEDED", str(out)[:300])
ok &= check("execute_sql: no truncation flag on full result", "truncated" not in out,
            str(out)[:300])

# ---------------------------------------------------------------- 7. execute_sql: PENDING -> statement_id + poll hint
out, ex = run_tool("databricks",
                   params("databricks.execute_sql", statement="SELECT * FROM big"), [
    resp(200, body={"statement_id": "stmt-slow", "status": {"state": "PENDING"}}),
])
ok &= check("execute_sql pending: default row_limit 1000", ex[0].json.get("row_limit") == 1000,
            str(ex[0].body))
ok &= check("execute_sql pending: statement_id + state",
            out.get("statement_id") == "stmt-slow" and out.get("state") == "PENDING",
            str(out)[:250])
ok &= check("execute_sql pending: poll hint names get_statement",
            "databricks.get_statement" in out.get("hint", ""), str(out)[:250])

# ---------------------------------------------------------------- 8. get_statement: chunked results fetched
out, ex = run_tool("databricks", params("databricks.get_statement", statement_id="stmt-1"), [
    resp(200, body={
        "statement_id": "stmt-1", "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": "n"}]}, "total_row_count": 4},
        "result": {"data_array": [["1"], ["2"]], "next_chunk_index": 1},
    }),
    resp(200, body={"data_array": [["3"], ["4"]]}),
])
ok &= check("get_statement: two requests (statement + chunk)", len(ex) == 2, repr(ex))
ok &= check("get_statement: statement URL",
            ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.0/sql/statements/stmt-1",
            ex[0].url)
ok &= check("get_statement: chunk URL",
            ex[1].url == "https://adb-123.4.azuredatabricks.net/api/2.0/sql/statements/stmt-1"
            "/result/chunks/1", ex[1].url)
ok &= check("get_statement: chunk request authenticated",
            ex[1].headers.get("authorization") == "Bearer dapiSECRETTOKEN123", str(ex[1].headers))
ok &= check("get_statement: rows merged across chunks",
            out["rows"] == [{"n": "1"}, {"n": "2"}, {"n": "3"}, {"n": "4"}]
            and out["row_count"] == 4, str(out)[:300])
ok &= check("get_statement: no truncation after all chunks fetched", "truncated" not in out,
            str(out)[:300])

# ---------------------------------------------------------------- 9. run_job: write path body exactness (must-verify)
out, ex = run_tool("databricks", params("databricks.run_job", job_id=42), [
    resp(200, body={"run_id": 9001}),
])
ok &= check("run_job: POST to /api/2.2/jobs/run-now",
            ex[0].method == "POST"
            and ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.2/jobs/run-now",
            repr(ex[0]))
ok &= check("run_job: body is exactly {\"job_id\": 42}", ex[0].json == {"job_id": 42},
            str(ex[0].body))
ok &= check("run_job: output", out == {"job_id": 42, "run_id": 9001, "started": True},
            str(out)[:200])

# run_job with a non-integer job_id must fail without any HTTP call
out, ex = run_tool("databricks", params("databricks.run_job", job_id="not-a-number"), [])
ok &= check("run_job: non-int job_id rejected, no request",
            "error" in out and "integer" in out["error"] and len(ex) == 0, str(out)[:200])

# ---------------------------------------------------------------- 10. cancel_statement
out, ex = run_tool("databricks", params("databricks.cancel_statement", statement_id="stmt-9"), [
    resp(200, body={}),
])
ok &= check("cancel: POST to /cancel",
            ex[0].method == "POST"
            and ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.0/sql/statements"
            "/stmt-9/cancel", repr(ex[0]))
ok &= check("cancel: output", out == {"statement_id": "stmt-9", "cancelled": True},
            str(out)[:200])

# ---------------------------------------------------------------- 11. error paths: 401 friendly, no traceback, no secret
out, ex = run_tool("databricks", params("databricks.list_warehouses"), [
    err(401, body={"error_code": "PERMISSION_DENIED", "message": "Invalid access token."}),
])
printed = str(out)
ok &= check("401: friendly error with status", "error" in out and "401" in out["error"],
            printed[:250])
ok &= check("401: server message surfaced", "Invalid access token." in out["error"],
            printed[:250])
ok &= check("401: no traceback", "Traceback" not in printed and "urllib" not in printed,
            printed[:250])
ok &= check("401: secret token not leaked", "dapiSECRETTOKEN123" not in printed, printed[:250])

# 429 rate limit also surfaces as a friendly error with the status code
out, ex = run_tool("databricks",
                   params("databricks.execute_sql", statement="SELECT 1"), [
    err(429, body={"error_code": "REQUEST_LIMIT_EXCEEDED", "message": "Too many requests"},
        headers={"Retry-After": "5"}),
])
ok &= check("429: friendly error with status",
            "error" in out and "429" in out["error"] and "Traceback" not in str(out),
            str(out)[:250])

# non-JSON error body must not crash the error shaping
out, ex = run_tool("databricks", params("databricks.list_jobs"), [
    err(503, body="<html>Service Unavailable</html>"),
])
ok &= check("503 html body: still friendly error",
            "error" in out and "503" in out["error"], str(out)[:250])

# ---------------------------------------------------------------- 12. security: path-ish statement_id is percent-encoded
out, ex = run_tool("databricks",
                   params("databricks.get_statement", statement_id="abc/../def?x=1"), [
    resp(200, body={"statement_id": "abc/../def?x=1", "status": {"state": "SUCCEEDED"},
                    "manifest": {"schema": {"columns": []}}, "result": {"data_array": []}}),
])
ok &= check("security: statement_id percent-encoded in URL (no path escape)",
            ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.0/sql/statements/"
            "abc%2F..%2Fdef%3Fx%3D1", ex[0].url)

out, ex = run_tool("databricks",
                   params("databricks.cancel_statement", statement_id="../jobs/run-now"), [
    resp(200, body={}),
])
ok &= check("security: cancel statement_id percent-encoded",
            ex[0].url == "https://adb-123.4.azuredatabricks.net/api/2.0/sql/statements/"
            "..%2Fjobs%2Frun-now/cancel", ex[0].url)

# ---------------------------------------------------------------- 13. guardrails: missing credentials / unknown tool
out, ex = run_tool("databricks", {"tool": "databricks.list_warehouses",
                                  "baseUrl": BASE["baseUrl"], "apiToken": ""}, [])
ok &= check("missing creds: friendly error, zero requests",
            "error" in out and "credential" in out["error"].lower() and len(ex) == 0,
            str(out)[:250])

out, ex = run_tool("databricks", params("databricks.does_not_exist"), [])
ok &= check("unknown tool: friendly error",
            out.get("error") == "Unknown tool: databricks.does_not_exist", str(out)[:200])

out, ex = run_tool("databricks", params("databricks.execute_sql"), [])
ok &= check("execute_sql: missing statement rejected, no request",
            out.get("error") == "statement required" and len(ex) == 0, str(out)[:200])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
