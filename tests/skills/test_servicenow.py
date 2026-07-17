"""Offline mock-HTTP integration tests for the servicenow Sophon skill."""
import base64
import json
import sys
import urllib.parse

from mockhttp import run_tool, resp, err, check

BASE = "https://acme.service-now.com"
BASIC = {"baseUrl": BASE, "username": "svc-sophon", "password": "s3cr3t!pw"}
OAUTH = {"baseUrl": BASE, "clientId": "cid-abc", "clientSecret": "shh-oauth-secret"}

ok = True


def qs(url):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)


def path_of(url):
    return urllib.parse.urlsplit(url).path


# ---------------------------------------------------------------- 1. AUTH: basic
print("[auth: basic]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.search_records", "table": "incident"},
    [resp(200, body={"result": []})])
expected_basic = "Basic " + base64.b64encode(b"svc-sophon:s3cr3t!pw").decode()
ok &= check("exactly one request", len(ex) == 1, repr(ex))
ok &= check("Authorization is exact Basic base64(user:pass)",
            ex[0].headers.get("authorization") == expected_basic, str(ex[0].headers))
ok &= check("GET method", ex[0].method == "GET", ex[0].method)
ok &= check("path is /api/now/table/incident",
            path_of(ex[0].url) == "/api/now/table/incident", ex[0].url)
q = qs(ex[0].url)
ok &= check("sysparm_display_value=true", q.get("sysparm_display_value") == ["true"], str(q))
ok &= check("sysparm_exclude_reference_link=true",
            q.get("sysparm_exclude_reference_link") == ["true"], str(q))
ok &= check("default sysparm_limit=20", q.get("sysparm_limit") == ["20"], str(q))
ok &= check("default sysparm_fields sent",
            q.get("sysparm_fields") ==
            ["sys_id,number,name,short_description,state,priority,assigned_to,sys_updated_on"],
            str(q))
ok &= check("empty result shapes to count=0", out == {"count": 0, "records": []}, str(out))

# ---------------------------------------------------------------- 2. AUTH: OAuth
print("[auth: oauth client-credentials]")
out, ex = run_tool(
    "servicenow",
    {**OAUTH, "tool": "snow.get_record", "table": "incident",
     "sys_id": "9d385017c611228701d22104cc95c371"},
    [resp(200, body={"access_token": "atok-123", "token_type": "Bearer", "expires_in": 1800}),
     resp(200, body={"result": {"sys_id": "9d385017c611228701d22104cc95c371",
                                "number": "INC0000060", "short_description": "VPN down",
                                "state": "In Progress", "assigned_to": ""}})])
ok &= check("two requests: token then api", len(ex) == 2, repr(ex))
ok &= check("token POST to {baseUrl}/oauth_token.do",
            ex[0].method == "POST" and ex[0].url == f"{BASE}/oauth_token.do", repr(ex[0]))
ok &= check("token request is form-encoded",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
form = urllib.parse.parse_qs(ex[0].body or "")
ok &= check("token form: grant_type=client_credentials",
            form.get("grant_type") == ["client_credentials"], str(form))
ok &= check("token form: client_id + client_secret",
            form.get("client_id") == ["cid-abc"] and
            form.get("client_secret") == ["shh-oauth-secret"], str(form))
ok &= check("token request has no Authorization header",
            "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("api call uses Bearer token",
            ex[1].headers.get("authorization") == "Bearer atok-123", str(ex[1].headers))
ok &= check("get_record path table/sys_id",
            path_of(ex[1].url) == "/api/now/table/incident/9d385017c611228701d22104cc95c371",
            ex[1].url)
q = qs(ex[1].url)
ok &= check("get_record sends display-value params",
            q.get("sysparm_display_value") == ["true"] and
            q.get("sysparm_exclude_reference_link") == ["true"], str(q))
ok &= check("get_record output shaped, empty fields trimmed",
            out == {"sys_id": "9d385017c611228701d22104cc95c371", "number": "INC0000060",
                    "short_description": "VPN down", "state": "In Progress"}, str(out))

# ---------------------------------------------------------------- 3. HAPPY: search_records
print("[happy: search_records]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.search_records", "table": "change_request",
     "sysparm_query": "active=true^priority=1", "limit": 2, "offset": 4,
     "fields": "sys_id,number,state"},
    [resp(200, body={"result": [
        {"sys_id": "aaa", "number": "CHG001", "state": "Assess"},
        {"sys_id": "bbb", "number": "CHG002", "state": ""}]})])
q = qs(ex[0].url)
ok &= check("sysparm_query passed through", q.get("sysparm_query") == ["active=true^priority=1"],
            str(q))
