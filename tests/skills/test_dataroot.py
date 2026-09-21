"""Offline mock-HTTP integration tests for the dataroot Sophon skill."""
import contextlib
import io
import json
import sys
import urllib.error

from mockhttp import REPO, run_tool, resp, err, check, patched

BASE = "https://api.dev.dataroot.at"
CREDS = {"baseUrl": BASE, "emailAddress": "u@x.io", "password": "p@ss-SECRET-123"}
LOGIN_OK = resp(200, body={"accessToken": "jwt-abc", "refreshToken": "r-xyz"})
ORGS_BODY = [{"id": "org-1", "name": "Acme"}, {"id": "org-2", "name": "Beta"}]
ORGS = resp(200, body=ORGS_BODY)

ok = True


# ---------------------------------------------------------------- 1. auth exactness
print("scenario 1: auth exactness (login body has no username; Bearer on API; no org header on /organizations)")
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.list_organizations"},
                   [LOGIN_OK, ORGS])
ok &= check("two requests (login + organizations)", len(ex) == 2, repr(ex))
ok &= check("login POST to {baseUrl}/api/v1/accounts/login",
            ex[0].method == "POST" and ex[0].url == f"{BASE}/api/v1/accounts/login", repr(ex[0]))
ok &= check("login body sends empty username + email + password (API requires username key present)",
            ex[0].json == {"username": "", "emailAddress": "u@x.io",
                           "password": "p@ss-SECRET-123"}, str(ex[0].body))
ok &= check("login content-type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("no authorization header on login", "authorization" not in ex[0].headers,
            str(ex[0].headers))
ok &= check("organizations call carries Bearer token",
            ex[1].url == f"{BASE}/api/v1/organizations"
            and ex[1].headers.get("authorization") == "Bearer jwt-abc", str(ex[1].headers))
ok &= check("no org header on /organizations", "x-organization-id" not in ex[1].headers,
            str(ex[1].headers))
ok &= check("user-agent set", ex[1].headers.get("user-agent") == "sophon-dataroot-skill",
            str(ex[1].headers))
ok &= check("output shaped {count, organizations}",
            out == {"count": 2, "organizations": ORGS_BODY}, str(out)[:300])


# ---------------------------------------------------------------- 2. org header threading
print("scenario 2: list_connections threads X-Organization-Id (resolved) + shaping")
CONNS = resp(200, body={"items": [
    {"id": "c1", "name": "Prod DB", "description": "main", "status": "Active",
     "dataSources": [{"id": "d1", "name": "pg"}]},
    {"id": "c2", "name": "Lake", "description": None, "status": "Draft", "dataSources": []},
]})
out, ex = run_tool("dataroot",
                   {**CREDS, "tool": "dataroot.list_connections", "organization": "Acme"},
                   [LOGIN_OK, ORGS, CONNS])
ok &= check("three requests (login + resolve + connections)", len(ex) == 3, repr(ex))
ok &= check("resolve /organizations call sends no org header",
            ex[1].url == f"{BASE}/api/v1/organizations" and "x-organization-id" not in ex[1].headers,
            str(ex[1].headers))
ok &= check("/connections URL + resolved org header",
            ex[2].url == f"{BASE}/api/v1/connections"
            and ex[2].headers.get("x-organization-id") == "org-1", repr(ex[2]))
ok &= check("connections shaped with dataSourceCount",
            out.get("count") == 2 and out["connections"][0] == {
                "id": "c1", "name": "Prod DB", "description": "main", "status": "Active",
                "dataSourceCount": 1}, str(out)[:400])


# ---------------------------------------------------------------- 3. org name->id resolution
print("scenario 3: organization resolves by name (case-insensitive), id passthrough, miss, ambiguous")
_, ex = run_tool("dataroot",
                 {**CREDS, "tool": "dataroot.list_connections", "organization": "acme"},
                 [LOGIN_OK, ORGS, resp(200, body={"items": []})])
