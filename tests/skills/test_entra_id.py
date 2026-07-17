"""Offline mock-HTTP integration tests for the entra-id Sophon skill."""
import sys
import urllib.parse

from mockhttp import run_tool, resp, err, check

ok = True
CREDS = {"tenantId": "11111111-2222-3333-4444-555555555555", "clientId": "cid-abc",
         "clientSecret": "S3cr3t~Value!xyz"}
TOKEN_URL = ("https://login.microsoftonline.com/11111111-2222-3333-4444-555555555555"
             "/oauth2/v2.0/token")
TOKEN_OK = resp(200, body={"access_token": "graphtok", "token_type": "Bearer", "expires_in": 3599})


def p(**kw):
    d = dict(CREDS)
    d.update(kw)
    return d


def path_of(url):
    return urllib.parse.urlsplit(url).path


# =========================================================================
# 1. AUTH EXACTNESS — token request byte-exact, Bearer on Graph call
# =========================================================================
print("[auth exactness]")
out, ex = run_tool("entra-id", p(tool="entra.list_applications"),
                   [TOKEN_OK, resp(200, body={"value": []})])
ok &= check("token: POST method", ex[0].method == "POST", repr(ex[0]))
ok &= check("token: exact tenant token URL", ex[0].url == TOKEN_URL, ex[0].url)
ok &= check("token: form-urlencoded content type",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("token: exact client-credentials form body",
            ex[0].body == ("grant_type=client_credentials&client_id=cid-abc"
                           "&client_secret=S3cr3t~Value%21xyz"
                           "&scope=https%3A%2F%2Fgraph.microsoft.com%2F.default"),
            str(ex[0].body))
ok &= check("graph: Bearer token from token response",
            ex[1].headers.get("authorization") == "Bearer graphtok", str(ex[1].headers))
ok &= check("graph: Accept application/json",
            ex[1].headers.get("accept") == "application/json", str(ex[1].headers))
ok &= check("graph: v1.0 base URL",
            ex[1].url.startswith("https://graph.microsoft.com/v1.0/applications?"), ex[1].url)

# =========================================================================
# 2. HAPPY PATHS — output shaping (trimmed fields present, raw fields absent)
# =========================================================================
print("[happy: search_users]")
raw_user = {"id": "u-1", "displayName": "Ann Lee", "mail": "ann@contoso.com",
            "userPrincipalName": "ann@contoso.com", "jobTitle": "Engineer",
            "department": "R&D", "accountEnabled": True,
            "businessPhones": ["+1 555"], "surname": "Lee"}
out, ex = run_tool("entra-id", p(tool="entra.search_users", query="ann"),
                   [TOKEN_OK, resp(200, body={"@odata.count": 1, "value": [raw_user]})])
ok &= check("search_users: GET /users", ex[1].method == "GET" and path_of(ex[1].url) == "/v1.0/users",
            repr(ex[1]))
ok &= check("search_users: ConsistencyLevel eventual header",
            ex[1].headers.get("consistencylevel") == "eventual", str(ex[1].headers))
ok &= check("search_users: $count=true sent", "%24count=true" in ex[1].url, ex[1].url)
ok &= check("search_users: uses $search with displayName/mail phrases",
            "%24search=" in ex[1].url and
            urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)["$search"][0]
            == '"displayName:ann" OR "mail:ann"', ex[1].url)
ok &= check("search_users: $select trims fields server-side",
            "%24select=id%2CdisplayName%2Cmail%2CuserPrincipalName%2CjobTitle%2Cdepartment"
            "%2CaccountEnabled" in ex[1].url, ex[1].url)
ok &= check("search_users: count shaping", out.get("count") == 1, str(out)[:200])
ok &= check("search_users: trimmed fields present",
            out["users"][0].get("displayName") == "Ann Lee"
            and out["users"][0].get("jobTitle") == "Engineer", str(out)[:300])
ok &= check("search_users: raw payload fields absent",
            "businessPhones" not in out["users"][0] and "surname" not in out["users"][0]
            and "@odata.count" not in out, str(out)[:300])

print("[happy: search_users prefix mode]")
out, ex = run_tool("entra-id", p(tool="entra.search_users", query="O'Brien", prefix=True),
                   [TOKEN_OK, resp(200, body={"value": []})])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("search_users(prefix): startswith filter with escaped quote",
            qs.get("$filter", [""])[0]
            == "startswith(displayName,'O''Brien') or startswith(mail,'O''Brien') "
               "or startswith(userPrincipalName,'O''Brien')", ex[1].url)
