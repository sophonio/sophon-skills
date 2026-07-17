"""Offline mock-HTTP integration tests for the freshdesk skill."""
import base64
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = {"baseUrl": "https://acme.freshdesk.com", "apiKey": "sekret-key-9"}
EXPECTED_AUTH = "Basic " + base64.b64encode(b"sekret-key-9:X").decode()

ok = True


def section(name):
    print(name)


# ---------------------------------------------------------------- list_tickets
section("freshdesk.list_tickets — auth exactness + shaping")
raw_ticket = {
    "id": 101, "subject": "Printer on fire", "status": 2, "priority": 4,
    "requester_id": 7, "responder_id": 3, "created_at": "2026-07-01T09:00:00Z",
    "updated_at": "2026-07-02T10:00:00Z", "due_by": "2026-07-05T00:00:00Z",
    "tags": ["hardware"], "description": "<b>raw html</b>", "cc_emails": ["boss@acme.com"],
    "fr_escalated": False, "custom_fields": {"secret_field": 1},
}
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.list_tickets",
                                 "filter": "new_and_my_open", "orderBy": "updated_at",
                                 "orderType": "asc", "limit": 5},
                   [resp(200, body=[raw_ticket])])
ok &= check("one GET request", len(ex) == 1 and ex[0].method == "GET", repr(ex))
ok &= check("Authorization is Basic base64(apiKey + ':X')",
            ex[0].headers.get("authorization") == EXPECTED_AUTH, str(ex[0].headers))
ok &= check("Content-Type absent on GET (no body)",
            "content-type" not in ex[0].headers, str(ex[0].headers))
ok &= check("User-Agent identifies the skill",
            ex[0].headers.get("user-agent") == "sophon-freshdesk-skill", str(ex[0].headers))
ok &= check("url path is {base}/api/v2/tickets",
            ex[0].url.startswith("https://acme.freshdesk.com/api/v2/tickets?"), ex[0].url)
ok &= check("query params carried through",
            "filter=new_and_my_open" in ex[0].url and "order_by=updated_at" in ex[0].url
            and "order_type=asc" in ex[0].url and "per_page=5" in ex[0].url, ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
t = out["tickets"][0]
ok &= check("status int mapped to name", t.get("status") == "Open", str(t))
ok &= check("priority int mapped to name", t.get("priority") == "Urgent", str(t))
ok &= check("trimmed fields present", t.get("id") == 101 and t.get("subject") == "Printer on fire"
            and t.get("tags") == ["hardware"] and t.get("due_by") == "2026-07-05T00:00:00Z", str(t))
ok &= check("raw payload fields absent",
            "description" not in t and "cc_emails" not in t and "custom_fields" not in t, str(t))

section("freshdesk.list_tickets — limit clamped to 100, unknown status passes through")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.list_tickets", "limit": 5000},
                   [resp(200, body=[{"id": 1, "status": 99, "priority": 1}])])
ok &= check("per_page clamped to 100", "per_page=100" in ex[0].url, ex[0].url)
ok &= check("unmapped status stays numeric", out["tickets"][0]["status"] == 99, str(out)[:200])
ok &= check("priority 1 -> Low", out["tickets"][0]["priority"] == "Low", str(out)[:200])

# ------------------------------------------------------------------ get_ticket
section("freshdesk.get_ticket — two calls (ticket + conversations)")
raw_full = dict(raw_ticket, description_text="plain text body", type="Incident",
                attachments=[{"id": 1}])
convs = [{"id": 900, "body": "<p>html</p>", "body_text": "plain reply", "private": False,
          "incoming": True, "user_id": 7, "created_at": "2026-07-02T10:00:00Z",
          "attachments": [], "support_email": "help@acme.com"}]
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.get_ticket", "ticketId": 101},
                   [resp(200, body=raw_full), resp(200, body=convs)])
