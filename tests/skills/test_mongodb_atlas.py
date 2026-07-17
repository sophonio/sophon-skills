"""Offline mock-HTTP integration tests for the mongodb-atlas Sophon skill."""
import base64
import json
import sys

from mockhttp import run_tool, resp, err, check

SKILL = "mongodb-atlas"
TOKEN_URL = "https://cloud.mongodb.com/api/oauth/token"
API_BASE = "https://cloud.mongodb.com/api/atlas/v2"
ACCEPT = "application/vnd.atlas.2025-03-12+json"
CREDS = {"clientId": "cid-123", "clientSecret": "s3cr3t-VALUE"}
EXPECTED_BASIC = "Basic " + base64.b64encode(b"cid-123:s3cr3t-VALUE").decode()

TOKEN_OK = resp(200, body={"access_token": "atok-xyz", "expires_in": 3600,
                           "token_type": "Bearer"})

ok = True


def token_checks(prefix, ex0):
    global ok
    ok &= check(f"{prefix}: token POST url exact", ex0.url == TOKEN_URL, ex0.url)
    ok &= check(f"{prefix}: token method POST", ex0.method == "POST", ex0.method)
    ok &= check(f"{prefix}: token Basic auth exact",
                ex0.headers.get("authorization") == EXPECTED_BASIC, str(ex0.headers))
    ok &= check(f"{prefix}: token body is form grant_type",
                ex0.body == "grant_type=client_credentials", repr(ex0.body))
    ok &= check(f"{prefix}: token content-type form-urlencoded",
                ex0.headers.get("content-type") == "application/x-www-form-urlencoded",
                str(ex0.headers))


def api_checks(prefix, ex1):
    global ok
    ok &= check(f"{prefix}: api Bearer token",
                ex1.headers.get("authorization") == "Bearer atok-xyz", str(ex1.headers))
    ok &= check(f"{prefix}: api pinned versioned Accept",
                ex1.headers.get("accept") == ACCEPT, str(ex1.headers))


# ---------------------------------------------------------------- 1. list_projects (happy)
out, ex = run_tool(SKILL, {"tool": "atlas.list_projects", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={"results": [
                        {"id": "p1", "name": "Prod", "clusterCount": 2,
                         "created": "2024-01-01T00:00:00Z", "orgId": "org1",
                         "links": [{"rel": "self"}]},
                        {"id": "p2", "name": "Dev", "clusterCount": 1,
                         "created": "2024-02-01T00:00:00Z", "orgId": "org1",
                         "links": []},
                    ], "totalCount": 2})])
ok &= check("list_projects: two requests (token + api)", len(ex) == 2, repr(ex))
token_checks("list_projects", ex[0])
api_checks("list_projects", ex[1])
ok &= check("list_projects: GET /groups with itemsPerPage",
            ex[1].method == "GET" and ex[1].url == f"{API_BASE}/groups?itemsPerPage=25",
            ex[1].url)
ok &= check("list_projects: count/totalCount shaped",
            out.get("count") == 2 and out.get("totalCount") == 2, str(out)[:200])
ok &= check("list_projects: trimmed fields present",
            out["projects"][0] == {"id": "p1", "name": "Prod", "clusterCount": 2,
                                   "created": "2024-01-01T00:00:00Z"},
            str(out["projects"][0]))
ok &= check("list_projects: raw fields absent",
            "orgId" not in out["projects"][0] and "links" not in out["projects"][0],
            str(out["projects"][0]))

# limit clamp: limit=500 -> 100
out, ex = run_tool(SKILL, {"tool": "atlas.list_projects", "limit": 500, **CREDS},
                   [TOKEN_OK, resp(200, body={"results": [], "totalCount": 0})])
ok &= check("list_projects: limit clamped to 100", "itemsPerPage=100" in ex[1].url, ex[1].url)

# ---------------------------------------------------------------- 2. list_clusters (happy, explicit projectId)
out, ex = run_tool(SKILL, {"tool": "atlas.list_clusters", "projectId": "abc123", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={"results": [
                        {"name": "Cluster0", "stateName": "IDLE",
                         "mongoDBVersion": "8.0.5", "paused": False,
                         "connectionStrings": {"standardSrv": "mongodb+srv://x"},
                         "replicationSpecs": [{"regionConfigs": [
                             {"electableSpecs": {"instanceSize": "M10",
                                                 "diskSizeGB": 10}}]}]},
                    ], "totalCount": 1})])
token_checks("list_clusters", ex[0])
api_checks("list_clusters", ex[1])
ok &= check("list_clusters: url uses given projectId",
            ex[1].url == f"{API_BASE}/groups/abc123/clusters?itemsPerPage=25", ex[1].url)