ok &= check("search_users(prefix): ConsistencyLevel eventual + $count=true",
            ex[1].headers.get("consistencylevel") == "eventual"
            and qs.get("$count") == ["true"], str(ex[1].headers))
ok &= check("search_users(prefix): empty result shaped", out == {"count": 0, "users": []},
            str(out)[:200])

print("[happy: get_user]")
raw_full = {"id": "u-9", "displayName": "Bob Kim", "mail": "bob@contoso.com",
            "userPrincipalName": "bob@contoso.com", "jobTitle": "PM", "department": "Product",
            "accountEnabled": True, "officeLocation": "B2", "mobilePhone": "+1 555",
            "createdDateTime": "2024-01-01T00:00:00Z", "userType": "Member",
            "manager": {"id": "m-1", "displayName": "Cara Diaz", "mail": "cara@contoso.com",
                        "@odata.type": "#microsoft.graph.user"}}
out, ex = run_tool("entra-id", p(tool="entra.get_user", userId="bob@contoso.com"),
                   [TOKEN_OK, resp(200, body=raw_full)])
ok &= check("get_user: single GET /users/{id} (no /manager path)",
            len(ex) == 2 and path_of(ex[1].url) == "/v1.0/users/bob%40contoso.com"
            and not any(path_of(e.url).endswith("/manager") for e in ex), repr(ex))
ok &= check("get_user: $expand=manager($select=...) used",
            urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
            .get("$expand", [""])[0] == "manager($select=id,displayName,mail)", ex[1].url)
ok &= check("get_user: manager trimmed to id/displayName/mail",
            out.get("manager") == {"id": "m-1", "displayName": "Cara Diaz",
                                   "mail": "cara@contoso.com"}, str(out)[:300])
ok &= check("get_user: extended profile fields present",
            out.get("officeLocation") == "B2" and out.get("userType") == "Member"
            and out.get("createdDateTime") == "2024-01-01T00:00:00Z", str(out)[:300])

print("[happy: get_user without manager]")
out, ex = run_tool("entra-id", p(tool="entra.get_user", userId="u-9"),
                   [TOKEN_OK, resp(200, body={"id": "u-9", "displayName": "Bob Kim"})])
ok &= check("get_user: manager null when absent", out.get("manager") is None, str(out)[:200])

print("[happy: list_role_members]")
out, ex = run_tool(
    "entra-id", p(tool="entra.list_role_members", roleName="global administrator"),
    [TOKEN_OK,
     resp(200, body={"value": [
         {"id": "r-1", "displayName": "Global Administrator"},
         {"id": "r-2", "displayName": "User Administrator"}]}),
     resp(200, body={"value": [
         {"id": "u-1", "displayName": "Ann Lee", "mail": "ann@contoso.com",
          "userPrincipalName": "ann@contoso.com",
          "@odata.type": "#microsoft.graph.user"}]})])
ok &= check("role_members: case-insensitive role match, members fetched by role id",
            path_of(ex[2].url) == "/v1.0/directoryRoles/r-1/members", repr(ex))
ok &= check("role_members: shaped output with role/count/type",
            out.get("role") == "Global Administrator" and out.get("count") == 1
            and out["members"][0].get("type") == "user" and out.get("truncated") is False,
            str(out)[:300])

print("[happy: list_role_members — role not activated]")
out, ex = run_tool("entra-id", p(tool="entra.list_role_members", roleName="Nonexistent Role"),
                   [TOKEN_OK, resp(200, body={"value": [
                       {"id": "r-2", "displayName": "User Administrator"}]})])
ok &= check("role_members: unactivated role returns message + activatedRoles",
            "message" in out and out.get("activatedRoles") == ["User Administrator"],
            str(out)[:300])

print("[happy: list_signin_logs]")
raw_signin = {"id": "s-1", "createdDateTime": "2026-07-16T08:00:00Z",
              "userPrincipalName": "ann@contoso.com", "userDisplayName": "Ann Lee",
              "appDisplayName": "Office 365", "ipAddress": "1.2.3.4",
              "clientAppUsed": "Browser",
              "status": {"errorCode": 50126, "failureReason": "Invalid credentials",
                         "additionalDetails": "MFA"},
              "location": {"city": "Oslo", "countryOrRegion": "NO", "state": "Oslo"},
              "deviceDetail": {"browser": "Edge"}}
out, ex = run_tool(
    "entra-id",
    p(tool="entra.list_signin_logs", since="2026-07-16T00:00:00Z",
      userPrincipalName="ann@contoso.com", errorCode=50126),
    [TOKEN_OK, resp(200, body={"value": [raw_signin]})])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("signin_logs: combined $filter",
            qs.get("$filter", [""])[0]
            == "createdDateTime ge 2026-07-16T00:00:00Z and "
               "userPrincipalName eq 'ann@contoso.com' and status/errorCode eq 50126",
            ex[1].url)
