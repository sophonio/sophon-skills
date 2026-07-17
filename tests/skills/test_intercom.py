"""Offline mock-HTTP integration tests for the Sophon 'intercom' skill.

Run: python test_intercom.py   (exit 1 on any failure)
"""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://api.intercom.io"
TOKEN = "SUPERSECRET-intercom-token-XYZ"
CREDS = {"baseUrl": BASE, "accessToken": TOKEN}

ok = True


def auth_ok(ex):
    return (ex.headers.get("authorization") == f"Bearer {TOKEN}"
            and ex.headers.get("intercom-version") == "2.15")


# ---------------------------------------------------------------- scenario 1
print("scenario 1: search_conversations — auth, POST query body, shaping, HTML strip")
out, ex = run_tool(
    "intercom",
    {"tool": "intercom.search_conversations", **CREDS,
     "state": "open", "limit": 5, "cursor": "cur1"},
    [resp(200, body={
        "type": "conversation.list",
        "conversations": [{
            "type": "conversation", "id": "c100", "state": "open", "priority": "priority",
            "read": True, "admin_assignee_id": 77, "team_assignee_id": None,
            "created_at": 1750000000, "updated_at": 1750000100,
            "source": {"type": "email", "subject": "<b>Billing</b> issue",
                       "body": "<p>Hello <i>there</i>,&nbsp;my card was <br/>charged twice</p>"},
            "tags": {"tags": []}, "statistics": {"time_to_admin_reply": 12345},
        }],
        "pages": {"type": "pages", "next": {"starting_after": "cur2"}},
        "total_count": 41,
    })])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("Bearer + Intercom-Version headers", auth_ok(ex[0]), str(ex[0].headers))
