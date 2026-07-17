"""Offline mock-HTTP integration tests for the clickhouse skill."""
import base64
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://ch.example.com:8443"
USER = "sophon"
PW = "pw-SECRET-VALUE"
BASIC = "Basic " + base64.b64encode(f"{USER}:{PW}".encode()).decode()


def creds(**extra):
    p = {"baseUrl": BASE, "username": USER, "password": PW}
    p.update(extra)
    return p


def envelope(meta, data):
    return {"meta": meta, "data": data, "rows": len(data),
            "statistics": {"elapsed": 0.001, "rows_read": len(data), "bytes_read": 100}}


ok = True

# ---------------------------------------------------------------------------
# 1. clickhouse.ping — happy path + Basic auth exactness
# ---------------------------------------------------------------------------
print("scenario: ping happy path / Basic auth exactness")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.ping"), [
    resp(200, body=envelope([{"name": "version()", "type": "String"}],
                            [{"version()": "24.3.1.100"}])),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (query + readonly=1)",
            ex[0].url == f"{BASE}/?query=SELECT+version%28%29+FORMAT+JSON&readonly=1", ex[0].url)
ok &= check("Authorization is exactly 'Basic base64(user:pass)'",
            ex[0].headers.get("authorization") == BASIC, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("User-Agent", ex[0].headers.get("user-agent") == "sophon-clickhouse-skill",
            str(ex[0].headers))
ok &= check("no request body on GET", ex[0].body is None, str(ex[0].body))
ok &= check("output shaped", out == {"ok": True, "version": "24.3.1.100"}, str(out))
ok &= check("password not echoed", PW not in json.dumps(out))

# ---------------------------------------------------------------------------
# 2. clickhouse.query — happy path, LIMIT handling, readonly=1 enforcement
# ---------------------------------------------------------------------------
print("scenario: query happy path (LIMIT appended, columns from meta)")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.query",
                                       sql="SELECT id, name FROM events"), [
    resp(200, body=envelope(
        [{"name": "id", "type": "UInt32"}, {"name": "name", "type": "String"}],
        [{"id": 1, "name": "signup"}, {"id": 2, "name": "login"}])),
])
ok &= check("URL byte-exact (LIMIT 100 appended on new line, readonly=1)",
            ex[0].url == f"{BASE}/?query=SELECT+id%2C+name+FROM+events%0ALIMIT+100"
                         f"+FORMAT+JSON&readonly=1", ex[0].url)
ok &= check("readonly=1 present (load-bearing)", "readonly=1" in ex[0].url, ex[0].url)
ok &= check("columns from meta",
            out.get("columns") == [{"name": "id", "type": "UInt32"},
                                   {"name": "name", "type": "String"}], str(out)[:300])
ok &= check("rows + count", out.get("count") == 2 and out["rows"][1]["name"] == "login",
            str(out)[:300])
ok &= check("raw envelope keys absent (meta/statistics)",
            "meta" not in out and "statistics" not in out, str(out)[:300])
ok &= check("no truncated flag when under cap", "truncated" not in out, str(out)[:300])

print("scenario: query keeps existing LIMIT and truncates over-delivery")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.query",
                                       sql="SELECT x FROM t LIMIT 10;", limit=2), [
    resp(200, body=envelope([{"name": "x", "type": "UInt8"}],
                            [{"x": 1}, {"x": 2}, {"x": 3}])),
])
ok &= check("no extra LIMIT appended (existing kept, trailing ; stripped)",
            ex[0].url == f"{BASE}/?query=SELECT+x+FROM+t+LIMIT+10+FORMAT+JSON&readonly=1",
            ex[0].url)
ok &= check("rows truncated to limit", out.get("count") == 2 and len(out["rows"]) == 2,
            str(out)[:200])
ok &= check("truncated flag set", out.get("truncated") is True, str(out)[:200])

print("scenario: query ending in a -- line comment still gets an effective LIMIT")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.query",
                                       sql="SELECT x FROM t -- latest"), [
    resp(200, body=envelope([{"name": "x", "type": "UInt8"}], [{"x": 1}])),
])
ok &= check("LIMIT appended on a new line, not swallowed by the trailing comment",
            ex[0].url == f"{BASE}/?query=SELECT+x+FROM+t+--+latest%0ALIMIT+100"
                         f"+FORMAT+JSON&readonly=1", ex[0].url)