ok &= check("case-insensitive name 'acme' -> org-1",
            ex[2].headers.get("x-organization-id") == "org-1", str(ex[2].headers))
_, ex = run_tool("dataroot",
                 {**CREDS, "tool": "dataroot.list_connections", "organization": "org-2"},
                 [LOGIN_OK, ORGS, resp(200, body={"items": []})])
ok &= check("id passthrough 'org-2' -> org-2",
            ex[2].headers.get("x-organization-id") == "org-2", str(ex[2].headers))
out, ex = run_tool("dataroot",
                   {**CREDS, "tool": "dataroot.list_connections", "organization": "Nope"},
                   [LOGIN_OK, ORGS])
ok &= check("unknown org -> friendly not-found listing available orgs",
            "not found" in out.get("error", "") and "Acme" in out["error"] and "Beta" in out["error"],
            str(out))
ok &= check("no connections call after failed resolve", len(ex) == 2, repr(ex))
out, _ = run_tool("dataroot",
                  {**CREDS, "tool": "dataroot.list_connections", "organization": "Dup"},
                  [LOGIN_OK, resp(200, body=[{"id": "o1", "name": "Dup"}, {"id": "o2", "name": "Dup"}])])
ok &= check("ambiguous name -> ambiguous error", "ambiguous" in out.get("error", ""), str(out))


# ---------------------------------------------------------------- 4. list_data_sources aggregate + cap
print("scenario 4: list_data_sources aggregates across connections, caps the scan, drops settings")
conns12 = {"items": [{"id": f"c{i}", "name": f"conn{i}", "status": "Active", "dataSources": []}
                     for i in range(12)]}
source_step = lambda i: resp(200, body={"items": [
    {"id": f"d{i}", "name": f"src{i}", "type": "PostgreSQL", "category": "RelationalDatabase",
     "status": "Ready", "tags": ["t"], "settings": {"password": "pg-SECRET"}}]})
out, ex = run_tool(
    "dataroot", {**CREDS, "tool": "dataroot.list_data_sources", "organization": "Acme"},
    [LOGIN_OK, ORGS, resp(200, body=conns12)] + [source_step(i) for i in range(10)])
ok &= check("requests = login + resolve + connections + 10 sources", len(ex) == 13, repr(len(ex)))
ok &= check("scan capped at 10 connections + truncated flag",
            out.get("connectionsScanned") == 10 and out.get("truncated") is True, str(out)[:300])
ok &= check("one source per scanned connection", out.get("count") == 10, str(out)[:200])
ok &= check("each source carries connectionId/connectionName and NO settings",
            all("settings" not in s and s.get("connectionId") and s.get("connectionName")
                for s in out["dataSources"]), str(out["dataSources"][0]))
ok &= check("source shaped fields",
            out["dataSources"][0]["type"] == "PostgreSQL"
            and out["dataSources"][0]["status"] == "Ready", str(out["dataSources"][0]))
ok &= check("no secret leaks from dropped settings", "pg-SECRET" not in json.dumps(out),
            json.dumps(out)[:200])
ok &= check("per-connection /sources URL + org header",
            ex[3].url == f"{BASE}/api/v1/connections/c0/sources"
            and ex[3].headers.get("x-organization-id") == "org-1", repr(ex[3]))
# sub-case: connectionId scopes to a single /sources call
out, ex = run_tool(
    "dataroot", {**CREDS, "tool": "dataroot.list_data_sources", "organization": "Acme",
                 "connectionId": "cX"},
    [LOGIN_OK, ORGS, resp(200, body={"items": [
        {"id": "dz", "name": "z", "type": "MySQL", "category": "RelationalDatabase",
         "status": "Ready"}]})])
ok &= check("connectionId -> login + resolve + one /sources call",
            len(ex) == 3 and ex[2].url == f"{BASE}/api/v1/connections/cX/sources", repr(ex))
ok &= check("scoped result: 1 scanned, not truncated",
            out.get("connectionsScanned") == 1 and out.get("truncated") is False
            and out.get("count") == 1, str(out)[:200])