ok &= check("custom fields/limit/offset",
            q.get("sysparm_fields") == ["sys_id,number,state"] and
            q.get("sysparm_limit") == ["2"] and q.get("sysparm_offset") == ["4"], str(q))
ok &= check("count reflects records", out.get("count") == 2, str(out))
ok &= check("records trimmed (empty state dropped)",
            out.get("records") == [{"sys_id": "aaa", "number": "CHG001", "state": "Assess"},
                                   {"sys_id": "bbb", "number": "CHG002"}], str(out))
ok &= check("no raw envelope keys in output", "result" not in out, str(out))

# ---------------------------------------------------------------- 4. HAPPY: search_knowledge
print("[happy: search_knowledge]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.search_knowledge", "query": "reset^password", "limit": 5},
    [resp(200, body={"result": [
        {"sys_id": "k1", "number": "KB0000001", "short_description": "How to reset password",
         "workflow_state": "Published", "sys_view_count": "42", "kb_category": ""}]})])
ok &= check("kb path", path_of(ex[0].url) == "/api/now/table/kb_knowledge", ex[0].url)
q = qs(ex[0].url)
ok &= check("query pinned to published + '^' in user text stripped",
            q.get("sysparm_query") ==
            ["workflow_state=published^short_descriptionLIKEreset password"
             "^ORtextLIKEreset password"], str(q))
ok &= check("kb limit honored", q.get("sysparm_limit") == ["5"], str(q))
ok &= check("articles shaped with count", out.get("count") == 1 and
            out.get("articles") == [{"sys_id": "k1", "number": "KB0000001",
                                     "short_description": "How to reset password",
                                     "workflow_state": "Published", "sys_view_count": "42"}],
            str(out))

# ---------------------------------------------------------------- 5. HAPPY: get_user (user + group)
print("[happy: get_user]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.get_user", "query": "abel.tuter@example.com"},
    [resp(200, body={"result": [
        {"sys_id": "u1", "user_name": "abel.tuter", "name": "Abel Tuter",
         "email": "abel.tuter@example.com", "title": "", "active": "true"}]})])
ok &= check("user lookup hits sys_user", path_of(ex[0].url) == "/api/now/table/sys_user",
            ex[0].url)
q = qs(ex[0].url)
ok &= check("user encoded query",
            q.get("sysparm_query") ==
            ["user_name=abel.tuter@example.com^ORemail=abel.tuter@example.com"
             "^ORnameLIKEabel.tuter@example.com"], str(q))
ok &= check("users key + trim", out == {"count": 1, "users": [
    {"sys_id": "u1", "user_name": "abel.tuter", "name": "Abel Tuter",
     "email": "abel.tuter@example.com", "active": "true"}]}, str(out))

out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.get_user", "query": "Network", "type": "group"},
    [resp(200, body={"result": [{"sys_id": "g1", "name": "Network", "email": "",
                                 "active": "true"}]})])
ok &= check("group lookup hits sys_user_group",
            path_of(ex[0].url) == "/api/now/table/sys_user_group", ex[0].url)
ok &= check("groups key in output", out.get("count") == 1 and
            out.get("groups") == [{"sys_id": "g1", "name": "Network", "active": "true"}],
            str(out))

# ---------------------------------------------------------------- 6. WRITE: create_incident
print("[write: create_incident]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.create_incident", "short_description": "Email down",
     "description": "Mail server unreachable", "caller_id": "u1sysid", "urgency": "1",
     "impact": "2", "assignment_group": "g1sysid"},
    [resp(201, body={"result": {"sys_id": "newinc", "number": "INC0010001",
                                "short_description": "Email down", "state": "New",
                                "priority": "2 - High", "urgency": "1 - High",
                                "impact": "2 - Medium", "assignment_group": "Network",
                                "opened_at": "2026-07-17 10:00:00"}})])
ok &= check("POST to /api/now/table/incident",
            ex[0].method == "POST" and path_of(ex[0].url) == "/api/now/table/incident",
            repr(ex[0]))
ok &= check("create body exact JSON",
            ex[0].json == {"short_description": "Email down",
                           "description": "Mail server unreachable", "caller_id": "u1sysid",
                           "urgency": "1", "impact": "2", "assignment_group": "g1sysid"},
            str(ex[0].body))
ok &= check("create sends Content-Type json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
q = qs(ex[0].url)
ok &= check("create query has display-value params",
            q.get("sysparm_display_value") == ["true"] and
            q.get("sysparm_exclude_reference_link") == ["true"], str(q))
ok &= check("created record shaped", out.get("number") == "INC0010001" and
            out.get("sys_id") == "newinc" and "result" not in out, str(out))

# ---------------------------------------------------------------- 7. WRITE: update_record + add_work_note
print("[write: update_record / add_work_note]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.update_record", "table": "incident", "sys_id": "abc123",
     "fields": {"state": "2", "assignment_group": "g1sysid"}},
    [resp(200, body={"result": {"sys_id": "abc123", "number": "INC0000060", "state": "In Progress",
                                "sys_updated_on": "2026-07-17 10:05:00"}})])