ok &= check("list_clusters: shaped summary",
            out["count"] == 1 and out["clusters"][0] == {
                "name": "Cluster0", "stateName": "IDLE", "mongoDBVersion": "8.0.5",
                "instanceSize": "M10", "paused": False},
            str(out)[:300])
ok &= check("list_clusters: connectionStrings not leaked in list",
            "connectionStrings" not in out["clusters"][0], str(out["clusters"][0]))

# ---------------------------------------------------------------- 3. projectId fallback + missing
# NOTE: the Sophon runtime merges connection-card fields into the same flat params dict
# as tool arguments, so at this layer a connection-field projectId is indistinguishable
# from an explicit one. The real fallback coverage is the missing-projectId ValueError
# test below (no key anywhere -> friendly error, zero HTTP calls).
out, ex = run_tool(SKILL, {"tool": "atlas.list_clusters", "projectId": "fallback-pid", **CREDS},
                   [TOKEN_OK, resp(200, body={"results": [], "totalCount": 0})])
ok &= check("list_clusters: projectId via params (connection fields merge here at runtime)",
            "/groups/fallback-pid/clusters" in ex[1].url, ex[1].url)

out, ex = run_tool(SKILL, {"tool": "atlas.list_clusters", **CREDS}, [])
ok &= check("list_clusters: no projectId anywhere -> friendly error",
            "error" in out and "projectId required" in out["error"], str(out)[:200])
ok &= check("list_clusters: no HTTP calls made without projectId", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------- 4. get_cluster (happy + security probe)
out, ex = run_tool(SKILL, {"tool": "atlas.get_cluster", "projectId": "p1",
                           "clusterName": "Cluster0", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={
                        "id": "c1", "name": "Cluster0", "stateName": "IDLE",
                        "clusterType": "REPLICASET", "mongoDBVersion": "8.0.5",
                        "mongoDBMajorVersion": "8.0", "paused": False,
                        "backupEnabled": True, "createDate": "2024-03-01T00:00:00Z",
                        "connectionStrings": {"standardSrv": "mongodb+srv://c0.x.mongodb.net",
                                              "privateSrv": "mongodb+srv://private"},
                        "replicationSpecs": [{"regionConfigs": [
                            {"electableSpecs": {"instanceSize": "M20", "diskSizeGB": 40}}]}],
                        "labels": [{"key": "internal"}]})])
api_checks("get_cluster", ex[1])
ok &= check("get_cluster: url exact",
            ex[1].url == f"{API_BASE}/groups/p1/clusters/Cluster0", ex[1].url)
ok &= check("get_cluster: shaped output",
            out.get("instanceSize") == "M20" and out.get("diskSizeGB") == 40
            and out.get("connectionStringSrv") == "mongodb+srv://c0.x.mongodb.net",
            str(out)[:300])
ok &= check("get_cluster: raw fields absent",
            "labels" not in out and "replicationSpecs" not in out
            and "connectionStrings" not in out, str(out)[:300])

# security probe (a): path-ish clusterName must be percent-encoded, no path escape
out, ex = run_tool(SKILL, {"tool": "atlas.get_cluster", "projectId": "p1",
                           "clusterName": "abc/../def?x=1", **CREDS},
                   [TOKEN_OK, resp(200, body={"name": "abc/../def?x=1"})])
ok &= check("get_cluster: path-ish clusterName percent-encoded",
            ex[1].url == f"{API_BASE}/groups/p1/clusters/abc%2F..%2Fdef%3Fx%3D1", ex[1].url)
ok &= check("get_cluster: no raw '../' or '?' in url",
            "../" not in ex[1].url and "?" not in ex[1].url, ex[1].url)

# security probe (a'): path-ish projectId also percent-encoded
out, ex = run_tool(SKILL, {"tool": "atlas.list_alerts", "projectId": "p/../q", **CREDS},
                   [TOKEN_OK, resp(200, body={"results": [], "totalCount": 0})])
ok &= check("list_alerts: path-ish projectId percent-encoded",
            f"{API_BASE}/groups/p%2F..%2Fq/alerts" in ex[1].url, ex[1].url)

# ---------------------------------------------------------------- 5. list_alerts (happy)
out, ex = run_tool(SKILL, {"tool": "atlas.list_alerts", "projectId": "p1", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={"results": [
                        {"id": "a1", "eventTypeName": "OUTSIDE_METRIC_THRESHOLD",
                         "status": "OPEN", "created": "2026-07-16T00:00:00Z",
                         "metricName": "CONNECTIONS", "groupId": "p1",
                         "links": []}], "totalCount": 1})])
api_checks("list_alerts", ex[1])
ok &= check("list_alerts: status=OPEN filter in query",
            "status=OPEN" in ex[1].url and "/groups/p1/alerts" in ex[1].url, ex[1].url)