# ---------------------------------------------------------------- 5. get_data_source secret masking
print("scenario 5: get_data_source masks secret settings, keeps structural fields")
DS = {"dataSource": {
    "id": "d1", "organizationId": "org-1", "name": "pg", "type": "PostgreSQL",
    "category": "RelationalDatabase", "status": "Ready", "tags": ["x"],
    "settings": {
        "host": "db.acme", "port": 5432, "database": "main", "username": "svc",
        "sslEnabled": True, "warehouse": "wh1", "role": "reader",
        "password": "pg-SECRET", "s3SecretKey": "AKIA-SECRET",
        "credentialsJson": "{\"k\":\"v-SECRET\"}",
        "extraProperties": {"apiToken": "tok-SECRET", "note": "plain"}}}}
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.get_data_source",
                                "organization": "Acme", "connectionId": "c1", "sourceId": "d1"},
                   [LOGIN_OK, ORGS, resp(200, body=DS)])
ok &= check("/sources/{id} URL + org header",
            ex[2].url == f"{BASE}/api/v1/connections/c1/sources/d1"
            and ex[2].headers.get("x-organization-id") == "org-1", repr(ex[2]))
s = out.get("settings", {})
ok &= check("secret keys masked to '***'",
            s.get("password") == "***" and s.get("s3SecretKey") == "***"
            and s.get("credentialsJson") == "***", str(s))
ok &= check("structural fields preserved",
            s.get("host") == "db.acme" and s.get("port") == 5432
            and s.get("username") == "svc" and s.get("database") == "main"
            and s.get("sslEnabled") is True and s.get("role") == "reader", str(s))
ok &= check("extraProperties values masked wholesale",
            s.get("extraProperties", {}).get("apiToken") == "***"
            and s.get("extraProperties", {}).get("note") == "***", str(s.get("extraProperties")))
ok &= check("top-level fields shaped", out.get("id") == "d1" and out.get("type") == "PostgreSQL"
            and out.get("organizationId") == "org-1", str(out)[:200])
printed = json.dumps(out)
ok &= check("no raw secret string anywhere in output",
            all(x not in printed for x in ("pg-SECRET", "AKIA-SECRET", "v-SECRET", "tok-SECRET")),
            printed[:300])


# ---------------------------------------------------------------- 6. get_data_source_metadata
print("scenario 6: metadata summarized (columns are name/type only) + table cap -> truncated")
META = {"metadata": {"id": "m1", "dataSourceId": "d1", "schemas": {
    "public": {"name": "public", "tables": {
        "users": {"name": "users", "columns": {
            "id": {"name": "id", "type": "int", "isNullable": False, "description": "pk"},
            "email": {"name": "email", "type": "varchar"}}},
        "orders": {"name": "orders", "columns": {"id": {"name": "id", "type": "int"}}}}}}}}
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.get_data_source_metadata",
                                "organization": "Acme", "dataSourceId": "d1"},
                   [LOGIN_OK, ORGS, resp(200, body=META)])
ok &= check("metadata URL + org header",
            ex[2].url == f"{BASE}/api/v1/data-sources/d1/metadata"
            and ex[2].headers.get("x-organization-id") == "org-1", repr(ex[2]))
ok &= check("shaped: dataSourceId + schemaCount", out.get("dataSourceId") == "d1"
            and out.get("schemaCount") == 1 and out.get("truncated") is False, str(out)[:200])
sc = out["schemas"][0]
ok &= check("schema name + tableCount", sc.get("name") == "public" and sc.get("tableCount") == 2,
            str(sc)[:200])
users = next(t for t in sc["tables"] if t["name"] == "users")
ok &= check("columns trimmed to name/type only",
            users["columns"] == [{"name": "id", "type": "int"},
                                 {"name": "email", "type": "varchar"}]
            and users.get("columnCount") == 2, str(users))
