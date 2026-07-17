"""Offline mock-HTTP integration tests for the okta skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://acme.okta.com"
TOK = "tok123-SECRET-VALUE"


def creds(**extra):
    p = {"baseUrl": BASE, "apiToken": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. okta.search_users — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: search_users happy path / auth exactness")
out, ex = run_tool("okta", creds(tool="okta.search_users", q="ann"), [
    resp(200, body=[
        {"id": "00u1", "status": "ACTIVE", "created": "2025-01-01T00:00:00.000Z",
         "lastLogin": "2026-07-01T00:00:00.000Z", "type": {"id": "oty1"},
         "credentials": {"password": {}, "provider": {"type": "OKTA"}},
         "profile": {"firstName": "Ann", "lastName": "Lee", "email": "ann@x.co",
                     "login": "ann@x.co", "mobilePhone": "555"}},
        {"id": "00u2", "status": "SUSPENDED", "profile": {"firstName": "Bob",
         "lastName": "Ray", "email": "bob@x.co", "login": "bob@x.co"}},
    ]),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v1/users?limit=25&q=ann", ex[0].url)
ok &= check("Authorization is exactly 'SSWS <token>' (not Bearer)",
            ex[0].headers.get("authorization") == f"SSWS {TOK}", str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("trimmed fields present",
            out["users"][0]["email"] == "ann@x.co" and out["users"][0]["status"] == "ACTIVE"
            and out["users"][0]["lastLogin"] == "2026-07-01T00:00:00.000Z", str(out)[:300])
ok &= check("raw fields absent (credentials/created/nested profile)",
            "credentials" not in out["users"][0] and "created" not in out["users"][0]
            and "profile" not in out["users"][0], str(out["users"][0]))
ok &= check("token not echoed in output", TOK not in json.dumps(out))

# search param takes precedence over q
print("scenario: search_users uses 'search' param over 'q'")
out, ex = run_tool("okta", creds(tool="okta.search_users",
                                 search='status eq "ACTIVE"', q="ignored"), [
    resp(200, body=[]),
])
ok &= check("search encoded, q omitted",
            ex[0].url == f"{BASE}/api/v1/users?limit=25&search=status+eq+%22ACTIVE%22",
            ex[0].url)
ok &= check("empty result count 0", out.get("count") == 0, str(out))

# ---------------------------------------------------------------------------
# 2. okta.get_user — happy path
# ---------------------------------------------------------------------------
print("scenario: get_user happy path")
out, ex = run_tool("okta", creds(tool="okta.get_user", userId="00u1abcd"), [
    resp(200, body={"id": "00u1abcd", "status": "ACTIVE",
                    "created": "2025-01-01T00:00:00.000Z",
                    "activated": "2025-01-02T00:00:00.000Z",
                    "lastLogin": "2026-07-01T00:00:00.000Z",
                    "credentials": {"password": {"value-should-not-leak": True},
                                    "provider": {"type": "OKTA", "name": "OKTA"}},
                    "profile": {"firstName": "Ann", "login": "ann@x.co"},
                    "_links": {"self": {"href": "x"}}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v1/users/00u1abcd", ex[0].url)
ok &= check("SSWS auth", ex[0].headers.get("authorization") == f"SSWS {TOK}")
ok &= check("profile passed through", out.get("profile", {}).get("login") == "ann@x.co",
            str(out)[:300])
ok &= check("provider flattened to type", out.get("provider") == "OKTA", str(out)[:300])
ok &= check("raw credentials/_links absent",
            "credentials" not in out and "_links" not in out, str(out)[:300])

# ---------------------------------------------------------------------------
# 3. okta.list_groups — happy path
# ---------------------------------------------------------------------------
print("scenario: list_groups happy path")
out, ex = run_tool("okta", creds(tool="okta.list_groups", q="eng", limit=5), [
    resp(200, body=[{"id": "00g1", "type": "OKTA_GROUP",
                     "created": "2025-01-01T00:00:00.000Z",
                     "objectClass": ["okta:user_group"],
                     "profile": {"name": "Engineering", "description": "Eng team"}}]),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v1/groups?q=eng&limit=5", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out))
ok &= check("group summary shaped",
            out["groups"][0] == {"id": "00g1", "name": "Engineering",
                                 "description": "Eng team", "type": "OKTA_GROUP"},
            str(out["groups"][0]))

# ---------------------------------------------------------------------------
# 4. okta.list_user_apps — happy path (filter expression)
# ---------------------------------------------------------------------------
print("scenario: list_user_apps happy path")
out, ex = run_tool("okta", creds(tool="okta.list_user_apps", userId="00u1"), [
    resp(200, body=[{"id": "0oa1", "label": "Slack", "status": "ACTIVE",
                     "signOnMode": "SAML_2_0", "settings": {"deep": "stuff"}}]),
])
ok &= check("URL has encoded user.id filter",
            ex[0].url == f"{BASE}/api/v1/apps?filter=user.id+eq+%2200u1%22&limit=50",
            ex[0].url)
ok &= check("apps shaped, raw settings absent",
            out == {"count": 1, "apps": [{"id": "0oa1", "label": "Slack",
                                          "status": "ACTIVE", "signOnMode": "SAML_2_0"}]},
            str(out))

# ---------------------------------------------------------------------------
# 5. okta.query_system_log — happy path
# ---------------------------------------------------------------------------
print("scenario: query_system_log happy path")
out, ex = run_tool("okta", creds(tool="okta.query_system_log",
                                 since="2026-07-16T00:00:00Z", limit=10), [
    resp(200, body=[{"eventType": "user.session.start",
                     "published": "2026-07-16T12:00:00.000Z",
                     "displayMessage": "User login to Okta",
                     "severity": "INFO", "uuid": "raw-uuid",
                     "actor": {"id": "00u1", "displayName": "Ann Lee",
                               "alternateId": "ann@x.co"},
                     "outcome": {"result": "SUCCESS", "reason": None},
                     "target": [{"id": "t1", "type": "AppInstance",
                                 "displayName": "Slack", "alternateId": "slack"}]}]),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/api/v1/logs?since=2026-07-16T00%3A00%3A00Z&limit=10",
            ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ev = out["events"][0]
ok &= check("event shaped (actor/outcome/targets trimmed)",
            ev["eventType"] == "user.session.start" and ev["outcome"] == "SUCCESS"
            and ev["actor"] == {"displayName": "Ann Lee", "alternateId": "ann@x.co"}
            and ev["targets"] == [{"type": "AppInstance", "displayName": "Slack",
                                   "alternateId": "slack"}],
            str(ev))
ok &= check("raw uuid/severity absent", "uuid" not in ev and "severity" not in ev, str(ev))

# ---------------------------------------------------------------------------
# 6. okta.list_group_members — Link rel="next" pagination with cap
# ---------------------------------------------------------------------------
print("scenario: list_group_members follows Link rel=next with cap")


def member(i):
    return {"id": f"00u{i}", "status": "ACTIVE",
            "profile": {"firstName": f"F{i}", "lastName": f"L{i}",
                        "email": f"u{i}@x.co", "login": f"u{i}@x.co"}}


out, ex = run_tool("okta", creds(tool="okta.list_group_members", groupId="00g1", limit=3), [
    resp(200, body=[member(1), member(2)],
         headers={"Link": '<https://acme.okta.com/api/v1/groups/00g1/users?limit=2>; rel="self", '
                          '<https://acme.okta.com/api/v1/groups/00g1/users?after=cur2&limit=2>; rel="next"'}),
    resp(200, body=[member(3), member(4), member(5)]),  # no next link; over-delivers
])
ok &= check("two requests made (followed next link)", len(ex) == 2, repr(ex))
ok &= check("first page URL", ex[0].url == f"{BASE}/api/v1/groups/00g1/users?limit=3", ex[0].url)
ok &= check("second page carries after cursor",
            ex[1].url == f"{BASE}/api/v1/groups/00g1/users?limit=1&after=cur2", ex[1].url)
ok &= check("both pages authed with SSWS",
            all(e.headers.get("authorization") == f"SSWS {TOK}" for e in ex))
ok &= check("cap enforced: count == 3", out.get("count") == 3, str(out)[:200])
ok &= check("members list trimmed to cap and shaped",
            len(out["members"]) == 3 and out["members"][2]["login"] == "u3@x.co"
            and "profile" not in out["members"][0], str(out)[:300])

# stops when a page has no next link even if under cap
print("scenario: list_group_members stops without next link")
out, ex = run_tool("okta", creds(tool="okta.list_group_members", groupId="00g1", limit=500), [
    resp(200, body=[member(1)]),
])
ok &= check("single request, no phantom follow-up", len(ex) == 1, repr(ex))
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])

# ---------------------------------------------------------------------------
# 7. WRITE PATHS — add_user_to_group (PUT) and suspend_user (POST lifecycle)
# ---------------------------------------------------------------------------
print("scenario: add_user_to_group write path")
out, ex = run_tool("okta", creds(tool="okta.add_user_to_group",
                                 groupId="00g1", userId="00u1"), [
    resp(204),
])
ok &= check("method PUT", ex[0].method == "PUT", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v1/groups/00g1/users/00u1", ex[0].url)
ok &= check("no body on membership PUT", ex[0].body is None, str(ex[0].body))
ok &= check("SSWS auth on write", ex[0].headers.get("authorization") == f"SSWS {TOK}")
ok &= check("success output", out == {"added": True, "groupId": "00g1", "userId": "00u1"},
            str(out))

print("scenario: suspend_user POSTs to /lifecycle/suspend")
out, ex = run_tool("okta", creds(tool="okta.suspend_user", userId="00u9"), [
    resp(200, body={}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL is /lifecycle/suspend byte-exact",
            ex[0].url == f"{BASE}/api/v1/users/00u9/lifecycle/suspend", ex[0].url)
ok &= check("no body on suspend POST", ex[0].body is None, str(ex[0].body))
ok &= check("success output", out == {"suspended": True, "userId": "00u9"}, str(out))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("okta", creds(tool="okta.get_user", userId="00u1"), [
    err(401, body={"errorCode": "E0000011",
                   "errorSummary": "Invalid token provided",
                   "errorCauses": []}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API errorSummary", "Invalid token provided" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("token not leaked in error output", TOK not in raw, raw[:300])

print("scenario: 429 includes X-Rate-Limit-Reset")
out, ex = run_tool("okta", creds(tool="okta.search_users", q="x"), [
    err(429, body={"errorSummary": "API call exceeded rate limit"},
        headers={"X-Rate-Limit-Limit": "600", "X-Rate-Limit-Remaining": "0",
                 "X-Rate-Limit-Reset": "1789000123"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("reset epoch included", "1789000123" in out["error"], out.get("error", ""))
ok &= check("summary included", "rate limit" in out["error"].lower(), out.get("error", ""))

print("scenario: error causes appended, non-JSON error body tolerated")
out, ex = run_tool("okta", creds(tool="okta.get_user", userId="00u1"), [
    err(400, body={"errorSummary": "Bad request",
                   "errorCauses": [{"errorSummary": "field is invalid"}]}),
])
ok &= check("400 with causes", "400" in out["error"] and "field is invalid" in out["error"],
            out.get("error", ""))
out, ex = run_tool("okta", creds(tool="okta.get_user", userId="00u1"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("okta", creds(tool="okta.get_user"), [])
ok &= check("userId required error", out.get("error") == "userId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> friendly error, no HTTP call")
out, ex = run_tool("okta", {"tool": "okta.search_users", "baseUrl": "", "apiToken": ""}, [])
ok &= check("missing-credentials message",
            "error" in out and "credentials" in out["error"].lower(), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("okta", creds(tool="okta.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: okta.nope", str(out))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal id is percent-encoded")
evil = "abc/../def?x=1"
out, ex = run_tool("okta", creds(tool="okta.get_user", userId=evil), [
    resp(200, body={"id": "x", "profile": {}}),
])
ok &= check("id fully quoted in URL (no path escape)",
            ex[0].url == f"{BASE}/api/v1/users/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' or '?' in path", "../" not in ex[0].url and "?" not in ex[0].url,
            ex[0].url)

print("scenario: path-traversal groupId/userId on write tools percent-encoded")
out, ex = run_tool("okta", creds(tool="okta.suspend_user", userId="a/b c"), [
    resp(200, body={}),
])
ok &= check("suspend_user id quoted",
            ex[0].url == f"{BASE}/api/v1/users/a%2Fb%20c/lifecycle/suspend", ex[0].url)
out, ex = run_tool("okta", creds(tool="okta.add_user_to_group",
                                 groupId="g/../x", userId="u#1"), [
    resp(204),
])
ok &= check("add_user_to_group ids quoted",
            ex[0].url == f"{BASE}/api/v1/groups/g%2F..%2Fx/users/u%231", ex[0].url)

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("okta", creds(tool="okta.list_groups"), [
    err(403, body={"errorSummary": "forbidden"}),
])
ok &= check("apiToken absent from error output", TOK not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