ok &= check("signin_logs: shaped entry (raw sub-fields absent)",
            out.get("count") == 1 and out["signIns"][0]["status"] == {
                "errorCode": 50126, "failureReason": "Invalid credentials"}
            and out["signIns"][0]["location"] == {"city": "Oslo", "countryOrRegion": "NO"}
            and "deviceDetail" not in out["signIns"][0], str(out)[:400])

print("[happy: list_applications]")
out, ex = run_tool("entra-id", p(tool="entra.list_applications"),
                   [TOKEN_OK, resp(200, body={"value": [
                       {"id": "obj-1", "appId": "app-1", "displayName": "My App",
                        "passwordCredentials": [
                            {"keyId": "k1", "displayName": "old", "hint": "abc",
                             "endDateTime": "2026-09-01T00:00:00Z"}]}]})])
ok &= check("applications: secret credentials trimmed to endDateTime only",
            out == {"count": 1, "applications": [
                {"appId": "app-1", "displayName": "My App",
                 "passwordCredentials": [{"endDateTime": "2026-09-01T00:00:00Z"}]}]},
            str(out)[:300])

print("[happy: list_user_groups]")
out, ex = run_tool("entra-id", p(tool="entra.list_user_groups", userId="u-9", limit=7),
                   [TOKEN_OK, resp(200, body={"value": [
                       {"id": "g-1", "displayName": "Eng", "groupTypes": ["Unified"],
                        "securityEnabled": True}]})])
ok &= check("user_groups: OData group cast path with $top",
            path_of(ex[1].url) == "/v1.0/users/u-9/memberOf/microsoft.graph.group"
            and "%24top=7" in ex[1].url, ex[1].url)
ok &= check("user_groups: shaped output",
            out == {"count": 1, "groups": [
                {"id": "g-1", "displayName": "Eng", "groupTypes": ["Unified"]}]}, str(out)[:300])

# =========================================================================
# 3. PAGINATION — list_group_members via @odata.nextLink
# =========================================================================
print("[pagination: list_group_members]")


def members_page(start, n, next_link=None):
    body = {"value": [
        {"id": f"u-{i}", "displayName": f"User {i}", "mail": f"u{i}@contoso.com",
         "userPrincipalName": f"u{i}@contoso.com", "@odata.type": "#microsoft.graph.user"}
        for i in range(start, start + n)]}
    if next_link:
        body["@odata.nextLink"] = next_link
    return resp(200, body=body)


NEXT1 = "https://graph.microsoft.com/v1.0/groups/g-1/members?$skiptoken=page2tok"
out, ex = run_tool(
    "entra-id", p(tool="entra.list_group_members", groupId="g-1", limit=5),
    [TOKEN_OK, members_page(0, 3, NEXT1), members_page(3, 3)])
ok &= check("members: first page GET /groups/{id}/members",
            path_of(ex[1].url) == "/v1.0/groups/g-1/members", repr(ex))
ok &= check("members: nextLink followed verbatim", ex[2].url == NEXT1, ex[2].url)
ok &= check("members: capped at limit with truncated flag",
            out.get("count") == 5 and len(out["members"]) == 5 and out.get("truncated") is True,
            str(out)[:300])
ok &= check("members: member shaping (type trimmed)",
            out["members"][0] == {"id": "u-0", "displayName": "User 0",
                                  "mail": "u0@contoso.com",
                                  "userPrincipalName": "u0@contoso.com", "type": "user"},
            str(out["members"][0]))

# page cap: 5 pages max even when nextLink keeps coming and limit not reached
pages = [members_page(i * 10, 10, f"https://graph.microsoft.com/v1.0/groups/g-1/members?$skiptoken=p{i+2}")
         for i in range(5)]
out, ex = run_tool("entra-id", p(tool="entra.list_group_members", groupId="g-1", limit=200),
                   [TOKEN_OK] + pages)
ok &= check("members: stops at 5 pages (6 HTTP calls incl. token)",
            len(ex) == 6 and out.get("count") == 50 and out.get("truncated") is True,
            f"exchanges={len(ex)} out={str(out)[:150]}")

# single page, no nextLink -> not truncated
out, ex = run_tool("entra-id", p(tool="entra.list_group_members", groupId="g-1"),
                   [TOKEN_OK, members_page(0, 2)])