big_tables = {f"t{i}": {"name": f"t{i}", "columns": {"c": {"name": "c", "type": "int"}}}
              for i in range(51)}
out, _ = run_tool("dataroot", {**CREDS, "tool": "dataroot.get_data_source_metadata",
                               "organization": "Acme", "dataSourceId": "d2"},
                  [LOGIN_OK, ORGS, resp(200, body={"metadata": {"dataSourceId": "d2", "schemas": {
                      "public": {"name": "public", "tables": big_tables}}}})])
ok &= check("table cap: 51 tables -> 50 returned + truncated",
            out["schemas"][0]["tableCount"] == 51 and len(out["schemas"][0]["tables"]) == 50
            and out.get("truncated") is True, str(out)[:200])


# ---------------------------------------------------------------- 7. whoami (+ quota degrade)
print("scenario 7: whoami shapes profile + quota; quota failure degrades to null")
INFO = {"userId": "u1", "email": "u@x.io", "userName": "user", "firstName": "U", "lastName": "Ser",
        "roles": ["admin"], "isActive": True, "timezone": "UTC", "locale": "en",
        "bio": "ignored", "lastLoginAt": "2026-07-01"}
QUOTA = {"planName": "Pro", "remainingRequests": 90, "usedRequests": 10, "monthlyLimit": 100,
         "usagePercentage": 10, "periodEndsAt": "2026-08-01", "payAsYouGoEnabled": False}
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.whoami"},
                   [LOGIN_OK, resp(200, body=INFO), resp(200, body=QUOTA)])
ok &= check("info + quota URLs, no org header",
            ex[1].url == f"{BASE}/api/v1/accounts/manage/info"
            and ex[2].url == f"{BASE}/api/v1/quota/status"
            and "x-organization-id" not in ex[1].headers, repr(ex))
ok &= check("profile shaped (raw extra fields dropped)",
            out["profile"]["email"] == "u@x.io" and out["profile"]["roles"] == ["admin"]
            and out["profile"]["isActive"] is True and "bio" not in out["profile"], str(out)[:300])
ok &= check("quota shaped", out["quota"]["planName"] == "Pro"
            and out["quota"]["remainingRequests"] == 90, str(out.get("quota")))
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.whoami"},
                   [LOGIN_OK, resp(200, body=INFO), err(404, body={"title": "Not Found"})])
ok &= check("quota 404 degrades to null without failing whoami",
            out.get("quota") is None and out["profile"]["email"] == "u@x.io" and len(ex) == 3,
            str(out)[:200])
ok &= check("no traceback on degraded quota", "Traceback" not in json.dumps(out), str(out)[:200])


# ---------------------------------------------------------------- 8. error paths
print("scenario 8: login 401 + API 403 + network unreachable are friendly, no leaks")
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.list_organizations"},
                   [err(401, body={"title": "Unauthorized", "detail": "bad creds"})])
printed = json.dumps(out)
ok &= check("login 401 -> friendly error with status + detail",
            "401" in out.get("error", "") and "bad creds" in out["error"], str(out))
ok &= check("only the login request was made", len(ex) == 1, repr(ex))
ok &= check("no traceback / password never leaked on login failure",
            "Traceback" not in printed and "p@ss-SECRET-123" not in printed, printed[:300])
out, _ = run_tool("dataroot",
                  {**CREDS, "tool": "dataroot.list_connections", "organization": "Acme"},
                  [LOGIN_OK, ORGS, err(403, body={"title": "Forbidden", "detail": "no access"})])
ok &= check("API 403 -> 'Dataroot API error 403: ...'",
            out.get("error", "").startswith("Dataroot API error 403")
            and "no access" in out["error"], str(out))
# network unreachable (URLError) via a custom transport
_src = open(f"{REPO}/skills/dataroot/main.py", encoding="utf-8").read()


def _unreachable(req, *a, **k):
    raise urllib.error.URLError("connection refused")