ok &= check("PATCH to table/sys_id",
            ex[0].method == "PATCH" and
            path_of(ex[0].url) == "/api/now/table/incident/abc123", repr(ex[0]))
ok &= check("update body is exactly the fields object",
            ex[0].json == {"state": "2", "assignment_group": "g1sysid"}, str(ex[0].body))
ok &= check("updated flag set", out.get("updated") is True and out.get("state") == "In Progress",
            str(out))

out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.add_work_note", "sys_id": "abc123",
     "work_notes": "Rebooted the switch"},
    [resp(200, body={"result": {"sys_id": "abc123", "number": "INC0000060",
                                "state": "In Progress"}})])
ok &= check("work note PATCHes incident/sys_id",
            ex[0].method == "PATCH" and
            path_of(ex[0].url) == "/api/now/table/incident/abc123", repr(ex[0]))
ok &= check("work note body exact", ex[0].json == {"work_notes": "Rebooted the switch"},
            str(ex[0].body))
ok &= check("work_note_added flag", out.get("work_note_added") is True, str(out))

# ---------------------------------------------------------------- 8. ERRORS
print("[errors]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.get_record", "table": "incident", "sys_id": "abc123"},
    [err(401, body={"error": {"message": "User Not Authenticated",
                              "detail": "Required to provide Auth information"},
                    "status": "failure"})])
raw = json.dumps(out)
ok &= check("401 -> friendly error object", set(out.keys()) == {"error"}, str(out))
ok &= check("401 error includes status code", "401" in out.get("error", ""), str(out))
ok &= check("401 error includes server message", "User Not Authenticated" in out.get("error", ""),
            str(out))
ok &= check("no traceback leaked", "Traceback" not in raw and "urllib" not in raw, raw[:300])

out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.search_records", "table": "incident"},
    [err(429, body=b"", headers={"Retry-After": "30"})])
ok &= check("429 -> error with status", "429" in out.get("error", ""), str(out))
ok &= check("429 -> rate-limit message", "rate limit" in out.get("error", "").lower(), str(out))

out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.does_not_exist"},
    [], )
ok &= check("unknown tool -> error, no request",
            "Unknown tool" in out.get("error", "") and len(ex) == 0, str(out))

out, ex = run_tool(
    "servicenow",
    {"tool": "snow.get_record", "baseUrl": BASE, "username": "only-user",
     "table": "incident", "sys_id": "x"},
    [], )
ok &= check("incomplete credentials -> connect-integration error",
            "credentials" in out.get("error", "").lower() and len(ex) == 0, str(out))

# ---------------------------------------------------------------- 9. SECURITY
print("[security]")
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.get_record", "table": "incident", "sys_id": "abc/../def?x=1"},
    [resp(200, body={"result": {"sys_id": "weird"}})])
ok &= check("path-ish sys_id fully percent-encoded",
            path_of(ex[0].url) == "/api/now/table/incident/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok &= check("no path traversal or query smuggling in URL",
            "../" not in ex[0].url and "?x=1" not in ex[0].url, ex[0].url)

out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.search_records", "table": "incident/../sys_user?bad=1"},
    [resp(200, body={"result": []})])
ok &= check("path-ish table name percent-encoded",
            path_of(ex[0].url) == "/api/now/table/incident%2F..%2Fsys_user%3Fbad%3D1", ex[0].url)

# secret non-leakage: basic-auth password on an error path
out, ex = run_tool(
    "servicenow",
    {**BASIC, "tool": "snow.get_record", "table": "incident", "sys_id": "abc123"},
    [err(403, body={"error": {"message": "Insufficient rights"}})])
ok &= check("password never appears in output", "s3cr3t!pw" not in json.dumps(out),
            json.dumps(out)[:300])

# secret non-leakage: OAuth client secret when the token endpoint itself fails
out, ex = run_tool(
    "servicenow",
    {**OAUTH, "tool": "snow.search_records", "table": "incident"},
    [err(401, body={"error": "invalid_client",
                    "error_description": "Invalid client credentials"})])
raw = json.dumps(out)
ok &= check("token failure -> friendly error with status",
            "401" in out.get("error", "") and "Invalid client credentials" in out.get("error", ""),
            str(out))
ok &= check("client secret never appears in output", "shh-oauth-secret" not in raw, raw[:300])
ok &= check("no traceback on token failure", "Traceback" not in raw, raw[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
