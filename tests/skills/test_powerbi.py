"""Offline mock-HTTP integration tests for the powerbi skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

ok = True

CREDS = {"tenantId": "tid-123", "clientId": "cid-456", "clientSecret": "s3cr3t-XYZ"}
TOKEN = resp(200, body={"access_token": "atok", "token_type": "Bearer", "expires_in": 3599})


def creds(**extra):
    p = dict(CREDS)
    p.update(extra)
    return p


# ---------------------------------------------------------------- 1. AUTH EXACTNESS
print("[auth exactness]")
out, ex = run_tool("powerbi", creds(tool="powerbi.list_workspaces"),
                   [TOKEN, resp(200, body={"value": []})])
ok &= check("two requests (token + api)", len(ex) == 2, repr(ex))
ok &= check("token POST method", ex[0].method == "POST", ex[0].method)
ok &= check("token endpoint url",
            ex[0].url == "https://login.microsoftonline.com/tid-123/oauth2/v2.0/token", ex[0].url)
ok &= check("token content-type form-urlencoded",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
expected_form = ("grant_type=client_credentials&client_id=cid-456&client_secret=s3cr3t-XYZ"
                 "&scope=https%3A%2F%2Fanalysis.windows.net%2Fpowerbi%2Fapi%2F.default")
ok &= check("token body byte-exact (incl. powerbi scope, NOT graph)",
            ex[0].body == expected_form, ex[0].body)
ok &= check("scope is powerbi .default",
            "analysis.windows.net%2Fpowerbi%2Fapi%2F.default" in ex[0].body
            and "graph" not in ex[0].body, ex[0].body)
ok &= check("api call uses Bearer token",
            ex[1].headers.get("authorization") == "Bearer atok", str(ex[1].headers))
ok &= check("api url is myorg groups",
            ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups", ex[1].url)
ok &= check("api GET has no body", ex[1].body is None, repr(ex[1].body))

# ---------------------------------------------------------------- 2. HAPPY PATHS
print("[happy: list_workspaces]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_workspaces"),
    [TOKEN,
     resp(200, body={"@odata.context": "ctx", "value": [
         {"id": "w1", "name": "Sales", "isReadOnly": False, "isOnDedicatedCapacity": True,
          "capacityId": "cap-1", "type": "Workspace"},
         {"id": "w2", "name": "Marketing", "isReadOnly": False,
          "isOnDedicatedCapacity": False, "type": "Workspace"}]})])
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("trimmed fields present",
            out["workspaces"][0] == {"id": "w1", "name": "Sales",
                                     "isOnDedicatedCapacity": True}, str(out)[:300])
ok &= check("raw fields absent (capacityId/type/isReadOnly)",
            all(k not in out["workspaces"][0] for k in ("capacityId", "type", "isReadOnly")),
            str(out)[:300])

print("[happy: list_datasets]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_datasets", workspaceId="ws-guid-1"),
    [TOKEN,
     resp(200, body={"value": [
         {"id": "d1", "name": "SalesModel", "webUrl": "https://app.powerbi.com/d1",
          "addRowsAPIEnabled": False, "configuredBy": "sp@corp.com",
          "isRefreshable": True, "isEffectiveIdentityRequired": False,
          "targetStorageMode": "Abf"}]})])
ok &= check("datasets url", ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/ws-guid-1/datasets",
            ex[1].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("dataset trimmed",
            out["datasets"][0] == {"id": "d1", "name": "SalesModel",
                                   "configuredBy": "sp@corp.com", "isRefreshable": True},
            str(out)[:300])
ok &= check("dataset raw fields absent",
            "webUrl" not in out["datasets"][0] and "targetStorageMode" not in out["datasets"][0],
            str(out)[:300])

print("[happy: list_reports]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_reports", workspaceId="ws-guid-1"),
    [TOKEN,
     resp(200, body={"value": [
         {"id": "r1", "reportType": "PowerBIReport", "name": "Q2 Sales",
          "webUrl": "https://app.powerbi.com/r1", "embedUrl": "https://embed/r1",
          "datasetId": "d1", "users": [], "subscriptions": []}]})])
ok &= check("reports url", ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/ws-guid-1/reports",
            ex[1].url)
ok &= check("report trimmed",
            out["reports"][0] == {"id": "r1", "name": "Q2 Sales",
                                  "webUrl": "https://app.powerbi.com/r1", "datasetId": "d1"},
            str(out)[:300])
ok &= check("report raw fields absent (embedUrl/users)",
            "embedUrl" not in out["reports"][0] and "users" not in out["reports"][0],
            str(out)[:300])

print("[happy: list_dashboards + tiles variant]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_dashboards", workspaceId="ws-guid-1"),
    [TOKEN,
     resp(200, body={"value": [
         {"id": "db1", "displayName": "Exec Board", "isReadOnly": False,
          "embedUrl": "https://embed/db1"}]})])
ok &= check("dashboard trimmed",
            out["dashboards"][0] == {"id": "db1", "displayName": "Exec Board"}, str(out)[:300])
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_dashboards", workspaceId="ws-guid-1", dashboardId="db1"),
    [TOKEN,
     resp(200, body={"value": [
         {"id": "t1", "title": "Revenue", "rowSpan": 2, "colSpan": 2,
          "embedUrl": "https://embed/t1", "reportId": "r1", "datasetId": "d1"}]})])
ok &= check("tiles url", ex[1].url ==
            "https://api.powerbi.com/v1.0/myorg/groups/ws-guid-1/dashboards/db1/tiles", ex[1].url)
ok &= check("tile trimmed",
            out["tiles"][0] == {"id": "t1", "title": "Revenue", "reportId": "r1",
                                "datasetId": "d1"}, str(out)[:300])
ok &= check("tiles output has dashboardId + count",
            out.get("dashboardId") == "db1" and out.get("count") == 1, str(out)[:200])

print("[happy: get_refresh_history]")
long_exc = "X" * 900
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.get_refresh_history", workspaceId="ws-guid-1",
                     datasetId="ds-guid-1", limit=5),
    [TOKEN,
     resp(200, body={"value": [
         {"refreshType": "ViaApi", "startTime": "2026-07-16T01:00:00Z",
          "endTime": "2026-07-16T01:05:00Z", "status": "Completed", "requestId": "req-1"},
         {"refreshType": "Scheduled", "startTime": "2026-07-15T01:00:00Z",
          "endTime": "2026-07-15T01:02:00Z", "status": "Failed",
          "serviceExceptionJson": long_exc, "requestId": "req-2"}]})])
ok &= check("refreshes url with $top",
            ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/ws-guid-1/datasets/ds-guid-1/refreshes?%24top=5",
            ex[1].url)
ok &= check("refresh trimmed",
            out["refreshes"][0] == {"status": "Completed", "startTime": "2026-07-16T01:00:00Z",
                                    "endTime": "2026-07-16T01:05:00Z",
                                    "serviceExceptionJson": None}, str(out)[:400])
ok &= check("long serviceExceptionJson truncated to 500 + marker",
            out["refreshes"][1]["serviceExceptionJson"] == "X" * 500 + "... (truncated)",
            str(out["refreshes"][1])[:200])
ok &= check("refresh raw fields absent (requestId/refreshType)",
            "requestId" not in out["refreshes"][0] and "refreshType" not in out["refreshes"][0],
            str(out)[:300])

# ---------------------------------------------------------------- 3. WRITE PATHS
print("[write: refresh_dataset]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.refresh_dataset", workspaceId="ws-guid-1",
                     datasetId="ds-guid-1"),
    [TOKEN, resp(202, body=None)])
ok &= check("refresh POST method", ex[1].method == "POST", ex[1].method)
ok &= check("refresh url",
            ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/ws-guid-1/datasets/ds-guid-1/refreshes",
            ex[1].url)
ok &= check("refresh body is EMPTY JSON object", ex[1].body == "{}", repr(ex[1].body))
ok &= check("refresh content-type json",
            ex[1].headers.get("content-type") == "application/json", str(ex[1].headers))
ok &= check("refresh output", out == {"workspaceId": "ws-guid-1", "datasetId": "ds-guid-1",
                                      "refreshRequested": True}, str(out)[:200])

print("[write: execute_dax exact body]")
dax = "EVALUATE TOPN(10, 'Sales')"
rows = [{"[Amount]": i} for i in range(5)]
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.execute_dax", workspaceId="ws-guid-1",
                     datasetId="ds-guid-1", query=dax, maxRows=3),
    [TOKEN,
     resp(200, body={"results": [{"tables": [{"rows": rows}]}]})])
ok &= check("executeQueries url",
            ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/ws-guid-1/datasets/ds-guid-1/executeQueries",
            ex[1].url)
ok &= check("executeQueries POST", ex[1].method == "POST", ex[1].method)
ok &= check("executeQueries exact body",
            ex[1].json == {"queries": [{"query": dax}],
                           "serializerSettings": {"includeNulls": True}}, ex[1].body)
ok &= check("row cap respected (3 of 5)", len(out.get("rows", [])) == 3, str(out)[:300])
ok &= check("truncated flag set", out.get("truncated") is True, str(out)[:200])
ok &= check("rowCount reports full server count", out.get("rowCount") == 5, str(out)[:200])

print("[execute_dax: under-cap not truncated]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.execute_dax", workspaceId="ws-guid-1",
                     datasetId="ds-guid-1", query=dax),
    [TOKEN,
     resp(200, body={"results": [{"tables": [{"rows": rows[:2]}]}]})])
ok &= check("2 rows, default cap 100, not truncated",
            out.get("rowCount") == 2 and out.get("truncated") is False
            and len(out["rows"]) == 2, str(out)[:300])

# ---------------------------------------------------------------- 4. ERROR PATHS
print("[error: 401 on api call]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_workspaces"),
    [TOKEN,
     err(401, body={"error": {"code": "Unauthorized",
                              "message": "The caller is not authorized"}})])
txt = json.dumps(out)
ok &= check("401 surfaces friendly error", isinstance(out.get("error"), str), str(out)[:300])
ok &= check("401 status in message", "401" in out.get("error", ""), str(out)[:300])
ok &= check("401 message included", "not authorized" in out.get("error", ""), str(out)[:300])
ok &= check("no traceback in output", "Traceback" not in txt and "urllib" not in txt, txt[:300])

print("[error: token endpoint failure, secret not leaked]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_workspaces"),
    [err(401, body={"error": "invalid_client",
                    "error_description": "AADSTS7000215: Invalid client secret provided."})])
txt = json.dumps(out)
ok &= check("token failure surfaces error with status",
            "error" in out and "401" in out["error"], str(out)[:300])
ok &= check("AADSTS description surfaced", "AADSTS7000215" in out.get("error", ""), str(out)[:300])
ok &= check("client secret NOT leaked in output", "s3cr3t-XYZ" not in txt, txt[:300])
ok &= check("no traceback on token failure", "Traceback" not in txt, txt[:300])

print("[error: 429 Retry-After surfaced]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.execute_dax", workspaceId="ws-guid-1",
                     datasetId="ds-guid-1", query=dax),
    [TOKEN,
     err(429, body={"error": {"code": "TooManyRequests", "message": "Rate limit exceeded"}},
         headers={"Retry-After": "37"})])
ok &= check("429 status surfaced", "429" in out.get("error", ""), str(out)[:300])
ok &= check("Retry-After value surfaced", "retry after 37 seconds" in out.get("error", ""),
            str(out)[:300])

print("[error: pbi.error details flattened]")
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.execute_dax", workspaceId="ws-guid-1",
                     datasetId="ds-guid-1", query="EVALUATE bogus"),
    [TOKEN,
     err(400, body={"error": {"code": "DatasetExecuteQueriesError",
                              "pbi.error": {"code": "DatasetExecuteQueriesError",
                                            "details": [{"code": "DetailsMessage",
                                                         "detail": {"type": 1,
                                                                    "value": "Query (1, 10) The syntax is incorrect."}}]}}})])
ok &= check("400 with pbi.error detail surfaced",
            "400" in out.get("error", "") and "syntax is incorrect" in out.get("error", ""),
            str(out)[:400])

print("[error: missing required param]")
out, ex = run_tool("powerbi", creds(tool="powerbi.list_datasets"), [TOKEN])
ok &= check("missing workspaceId -> error", out.get("error") == "workspaceId required",
            str(out)[:200])

print("[error: unknown tool]")
out, ex = run_tool("powerbi", creds(tool="powerbi.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: powerbi.nope", str(out)[:200])

print("[error: missing credentials]")
out, ex = run_tool("powerbi", {"tool": "powerbi.list_workspaces", "tenantId": "t"}, [])
ok &= check("missing creds friendly error",
            "Missing Power BI credentials" in out.get("error", ""), str(out)[:300])

# ---------------------------------------------------------------- 5. SECURITY PROBES
print("[security: path-ish ids percent-encoded]")
evil = "abc/../def?x=1"
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_datasets", workspaceId=evil),
    [TOKEN, resp(200, body={"value": []})])
ok &= check("workspaceId fully quoted (no path escape)",
            ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/abc%2F..%2Fdef%3Fx%3D1/datasets",
            ex[1].url)
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.execute_dax", workspaceId="ws1", datasetId=evil, query=dax),
    [TOKEN, resp(200, body={"results": [{"tables": [{"rows": []}]}]})])
ok &= check("datasetId fully quoted in executeQueries",
            ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/ws1/datasets/abc%2F..%2Fdef%3Fx%3D1/executeQueries",
            ex[1].url)
out, ex = run_tool(
    "powerbi", creds(tool="powerbi.list_dashboards", workspaceId="ws1", dashboardId=evil),
    [TOKEN, resp(200, body={"value": []})])
ok &= check("dashboardId fully quoted in tiles url",
            ex[1].url == "https://api.powerbi.com/v1.0/myorg/groups/ws1/dashboards/abc%2F..%2Fdef%3Fx%3D1/tiles",
            ex[1].url)

print("[security: tenantId quoted in token url]")
out, ex = run_tool(
    "powerbi", {"tool": "powerbi.list_workspaces", "tenantId": "tid/../evil",
                "clientId": "c", "clientSecret": "s"},
    [TOKEN, resp(200, body={"value": []})])
ok &= check("tenantId percent-encoded",
            ex[0].url == "https://login.microsoftonline.com/tid%2F..%2Fevil/oauth2/v2.0/token",
            ex[0].url)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