_buf = io.StringIO()
with patched(_unreachable), contextlib.redirect_stdout(_buf):
    exec(compile(_src, "dataroot/main.py", "exec"),
         {"params": {**CREDS, "tool": "dataroot.list_organizations"}})
out = json.loads(_buf.getvalue().strip())
ok &= check("URLError -> 'Could not reach Dataroot' with reason",
            out.get("error", "").startswith("Could not reach Dataroot")
            and "connection refused" in out["error"], str(out))
ok &= check("no traceback on URLError", "Traceback" not in json.dumps(out), str(out))


# ---------------------------------------------------------------- 9. guardrails
print("scenario 9: unknown tool / missing credentials / missing arg")
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.nope"}, [])
ok &= check("unknown tool -> error, zero requests",
            "Unknown tool" in out.get("error", "") and len(ex) == 0, str(out))
out, ex = run_tool("dataroot", {"baseUrl": BASE, "emailAddress": "u@x.io",
                                "tool": "dataroot.list_organizations"}, [])
ok &= check("missing password -> names the missing field, connect message, zero requests",
            "credentials" in out.get("error", "").lower() and "connect" in out["error"].lower()
            and "password" in out["error"] and len(ex) == 0, str(out))
ok &= check("missing-creds error carries a value-free receivedParamShape diagnostic",
            isinstance(out.get("receivedParamShape"), dict)
            and out["receivedParamShape"].get("tool") == "str"
            and "password" not in out["receivedParamShape"]
            and "p@ss-SECRET-123" not in json.dumps(out), str(out.get("receivedParamShape")))

# ---------------------------------------------------------------- 9b. defensive credential resolution
print("scenario 9b: credentials nested under a container object still resolve")
out, ex = run_tool("dataroot", {"tool": "dataroot.list_organizations",
                                "credentials": {"baseUrl": BASE, "emailAddress": "u@x.io",
                                                "password": "p@ss-SECRET-123"}},
                   [LOGIN_OK, ORGS])
ok &= check("nested credentials -> login happens (2 requests), no missing-creds error",
            len(ex) == 2 and "organizations" in out and "error" not in out, str(out)[:200])
ok &= check("nested creds produce the same correct login body",
            ex[0].json == {"username": "", "emailAddress": "u@x.io",
                           "password": "p@ss-SECRET-123"}, str(ex[0].body))
out, ex = run_tool("dataroot", {"tool": "dataroot.list_organizations",
                                "connections": {"dataroot": {"baseUrl": BASE,
                                                             "emailAddress": "u@x.io",
                                                             "password": "p@ss-SECRET-123"}}},
                   [LOGIN_OK, ORGS])
ok &= check("service-keyed nested map (connections.dataroot.*) also resolves",
            len(ex) == 2 and "organizations" in out, str(out)[:200])
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.get_data_source",
                                "organization": "Acme", "connectionId": "c1"},
                   [LOGIN_OK, ORGS])
ok &= check("missing sourceId -> validation error after auth+resolve only",
            out.get("error") == "connectionId and sourceId required" and len(ex) == 2, str(out))


# ---------------------------------------------------------------- 10. security: path-traversal ids
print("scenario 10: path-ish ids are percent-encoded (no path/query escape)")
out, ex = run_tool("dataroot", {**CREDS, "tool": "dataroot.get_data_source",
                                "organization": "Acme", "connectionId": "c1",
                                "sourceId": "abc/../x?y=1"},
                   [LOGIN_OK, ORGS, resp(200, body={"dataSource": {"id": "d1", "settings": {}}})])
ok &= check("sourceId percent-encoded in URL",
            "abc%2F..%2Fx%3Fy%3D1" in ex[2].url, ex[2].url)
ok &= check("no raw traversal or query injection in URL",
            "abc/../x" not in ex[2].url and "?y=1" not in ex[2].url, ex[2].url)
ok &= check("password never appears in output", "p@ss-SECRET-123" not in json.dumps(out),
            json.dumps(out)[:200])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
