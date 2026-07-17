"""Offline mock-HTTP integration tests for the zendesk skill."""
import sys

from mockhttp import run_tool, resp, err, check

ok = True

CREDS = {"subdomain": "acme", "clientId": "cid-123", "clientSecret": "s3cr3t-XYZ"}
TOKEN_RESP = resp(200, body={"access_token": "ztok-abc", "token_type": "bearer"})


def creds(**kw):
    p = dict(CREDS)
    p.update(kw)
    return p


# ---------------------------------------------------------------------------
# 1. AUTH EXACTNESS — token POST is JSON to /oauth/tokens, API calls use Bearer
# ---------------------------------------------------------------------------
print("[auth exactness]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.search", query="type:ticket status:open"),
    [TOKEN_RESP,
     resp(200, body={"results": []})])
ok &= check("token request is POST", ex[0].method == "POST", repr(ex[0]))
ok &= check("token URL exact", ex[0].url == "https://acme.zendesk.com/oauth/tokens", ex[0].url)
ok &= check("token Content-Type is application/json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("token body is JSON (not form)",
            ex[0].body.lstrip().startswith("{") and ex[0].json is not None, str(ex[0].body)[:150])
ok &= check("token body grant_type=client_credentials",
            ex[0].json.get("grant_type") == "client_credentials", str(ex[0].json))
ok &= check("token body carries client_id byte-exactly",
            ex[0].json.get("client_id") == "cid-123", str(ex[0].json))
ok &= check("token body carries client_secret byte-exactly",
            ex[0].json.get("client_secret") == "s3cr3t-XYZ", str(ex[0].json))
ok &= check("API call uses Bearer token",
            ex[1].headers.get("authorization") == "Bearer ztok-abc", str(ex[1].headers))
ok &= check("API call has no client secret in headers",
            "s3cr3t-XYZ" not in str(ex[1].headers), str(ex[1].headers))

# ---------------------------------------------------------------------------
# 2. HAPPY PATHS — search, list_tickets, get_user (by id and by email)
# ---------------------------------------------------------------------------
print("[happy path: zendesk.search]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.search", query="login error", limit=2),
    [TOKEN_RESP,
     resp(200, body={"results": [
         {"result_type": "ticket", "id": 35, "subject": "Login error", "status": "open",
          "priority": "high", "type": "incident", "requester_id": 9, "assignee_id": 4,
          "tags": ["auth"], "created_at": "2026-07-01T00:00:00Z",
          "updated_at": "2026-07-02T00:00:00Z", "url": "https://acme.zendesk.com/api/v2/tickets/35.json",
          "description": "very long raw description", "raw_subject": "Login error"},
         {"result_type": "user", "id": 9, "name": "Ann Lee", "email": "ann@x.co", "role": "end-user",
          "active": True, "suspended": False, "organization_id": 1, "time_zone": "UTC",
          "created_at": "2025-01-01T00:00:00Z", "photo": {"big": "blob"}},
     ]})])
ok &= check("search: GET /api/v2/search.json",
            ex[1].method == "GET" and ex[1].url.startswith("https://acme.zendesk.com/api/v2/search.json?"),
            ex[1].url)
ok &= check("search: query params include query and per_page",
            "query=login+error" in ex[1].url and "per_page=2" in ex[1].url, ex[1].url)
ok &= check("search: count == 2", out.get("count") == 2, str(out)[:300])
ok &= check("search: ticket result shaped with result_type",
            out["results"][0].get("result_type") == "ticket"
            and out["results"][0].get("subject") == "Login error"
            and out["results"][0].get("status") == "open", str(out["results"][0]))
ok &= check("search: raw ticket fields trimmed (url/description/raw_subject absent)",
            "url" not in out["results"][0] and "description" not in out["results"][0]
            and "raw_subject" not in out["results"][0], str(out["results"][0]))
ok &= check("search: user result shaped, raw photo absent",
            out["results"][1].get("result_type") == "user"
            and out["results"][1].get("email") == "ann@x.co"
            and "photo" not in out["results"][1], str(out["results"][1]))