ok &= check("exactly two requests", len(ex) == 2, repr(ex))
ok &= check("first call GETs the ticket",
            ex[0].method == "GET" and ex[0].url == "https://acme.freshdesk.com/api/v2/tickets/101",
            repr(ex[0]))
ok &= check("second call GETs /conversations with default per_page=30",
            ex[1].method == "GET"
            and ex[1].url == "https://acme.freshdesk.com/api/v2/tickets/101/conversations?per_page=30",
            repr(ex[1]))
ok &= check("both calls authenticated",
            all(e.headers.get("authorization") == EXPECTED_AUTH for e in ex), repr(ex))
ok &= check("status/priority names in detail output",
            out.get("status") == "Open" and out.get("priority") == "Urgent", str(out)[:300])
ok &= check("description_text and type present",
            out.get("description_text") == "plain text body" and out.get("type") == "Incident",
            str(out)[:300])
c = out["conversations"][0]
ok &= check("conversation trimmed (body_text kept, html body dropped)",
            c.get("body_text") == "plain reply" and "body" not in c
            and "support_email" not in c, str(c))
ok &= check("raw ticket fields absent from detail", "attachments" not in out and "cc_emails" not in out,
            str(out)[:300])

section("freshdesk.get_ticket — conversationLimit clamped to 100")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.get_ticket", "ticketId": 101,
                                 "conversationLimit": 500},
                   [resp(200, body=raw_full), resp(200, body=[])])
ok &= check("conversations per_page clamped to 100",
            ex[1].url.endswith("/conversations?per_page=100"), ex[1].url)

section("freshdesk.get_ticket — missing ticketId is a friendly error, no HTTP")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.get_ticket"}, [])
ok &= check("no HTTP calls made", len(ex) == 0, repr(ex))
ok &= check("error mentions ticketId", "ticketId" in out.get("error", ""), str(out))

# -------------------------------------------------------------- search_tickets
section("freshdesk.search_tickets — query wrapped in double quotes in the URL")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_tickets",
                                 "query": "status:2 AND priority:4"},
                   [resp(200, body={"results": [raw_ticket], "total": 27})])
ok &= check("GET /search/tickets", ex[0].url.startswith(
    "https://acme.freshdesk.com/api/v2/search/tickets?"), ex[0].url)
ok &= check("query percent-encoded and wrapped in %22...%22",
            "query=%22status%3A2+AND+priority%3A4%22" in ex[0].url, ex[0].url)
ok &= check("count/total shaped", out.get("count") == 1 and out.get("total") == 27, str(out)[:200])
ok &= check("search result status mapped", out["tickets"][0]["status"] == "Open", str(out)[:200])

section("freshdesk.search_tickets — over-long query raises ValueError as {'error'}")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_tickets", "query": "a" * 513},
                   [])
ok &= check("no HTTP call for over-long query", len(ex) == 0, repr(ex))
ok &= check("error mentions the 510-char limit",
            "510" in out.get("error", "") and "512" in out.get("error", ""), str(out))
ok &= check("no traceback in output", "Traceback" not in json.dumps(out), str(out))

section("freshdesk.search_tickets — 510-char query is allowed (boundary)")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_tickets", "query": "b" * 510},
                   [resp(200, body={"results": [], "total": 0})])
ok &= check("boundary query goes through", out.get("count") == 0 and "error" not in out,
            str(out)[:200])

# ------------------------------------------------------------- search_contacts
section("freshdesk.search_contacts — exact email lookup + shaping")
raw_contact = {"id": 55, "name": "Jane Doe", "email": "jane@x.co", "phone": "123",
               "mobile": None, "company_id": 9, "active": True,
               "created_at": "2025-01-01T00:00:00Z", "avatar": {"url": "http://x"},
               "other_emails": ["j@y.z"]}
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_contacts",
                                 "email": "jane+test@x.co"},
                   [resp(200, body=[raw_contact])])
ok &= check("GET /contacts with urlencoded email",
            ex[0].url == "https://acme.freshdesk.com/api/v2/contacts?email=jane%2Btest%40x.co",
            ex[0].url)