ok &= check("rows returned", out.get("count") == 1, str(out)[:200])

print("scenario: query rejects a FORMAT clause (no HTTP)")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.query", sql="SELECT 1 FORMAT CSV"), [])
ok &= check("FORMAT clause rejected", "error" in out and "FORMAT" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: server rejects write statement via readonly=1")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.query", sql="DROP TABLE web.hits"), [
    err(500, body="Code: 164. DB::Exception: sophon: Cannot execute query in readonly mode."),
])
ok &= check("readonly=1 was sent with the statement", "readonly=1" in ex[0].url, ex[0].url)
ok &= check("server rejection surfaced with status",
            "500" in out.get("error", "") and "readonly mode" in out.get("error", ""), str(out))

# ---------------------------------------------------------------------------
# 3. clickhouse.list_databases — happy path
# ---------------------------------------------------------------------------
print("scenario: list_databases happy path")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.list_databases"), [
    resp(200, body=envelope([{"name": "name", "type": "String"}],
                            [{"name": "default"}, {"name": "system"}, {"name": "web"}])),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/?query=SELECT+name+FROM+system.databases+ORDER+BY+name"
                         f"+FORMAT+JSON&readonly=1", ex[0].url)
ok &= check("Basic auth on read", ex[0].headers.get("authorization") == BASIC)
ok &= check("shaped to flat name list",
            out == {"count": 3, "databases": ["default", "system", "web"]}, str(out))

# ---------------------------------------------------------------------------
# 4. clickhouse.list_tables — param_ binding + UInt64-string coercion
# ---------------------------------------------------------------------------
print("scenario: list_tables uses {db:String} + param_db binding")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.list_tables", database="web"), [
    resp(200, body=envelope(
        [{"name": "name", "type": "String"}, {"name": "engine", "type": "String"},
         {"name": "total_rows", "type": "Nullable(UInt64)"},
         {"name": "total_bytes", "type": "Nullable(UInt64)"}],
        [{"name": "hits", "engine": "MergeTree", "total_rows": "12345",
          "total_bytes": "678901"},
         {"name": "visits", "engine": "MergeTree", "total_rows": None,
          "total_bytes": None}])),
])
ok &= check("URL byte-exact (placeholder in SQL, value in param_db)",
            ex[0].url == f"{BASE}/?query=SELECT+name%2C+engine%2C+total_rows%2C+total_bytes"
                         f"+FROM+system.tables+WHERE+database+%3D+%7Bdb%3AString%7D"
                         f"+ORDER+BY+name+FORMAT+JSON&database=web&param_db=web&readonly=1",
            ex[0].url)
ok &= check("count and database echoed", out.get("count") == 2 and out.get("database") == "web",
            str(out)[:200])
ok &= check("UInt64 strings coerced to ints",
            out["tables"][0] == {"name": "hits", "engine": "MergeTree",
                                 "totalRows": 12345, "totalBytes": 678901},
            str(out["tables"][0]))
ok &= check("null totals tolerated",
            out["tables"][1]["totalRows"] is None and out["tables"][1]["totalBytes"] is None,
            str(out["tables"][1]))

print("scenario: list_tables SQL-injection attempt stays inside param binding")
evil_db = "web' OR '1'='1"
out, ex = run_tool("clickhouse", creds(tool="clickhouse.list_tables", database=evil_db), [
    resp(200, body=envelope([], [])),
])
ok &= check("placeholder untouched in SQL", "%7Bdb%3AString%7D" in ex[0].url, ex[0].url)
ok &= check("evil value only as encoded param_db",
            "param_db=web%27+OR+%271%27%3D%271" in ex[0].url, ex[0].url)
ok &= check("no raw quote character in URL", "'" not in ex[0].url, ex[0].url)
ok &= check("empty result count 0", out.get("count") == 0, str(out))

