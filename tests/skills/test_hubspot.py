"""Offline mock-HTTP integration tests for the hubspot skill."""
import contextlib
import io
import json
import sys
import urllib.error

from mockhttp import REPO, run_tool, resp, err, check, patched

BASE = "https://api.hubapi.com"
TOK = "pat-na1-SECRET-VALUE-123"


def creds(**extra):
    p = {"accessToken": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. hubspot.search_objects — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: search_objects happy path / auth exactness")
out, ex = run_tool("hubspot", creds(tool="hubspot.search_objects", objectType="contacts",
                                    propertyName="email", operator="eq", value="ann@x.co",
                                    properties=["email", "firstname"]), [
    resp(200, body={
        "total": 2,
        "results": [
            {"id": "501", "properties": {"email": "ann@x.co", "firstname": "Ann",
                                         "hs_object_id": "501"},
             "createdAt": "2025-01-01T00:00:00Z", "updatedAt": "2026-07-01T00:00:00Z",
             "archived": False},
            {"id": "502", "properties": {"email": "ann@x.co", "firstname": "Ann2"},
             "createdAt": "2025-02-01T00:00:00Z", "updatedAt": "2026-07-02T00:00:00Z"},
        ],
        "paging": {"next": {"after": "cursor-99", "link": "https://evil.example/next"}},
    }),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/crm/v3/objects/contacts/search", ex[0].url)
ok &= check("Authorization is exactly 'Bearer <token>'",
            ex[0].headers.get("authorization") == f"Bearer {TOK}", str(ex[0].headers))
ok &= check("Content-Type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("User-Agent set", ex[0].headers.get("user-agent") == "sophon-hubspot-skill",
            str(ex[0].headers))
body = ex[0].json
ok &= check("body: filterGroups single EQ filter (operator upper-cased)",
            body.get("filterGroups") == [{"filters": [{"propertyName": "email",
                                                       "operator": "EQ",
                                                       "value": "ann@x.co"}]}],
            str(body))
ok &= check("body: properties passed", body.get("properties") == ["email", "firstname"],
            str(body))
ok &= check("body: default limit 20", body.get("limit") == 20, str(body))
ok &= check("body: no query key when absent", "query" not in body, str(body))
ok &= check("count == 2 and total surfaced", out.get("count") == 2 and out.get("total") == 2,
            str(out)[:300])
ok &= check("results shaped (id + properties + timestamps)",
            out["results"][0]["id"] == "501"
            and out["results"][0]["properties"]["email"] == "ann@x.co"
            and out["results"][0]["updatedAt"] == "2026-07-01T00:00:00Z", str(out)[:300])
ok &= check("raw archived flag absent from summary", "archived" not in out["results"][0],
            str(out["results"][0]))
ok &= check("nextAfter cursor returned (no link followed)",
            out.get("nextAfter") == "cursor-99" and len(ex) == 1, str(out)[:300])
ok &= check("token not echoed in output", TOK not in json.dumps(out))

print("scenario: search_objects free-text query, limit clamped to 100, after cursor")
out, ex = run_tool("hubspot", creds(tool="hubspot.search_objects", objectType="deals",
                                    query="renewal", limit=5000, after="cur-1"), [
    resp(200, body={"total": 0, "results": []}),
])
body = ex[0].json
ok &= check("URL uses deals", ex[0].url == f"{BASE}/crm/v3/objects/deals/search", ex[0].url)
ok &= check("body: query + after + clamped limit",
            body.get("query") == "renewal" and body.get("after") == "cur-1"
            and body.get("limit") == 100, str(body))
ok &= check("body: no filterGroups without propertyName", "filterGroups" not in body, str(body))
ok &= check("empty result count 0", out.get("count") == 0 and "nextAfter" not in out, str(out))

print("scenario: search_objects operator/value without propertyName rejected before HTTP")
out, ex = run_tool("hubspot", creds(tool="hubspot.search_objects", objectType="contacts",
                                    value="ann@x.co"), [])
ok &= check("propertyName-less filter rejected",
            out.get("error") == "propertyName required when operator/value are given", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: search_objects value-less HAS_PROPERTY filter omits 'value'")
out, ex = run_tool("hubspot", creds(tool="hubspot.search_objects", objectType="contacts",
                                    propertyName="email", operator="HAS_PROPERTY"), [
    resp(200, body={"total": 0, "results": []}),
])
flt = ex[0].json["filterGroups"][0]["filters"][0]
ok &= check("filter has propertyName + operator, no value",
            flt == {"propertyName": "email", "operator": "HAS_PROPERTY"}, str(flt))

# ---------------------------------------------------------------------------
# 2. hubspot.get_object — happy path with properties + associations
# ---------------------------------------------------------------------------
print("scenario: get_object happy path")
out, ex = run_tool("hubspot", creds(tool="hubspot.get_object", objectType="deals",
                                    objectId="9871234", properties=["dealname", "amount"],
                                    associations=["contacts"]), [
    resp(200, body={"id": "9871234",
                    "properties": {"dealname": "Big Deal", "amount": "5000"},
                    "createdAt": "2025-03-01T00:00:00Z",
                    "updatedAt": "2026-07-10T00:00:00Z",
                    "archived": False,
                    "associations": {"contacts": {"results": [
                        {"id": "501", "type": "deal_to_contact"},
                        {"id": "502", "type": "deal_to_contact"}]}}}),
])
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (csv query params)",
            ex[0].url == f"{BASE}/crm/v3/objects/deals/9871234"
                         "?properties=dealname%2Camount&associations=contacts", ex[0].url)
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("properties trimmed through",
            out.get("properties") == {"dealname": "Big Deal", "amount": "5000"}, str(out)[:300])
ok &= check("associations flattened to id lists",
            out.get("associations") == {"contacts": ["501", "502"]}, str(out)[:300])
ok &= check("objectType echoed", out.get("objectType") == "deals", str(out)[:200])

print("scenario: get_object invalid objectType rejected before HTTP")
out, ex = run_tool("hubspot", creds(tool="hubspot.get_object", objectType="owners",
                                    objectId="1"), [])
ok &= check("objectType enum enforced",
            "objectType must be one of" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 3. hubspot.list_pipelines — happy path + enum restriction
# ---------------------------------------------------------------------------
print("scenario: list_pipelines happy path")
out, ex = run_tool("hubspot", creds(tool="hubspot.list_pipelines", objectType="deals"), [
    resp(200, body={"results": [
        {"id": "default", "label": "Sales Pipeline", "displayOrder": 0,
         "createdAt": "2020-01-01T00:00:00Z",
         "stages": [
             {"id": "appt", "label": "Appointment", "displayOrder": 0,
              "metadata": {"probability": "0.2"}},
             {"id": "won", "label": "Closed Won", "displayOrder": 1,
              "metadata": {"probability": "1.0"}}]}]}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/crm/v3/pipelines/deals", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("pipeline shaped id/label/stages",
            out["pipelines"][0] == {"id": "default", "label": "Sales Pipeline",
                                    "stages": [{"id": "appt", "label": "Appointment",
                                                "displayOrder": 0},
                                               {"id": "won", "label": "Closed Won",
                                                "displayOrder": 1}]},
            str(out["pipelines"][0]))

print("scenario: list_pipelines rejects contacts (deals|tickets only)")
out, ex = run_tool("hubspot", creds(tool="hubspot.list_pipelines", objectType="contacts"), [])
ok &= check("contacts rejected for pipelines",
            out.get("error") == "objectType must be one of: deals, tickets", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 4. hubspot.list_owners — happy path + clamp
# ---------------------------------------------------------------------------
print("scenario: list_owners happy path with clamped limit")
out, ex = run_tool("hubspot", creds(tool="hubspot.list_owners", limit=9999), [
    resp(200, body={"results": [
        {"id": "77", "email": "ann@x.co", "firstName": "Ann", "lastName": "Lee",
         "userId": 123, "archived": False, "teams": [{"id": "t1"}]}]}),
])
ok &= check("URL clamped to max 500", ex[0].url == f"{BASE}/crm/v3/owners?limit=500", ex[0].url)
ok &= check("owner shaped",
            out == {"count": 1, "owners": [{"id": "77", "email": "ann@x.co",
                                            "firstName": "Ann", "lastName": "Lee"}]},
            str(out))

print("scenario: list_owners limit=0 clamps to lower bound 1")
out, ex = run_tool("hubspot", creds(tool="hubspot.list_owners", limit=0), [
    resp(200, body={"results": []}),
])
ok &= check("URL clamped to min 1", ex[0].url == f"{BASE}/crm/v3/owners?limit=1", ex[0].url)

# ---------------------------------------------------------------------------
# 5. WRITE PATHS — create_object, update_object, add_note bodies
# ---------------------------------------------------------------------------
print("scenario: create_object write body")
out, ex = run_tool("hubspot", creds(tool="hubspot.create_object", objectType="contacts",
                                    properties={"email": "ann@x.co", "firstname": "Ann"}), [
    resp(201, body={"id": "601", "properties": {"email": "ann@x.co", "firstname": "Ann"},
                    "createdAt": "2026-07-18T00:00:00Z"}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/crm/v3/objects/contacts", ex[0].url)
ok &= check("body is exactly {properties: {...}}",
            ex[0].json == {"properties": {"email": "ann@x.co", "firstname": "Ann"}},
            str(ex[0].body))
ok &= check("Bearer auth on write", ex[0].headers.get("authorization") == f"Bearer {TOK}")
ok &= check("create output shaped",
            out.get("id") == "601" and out.get("objectType") == "contacts", str(out))

print("scenario: create_object requires non-empty properties")
out, ex = run_tool("hubspot", creds(tool="hubspot.create_object", objectType="contacts",
                                    properties={}), [])
ok &= check("empty properties rejected, no HTTP",
            "properties" in out.get("error", "") and len(ex) == 0, str(out))

print("scenario: update_object PATCH body")
out, ex = run_tool("hubspot", creds(tool="hubspot.update_object", objectType="tickets",
                                    objectId="42", properties={"hs_ticket_priority": "HIGH"}), [
    resp(200, body={"id": "42", "updatedAt": "2026-07-18T01:00:00Z"}),
])
ok &= check("method PATCH", ex[0].method == "PATCH", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/crm/v3/objects/tickets/42", ex[0].url)
ok &= check("PATCH body", ex[0].json == {"properties": {"hs_ticket_priority": "HIGH"}},
            str(ex[0].body))
ok &= check("update output", out == {"id": "42", "objectType": "tickets", "updated": True,
                                     "updatedAt": "2026-07-18T01:00:00Z"}, str(out))

print("scenario: add_note body — contact association typeId 202")
out, ex = run_tool("hubspot", creds(tool="hubspot.add_note", objectType="contacts",
                                    objectId=501, body="Agreed to follow up",
                                    timestamp="2026-07-18T12:00:00Z"), [
    resp(201, body={"id": "n-1", "createdAt": "2026-07-18T12:00:01Z"}),
])
ok &= check("URL is notes endpoint", ex[0].url == f"{BASE}/crm/v3/objects/notes", ex[0].url)
ok &= check("note body exact (hs_note_body + hs_timestamp + association 202)",
            ex[0].json == {"properties": {"hs_note_body": "Agreed to follow up",
                                          "hs_timestamp": "2026-07-18T12:00:00Z"},
                           "associations": [{"to": {"id": "501"},
                                             "types": [{"associationCategory": "HUBSPOT_DEFINED",
                                                        "associationTypeId": 202}]}]},
            str(ex[0].body))
ok &= check("note output", out == {"id": "n-1", "objectType": "contacts", "objectId": "501",
                                   "createdAt": "2026-07-18T12:00:01Z"}, str(out))

print("scenario: add_note association typeIds per objectType (190/214/228)")
for ot, type_id in (("companies", 190), ("deals", 214), ("tickets", 228)):
    out, ex = run_tool("hubspot", creds(tool="hubspot.add_note", objectType=ot, objectId="7",
                                        body="x", timestamp="2026-07-18T12:00:00Z"), [
        resp(201, body={"id": "n-2"}),
    ])
    ok &= check(f"{ot} -> associationTypeId {type_id}",
                ex[0].json["associations"][0]["types"][0]["associationTypeId"] == type_id,
                str(ex[0].json))

print("scenario: add_note requires timestamp (hs_timestamp mandatory)")
out, ex = run_tool("hubspot", creds(tool="hubspot.add_note", objectType="contacts",
                                    objectId="501", body="x"), [])
ok &= check("timestamp required error, no HTTP",
            "timestamp required" in out.get("error", "") and len(ex) == 0, str(out))

# ---------------------------------------------------------------------------
# 6. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("hubspot", creds(tool="hubspot.get_object", objectType="contacts",
                                    objectId="501"), [
    err(401, body={"status": "error", "category": "INVALID_AUTHENTICATION",
                   "message": "Authentication credentials not found.",
                   "correlationId": "abc"}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API message", "Authentication credentials not found." in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("token not leaked in error output", TOK not in raw, raw[:300])

print("scenario: 403 surfaces missing-scope hint")
out, ex = run_tool("hubspot", creds(tool="hubspot.search_objects", objectType="tickets"), [
    err(403, body={"status": "error", "message": "This app hasn't been granted all required scopes"}),
])
ok &= check("403 surfaced with scope hint",
            "403" in out.get("error", "") and "scope" in out["error"].lower(), str(out)[:300])

print("scenario: 429 includes Retry-After")
out, ex = run_tool("hubspot", creds(tool="hubspot.search_objects", objectType="contacts",
                                    query="x"), [
    err(429, body={"status": "error", "category": "RATE_LIMITS",
                   "message": "You have reached your secondly limit."},
        headers={"Retry-After": "7"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After included", "7" in out["error"] and "retry after" in out["error"].lower(),
            out.get("error", ""))
ok &= check("rate limit message included", "secondly limit" in out["error"], out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("hubspot", creds(tool="hubspot.list_owners"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: network unreachable (URLError) -> friendly error")
_src = open(f"{REPO}/skills/hubspot/main.py", encoding="utf-8").read()


def _unreachable(req, *a, **k):
    raise urllib.error.URLError("connection refused")


_buf = io.StringIO()
with patched(_unreachable), contextlib.redirect_stdout(_buf):
    exec(compile(_src, "hubspot/main.py", "exec"),
         {"params": creds(tool="hubspot.list_owners")})
out = json.loads(_buf.getvalue().strip())
ok &= check("URLError -> 'Could not reach HubSpot' with reason",
            out.get("error", "").startswith("Could not reach HubSpot")
            and "connection refused" in out["error"], str(out))
ok &= check("no traceback on URLError", "Traceback" not in json.dumps(out), str(out))

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("hubspot", creds(tool="hubspot.get_object", objectType="contacts"), [])
ok &= check("objectId required error", out.get("error") == "objectId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("hubspot", {"tool": "hubspot.search_objects", "objectType": "contacts",
                               "accessToken": ""}, [])
ok &= check("connect-first message names accessToken",
            "connect the HubSpot integration first" in out.get("error", "")
            and "accessToken" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("hubspot", creds(tool="hubspot.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: hubspot.nope", str(out))

# ---------------------------------------------------------------------------
# 7. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal objectId is percent-encoded")
evil = "abc/../def?x=1"
out, ex = run_tool("hubspot", creds(tool="hubspot.get_object", objectType="contacts",
                                    objectId=evil), [
    resp(200, body={"id": "x", "properties": {}}),
])
ok &= check("id fully quoted in URL (no path escape)",
            ex[0].url == f"{BASE}/crm/v3/objects/contacts/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' or '?' in URL", "../" not in ex[0].url and "?" not in ex[0].url,
            ex[0].url)

print("scenario: bare '..' objectId rejected outright")
out, ex = run_tool("hubspot", creds(tool="hubspot.update_object", objectType="contacts",
                                    objectId="..", properties={"a": "b"}), [])
ok &= check("'..' rejected, no HTTP", "Invalid objectId" in out.get("error", "") and len(ex) == 0,
            str(out))

print("scenario: objectType cannot be used for path injection")
out, ex = run_tool("hubspot", creds(tool="hubspot.search_objects",
                                    objectType="contacts/../../secrets"), [])
ok &= check("evil objectType rejected by enum, no HTTP",
            "objectType must be one of" in out.get("error", "") and len(ex) == 0, str(out))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("hubspot", creds(tool="hubspot.list_pipelines", objectType="tickets"), [
    err(403, body={"message": "forbidden"}),
])
ok &= check("accessToken absent from error output", TOK not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
