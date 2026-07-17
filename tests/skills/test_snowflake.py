"""Offline mock-HTTP integration tests for the Sophon "snowflake" skill.

Run: python test_snowflake.py  (exits 1 on any failure)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mockhttp import run_tool, resp, err, check  # noqa: E402

ACCOUNT = "https://acme-xy12345.snowflakecomputing.com"
PAT = "sekret-pat-value-12345"
BASE = {"accountUrl": ACCOUNT, "pat": PAT, "warehouse": "COMPUTE_WH"}

results = []


def ok(label, cond, detail=""):
    results.append(check(label, cond, detail))


def scenario(title):
    print(f"\n[{title}]")


# ---------------------------------------------------------------- S1: auth exactness
scenario("S1 auth exactness on a catalog GET (list_databases)")
out, ex = run_tool("snowflake", {**BASE, "tool": "snowflake.list_databases"},
                   [resp(200, body=[{
                       "name": "ANALYTICS", "owner": "SYSADMIN", "kind": "STANDARD",
                       "comment": "main db", "created_on": "2024-01-01T00:00:00Z",
                       "options": "", "retention_time": 1, "is_default": "N",
                       "is_current": "Y", "origin": "",
                   }])])
ok("exactly one request", len(ex) == 1, repr(ex))
ok("method GET", ex[0].method == "GET", ex[0].method)
ok("URL exact", ex[0].url == f"{ACCOUNT}/api/v2/databases?showLimit=25", ex[0].url)
ok("Authorization: Bearer {pat} byte-exact",
   ex[0].headers.get("authorization") == f"Bearer {PAT}", str(ex[0].headers))
ok("X-Snowflake-Authorization-Token-Type header byte-exact",
   ex[0].headers.get("x-snowflake-authorization-token-type") == "PROGRAMMATIC_ACCESS_TOKEN",
   str(ex[0].headers))
ok("Accept: application/json", ex[0].headers.get("accept") == "application/json")
ok("no body on GET", ex[0].body is None, repr(ex[0].body))

# ---------------------------------------------------------------- S2: list_databases shaping
scenario("S2 list_databases output shaping")
ok("count == 1", out.get("count") == 1, json.dumps(out))
db = (out.get("databases") or [{}])[0]
ok("trimmed fields present",
   db.get("name") == "ANALYTICS" and db.get("owner") == "SYSADMIN"
   and db.get("kind") == "STANDARD" and db.get("comment") == "main db"
   and db.get("created_on") == "2024-01-01T00:00:00Z", json.dumps(db))
ok("raw payload fields absent",
   "retention_time" not in db and "is_default" not in db and "options" not in db
   and "is_current" not in db, json.dumps(db))

# ---------------------------------------------------------------- S3: list_tables shaping + limit
scenario("S3 list_tables happy path (limit clamps list, showLimit in query)")
tables_body = [
    {"name": f"T{i}", "kind": "TABLE", "rows": i * 10, "bytes": i * 1024,
     "comment": None, "created_on": "2024-02-02", "database_name": "DB",
     "schema_name": "PUBLIC", "cluster_by": "", "automatic_clustering": False}
    for i in range(1, 4)
]
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.list_tables",
                    "database": "DB", "schema": "PUBLIC", "limit": 2},
                   [resp(200, body=tables_body)])
ok("URL exact", ex[0].url == f"{ACCOUNT}/api/v2/databases/DB/schemas/PUBLIC/tables?showLimit=2",
   ex[0].url)
ok("count trimmed to limit", out.get("count") == 2, json.dumps(out))
t = out["tables"][0]
ok("trimmed table fields present",
   t.get("name") == "T1" and t.get("kind") == "TABLE" and t.get("rows") == 10
   and t.get("bytes") == 1024, json.dumps(t))
ok("raw table fields absent",
   "cluster_by" not in t and "automatic_clustering" not in t and "database_name" not in t,
   json.dumps(t))

# ---------------------------------------------------------------- S4: list_warehouses shaping
scenario("S4 list_warehouses happy path")
out, ex = run_tool("snowflake", {**BASE, "tool": "snowflake.list_warehouses"},
                   [resp(200, body=[{
                       "name": "COMPUTE_WH", "state": "STARTED", "type": "STANDARD",
                       "size": "X-Small", "auto_suspend": 600, "auto_resume": "true",
                       "owner": "SYSADMIN", "comment": "",
                       "resource_monitor": "null", "queued": 0, "running": 1,
                   }])])
ok("URL exact", ex[0].url == f"{ACCOUNT}/api/v2/warehouses", ex[0].url)
ok("count == 1", out.get("count") == 1, json.dumps(out))
w = out["warehouses"][0]
ok("trimmed warehouse fields present",
   w.get("name") == "COMPUTE_WH" and w.get("state") == "STARTED"
   and w.get("size") == "X-Small" and w.get("auto_suspend") == 600, json.dumps(w))
ok("raw warehouse fields absent",
   "resource_monitor" not in w and "queued" not in w and "running" not in w, json.dumps(w))

# ---------------------------------------------------------------- S5: query write path (sync)
scenario("S5 snowflake.query sync — exact POST body, row mapping via rowType")
sql_body = {
    "statementHandle": "01aa-handle-1",
    "resultSetMetaData": {
        "numRows": 2,
        "rowType": [{"name": "ID", "type": "fixed", "scale": 0, "precision": 38},
                    {"name": "NAME", "type": "text", "length": 100}],
    },
    "data": [["1", "Alice"], ["2", "Bob"]],
    "message": "Statement executed successfully.",
}
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.query", "statement": "SELECT id, name FROM users"},
                   [resp(200, body=sql_body)])
ok("method POST", ex[0].method == "POST", ex[0].method)
ok("URL exact (no async flag on sync submit)",
   ex[0].url == f"{ACCOUNT}/api/v2/statements", ex[0].url)
ok("POST body exact: statement + timeout + warehouse only",
   ex[0].json == {"statement": "SELECT id, name FROM users", "timeout": 20,
                  "warehouse": "COMPUTE_WH"}, ex[0].body)
ok("Content-Type json on POST", ex[0].headers.get("content-type") == "application/json")
ok("auth headers on POST too",
   ex[0].headers.get("authorization") == f"Bearer {PAT}"
   and ex[0].headers.get("x-snowflake-authorization-token-type") == "PROGRAMMATIC_ACCESS_TOKEN")
ok("status complete + handle echoed",
   out.get("status") == "complete" and out.get("statementHandle") == "01aa-handle-1",
   json.dumps(out))
ok("columns from rowType (name/type only)",
   out.get("columns") == [{"name": "ID", "type": "fixed"}, {"name": "NAME", "type": "text"}],
   json.dumps(out.get("columns")))
ok("rows mapped to objects keyed by column name",
   out.get("rows") == [{"ID": "1", "NAME": "Alice"}, {"ID": "2", "NAME": "Bob"}],
   json.dumps(out.get("rows")))
ok("rowCount + not truncated", out.get("rowCount") == 2 and out.get("truncated") is False,
   json.dumps(out))

# ---------------------------------------------------------------- S6: query with contexts in body
scenario("S6 snowflake.query body carries database/schema/role when provided")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.query", "statement": "SELECT 1",
                    "database": "DB", "schema": "PUBLIC", "role": "ANALYST"},
                   [resp(200, body={"statementHandle": "h", "resultSetMetaData":
                                    {"rowType": [{"name": "1", "type": "fixed"}], "numRows": 1},
                                    "data": [["1"]]})])
ok("POST body includes contexts",
   ex[0].json == {"statement": "SELECT 1", "timeout": 20, "warehouse": "COMPUTE_WH",
                  "database": "DB", "schema": "PUBLIC", "role": "ANALYST"}, ex[0].body)

# ---------------------------------------------------------------- S7: query 202 => running, not error
scenario("S7 snowflake.query 202 response yields running + poll hint")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.query", "statement": "CALL long_proc()"},
                   [resp(202, body={"statementHandle": "01bb-handle-2",
                                    "message": "Asynchronous execution in progress."})])
ok("no error key", "error" not in out, json.dumps(out))
ok("statementHandle surfaced", out.get("statementHandle") == "01bb-handle-2", json.dumps(out))
ok("status running", out.get("status") == "running", json.dumps(out))
ok("poll hint mentions get_statement",
   "snowflake.get_statement" in (out.get("hint") or ""), json.dumps(out))

# ---------------------------------------------------------------- S8: async submit (timeout > 20)
scenario("S8 snowflake.query timeout>20 submits with ?async=true and keeps server timeout")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.query", "statement": "COPY INTO t", "timeout": 3600},
                   [resp(202, body={"statementHandle": "01cc-handle-3"})])
ok("URL has async=true", ex[0].url == f"{ACCOUNT}/api/v2/statements?async=true", ex[0].url)
ok("body keeps timeout 3600", ex[0].json.get("timeout") == 3600, ex[0].body)
ok("202 gives running + handle",
   out.get("status") == "running" and out.get("statementHandle") == "01cc-handle-3",
   json.dumps(out))

# ---------------------------------------------------------------- S9: get_statement stitches partitions
scenario("S9 get_statement stitches multiple partitions and maps rows")
first = {
    "statementHandle": "01dd-handle-4",
    "resultSetMetaData": {
        "numRows": 5,
        "partitionInfo": [{"rowCount": 2}, {"rowCount": 2}, {"rowCount": 1}],
        "rowType": [{"name": "REGION", "type": "text"}, {"name": "TOTAL", "type": "fixed"}],
    },
    "data": [["emea", "10"], ["apac", "20"]],
}
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.get_statement",
                    "statementHandle": "01dd-handle-4"},
                   [resp(200, body=first),
                    resp(200, body={"data": [["amer", "30"], ["latam", "40"]]}),
                    resp(200, body={"data": [["anz", "50"]]})])
ok("three requests made", len(ex) == 3, repr(ex))
ok("first URL exact", ex[0].url == f"{ACCOUNT}/api/v2/statements/01dd-handle-4", ex[0].url)
ok("partition 1 fetched", ex[1].url == f"{ACCOUNT}/api/v2/statements/01dd-handle-4?partition=1",
   ex[1].url)
ok("partition 2 fetched", ex[2].url == f"{ACCOUNT}/api/v2/statements/01dd-handle-4?partition=2",
   ex[2].url)
ok("all partitions stitched, mapped by rowType names",
   out.get("rows") == [{"REGION": "emea", "TOTAL": "10"}, {"REGION": "apac", "TOTAL": "20"},
                       {"REGION": "amer", "TOTAL": "30"}, {"REGION": "latam", "TOTAL": "40"},
                       {"REGION": "anz", "TOTAL": "50"}], json.dumps(out.get("rows")))
ok("rowCount 5, complete, not truncated",
   out.get("rowCount") == 5 and out.get("status") == "complete"
   and out.get("truncated") is False, json.dumps(out))

# ---------------------------------------------------------------- S10: get_statement still running
scenario("S10 get_statement 202 => still running, no partition fetches")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.get_statement", "statementHandle": "01ee-5"},
                   [resp(202, body={"statementHandle": "01ee-5",
                                    "message": "Statement is still running."})])
ok("single request only", len(ex) == 1, repr(ex))
ok("running with message",
   out.get("status") == "running" and out.get("statementHandle") == "01ee-5"
   and out.get("message") == "Statement is still running.", json.dumps(out))

# ---------------------------------------------------------------- S11: cancel_statement write path
scenario("S11 cancel_statement POSTs to /cancel")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.cancel_statement", "statementHandle": "01ff-6"},
                   [resp(200, body={"message": "Statement canceled."})])
ok("method POST", ex[0].method == "POST", ex[0].method)
ok("URL exact", ex[0].url == f"{ACCOUNT}/api/v2/statements/01ff-6/cancel", ex[0].url)
ok("output shape", out == {"statementHandle": "01ff-6", "canceled": True,
                           "message": "Statement canceled."}, json.dumps(out))

# ---------------------------------------------------------------- S12: describe_table happy path
scenario("S12 describe_table shapes columns from REST catalog")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.describe_table",
                    "database": "DB", "schema": "PUBLIC", "table": "ORDERS"},
                   [resp(200, body={
                       "name": "ORDERS", "database_name": "DB", "schema_name": "PUBLIC",
                       "kind": "TABLE", "rows": 42, "bytes": 4096, "comment": "orders",
                       "columns": [{"name": "ID", "datatype": "NUMBER(38,0)", "nullable": False,
                                    "default": None, "comment": None, "position": 1,
                                    "autoincrement": False}],
                   })])
ok("single GET, URL exact",
   len(ex) == 1 and ex[0].url == f"{ACCOUNT}/api/v2/databases/DB/schemas/PUBLIC/tables/ORDERS",
   repr(ex))
ok("table detail shaped",
   out.get("name") == "ORDERS" and out.get("database") == "DB" and out.get("schema") == "PUBLIC"
   and out.get("kind") == "TABLE" and out.get("rows") == 42, json.dumps(out))
col = out["columns"][0]
ok("column trimmed fields present",
   col.get("name") == "ID" and col.get("datatype") == "NUMBER(38,0)"
   and col.get("nullable") is False, json.dumps(col))
ok("raw column fields absent", "position" not in col and "autoincrement" not in col,
   json.dumps(col))

# ---------------------------------------------------------------- S13: describe_table DESCRIBE fallback
scenario("S13 describe_table falls back to DESCRIBE TABLE when catalog omits columns")
desc_body = {
    "statementHandle": "01gg-7",
    "resultSetMetaData": {
        "numRows": 1,
        "rowType": [{"name": "name", "type": "text"}, {"name": "type", "type": "text"},
                    {"name": "null?", "type": "text"}, {"name": "default", "type": "text"},
                    {"name": "comment", "type": "text"}],
    },
    "data": [["ID", "NUMBER(38,0)", "N", None, "pk"]],
}
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.describe_table",
                    "database": "DB", "schema": "PUBLIC", "table": "ORDERS"},
                   [resp(200, body={"name": "ORDERS", "database_name": "DB",
                                    "schema_name": "PUBLIC", "kind": "TABLE"}),
                    resp(200, body=desc_body)])
ok("second request is POST /api/v2/statements",
   ex[1].method == "POST" and ex[1].url == f"{ACCOUNT}/api/v2/statements", repr(ex))
ok("DESCRIBE statement uses catalog-echoed quoted names",
   ex[1].json.get("statement") == 'DESCRIBE TABLE "DB"."PUBLIC"."ORDERS"', ex[1].body)
ok("fallback columns mapped",
   out.get("columns") == [{"name": "ID", "datatype": "NUMBER(38,0)", "nullable": False,
                           "default": None, "comment": "pk"}], json.dumps(out.get("columns")))

# ---------------------------------------------------------------- S14: 401 friendly error, no secret leak
scenario("S14 401 surfaces friendly error; token never leaks; no traceback")
out, ex = run_tool("snowflake", {**BASE, "tool": "snowflake.list_databases"},
                   [err(401, body={"message": "Invalid programmatic access token.",
                                   "code": "390303"})])
printed = json.dumps(out)
ok("error key present", "error" in out, printed)
ok("includes HTTP status 401", "401" in out.get("error", ""), printed)
ok("includes API message", "Invalid programmatic access token." in out.get("error", ""), printed)
ok("no Python traceback", "Traceback" not in printed and "urllib" not in printed, printed)
ok("PAT not leaked in output", PAT not in printed, printed)

# ---------------------------------------------------------------- S15: 429 surfaces status
scenario("S15 429 on query surfaces friendly error with status")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.query", "statement": "SELECT 1"},
                   [err(429, body={"message": "Number of requests exceeded the limit."})])
ok("error includes 429 and message",
   "429" in out.get("error", "") and "Number of requests exceeded the limit." in out.get("error", ""),
   json.dumps(out))
ok("no traceback / PAT on 429", "Traceback" not in json.dumps(out) and PAT not in json.dumps(out),
   json.dumps(out))

# ---------------------------------------------------------------- S16: path-traversal id is percent-encoded
scenario("S16 path-ish statementHandle is percent-encoded (no path escape)")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.get_statement",
                    "statementHandle": "abc/../def?x=1"},
                   [resp(200, body={"statementHandle": "abc/../def?x=1",
                                    "resultSetMetaData": {"rowType": [], "numRows": 0},
                                    "data": []})])
ok("handle fully percent-encoded in URL",
   ex[0].url == f"{ACCOUNT}/api/v2/statements/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok("no raw slash or query chars from id in path",
   "abc/../def" not in ex[0].url and "?x=1" not in ex[0].url, ex[0].url)

scenario("S17 path-ish database/schema names percent-encoded in catalog URLs")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.list_schemas", "database": "my db/../x"},
                   [resp(200, body=[])])
ok("database segment encoded",
   ex[0].url == f"{ACCOUNT}/api/v2/databases/my%20db%2F..%2Fx/schemas?showLimit=25", ex[0].url)
ok("empty result count 0", out.get("count") == 0 and out.get("schemas") == [], json.dumps(out))

# ---------------------------------------------------------------- S18: duplicate column names suffixed
scenario("S18 duplicate column names get _2 suffix in mapped rows")
out, ex = run_tool("snowflake",
                   {**BASE, "tool": "snowflake.query",
                    "statement": "SELECT a.id, b.id FROM a JOIN b"},
                   [resp(200, body={"statementHandle": "01hh-8",
                                    "resultSetMetaData": {
                                        "numRows": 1,
                                        "rowType": [{"name": "ID", "type": "fixed"},
                                                    {"name": "ID", "type": "fixed"}]},
                                    "data": [["1", "9"]]})])
ok("duplicate columns disambiguated",
   out.get("rows") == [{"ID": "1", "ID_2": "9"}], json.dumps(out.get("rows")))

# ---------------------------------------------------------------- S19: validation errors, no HTTP
scenario("S19 parameter validation and credential guard (no HTTP calls)")
out, ex = run_tool("snowflake", {**BASE, "tool": "snowflake.query"}, [])
ok("missing statement => error, no request",
   out == {"error": "statement required"} and len(ex) == 0, json.dumps(out))
out, ex = run_tool("snowflake", {"tool": "snowflake.list_databases",
                                 "accountUrl": ACCOUNT, "pat": "", "warehouse": "WH"}, [])
ok("missing pat => credentials error, no request",
   "Missing Snowflake credentials" in out.get("error", "") and len(ex) == 0, json.dumps(out))
out, ex = run_tool("snowflake", {**BASE, "tool": "snowflake.nope"}, [])
ok("unknown tool => error", out == {"error": "Unknown tool: snowflake.nope"}, json.dumps(out))

# ----------------------------------------------------------------
print()
total = len(results)
passed = sum(1 for r in results if r)
print(f"{passed}/{total} checks passed")
if passed != total:
    sys.exit(1)
print("ALL GREEN")