print("scenario: connection default database propagates (database= and param_db=)")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.list_tables", database="analytics"), [
    resp(200, body=envelope([], [])),
])
ok &= check("database param and param_db both carry the default",
            "&database=analytics&" in ex[0].url + "&"
            and "param_db=analytics" in ex[0].url, ex[0].url)
ok &= check("database precedes param_db precedes readonly",
            ex[0].url.endswith("&database=analytics&param_db=analytics&readonly=1"), ex[0].url)

# ---------------------------------------------------------------------------
# 5. clickhouse.describe_table — identifier validation + shaping
# ---------------------------------------------------------------------------
print("scenario: describe_table happy path")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.describe_table",
                                       database="web", table="hits"), [
    resp(200, body=envelope(
        [{"name": "name", "type": "String"}, {"name": "type", "type": "String"}],
        [{"name": "id", "type": "UInt64", "default_type": "", "default_expression": "",
          "comment": "", "codec_expression": "", "ttl_expression": ""},
         {"name": "ts", "type": "DateTime", "default_type": "DEFAULT",
          "default_expression": "now()", "comment": "event time",
          "codec_expression": "", "ttl_expression": ""}])),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/?query=DESCRIBE+TABLE+web.hits+FORMAT+JSON"
                         f"&database=web&readonly=1",
            ex[0].url)
ok &= check("columns shaped, empties nulled",
            out["columns"][0] == {"name": "id", "type": "UInt64", "defaultType": None,
                                  "defaultExpression": None, "comment": None},
            str(out["columns"][0]))
ok &= check("default expression kept",
            out["columns"][1]["defaultExpression"] == "now()"
            and out["columns"][1]["comment"] == "event time", str(out["columns"][1]))
ok &= check("raw codec/ttl fields absent", "codec_expression" not in json.dumps(out), str(out)[:300])
ok &= check("count/database/table echoed",
            out.get("count") == 2 and out.get("database") == "web" and out.get("table") == "hits",
            str(out)[:200])

print("scenario: describe_table missing table -> friendly error, no HTTP")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.describe_table"), [])
ok &= check("table required error", out.get("error") == "table required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 6. clickhouse.table_stats — param binding + numeric coercion
# ---------------------------------------------------------------------------
print("scenario: table_stats happy path")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.table_stats",
                                       database="web", table="hits"), [
    resp(200, body=envelope(
        [{"name": "partition", "type": "String"}],
        [{"partition": "202606", "parts": "3", "rows": "1000",
          "compressed_bytes": "2048", "uncompressed_bytes": "8192"},
         {"partition": "202607", "parts": "1", "rows": "500",
          "compressed_bytes": "1024", "uncompressed_bytes": "4096"}])),
])
ok &= check("SQL sums from system.parts (prefix byte-exact)",
            ex[0].url.startswith(
                f"{BASE}/?query=SELECT+partition%2C+count%28%29+AS+parts%2C+sum%28rows%29+AS+rows"),
            ex[0].url)
ok &= check("both identifiers bound as typed params",
            "%7Bdb%3AString%7D" in ex[0].url and "%7Btable%3AString%7D" in ex[0].url
            and ex[0].url.endswith("&param_db=web&param_table=hits&readonly=1"), ex[0].url)
ok &= check("active-parts filter present", "AND+active+GROUP+BY+partition" in ex[0].url, ex[0].url)
ok &= check("partitions shaped with int sums",
            out["partitions"][0] == {"partition": "202606", "parts": 3, "rows": 1000,
                                     "compressedBytes": 2048, "uncompressedBytes": 8192},
            str(out["partitions"][0]))
ok &= check("totalRows summed across partitions", out.get("totalRows") == 1500, str(out)[:200])
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])

# ---------------------------------------------------------------------------
# 7. clickhouse.insert_rows — WRITE PATH (JSONEachRow body, no readonly)
# ---------------------------------------------------------------------------
print("scenario: insert_rows write path (POST body byte-exact)")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.insert_rows", database="web",
                                       table="hits",
                                       rows=[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]), [
    resp(200, body=""),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL is bare root (no query string, no readonly)",
            ex[0].url == f"{BASE}/", ex[0].url)