ok &= check("Accept: application/json", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("POST /conversations/search",
            ex[0].method == "POST" and ex[0].url == f"{BASE}/conversations/search", repr(ex[0]))
ok &= check("Content-Type json on write body",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("exact search body {query, pagination}",
            ex[0].json == {"query": {"field": "state", "operator": "=", "value": "open"},
                           "pagination": {"per_page": 5, "starting_after": "cur1"}},
            str(ex[0].body))
ok &= check("count == 1", out.get("count") == 1, str(out)[:300])
conv = (out.get("conversations") or [{}])[0]
ok &= check("HTML stripped from snippet",
            conv.get("snippet") == "Hello there, my card was charged twice", str(conv)[:300])
ok &= check("HTML stripped from subject", conv.get("subject") == "Billing issue", str(conv)[:300])
ok &= check("trimmed fields present",
            conv.get("id") == "c100" and conv.get("state") == "open"
            and conv.get("adminAssigneeId") == 77 and conv.get("updatedAt") == 1750000100,
            str(conv)[:300])
ok &= check("raw payload fields absent",
            "source" not in conv and "statistics" not in conv and "tags" not in conv
            and "admin_assignee_id" not in conv, str(conv)[:300])
ok &= check("nextCursor surfaced", out.get("nextCursor") == "cur2", str(out)[:300])

# ---------------------------------------------------------------- scenario 2
print("scenario 2: search_conversations — no filters falls back to match-all query")
out, ex = run_tool(
    "intercom", {"tool": "intercom.search_conversations", **CREDS},
    [resp(200, body={"conversations": [], "pages": {}})])
ok &= check("match-all query body",
            ex[0].json == {"query": {"field": "updated_at", "operator": ">", "value": 0},
                           "pagination": {"per_page": 20}}, str(ex[0].body))
ok &= check("empty page shape", out == {"count": 0, "conversations": []}, str(out)[:200])

# ---------------------------------------------------------------- scenario 3
print("scenario 3: search_conversations — multiple filters combine with AND")
out, ex = run_tool(
    "intercom",
    {"tool": "intercom.search_conversations", **CREDS,
     "state": "closed", "assigneeId": "42", "updatedSince": 1749000000},
    [resp(200, body={"conversations": [], "pages": {}})])
ok &= check("AND query with three typed terms",
            ex[0].json["query"] == {"operator": "AND", "value": [
                {"field": "state", "operator": "=", "value": "closed"},
                {"field": "admin_assignee_id", "operator": "=", "value": 42},
                {"field": "updated_at", "operator": ">", "value": 1749000000},
            ]}, str(ex[0].body))

# ---------------------------------------------------------------- scenario 4
print("scenario 4: get_conversation — GET by id, parts trimmed, HTML stripped")
out, ex = run_tool(
    "intercom", {"tool": "intercom.get_conversation", **CREDS, "conversationId": "c100"},
    [resp(200, body={
        "type": "conversation", "id": "c100", "state": "open", "priority": "not_priority",
        "admin_assignee_id": 77, "team_assignee_id": 5,
        "created_at": 1750000000, "updated_at": 1750000100,
        "source": {"subject": "Refund <em>request</em>",
                   "body": "<div>Please refund &amp; close my account.</div>"},
        "contacts": {"contacts": [{"type": "contact", "id": "ct9"}]},
        "conversation_parts": {"type": "conversation_part.list", "total_count": 2,
                               "conversation_parts": [
            {"type": "conversation_part", "part_type": "comment",
             "author": {"type": "contact", "name": "Sam", "id": "ct9"},
             "body": "<p>It happened <b>again</b></p>", "created_at": 1750000050,
             "attachments": [], "redacted": False},
            {"type": "conversation_part", "part_type": "note",
             "author": {"type": "admin", "name": "Ann", "id": "77"},
             "body": "<p>Escalating to billing</p>", "created_at": 1750000090,
             "attachments": [], "redacted": False},
        ]},
    })])
ok &= check("GET /conversations/c100",
            ex[0].method == "GET" and ex[0].url == f"{BASE}/conversations/c100", repr(ex[0]))
ok &= check("Bearer + Intercom-Version headers", auth_ok(ex[0]), str(ex[0].headers))
ok &= check("no request body on GET", ex[0].body is None, str(ex[0].body))
ok &= check("snippet HTML stripped w/ entity",
            out.get("snippet") == "Please refund & close my account.", str(out)[:300])
ok &= check("contactIds extracted", out.get("contactIds") == ["ct9"], str(out)[:300])
ok &= check("totalParts counted", out.get("totalParts") == 2, str(out)[:300])
parts = out.get("conversationParts") or []
ok &= check("parts trimmed and HTML stripped",
            len(parts) == 2 and parts[0] == {"partType": "comment", "authorType": "contact",
                                             "authorName": "Sam", "body": "It happened again",
                                             "createdAt": 1750000050},
            str(parts)[:400])
ok &= check("raw part fields absent",
            "attachments" not in json.dumps(out) and "part_type" not in json.dumps(out),
            str(out)[:400])

# ---------------------------------------------------------------- scenario 5
print("scenario 5: search_contacts — email shortcut, POST query body, shaping")
out, ex = run_tool(
    "intercom", {"tool": "intercom.search_contacts", **CREDS, "email": "sam@x.co"},
    [resp(200, body={
        "type": "list", "total_count": 1,
        "data": [{"type": "contact", "id": "ct9", "role": "user", "name": "Sam Roe",
                  "email": "sam@x.co", "phone": None, "external_id": "u-9",
                  "created_at": 1740000000, "last_seen_at": 1750000000,
                  "custom_attributes": {"plan": "pro"}, "avatar": {"image_url": "http://x/a.png"}}],
        "pages": {"next": {"starting_after": "ctcur"}},
    })])
ok &= check("POST /contacts/search",
            ex[0].method == "POST" and ex[0].url == f"{BASE}/contacts/search", repr(ex[0]))
ok &= check("Bearer + Intercom-Version headers", auth_ok(ex[0]), str(ex[0].headers))
ok &= check("exact email query body",
            ex[0].json == {"query": {"field": "email", "operator": "=", "value": "sam@x.co"},
                           "pagination": {"per_page": 20}}, str(ex[0].body))
ok &= check("count and trimmed contact",
            out.get("count") == 1 and out["contacts"][0] == {
                "id": "ct9", "role": "user", "name": "Sam Roe", "email": "sam@x.co",
                "phone": None, "externalId": "u-9", "createdAt": 1740000000,
                "lastSeenAt": 1750000000}, str(out)[:400])
ok &= check("raw contact fields absent",
            "avatar" not in json.dumps(out) and "external_id" not in json.dumps(out),
            str(out)[:300])
ok &= check("nextCursor surfaced", out.get("nextCursor") == "ctcur", str(out)[:300])

# ---------------------------------------------------------------- scenario 6
print("scenario 6: search_contacts — IN operator turns comma list into array")
out, ex = run_tool(
    "intercom",
    {"tool": "intercom.search_contacts", **CREDS,
     "field": "role", "operator": "IN", "value": "user, lead"},
    [resp(200, body={"data": [], "pages": {}})])
ok &= check("IN value is an array",
            ex[0].json["query"] == {"field": "role", "operator": "IN", "value": ["user", "lead"]},
            str(ex[0].body))

# ---------------------------------------------------------------- scenario 7
print("scenario 7: get_contact — GET by id, profile shaping")
out, ex = run_tool(
    "intercom", {"tool": "intercom.get_contact", **CREDS, "contactId": "ct9"},
    [resp(200, body={
        "type": "contact", "id": "ct9", "role": "user", "name": "Sam Roe", "email": "sam@x.co",
        "phone": "+1555", "external_id": "u-9", "created_at": 1740000000,
        "updated_at": 1750000001, "signed_up_at": 1740000002, "last_seen_at": 1750000000,
        "location": {"type": "location", "city": "Oslo", "region": "Oslo", "country": "Norway",
                     "country_code": "NOR"},
        "companies": {"type": "list", "data": [{"type": "company", "id": "co1"}]},
        "custom_attributes": {"plan": "pro"},
        "avatar": {"image_url": "http://x/a.png"},
    })])
ok &= check("GET /contacts/ct9",
            ex[0].method == "GET" and ex[0].url == f"{BASE}/contacts/ct9", repr(ex[0]))
ok &= check("Bearer + Intercom-Version headers", auth_ok(ex[0]), str(ex[0].headers))
ok &= check("profile shaped",
            out.get("id") == "ct9" and out.get("externalId") == "u-9"
            and out.get("location") == {"city": "Oslo", "region": "Oslo", "country": "Norway"}
            and out.get("companies") == ["co1"]
            and out.get("customAttributes") == {"plan": "pro"}
            and out.get("signedUpAt") == 1740000002, str(out)[:400])
ok &= check("raw fields absent",
            "avatar" not in json.dumps(out) and "country_code" not in json.dumps(out),
            str(out)[:300])

# ---------------------------------------------------------------- scenario 8
print("scenario 8: list_articles — GET with query params, shaping")
out, ex = run_tool(
    "intercom", {"tool": "intercom.list_articles", **CREDS, "limit": 10, "page": 2},
    [resp(200, body={
        "type": "list", "total_count": 12,
        "data": [{"type": "article", "id": "a1", "title": "Getting started", "state": "published",
                  "url": "https://help.x.co/a1", "body": "<p>long html body</p>",
                  "author_id": 77, "workspace_id": "w1"}],
    })])
ok &= check("GET /articles with per_page and page",
            ex[0].method == "GET" and ex[0].url == f"{BASE}/articles?per_page=10&page=2",
            repr(ex[0]))
ok &= check("Bearer + Intercom-Version headers", auth_ok(ex[0]), str(ex[0].headers))
ok &= check("article shaping",
            out == {"count": 1, "totalCount": 12,
                    "articles": [{"id": "a1", "title": "Getting started", "state": "published",
                                  "url": "https://help.x.co/a1"}]}, str(out)[:400])

print("scenario 8b: list_articles — defaults omit page param")
out, ex = run_tool(
    "intercom", {"tool": "intercom.list_articles", **CREDS},
    [resp(200, body={"data": [], "total_count": 0})])
ok &= check("default per_page=25, no page", ex[0].url == f"{BASE}/articles?per_page=25",
            repr(ex[0]))

# ---------------------------------------------------------------- scenario 9
print("scenario 9: add_note — resolves admin via GET /me first, message_type note")
out, ex = run_tool(
    "intercom",
    {"tool": "intercom.add_note", **CREDS, "conversationId": "c100",
     "body": "<b>internal</b>: refund approved"},
    [resp(200, body={"type": "admin", "id": "784", "name": "Ann", "email": "ann@x.co"}),
     resp(200, body={"type": "conversation", "id": "c100", "state": "open"})])
ok &= check("two exchanges: /me then reply", len(ex) == 2, repr(ex))
ok &= check("first call is GET /me",
            ex[0].method == "GET" and ex[0].url == f"{BASE}/me", repr(ex[0]))
ok &= check("auth on /me", auth_ok(ex[0]), str(ex[0].headers))
ok &= check("POST /conversations/c100/reply",
            ex[1].method == "POST" and ex[1].url == f"{BASE}/conversations/c100/reply",
            repr(ex[1]))
ok &= check("auth on reply", auth_ok(ex[1]), str(ex[1].headers))
ok &= check("exact note body",
            ex[1].json == {"message_type": "note", "type": "admin", "admin_id": "784",
                           "body": "<b>internal</b>: refund approved"}, str(ex[1].body))
ok &= check("note output", out == {"id": "c100", "state": "open", "noteAdded": True},
            str(out)[:200])

# ---------------------------------------------------------------- scenario 10
print("scenario 10: reply_customer — message_type comment")
out, ex = run_tool(
    "intercom",
    {"tool": "intercom.reply_customer", **CREDS, "conversationId": "c100",
     "body": "Refund is on its way."},
    [resp(200, body={"type": "admin", "id": "784"}),
     resp(200, body={"type": "conversation", "id": "c100", "state": "open"})])
ok &= check("GET /me then POST reply",
            len(ex) == 2 and ex[0].url == f"{BASE}/me"
            and ex[1].method == "POST" and ex[1].url == f"{BASE}/conversations/c100/reply",
            repr(ex))
ok &= check("exact comment body",
            ex[1].json == {"message_type": "comment", "type": "admin", "admin_id": "784",
                           "body": "Refund is on its way."}, str(ex[1].body))
ok &= check("reply output", out == {"id": "c100", "state": "open", "replied": True},
            str(out)[:200])

# ---------------------------------------------------------------- scenario 11
print("scenario 11: update_conversation — close and snooze part payloads")
out, ex = run_tool(
    "intercom",
    {"tool": "intercom.update_conversation", **CREDS, "conversationId": "c100",
     "action": "close"},
    [resp(200, body={"type": "admin", "id": "784"}),
     resp(200, body={"type": "conversation", "id": "c100", "state": "closed",
                     "admin_assignee_id": 77, "team_assignee_id": None,
                     "snoozed_until": None})])
ok &= check("close: POST /conversations/c100/parts",
            ex[1].method == "POST" and ex[1].url == f"{BASE}/conversations/c100/parts",
            repr(ex))
ok &= check("close: exact payload",
            ex[1].json == {"message_type": "close", "type": "admin", "admin_id": "784"},
            str(ex[1].body))
ok &= check("close: shaped output",
            out == {"id": "c100", "state": "closed", "action": "close",
                    "adminAssigneeId": 77, "teamAssigneeId": None, "snoozedUntil": None},
            str(out)[:300])

out, ex = run_tool(
    "intercom",
    {"tool": "intercom.update_conversation", **CREDS, "conversationId": "c100",
     "action": "snooze", "snoozedUntil": 1750100000},
    [resp(200, body={"type": "admin", "id": "784"}),
     resp(200, body={"type": "conversation", "id": "c100", "state": "snoozed",
                     "snoozed_until": 1750100000})])
ok &= check("snooze: exact payload",
            ex[1].json == {"message_type": "snoozed", "admin_id": "784",
                           "snoozed_until": 1750100000}, str(ex[1].body))
ok &= check("snooze: output carries snoozedUntil",
            out.get("state") == "snoozed" and out.get("snoozedUntil") == 1750100000,
            str(out)[:300])

# ---------------------------------------------------------------- scenario 12
print("scenario 12: 401 error — friendly {error}, has status, no traceback, no token leak")
out, ex = run_tool(
    "intercom", {"tool": "intercom.get_conversation", **CREDS, "conversationId": "c100"},
    [err(401, body={"type": "error.list",
                    "errors": [{"code": "unauthorized", "message": "Access Token Invalid"}]})])
printed = json.dumps(out)
ok &= check("error key present", "error" in out and len(out) == 1, printed[:300])
ok &= check("status 401 in message", "401" in out.get("error", ""), printed[:300])
ok &= check("Intercom message surfaced", "Access Token Invalid" in out.get("error", ""),
            printed[:300])
ok &= check("no traceback in output", "Traceback" not in printed, printed[:300])
ok &= check("token not leaked in output", TOKEN not in printed, printed[:300])

# ---------------------------------------------------------------- scenario 13
print("scenario 13: 429 error — Retry-After surfaced in the message")
out, ex = run_tool(
    "intercom", {"tool": "intercom.list_articles", **CREDS},
    [err(429, body={"type": "error.list",
                    "errors": [{"code": "rate_limit_exceeded", "message": "Rate limit exceeded"}]},
         headers={"Retry-After": "23"})])
ok &= check("429 in message", "429" in out.get("error", ""), str(out)[:300])
ok &= check("retry-after hint present", "retry after 23" in out.get("error", ""),
            str(out)[:300])
ok &= check("no traceback / no token", "Traceback" not in json.dumps(out)
            and TOKEN not in json.dumps(out), str(out)[:300])

# ---------------------------------------------------------------- scenario 14
print("scenario 14: security — path-ish ids are percent-encoded (no path escape)")
EVIL = "abc/../def?x=1"
QUOTED = "abc%2F..%2Fdef%3Fx%3D1"
out, ex = run_tool(
    "intercom", {"tool": "intercom.get_conversation", **CREDS, "conversationId": EVIL},
    [resp(200, body={"id": "abc", "state": "open", "source": {},
                     "conversation_parts": {"conversation_parts": []}})])
ok &= check("get_conversation id percent-encoded",
            ex[0].url == f"{BASE}/conversations/{QUOTED}", ex[0].url)

out, ex = run_tool(
    "intercom", {"tool": "intercom.get_contact", **CREDS, "contactId": EVIL},
    [resp(200, body={"id": "abc"})])
ok &= check("get_contact id percent-encoded",
            ex[0].url == f"{BASE}/contacts/{QUOTED}", ex[0].url)

out, ex = run_tool(
    "intercom",
    {"tool": "intercom.add_note", **CREDS, "conversationId": EVIL, "body": "n"},
    [resp(200, body={"type": "admin", "id": "784"}),
     resp(200, body={"id": "abc", "state": "open"})])
ok &= check("add_note conversation id percent-encoded",
            ex[1].url == f"{BASE}/conversations/{QUOTED}/reply", ex[1].url)

# ---------------------------------------------------------------- scenario 15
print("scenario 15: validation — bad state / missing creds are friendly errors, no HTTP")
out, ex = run_tool(
    "intercom", {"tool": "intercom.search_conversations", **CREDS, "state": "pending"}, [])
ok &= check("bad state rejected without HTTP",
            len(ex) == 0 and "state must be one of" in out.get("error", ""), str(out)[:300])

out, ex = run_tool(
    "intercom", {"tool": "intercom.get_contact", "contactId": "ct9"}, [])
ok &= check("missing credentials friendly error",
            len(ex) == 0 and "credentials" in out.get("error", "").lower(), str(out)[:300])

out, ex = run_tool("intercom", {"tool": "intercom.nope", **CREDS}, [])
ok &= check("unknown tool friendly error",
            len(ex) == 0 and "Unknown tool" in out.get("error", ""), str(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