print("[happy path: zendesk.list_tickets]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.list_tickets", limit=1, sortBy="updated_at", sortOrder="asc"),
    [TOKEN_RESP,
     resp(200, body={"tickets": [
         {"id": 1, "subject": "Help", "status": "open", "priority": "normal", "type": None,
          "requester_id": 9, "assignee_id": None, "tags": [], "created_at": "2026-06-01T00:00:00Z",
          "updated_at": "2026-07-01T00:00:00Z", "url": "https://acme.zendesk.com/api/v2/tickets/1.json",
          "description": "raw body", "fields": [{"id": 5, "value": "x"}]}]})])
ok &= check("list_tickets: GET /api/v2/tickets.json with sort/per_page",
            ex[1].url.startswith("https://acme.zendesk.com/api/v2/tickets.json?")
            and "sort_by=updated_at" in ex[1].url and "sort_order=asc" in ex[1].url
            and "per_page=1" in ex[1].url, ex[1].url)
ok &= check("list_tickets: count + shaped ticket",
            out.get("count") == 1 and out["tickets"][0].get("subject") == "Help", str(out)[:300])
ok &= check("list_tickets: raw fields trimmed (url/description/fields absent)",
            all(k not in out["tickets"][0] for k in ("url", "description", "fields")),
            str(out["tickets"][0]))

print("[happy path: zendesk.list_tickets with status filter -> search API]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.list_tickets", status="open", sortBy="id"),
    [TOKEN_RESP,
     resp(200, body={"results": [
         {"result_type": "ticket", "id": 2, "subject": "Open one", "status": "open",
          "priority": None, "requester_id": 7, "tags": [], "created_at": "2026-07-10T00:00:00Z",
          "updated_at": "2026-07-11T00:00:00Z"}]})])
ok &= check("list_tickets(status): routed to search API",
            ex[1].url.startswith("https://acme.zendesk.com/api/v2/search.json?"), ex[1].url)
ok &= check("list_tickets(status): query encodes type:ticket status:open",
            "query=type%3Aticket+status%3Aopen" in ex[1].url, ex[1].url)
ok &= check("list_tickets(status): unsupported sortBy=id falls back to created_at",
            "sort_by=created_at" in ex[1].url, ex[1].url)
ok &= check("list_tickets(status): fallback note present",
            "note" in out and "created_at" in out["note"], str(out)[:300])
ok &= check("list_tickets(status): shaped output", out.get("count") == 1
            and out["tickets"][0]["subject"] == "Open one", str(out)[:300])

print("[happy path: zendesk.get_user]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.get_user", userId=42),
    [TOKEN_RESP,
     resp(200, body={"user": {"id": 42, "name": "Bo", "email": "bo@x.co", "role": "agent",
                              "active": True, "suspended": False, "organization_id": 3,
                              "time_zone": "UTC", "created_at": "2024-01-01T00:00:00Z",
                              "photo": {"big": "blob"}, "user_fields": {"x": 1}}})])
ok &= check("get_user: GET /api/v2/users/42.json",
            ex[1].method == "GET" and ex[1].url == "https://acme.zendesk.com/api/v2/users/42.json",
            ex[1].url)
ok &= check("get_user: shaped user, raw fields absent",
            out.get("id") == 42 and out.get("email") == "bo@x.co"
            and "photo" not in out and "user_fields" not in out, str(out))

out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.get_user", email="ann@x.co"),
    [TOKEN_RESP,
     resp(200, body={"users": [{"id": 9, "name": "Ann", "email": "ann@x.co", "role": "end-user",
                                "active": True, "suspended": False, "organization_id": None,
                                "time_zone": "UTC", "created_at": "2025-01-01T00:00:00Z"}]})])
ok &= check("get_user(email): GET /api/v2/users/search.json?query=...",
            ex[1].url == "https://acme.zendesk.com/api/v2/users/search.json?query=ann%40x.co",
            ex[1].url)