ok &= check("body byte-exact JSONEachRow",
            ex[0].body == 'INSERT INTO web.hits FORMAT JSONEachRow\n'
                          '{"id": 1, "name": "a"}\n{"id": 2, "name": "b"}', str(ex[0].body))
ok &= check("Basic auth on write", ex[0].headers.get("authorization") == BASIC)
ok &= check("text content type",
            (ex[0].headers.get("content-type") or "").startswith("text/plain"),
            str(ex[0].headers))
ok &= check("success output", out == {"inserted": 2, "database": "web", "table": "hits"},
            str(out))

print("scenario: insert_rows validates rows shape (no HTTP)")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.insert_rows", table="hits",
                                       rows="not-a-list"), [])
ok &= check("rows validation error",
            "rows must be a non-empty array" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("clickhouse", creds(tool="clickhouse.insert_rows", table="hits", rows=[]), [])
ok &= check("empty rows rejected", "rows must be a non-empty array" in out.get("error", ""),
            str(out))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error (plain-text ClickHouse body)")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.list_databases"), [
    err(401, body="Code: 516. DB::Exception: Authentication failed: password is incorrect, "
                  "or there is no user with such name."),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes server exception text", "Authentication failed" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("password not leaked in error output", PW not in raw, raw[:300])
ok &= check("base64 credential not leaked in error output",
            BASIC.split()[1] not in raw, raw[:300])

print("scenario: 429 includes Retry-After")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.ping"), [
    err(429, body="Too many simultaneous queries.", headers={"Retry-After": "30"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After included", "retry after 30s" in out["error"], out.get("error", ""))
ok &= check("body text included", "Too many simultaneous queries" in out["error"],
            out.get("error", ""))

print("scenario: JSON error body parsed for exception message")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.query", sql="SELECT bogus"), [
    err(400, body={"exception": "Code: 47. DB::Exception: Unknown identifier: bogus"}),
])
ok &= check("exception field extracted",
            "400" in out["error"] and "Unknown identifier: bogus" in out["error"]
            and "exception" not in out["error"], out.get("error", ""))

print("scenario: non-JSON success body -> friendly error")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.ping"), [
    resp(200, body="Ok.\n"),
])
ok &= check("non-JSON body handled without traceback",
            "error" in out and "non-JSON" in out["error"]
            and "Traceback" not in json.dumps(out), str(out))

print("scenario: missing credentials -> friendly error, no HTTP call")
out, ex = run_tool("clickhouse", {"tool": "clickhouse.list_databases",
                                  "baseUrl": "", "username": "", "password": ""}, [])
ok &= check("missing-credentials message names the fields",
            "connect the ClickHouse integration first" in out.get("error", "")
            and "baseUrl" in out["error"] and "username" in out["error"]
            and "password" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: clickhouse.nope", str(out))

print("scenario: empty sql -> friendly error, no HTTP")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.query", sql="  ;  "), [])
ok &= check("sql required error", out.get("error") == "sql required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES — identifier validation is the load-bearing control
# ---------------------------------------------------------------------------
print("scenario: path/SQL-injection table id rejected (identifier validation)")
evil = "abc/../def?x=1"
out, ex = run_tool("clickhouse", creds(tool="clickhouse.describe_table", table=evil), [])
ok &= check("evil table rejected with ValueError message",
            "Invalid table" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

out, ex = run_tool("clickhouse", creds(tool="clickhouse.table_stats",
                                       database="..", table="hits"), [])
ok &= check("dot-dot database rejected", "Invalid database" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: insert_rows identifier injection rejected before any HTTP")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.insert_rows",
                                       table="hits; DROP TABLE web.hits", rows=[{"id": 1}]), [])
ok &= check("injected table name rejected", "Invalid table" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

out, ex = run_tool("clickhouse", creds(tool="clickhouse.insert_rows",
                                       database="web`--", table="hits", rows=[{"id": 1}]), [])
ok &= check("injected database name rejected", "Invalid database" in out.get("error", ""),
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("clickhouse", creds(tool="clickhouse.list_tables", database="web"), [
    err(403, body="Code: 497. DB::Exception: sophon: Not enough privileges."),
])
ok &= check("password absent from error output", PW not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