ok &= check("members: single page not truncated",
            out.get("count") == 2 and out.get("truncated") is False, str(out)[:200])

# =========================================================================
# 4. ERROR PATHS
# =========================================================================
print("[errors]")
out, ex = run_tool(
    "entra-id", p(tool="entra.get_user", userId="u-9"),
    [TOKEN_OK, err(401, body={"error": {"code": "InvalidAuthenticationToken",
                                        "message": "Access token has expired."}})])
ok &= check("401: friendly error with status",
            list(out.keys()) == ["error"] and "401" in out["error"]
            and "Access token has expired." in out["error"], str(out)[:300])
ok &= check("401: no Python traceback",
            "Traceback" not in out["error"] and "urllib" not in out["error"], str(out)[:300])

out, ex = run_tool(
    "entra-id", p(tool="entra.search_users", query="ann"),
    [TOKEN_OK, err(429, body={"error": {"code": "TooManyRequests",
                                        "message": "Too many requests."}},
                   headers={"Retry-After": "120"})])
ok &= check("429: throttle message includes Retry-After seconds",
            "429" in out.get("error", "") and "retry after 120" in out["error"],
            str(out)[:300])

out, ex = run_tool(
    "entra-id", p(tool="entra.search_users", query="ann"),
    [err(400, body={"error": "invalid_client",
                    "error_description": "AADSTS7000215: Invalid client secret provided."})])
ok &= check("token failure: friendly error with status + AADSTS detail",
            "Token request failed (400)" in out.get("error", "")
            and "AADSTS7000215" in out["error"], str(out)[:300])

out, ex = run_tool(
    "entra-id",
    p(tool="entra.list_signin_logs", since="2026-07-16T00:00:00Z"),
    [TOKEN_OK, err(403, body={"error": {
        "code": "Authentication_RequestFromNonPremiumTenantOrB2CTenant",
        "message": "Neither tenant is B2C or tenant doesn't have premium license"}})])
ok &= check("signin_logs: P1/P2 license error surfaced clearly",
            "P1/P2 license" in out.get("error", ""), str(out)[:300])

# House style: token is obtained first, then params validated — so exactly one
# exchange (the token POST) and no Graph call for a malformed `since`.
out, ex = run_tool("entra-id",
                   p(tool="entra.list_signin_logs", since="yesterday"), [TOKEN_OK])
ok &= check("signin_logs: bad since rejected before any Graph call",
            len(ex) == 1 and "ISO 8601" in out.get("error", ""),
            f"exchanges={ex!r} out={str(out)[:200]}")

out, ex = run_tool("entra-id", {"tool": "entra.search_users", "query": "ann"}, [])
ok &= check("missing credentials: no HTTP, friendly error",
            len(ex) == 0 and "credentials" in out.get("error", "").lower(), str(out)[:200])

out, ex = run_tool("entra-id", p(tool="entra.bogus"), [])
ok &= check("unknown tool: friendly error", out == {"error": "Unknown tool: entra.bogus"},
            str(out)[:200])

# =========================================================================
# 5. SECURITY PROBES
# =========================================================================
print("[security]")
out, ex = run_tool("entra-id", p(tool="entra.get_user", userId="abc/../def?x=1"),
                   [TOKEN_OK, resp(200, body={"id": "abc"})])
ok &= check("path probe: id percent-encoded, no path escape",
            "/users/abc%2F..%2Fdef%3Fx%3D1" in ex[1].url and "abc/../def" not in ex[1].url
            and "?x=1" not in ex[1].url.replace("%3Fx%3D1", ""), ex[1].url)

out, ex = run_tool("entra-id", p(tool="entra.list_group_members", groupId="g/../h"),
                   [TOKEN_OK, resp(200, body={"value": []})])
ok &= check("path probe: groupId percent-encoded",
            path_of(ex[1].url) == "/v1.0/groups/g%2F..%2Fh/members", ex[1].url)

out, ex = run_tool(
    "entra-id", p(tool="entra.search_users", query="ann"),
    [TOKEN_OK, err(401, body={"error": {"code": "InvalidAuthenticationToken",
                                        "message": "denied"}})])
ok &= check("secret never leaks into error output",
            "S3cr3t~Value!xyz" not in str(out) and "S3cr3t" not in str(out), str(out)[:300])

out, ex = run_tool("entra-id", p(tool="entra.search_users", query='a:b ("c")'),
                   [TOKEN_OK, resp(200, body={"value": []})])
ok &= check("KQL injection chars stripped from $search",
            urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)["$search"][0]
            == '"displayName:a b c" OR "mail:a b c"', ex[1].url)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