ok &= check("get_user(email): count + users list", out.get("count") == 1
            and out["users"][0]["name"] == "Ann", str(out)[:300])

# ---------------------------------------------------------------------------
# get_ticket makes TWO api calls (ticket + comments)
# ---------------------------------------------------------------------------
print("[zendesk.get_ticket: two API calls]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.get_ticket", ticketId=35, maxComments=2),
    [TOKEN_RESP,
     resp(200, body={"ticket": {"id": 35, "subject": "Login error", "status": "open",
                                "priority": "high", "type": "incident", "requester_id": 9,
                                "assignee_id": 4, "tags": ["auth"],
                                "created_at": "2026-07-01T00:00:00Z",
                                "updated_at": "2026-07-02T00:00:00Z",
                                "description": "cannot log in",
                                "organization_id": 3, "group_id": 5,
                                "via": {"channel": "email", "source": {"from": {}}},
                                "url": "https://acme.zendesk.com/api/v2/tickets/35.json"}}),
     resp(200, body={"comments": [
         {"id": 100, "author_id": 9, "public": True, "body": "cannot log in",
          "created_at": "2026-07-01T00:00:00Z", "html_body": "<p>cannot log in</p>",
          "attachments": []},
         {"id": 101, "author_id": 4, "public": False, "body": "looking into it",
          "created_at": "2026-07-01T01:00:00Z", "html_body": "<p>x</p>", "attachments": []},
         {"id": 102, "author_id": 9, "public": True, "body": "extra beyond max",
          "created_at": "2026-07-01T02:00:00Z"},
     ]})])
ok &= check("get_ticket: exactly 3 requests total (token + ticket + comments)",
            len(ex) == 3, repr(ex))
ok &= check("get_ticket: ticket URL", ex[1].url == "https://acme.zendesk.com/api/v2/tickets/35.json",
            ex[1].url)
ok &= check("get_ticket: comments URL with per_page",
            ex[2].url == "https://acme.zendesk.com/api/v2/tickets/35/comments.json?per_page=2",
            ex[2].url)
ok &= check("get_ticket: both API calls Bearer",
            ex[1].headers.get("authorization") == "Bearer ztok-abc"
            and ex[2].headers.get("authorization") == "Bearer ztok-abc", str(ex[2].headers))
ok &= check("get_ticket: detail shaped (description, via channel, org/group)",
            out.get("id") == 35 and out.get("description") == "cannot log in"
            and out.get("via") == "email" and out.get("organization_id") == 3
            and out.get("group_id") == 5, str(out)[:400])
ok &= check("get_ticket: comments clamped to maxComments and shaped",
            out.get("comment_count") == 2 and len(out["comments"]) == 2
            and out["comments"][0]["body"] == "cannot log in"
            and "html_body" not in out["comments"][0]
            and "attachments" not in out["comments"][0], str(out.get("comments"))[:300])
ok &= check("get_ticket: raw ticket url field absent", "url" not in out, str(out)[:400])

# ---------------------------------------------------------------------------
# 3. WRITE PATHS — add_comment (must-verify body), create_ticket, update_ticket
# ---------------------------------------------------------------------------
print("[write path: zendesk.add_comment]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.add_comment", ticketId=35, body="On it!", public=False),
    [TOKEN_RESP,
     resp(200, body={"ticket": {"id": 35, "status": "open"}})])
ok &= check("add_comment: PUT /api/v2/tickets/35.json",
            ex[1].method == "PUT" and ex[1].url == "https://acme.zendesk.com/api/v2/tickets/35.json",
            repr(ex[1]))
ok &= check("add_comment: exact body shape",
            ex[1].json == {"ticket": {"comment": {"body": "On it!", "public": False}}},
            str(ex[1].body))
ok &= check("add_comment: output confirms", out.get("commented") is True
            and out.get("public") is False and out.get("id") == 35, str(out))

out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.add_comment", ticketId=35, body="Reply"),
    [TOKEN_RESP, resp(200, body={"ticket": {"id": 35, "status": "open"}})])