ok &= check("contact shaped", out.get("count") == 1 and out["contacts"][0]["name"] == "Jane Doe",
            str(out)[:200])
ok &= check("raw contact fields absent",
            "avatar" not in out["contacts"][0] and "other_emails" not in out["contacts"][0],
            str(out)[:200])

section("freshdesk.search_contacts — query path wraps in quotes")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_contacts",
                                 "query": "name:'Jane'"},
                   [resp(200, body={"results": [raw_contact], "total": 1})])
ok &= check("GET /search/contacts with quoted query",
            "search/contacts?" in ex[0].url and "query=%22name%3A%27Jane%27%22" in ex[0].url,
            ex[0].url)
ok &= check("count shaped", out.get("count") == 1, str(out)[:200])

section("freshdesk.search_contacts — neither query nor email is a friendly error, no HTTP")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_contacts"}, [])
ok &= check("no HTTP call", len(ex) == 0, repr(ex))
ok &= check("error asks for query or email",
            "query" in out.get("error", "") and "email" in out.get("error", ""), str(out))

section("freshdesk.search_contacts — over-long query rejected without HTTP")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_contacts", "query": "c" * 511},
                   [])
ok &= check("no HTTP call for over-long contact query", len(ex) == 0, repr(ex))
ok &= check("contact query limit error mentions 510", "510" in out.get("error", ""), str(out))

# --------------------------------------------------------- write: create_ticket
section("freshdesk.create_ticket — exact POST body and method")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.create_ticket",
                                 "subject": "Help", "description": "It broke",
                                 "email": "u@x.co", "tags": ["vip"]},
                   [resp(201, body={"id": 200, "subject": "Help", "status": 2, "priority": 1,
                                    "created_at": "2026-07-17T00:00:00Z"})])
ok &= check("POST to /api/v2/tickets",
            ex[0].method == "POST" and ex[0].url == "https://acme.freshdesk.com/api/v2/tickets",
            repr(ex[0]))
ok &= check("Content-Type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("exact request body (defaults priority=1, status=2)",
            ex[0].json == {"subject": "Help", "description": "It broke", "email": "u@x.co",
                           "priority": 1, "status": 2, "tags": ["vip"]}, str(ex[0].body))
ok &= check("created ticket shaped with names",
            out == {"id": 200, "subject": "Help", "status": "Open", "priority": "Low",
                    "created_at": "2026-07-17T00:00:00Z"}, str(out))

# --------------------------------------------------------- write: update_ticket
section("freshdesk.update_ticket — PUT with only provided fields")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.update_ticket",
                                 "ticketId": 101, "status": 4, "responderId": 3},
                   [resp(200, body={"id": 101, "subject": "Printer on fire", "status": 4,
                                    "priority": 4, "responder_id": 3, "tags": []})])
ok &= check("PUT /tickets/101",
            ex[0].method == "PUT" and ex[0].url == "https://acme.freshdesk.com/api/v2/tickets/101",
            repr(ex[0]))
ok &= check("body has only status + responder_id",
            ex[0].json == {"status": 4, "responder_id": 3}, str(ex[0].body))
ok &= check("updated output mapped", out.get("status") == "Resolved" and out.get("updated") is True,
            str(out))

section("freshdesk.update_ticket — empty payload rejected without HTTP")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.update_ticket", "ticketId": 101}, [])
ok &= check("no HTTP call", len(ex) == 0, repr(ex))
ok &= check("friendly error", "nothing to update" in out.get("error", ""), str(out))

# -------------------------------------------------------------- write: add_note
section("freshdesk.add_note — private defaults to true in POST body")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.add_note",
                                 "ticketId": 101, "body": "Internal note"},
                   [resp(201, body={"id": 3000, "private": True,
                                    "created_at": "2026-07-17T01:00:00Z"})])
ok &= check("POST /tickets/101/notes",
            ex[0].method == "POST"
            and ex[0].url == "https://acme.freshdesk.com/api/v2/tickets/101/notes", repr(ex[0]))
