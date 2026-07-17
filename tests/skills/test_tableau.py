"""Offline mock-HTTP integration tests for the tableau skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://tableau.example.com"
SITE = "70b2a1b8-9e99-4b52-bc4d-a2a3c4f2d1aa"
TOKEN = "session-token-XYZ"
SECRET = "pat-secret-SHOULD-NEVER-LEAK"


def creds(**extra):
    p = {"baseUrl": BASE, "siteContentUrl": "mysite",
         "patName": "sophon-bot", "patSecret": SECRET}
    p.update(extra)
    return p


def signin_ok():
    return resp(200, body={"credentials": {
        "token": TOKEN,
        "site": {"id": SITE, "contentUrl": "mysite"},
        "user": {"id": "u-1"},
    }})


SIGNIN_URL = f"{BASE}/api/3.23/auth/signin"
SITE_BASE = f"{BASE}/api/3.23/sites/{SITE}"

ok = True

# ---------------------------------------------------------------------------
# 1. Auth exactness — PAT signin exchange + X-Tableau-Auth on the data call
# ---------------------------------------------------------------------------
print("scenario: signin exchange byte-exact + list_workbooks happy path")
out, ex = run_tool("tableau", creds(tool="tableau.list_workbooks"), [
    signin_ok(),
    resp(200, body={"pagination": {"totalAvailable": "2"}, "workbooks": {"workbook": [
        {"id": "wb1", "name": "Sales Overview", "contentUrl": "SalesOverview",
         "webpageUrl": "https://tableau.example.com/#/site/mysite/workbooks/1",
         "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-07-01T10:00:00Z",
         "size": "4", "project": {"id": "p1", "name": "Finance"},
         "owner": {"id": "u9", "name": "Ann Lee"},
         "tags": {"tag": [{"label": "kpi"}]}},
        {"id": "wb2", "name": "Ops", "project": {"id": "p2", "name": "Operations"},
         "owner": {"id": "u2"}},
    ]}}),
])
ok &= check("two requests (signin then workbooks)", len(ex) == 2, repr(ex))
ok &= check("signin URL byte-exact", ex[0].url == SIGNIN_URL, ex[0].url)
ok &= check("signin method POST", ex[0].method == "POST", ex[0].method)
ok &= check("signin Content-Type json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("signin Accept json",
            ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("signin User-Agent", ex[0].headers.get("user-agent") == "sophon-tableau-skill",
            str(ex[0].headers))
ok &= check("signin body byte-exact (PAT name/secret/site contentUrl)",
            ex[0].body == json.dumps({"credentials": {
                "personalAccessTokenName": "sophon-bot",
                "personalAccessTokenSecret": SECRET,
                "site": {"contentUrl": "mysite"}}}),
            str(ex[0].body))
ok &= check("workbooks URL byte-exact (site id threaded, pageSize clamped default)",
            ex[1].url == f"{SITE_BASE}/workbooks?pageSize=25", ex[1].url)
ok &= check("X-Tableau-Auth header carries session token",
            ex[1].headers.get("x-tableau-auth") == TOKEN, str(ex[1].headers))
ok &= check("no Authorization/Bearer header used",
            "authorization" not in ex[1].headers, str(ex[1].headers))
ok &= check("data call Accept json", ex[1].headers.get("accept") == "application/json",
            str(ex[1].headers))
ok &= check("data call User-Agent", ex[1].headers.get("user-agent") == "sophon-tableau-skill",
            str(ex[1].headers))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
wb = out["workbooks"][0]
ok &= check("workbook shaped (nested project/owner flattened)",
            wb == {"id": "wb1", "name": "Sales Overview", "project": "Finance",
                   "owner": "Ann Lee", "updatedAt": "2026-07-01T10:00:00Z",
                   "webpageUrl": "https://tableau.example.com/#/site/mysite/workbooks/1"},
            str(wb))
ok &= check("raw fields absent (size/tags/contentUrl/createdAt)",
            all(k not in wb for k in ("size", "tags", "contentUrl", "createdAt")), str(wb))
ok &= check("missing owner.name tolerated", out["workbooks"][1]["owner"] is None,
            str(out["workbooks"][1]))
ok &= check("PAT secret not echoed in output", SECRET not in json.dumps(out))

print("scenario: limit clamped to 100")
out, ex = run_tool("tableau", creds(tool="tableau.list_workbooks", limit=5000), [
    signin_ok(),
    resp(200, body={"workbooks": {"workbook": []}}),
])
ok &= check("pageSize capped at 100", ex[1].url == f"{SITE_BASE}/workbooks?pageSize=100",
            ex[1].url)
ok &= check("empty result count 0", out == {"count": 0, "workbooks": []}, str(out))

print("scenario: empty siteContentUrl (Server default site) sent as \"\"")
out, ex = run_tool("tableau", creds(tool="tableau.list_workbooks", siteContentUrl=""), [
    signin_ok(),
    resp(200, body={"workbooks": {"workbook": []}}),
])
ok &= check("signin body has contentUrl \"\"",
            json.loads(ex[0].body)["credentials"]["site"] == {"contentUrl": ""}, ex[0].body)

print("scenario: siteContentUrl key entirely absent -> contentUrl \"\" in signin body")
no_site = {"baseUrl": BASE, "patName": "sophon-bot", "patSecret": SECRET,
           "tool": "tableau.list_workbooks"}
out, ex = run_tool("tableau", no_site, [
    signin_ok(),
    resp(200, body={"workbooks": {"workbook": []}}),
])
ok &= check("absent siteContentUrl still sends contentUrl \"\"",
            json.loads(ex[0].body)["credentials"]["site"] == {"contentUrl": ""}, ex[0].body)

# ---------------------------------------------------------------------------
# 2. tableau.list_views — site-wide and per-workbook
# ---------------------------------------------------------------------------
print("scenario: list_views site-wide")
out, ex = run_tool("tableau", creds(tool="tableau.list_views"), [
    signin_ok(),
    resp(200, body={"views": {"view": [
        {"id": "v1", "name": "Overview", "contentUrl": "Sales/sheets/Overview",
         "createdAt": "2026-01-01T00:00:00Z", "viewUrlName": "Overview",
         "workbook": {"id": "wb1"}, "owner": {"id": "u9"},
         "usage": {"totalViewCount": "42"}},
    ]}}),
])
ok &= check("views URL byte-exact", ex[1].url == f"{SITE_BASE}/views?pageSize=25", ex[1].url)
ok &= check("view shaped (workbook.id flattened to workbookId)",
            out == {"count": 1, "views": [{"id": "v1", "name": "Overview",
                                           "contentUrl": "Sales/sheets/Overview",
                                           "workbookId": "wb1"}]},
            str(out))

print("scenario: list_views scoped to a workbook")
out, ex = run_tool("tableau", creds(tool="tableau.list_views", workbookId="wb1", limit=10), [
    signin_ok(),
    resp(200, body={"views": {"view": [{"id": "v2", "name": "Detail",
                                        "contentUrl": "c", "workbook": {"id": "wb1"}}]}}),
])
ok &= check("workbook-scoped URL byte-exact",
            ex[1].url == f"{SITE_BASE}/workbooks/wb1/views?pageSize=10", ex[1].url)
ok &= check("count == 1", out.get("count") == 1, str(out))

# ---------------------------------------------------------------------------
# 3. tableau.list_datasources — happy path
# ---------------------------------------------------------------------------
print("scenario: list_datasources happy path")
out, ex = run_tool("tableau", creds(tool="tableau.list_datasources"), [
    signin_ok(),
    resp(200, body={"datasources": {"datasource": [
        {"id": "ds1", "name": "Orders", "type": "postgres",
         "createdAt": "2025-01-01T00:00:00Z", "updatedAt": "2026-07-10T00:00:00Z",
         "isCertified": True, "contentUrl": "Orders",
         "project": {"id": "p1", "name": "Finance"}, "owner": {"id": "u9"}},
    ]}}),
])
ok &= check("datasources URL byte-exact",
            ex[1].url == f"{SITE_BASE}/datasources?pageSize=25", ex[1].url)
ok &= check("datasource shaped",
            out == {"count": 1, "datasources": [{"id": "ds1", "name": "Orders",
                                                 "type": "postgres", "project": "Finance",
                                                 "updatedAt": "2026-07-10T00:00:00Z"}]},
            str(out))

# ---------------------------------------------------------------------------
# 4. tableau.get_view_data — CSV parsed into columns/rows with cap
# ---------------------------------------------------------------------------
print("scenario: get_view_data parses CSV")
csv_body = 'Category,Sales\nFurniture,"1,200.50"\nTechnology,3400\n'
out, ex = run_tool("tableau", creds(tool="tableau.get_view_data", viewId="v1"), [
    signin_ok(),
    resp(200, body=csv_body),
])
ok &= check("view data URL byte-exact", ex[1].url == f"{SITE_BASE}/views/v1/data", ex[1].url)
ok &= check("Accept text/csv on data call", ex[1].headers.get("accept") == "text/csv",
            str(ex[1].headers))
ok &= check("columns parsed", out.get("columns") == ["Category", "Sales"], str(out)[:200])
ok &= check("rows parsed as objects (quoted comma intact)",
            out.get("rows") == [{"Category": "Furniture", "Sales": "1,200.50"},
                                {"Category": "Technology", "Sales": "3400"}],
            str(out)[:300])
ok &= check("count == 2 and not truncated",
            out.get("count") == 2 and out.get("truncated") is False, str(out)[:200])

print("scenario: get_view_data row cap sets truncated flag")
out, ex = run_tool("tableau", creds(tool="tableau.get_view_data", viewId="v1", maxRows=1), [
    signin_ok(),
    resp(200, body=csv_body),
])
ok &= check("capped at 1 row", out.get("count") == 1 and len(out["rows"]) == 1, str(out)[:200])
ok &= check("truncated flag set", out.get("truncated") is True, str(out)[:200])

print("scenario: get_view_data empty CSV tolerated")
out, ex = run_tool("tableau", creds(tool="tableau.get_view_data", viewId="v1"), [
    signin_ok(),
    resp(200, body=""),
])
ok &= check("empty CSV -> empty shape",
            out == {"columns": [], "count": 0, "rows": [], "truncated": False}, str(out))

# ---------------------------------------------------------------------------
# 5. tableau.search_content — three unfiltered page fetches, client-side match
# ---------------------------------------------------------------------------
print("scenario: search_content merges workbooks/views/datasources")
out, ex = run_tool("tableau", creds(tool="tableau.search_content", query="Sales Report"), [
    signin_ok(),
    resp(200, body={"workbooks": {"workbook": [
        {"id": "wb1", "name": "Sales Report", "project": {"name": "Finance"},
         "owner": {"name": "Ann"}, "updatedAt": "2026-07-01T00:00:00Z",
         "webpageUrl": "http://x"},
        {"id": "wb2", "name": "Ops Monitor", "project": {"name": "Operations"}}]}}),
    resp(200, body={"views": {"view": [
        {"id": "v1", "name": "Quarterly SALES REPORT Detail", "contentUrl": "c",
         "workbook": {"id": "wb1"}},
        {"id": "v2", "name": "Unrelated", "contentUrl": "d",
         "workbook": {"id": "wb2"}}]}}),
    resp(200, body={"datasources": {"datasource": []}}),
])
ok &= check("four requests (signin + 3 pages)", len(ex) == 4, repr(ex))
ok &= check("workbooks page URL byte-exact (no server-side filter, full page)",
            ex[1].url == f"{SITE_BASE}/workbooks?pageSize=100", ex[1].url)
ok &= check("views page URL byte-exact",
            ex[2].url == f"{SITE_BASE}/views?pageSize=100", ex[2].url)
ok &= check("datasources page URL byte-exact",
            ex[3].url == f"{SITE_BASE}/datasources?pageSize=100", ex[3].url)
ok &= check("all three authed with session token",
            all(e.headers.get("x-tableau-auth") == TOKEN for e in ex[1:]), repr(ex[1:]))
ok &= check("merged result keys",
            set(out.keys()) == {"workbooks", "views", "datasources"}, str(out)[:200])
ok &= check("non-matching names filtered out client-side",
            [w["id"] for w in out["workbooks"]] == ["wb1"]
            and [v["id"] for v in out["views"]] == ["v1"], str(out)[:300])
ok &= check("match is case-insensitive substring",
            out["views"][0]["name"] == "Quarterly SALES REPORT Detail", str(out)[:300])
ok &= check("merged shaped entries",
            out["workbooks"][0]["project"] == "Finance"
            and out["views"][0]["workbookId"] == "wb1" and out["datasources"] == [],
            str(out)[:300])

print("scenario: filter-syntax query is inert (no filter param, plain substring match)")
out, ex = run_tool("tableau",
                   creds(tool="tableau.search_content", query="x,ownerName:eq:admin"), [
    signin_ok(),
    resp(200, body={"workbooks": {"workbook": [
        {"id": "wb1", "name": "x,ownerName:eq:admin dashboard"},
        {"id": "wb2", "name": "Sales"}]}}),
    resp(200, body={"views": {"view": []}}),
    resp(200, body={"datasources": {"datasource": []}}),
])
ok &= check("no filter query parameter in any URL",
            all("filter" not in e.url for e in ex[1:]), repr(ex[1:]))
ok &= check("comma-bearing query matched literally, not parsed as filter expressions",
            [w["id"] for w in out["workbooks"]] == ["wb1"], str(out)[:300])

# ---------------------------------------------------------------------------
# 6. tableau.list_jobs — refresh-failure triage shape
# ---------------------------------------------------------------------------
print("scenario: list_jobs happy path")
out, ex = run_tool("tableau", creds(tool="tableau.list_jobs", limit=50), [
    signin_ok(),
    resp(200, body={"backgroundJobs": {"backgroundJob": [
        {"id": "j1", "jobType": "refresh_extracts", "status": "Failed",
         "createdAt": "2026-07-17T01:00:00Z", "startedAt": "2026-07-17T01:01:00Z",
         "endedAt": "2026-07-17T01:02:00Z", "priority": "50"},
        {"id": "j2", "jobType": "subscription_notify", "status": "Success",
         "createdAt": "2026-07-17T02:00:00Z"},
    ]}}),
])
ok &= check("jobs URL byte-exact", ex[1].url == f"{SITE_BASE}/jobs?pageSize=50", ex[1].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("job shaped (id/type/status/createdAt)",
            out["jobs"][0] == {"id": "j1", "type": "refresh_extracts", "status": "Failed",
                               "createdAt": "2026-07-17T01:00:00Z"},
            str(out["jobs"][0]))
ok &= check("raw startedAt/priority absent",
            "startedAt" not in out["jobs"][0] and "priority" not in out["jobs"][0],
            str(out["jobs"][0]))

# ---------------------------------------------------------------------------
# 7. WRITE PATH — refresh_datasource POSTs empty JSON body
# ---------------------------------------------------------------------------
print("scenario: refresh_datasource write path")
out, ex = run_tool("tableau", creds(tool="tableau.refresh_datasource", datasourceId="ds1"), [
    signin_ok(),
    resp(202, body={"job": {"id": "j9", "mode": "Asynchronous", "type": "RefreshExtract",
                            "createdAt": "2026-07-17T03:00:00Z"}}),
])
ok &= check("method POST", ex[1].method == "POST", ex[1].method)
ok &= check("refresh URL byte-exact",
            ex[1].url == f"{SITE_BASE}/datasources/ds1/refresh", ex[1].url)
ok &= check("body is exactly {} (empty JSON object)", ex[1].body == "{}", str(ex[1].body))
ok &= check("Content-Type json on write",
            ex[1].headers.get("content-type") == "application/json", str(ex[1].headers))
ok &= check("session token on write", ex[1].headers.get("x-tableau-auth") == TOKEN)
ok &= check("success output includes job id and full-refresh flag",
            out == {"refreshRequested": True, "refreshType": "full", "datasourceId": "ds1",
                    "jobId": "j9", "jobType": "RefreshExtract"},
            str(out))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 on signin surfaces friendly error")
out, ex = run_tool("tableau", creds(tool="tableau.list_workbooks"), [
    err(401, body={"error": {"summary": "Signin Error",
                             "detail": "Error signing in to Tableau Server: "
                                       "personal access token is invalid.",
                             "code": "401001"}}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API summary and detail",
            "Signin Error" in out["error"] and "token is invalid" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("PAT secret not leaked in error output", SECRET not in raw, raw[:300])

print("scenario: 401 on the data call (expired session token)")
out, ex = run_tool("tableau", creds(tool="tableau.list_views"), [
    signin_ok(),
    err(401, body={"error": {"summary": "Unauthorized Access",
                             "detail": "Invalid authentication credentials were provided.",
                             "code": "401002"}}),
])
ok &= check("data-call 401 friendly",
            "401" in out.get("error", "") and "Unauthorized Access" in out["error"],
            str(out)[:300])

print("scenario: 429 includes Retry-After")
out, ex = run_tool("tableau", creds(tool="tableau.list_datasources"), [
    signin_ok(),
    err(429, body={"error": {"summary": "Too Many Requests",
                             "detail": "Request limit exceeded.", "code": "429000"}},
        headers={"Retry-After": "42"}),
])
ok &= check("429 surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After included", "42" in out["error"], out.get("error", ""))
ok &= check("summary included", "Too Many Requests" in out["error"], out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("tableau", creds(tool="tableau.list_workbooks"), [
    signin_ok(),
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: signin response missing token -> friendly error")
out, ex = run_tool("tableau", creds(tool="tableau.list_workbooks"), [
    resp(200, body={"credentials": {"site": {"id": SITE}}}),
])
ok &= check("missing token error",
            "error" in out and "token" in out["error"].lower()
            and "Traceback" not in json.dumps(out), str(out))

print("scenario: missing required params -> friendly error, no HTTP call")
out, ex = run_tool("tableau", creds(tool="tableau.get_view_data"), [])
ok &= check("viewId required error", out.get("error") == "viewId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("tableau", creds(tool="tableau.refresh_datasource"), [])
ok &= check("datasourceId required error", out.get("error") == "datasourceId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("tableau", creds(tool="tableau.search_content"), [])
ok &= check("query required error", out.get("error") == "query required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> connect-first error, no HTTP call")
out, ex = run_tool("tableau", {"tool": "tableau.list_workbooks", "baseUrl": "",
                               "patName": "", "patSecret": ""}, [])
ok &= check("connect-first message",
            "error" in out and "connect the tableau integration" in out["error"].lower(),
            str(out))
ok &= check("message names the fields",
            all(f in out["error"] for f in ("baseUrl", "patName", "patSecret")), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("tableau", creds(tool="tableau.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: tableau.nope", str(out))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal viewId is percent-encoded")
evil = "abc/../def?x=1"
out, ex = run_tool("tableau", creds(tool="tableau.get_view_data", viewId=evil), [
    signin_ok(),
    resp(200, body="A\n1\n"),
])
ok &= check("id fully quoted in URL (no path escape)",
            ex[1].url == f"{SITE_BASE}/views/abc%2F..%2Fdef%3Fx%3D1/data", ex[1].url)
ok &= check("no raw '../' or '?' in URL", "../" not in ex[1].url and "?" not in ex[1].url,
            ex[1].url)

print("scenario: bare '..' segment rejected before any HTTP call")
out, ex = run_tool("tableau", creds(tool="tableau.refresh_datasource", datasourceId=".."), [])
ok &= check("dot-dot datasourceId rejected",
            "error" in out and "datasourceId" in out["error"], str(out))
ok &= check("no HTTP request made (not even signin)", len(ex) == 0, repr(ex))
out, ex = run_tool("tableau", creds(tool="tableau.list_views", workbookId="."), [])
ok &= check("dot workbookId rejected", "error" in out and "workbookId" in out["error"],
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: workbookId percent-encoded on scoped list_views")
out, ex = run_tool("tableau", creds(tool="tableau.list_views", workbookId="a/b c"), [
    signin_ok(),
    resp(200, body={"views": {"view": []}}),
])
ok &= check("workbookId quoted",
            ex[1].url == f"{SITE_BASE}/workbooks/a%2Fb%20c/views?pageSize=25", ex[1].url)

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("tableau", creds(tool="tableau.list_jobs"), [
    signin_ok(),
    err(403, body={"error": {"summary": "Forbidden", "detail": "No permission.",
                             "code": "403000"}}),
])
ok &= check("patSecret absent from error output", SECRET not in json.dumps(out),
            json.dumps(out)[:300])
ok &= check("session token absent from error output", TOKEN not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