ok &= check("add_comment: public defaults to true",
            ex[1].json == {"ticket": {"comment": {"body": "Reply", "public": True}}},
            str(ex[1].body))

print("[write path: zendesk.create_ticket]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.create_ticket", subject="Printer down", body="It smokes",
          requesterEmail="joe@x.co", requesterName="Joe", priority="high", tags=["hw"]),
    [TOKEN_RESP,
     resp(201, body={"ticket": {"id": 77, "subject": "Printer down", "status": "new",
                                "url": "https://acme.zendesk.com/api/v2/tickets/77.json"}})])
ok &= check("create_ticket: POST /api/v2/tickets.json",
            ex[1].method == "POST" and ex[1].url == "https://acme.zendesk.com/api/v2/tickets.json",
            repr(ex[1]))
ok &= check("create_ticket: exact body",
            ex[1].json == {"ticket": {"subject": "Printer down", "comment": {"body": "It smokes"},
                                      "requester": {"email": "joe@x.co", "name": "Joe"},
                                      "priority": "high", "tags": ["hw"]}},
            str(ex[1].body))
ok &= check("create_ticket: JSON content-type",
            ex[1].headers.get("content-type") == "application/json", str(ex[1].headers))
ok &= check("create_ticket: output", out.get("id") == 77 and out.get("created") is True, str(out))

print("[write path: zendesk.update_ticket]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.update_ticket", ticketId=35, status="solved", tags=[]),
    [TOKEN_RESP,
     resp(200, body={"ticket": {"id": 35, "status": "solved", "priority": "high",
                                "assignee_id": 4, "tags": []}})])
ok &= check("update_ticket: PUT with exact body (empty tags list preserved)",
            ex[1].method == "PUT"
            and ex[1].json == {"ticket": {"status": "solved", "tags": []}}, str(ex[1].body))
ok &= check("update_ticket: output", out.get("updated") is True and out.get("status") == "solved",
            str(out))

# ---------------------------------------------------------------------------
# 4. ERROR PATHS
# ---------------------------------------------------------------------------
print("[error: 401 on token]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.list_tickets"),
    [err(401, body={"error": "invalid_client",
                    "error_description": "Client authentication failed"})])
ok &= check("token 401: friendly error with status", "error" in out and "401" in out["error"],
            str(out))
ok &= check("token 401: friendly message included",
            "Client authentication failed" in out["error"], str(out))
ok &= check("token 401: no traceback", "Traceback" not in str(out), str(out))

print("[error: 401 on API call]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.search", query="x"),
    [TOKEN_RESP,
     err(401, body={"error": "Couldn't authenticate you"})])
ok &= check("api 401: friendly error with status", "error" in out and "401" in out["error"],
            str(out))
ok &= check("api 401: message surfaced", "Couldn't authenticate you" in out["error"], str(out))
ok &= check("api 401: no traceback", "Traceback" not in str(out), str(out))

print("[error: 429 rate limit]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.list_tickets"),
    [TOKEN_RESP,
     err(429, body={"error": "RateLimited"}, headers={"Retry-After": "37"})])
ok &= check("api 429: error mentions 429 + rate limit",
            "429" in out.get("error", "") and "rate limit" in out["error"], str(out))
ok &= check("api 429: Retry-After hint surfaced", "37" in out["error"], str(out))

out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.search", query="x"),
    [err(429, body="slow down", headers={"Retry-After": "60"})])
ok &= check("token 429: rate-limit message with hint",
            "429" in out.get("error", "") and "60" in out["error"], str(out))

print("[error: help-center 404 -> Guide not enabled]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.search_help_center", query="reset password"),
    [TOKEN_RESP,
     err(404, body={"error": "RecordNotFound", "description": "Not found"})])
ok &= check("help_center 404: Guide-not-enabled message",
            "Guide" in out.get("error", "") and "not enabled" in out["error"], str(out))