ok &= check("list_alerts: shaped alert",
            out["count"] == 1 and out["alerts"][0] == {
                "id": "a1", "eventTypeName": "OUTSIDE_METRIC_THRESHOLD", "status": "OPEN",
                "created": "2026-07-16T00:00:00Z", "metricName": "CONNECTIONS"},
            str(out)[:300])
ok &= check("list_alerts: raw fields absent",
            "groupId" not in out["alerts"][0] and "links" not in out["alerts"][0],
            str(out["alerts"][0]))

# ---------------------------------------------------------------- 6. write path: acknowledge_alert
out, ex = run_tool(SKILL, {"tool": "atlas.acknowledge_alert", "projectId": "p1",
                           "alertId": "a1", "acknowledgedUntil": "2026-07-18T00:00:00Z",
                           "comment": "handled", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={"id": "a1", "status": "OPEN",
                                    "acknowledgedUntil": "2026-07-18T00:00:00Z",
                                    "acknowledgementComment": "handled",
                                    "groupId": "p1"})])
token_checks("ack_alert", ex[0])
api_checks("ack_alert", ex[1])
ok &= check("ack_alert: PATCH method", ex[1].method == "PATCH", ex[1].method)
ok &= check("ack_alert: url exact",
            ex[1].url == f"{API_BASE}/groups/p1/alerts/a1", ex[1].url)
ok &= check("ack_alert: exact JSON body",
            ex[1].json == {"acknowledgedUntil": "2026-07-18T00:00:00Z",
                           "acknowledgementComment": "handled"}, repr(ex[1].body))
ok &= check("ack_alert: json content-type",
            ex[1].headers.get("content-type") == "application/json", str(ex[1].headers))
ok &= check("ack_alert: shaped output",
            out == {"id": "a1", "status": "OPEN",
                    "acknowledgedUntil": "2026-07-18T00:00:00Z",
                    "acknowledgementComment": "handled"}, str(out)[:300])

# without comment: body must omit acknowledgementComment
out, ex = run_tool(SKILL, {"tool": "atlas.acknowledge_alert", "projectId": "p1",
                           "alertId": "a1", "acknowledgedUntil": "2026-07-18T00:00:00Z",
                           **CREDS},
                   [TOKEN_OK, resp(200, body={"id": "a1", "status": "OPEN"})])
ok &= check("ack_alert: comment omitted from body when not given",
            ex[1].json == {"acknowledgedUntil": "2026-07-18T00:00:00Z"}, repr(ex[1].body))

# missing acknowledgedUntil -> ValueError, no HTTP
out, ex = run_tool(SKILL, {"tool": "atlas.acknowledge_alert", "projectId": "p1",
                           "alertId": "a1", **CREDS}, [])
ok &= check("ack_alert: missing acknowledgedUntil -> error, no HTTP",
            "error" in out and "acknowledgedUntil" in out["error"] and len(ex) == 0,
            str(out)[:200])

# ---------------------------------------------------------------- 7. get_process_metrics (happy)
out, ex = run_tool(SKILL, {"tool": "atlas.get_process_metrics", "projectId": "p1",
                           "processId": "host-00.ab1cd.mongodb.net:27017", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={"processId": "host-00.ab1cd.mongodb.net:27017",
                                    "granularity": "PT1M",
                                    "measurements": [
                                        {"name": "CONNECTIONS", "units": "SCALAR",
                                         "dataPoints": [
                                             {"timestamp": "t1", "value": None},
                                             {"timestamp": "t2", "value": 5.0},
                                             {"timestamp": "t3", "value": 7.0}]}],
                                    "links": []})])
api_checks("metrics", ex[1])
ok &= check("metrics: processId colon quoted in path",
            f"{API_BASE}/groups/p1/processes/host-00.ab1cd.mongodb.net%3A27017/measurements"
            in ex[1].url, ex[1].url)
ok &= check("metrics: default m params repeated (doseq)",
            "m=PROCESS_CPU_USER" in ex[1].url and "m=CONNECTIONS" in ex[1].url
            and "m=OPCOUNTER_DELETE" in ex[1].url, ex[1].url)
ok &= check("metrics: default granularity+period in query",
            "granularity=PT1M" in ex[1].url and "period=PT1H" in ex[1].url, ex[1].url)
ok &= check("metrics: null points dropped, shaping",
            out["count"] == 1 and out["measurements"][0]["points"] == [
                {"timestamp": "t2", "value": 5.0}, {"timestamp": "t3", "value": 7.0}],
            str(out)[:300])
ok &= check("metrics: raw dataPoints key absent",
            "dataPoints" not in out["measurements"][0], str(out["measurements"][0])[:200])