ok &= check("body defaults private=true",
            ex[0].json == {"body": "Internal note", "private": True}, str(ex[0].body))
ok &= check("note output shaped", out.get("id") == 3000 and out.get("ticket_id") == 101
            and out.get("private") is True, str(out))

section("freshdesk.add_note — explicit private=false honored")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.add_note",
                                 "ticketId": 101, "body": "Public reply-ish note",
                                 "private": False},
                   [resp(201, body={"id": 3001, "private": False,
                                    "created_at": "2026-07-17T01:00:00Z"})])
ok &= check("body sends private=false",
            ex[0].json == {"body": "Public reply-ish note", "private": False}, str(ex[0].body))

# ----------------------------------------------------------------- error paths
section("error paths — 401 friendly, no traceback, no secret leak")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.list_tickets"},
                   [err(401, body={"code": "invalid_credentials",
                                   "message": "You have to be logged in to perform this action."})])
printed = json.dumps(out)
ok &= check("401 surfaces as {'error': ...}", "error" in out, printed[:200])
ok &= check("error includes HTTP status 401", "401" in out["error"], printed[:200])
ok &= check("error includes API message", "logged in" in out["error"], printed[:200])
ok &= check("no Python traceback", "Traceback" not in printed and "urllib" not in printed,
            printed[:300])
ok &= check("apiKey secret absent from output", "sekret-key-9" not in printed, printed[:300])
ok &= check("base64 of secret absent from output",
            base64.b64encode(b"sekret-key-9:X").decode() not in printed, printed[:300])

section("error paths — 429 surfaces Retry-After")
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.search_tickets", "query": "x:1"},
                   [err(429, body="", headers={"Retry-After": "42"})])
ok &= check("429 in error", "429" in out.get("error", ""), str(out))
ok &= check("rate-limit wording", "rate limit" in out.get("error", ""), str(out))
ok &= check("Retry-After value surfaced", "Retry after 42 seconds" in out.get("error", ""),
            str(out))

section("error paths — missing credentials and unknown tool")
out, ex = run_tool("freshdesk", {"tool": "freshdesk.list_tickets", "baseUrl": "",
                                 "apiKey": ""}, [])
ok &= check("missing creds friendly error", "credentials" in out.get("error", ""), str(out))
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.nope"}, [])
ok &= check("unknown tool friendly error", "Unknown tool" in out.get("error", ""), str(out))

# ------------------------------------------------------------- security probes
section("security — path-ish ticketId is percent-encoded (no path escape)")
evil = "abc/../def?x=1"
out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.get_ticket", "ticketId": evil},
                   [resp(200, body={"id": 1, "status": 2, "priority": 1}),
                    resp(200, body=[])])
ok &= check("get_ticket URL quotes id",
            "/api/v2/tickets/abc%2F..%2Fdef%3Fx%3D1" in ex[0].url and evil not in ex[0].url,
            ex[0].url)
ok &= check("conversations URL quotes id too",
            "/api/v2/tickets/abc%2F..%2Fdef%3Fx%3D1/conversations" in ex[1].url
            and evil not in ex[1].url, ex[1].url)

out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.update_ticket", "ticketId": evil,
                                 "status": 2},
                   [resp(200, body={"id": 1, "status": 2, "priority": 1, "tags": []})])
ok &= check("update_ticket URL quotes id",
            "/api/v2/tickets/abc%2F..%2Fdef%3Fx%3D1" in ex[0].url and evil not in ex[0].url,
            ex[0].url)

out, ex = run_tool("freshdesk", {**BASE, "tool": "freshdesk.add_note", "ticketId": evil,
                                 "body": "n"},
                   [resp(201, body={"id": 1, "private": True})])
ok &= check("add_note URL quotes id",
            "/api/v2/tickets/abc%2F..%2Fdef%3Fx%3D1/notes" in ex[0].url and evil not in ex[0].url,
            ex[0].url)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