print("[happy path: zendesk.search_help_center]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.search_help_center", query="reset password", limit=1),
    [TOKEN_RESP,
     resp(200, body={"results": [
         {"id": 5, "title": "How to reset your password", "snippet": "…reset…",
          "html_url": "https://acme.zendesk.com/hc/en-us/articles/5", "section_id": 2,
          "locale": "en-us", "updated_at": "2026-01-01T00:00:00Z",
          "body": "<h1>huge html body</h1>", "outdated": False}]})])
ok &= check("help_center: GET articles/search.json with query+per_page",
            ex[1].url.startswith("https://acme.zendesk.com/api/v2/help_center/articles/search.json?")
            and "query=reset+password" in ex[1].url and "per_page=1" in ex[1].url, ex[1].url)
ok &= check("help_center: shaped articles, raw body absent",
            out.get("count") == 1 and out["articles"][0]["title"] == "How to reset your password"
            and "body" not in out["articles"][0] and "outdated" not in out["articles"][0],
            str(out)[:300])

print("[error: missing credentials / unknown tool / missing param]")
out, ex = run_tool("zendesk", {"tool": "zendesk.list_tickets", "subdomain": "acme"}, [])
ok &= check("missing creds: no HTTP, friendly error",
            len(ex) == 0 and "Missing Zendesk credentials" in out.get("error", ""), str(out))
out, ex = run_tool("zendesk", creds(tool="zendesk.nope"), [])
ok &= check("unknown tool: friendly error", out.get("error") == "Unknown tool: zendesk.nope",
            str(out))
# NOTE: handlers mint the OAuth token before validating tool params (house pattern),
# so exactly one HTTP exchange (the token POST) happens before the ValueError.
out, ex = run_tool("zendesk", creds(tool="zendesk.get_ticket"), [TOKEN_RESP])
ok &= check("get_ticket without ticketId: only token call, ValueError surfaced",
            len(ex) == 1 and ex[0].url.endswith("/oauth/tokens")
            and "ticketId required" in out.get("error", ""), str(out))

# ---------------------------------------------------------------------------
# 5. SECURITY PROBES
# ---------------------------------------------------------------------------
print("[security: path-ish ids are percent-encoded]")
out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.get_ticket", ticketId="abc/../def?x=1"),
    [TOKEN_RESP,
     resp(200, body={"ticket": {"id": 1}}),
     resp(200, body={"comments": []})])
ok &= check("get_ticket: path-ish ticketId percent-encoded in ticket URL",
            ex[1].url == "https://acme.zendesk.com/api/v2/tickets/abc%2F..%2Fdef%3Fx%3D1.json",
            ex[1].url)
ok &= check("get_ticket: path-ish ticketId percent-encoded in comments URL",
            ex[2].url.startswith(
                "https://acme.zendesk.com/api/v2/tickets/abc%2F..%2Fdef%3Fx%3D1/comments.json"),
            ex[2].url)

out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.get_user", userId="9/../../admin?a=1"),
    [TOKEN_RESP,
     resp(200, body={"user": {"id": 9}})])
ok &= check("get_user: path-ish userId percent-encoded",
            ex[1].url == "https://acme.zendesk.com/api/v2/users/9%2F..%2F..%2Fadmin%3Fa%3D1.json",
            ex[1].url)

out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.update_ticket", ticketId="1/../2?x=1", status="open"),
    [TOKEN_RESP,
     resp(200, body={"ticket": {"id": 2}})])
ok &= check("update_ticket: path-ish ticketId percent-encoded",
            ex[1].url == "https://acme.zendesk.com/api/v2/tickets/1%2F..%2F2%3Fx%3D1.json",
            ex[1].url)

print("[security: secret never leaks into printed output]")
raw_out, ex = run_tool(
    "zendesk",
    creds(tool="zendesk.list_tickets"),
    [err(500, body={"description": "Internal error"})])
ok &= check("secret absent from error output", "s3cr3t-XYZ" not in str(raw_out), str(raw_out))
ok &= check("clientId absent from error output", "cid-123" not in str(raw_out), str(raw_out))
ok &= check("500 on token: friendly error with status", "500" in raw_out.get("error", ""),
            str(raw_out))

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