# ---------------------------------------------------------------- 8. list_events + list_database_users
out, ex = run_tool(SKILL, {"tool": "atlas.list_events", "projectId": "p1", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={"results": [
                        {"id": "e1", "eventTypeName": "CLUSTER_READY",
                         "created": "2026-07-15T00:00:00Z", "username": "ops@x.co",
                         "remoteAddress": "1.2.3.4"}], "totalCount": 1})])
api_checks("list_events", ex[1])
ok &= check("list_events: url + shaping",
            "/groups/p1/events" in ex[1].url and out["events"][0] == {
                "id": "e1", "eventTypeName": "CLUSTER_READY",
                "created": "2026-07-15T00:00:00Z", "actor": "ops@x.co"},
            str(out)[:300])
ok &= check("list_events: raw remoteAddress absent",
            "remoteAddress" not in out["events"][0], str(out["events"][0]))

out, ex = run_tool(SKILL, {"tool": "atlas.list_database_users", "projectId": "p1", **CREDS},
                   [TOKEN_OK,
                    resp(200, body={"results": [
                        {"username": "app", "databaseName": "admin",
                         "roles": [{"roleName": "readWrite", "databaseName": "shop",
                                    "collectionName": "orders"}],
                         "password": "SHOULD-NEVER-APPEAR",
                         "awsIAMType": "NONE"}], "totalCount": 1})])
api_checks("list_db_users", ex[1])
ok &= check("list_db_users: url + shaping",
            "/groups/p1/databaseUsers" in ex[1].url and out["databaseUsers"][0] == {
                "username": "app", "authDatabase": "admin",
                "roles": [{"roleName": "readWrite", "databaseName": "shop"}]},
            str(out)[:300])
ok &= check("list_db_users: password material never surfaced",
            "SHOULD-NEVER-APPEAR" not in json.dumps(out), json.dumps(out)[:300])

# ---------------------------------------------------------------- 9. error paths
# 401 on the API call
out, ex = run_tool(SKILL, {"tool": "atlas.list_projects", **CREDS},
                   [TOKEN_OK,
                    err(401, body={"detail": "Invalid token", "errorCode": "UNAUTHORIZED"})])
printed = json.dumps(out)
ok &= check("401: friendly error with status", "error" in out and "401" in out["error"],
            printed[:200])
ok &= check("401: errorCode included", "UNAUTHORIZED" in out["error"], printed[:200])
ok &= check("401: no traceback in output", "Traceback" not in printed, printed[:300])
ok &= check("401: secret never printed (security probe b)",
            "s3cr3t-VALUE" not in printed and "cid-123" not in printed, printed[:300])

# 401 on the token mint itself
out, ex = run_tool(SKILL, {"tool": "atlas.list_projects", **CREDS},
                   [err(401, body={"error": "invalid_client",
                                   "error_description": "bad credentials"})])
printed = json.dumps(out)
ok &= check("token 401: friendly error with status",
            "error" in out and "401" in out["error"] and "bad credentials" in out["error"],
            printed[:200])
ok &= check("token 401: secret not leaked", "s3cr3t-VALUE" not in printed, printed[:300])
ok &= check("token 401: no traceback", "Traceback" not in printed, printed[:300])

# 429 with Retry-After surfaced
out, ex = run_tool(SKILL, {"tool": "atlas.list_projects", **CREDS},
                   [TOKEN_OK,
                    err(429, body={"detail": "Too many requests", "errorCode": "RATE_LIMITED"},
                        headers={"Retry-After": "42"})])
ok &= check("429: status + Retry-After surfaced",
            "error" in out and "429" in out["error"] and "Retry-After: 42" in out["error"],
            str(out)[:300])

# 403 IP access-list hint
out, ex = run_tool(SKILL, {"tool": "atlas.list_projects", **CREDS},
                   [TOKEN_OK,
                    err(403, body={"detail": "Forbidden",
                                   "errorCode": "API_KEY_MUST_BE_IN_ACCESS_LIST"})])
ok &= check("403 access-list: hint appended",
            "error" in out and "IP access list" in out["error"], str(out)[:400])

# token response missing access_token
out, ex = run_tool(SKILL, {"tool": "atlas.list_projects", **CREDS},
                   [resp(200, body={"token_type": "Bearer"})])
ok &= check("token: missing access_token -> error",
            "error" in out and "access_token" in out["error"], str(out)[:200])

# ---------------------------------------------------------------- 10. dispatch guards
out, ex = run_tool(SKILL, {"tool": "atlas.nope", **CREDS}, [])
ok &= check("unknown tool -> error, no HTTP",
            out.get("error", "").startswith("Unknown tool") and len(ex) == 0, str(out)[:200])

out, ex = run_tool(SKILL, {"tool": "atlas.list_projects"}, [])
ok &= check("missing credentials -> friendly error, no HTTP",
            "error" in out and "credentials" in out["error"].lower() and len(ex) == 0,
            str(out)[:200])

print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
