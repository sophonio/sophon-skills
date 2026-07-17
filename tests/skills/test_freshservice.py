"""Offline mock-HTTP integration tests for the freshservice skill."""
import base64
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://acme.freshservice.com"
KEY = "sekrit-api-key-123"
CREDS = {"baseUrl": BASE, "apiKey": KEY}
EXPECTED_AUTH = "Basic " + base64.b64encode(f"{KEY}:X".encode()).decode()

ok = True


def tool(name, **kw):
    p = dict(CREDS)
    p["tool"] = f"freshservice.{name}"
    p.update(kw)
    return p


# ---------------------------------------------------------------- 1. AUTH EXACTNESS
print("[auth exactness]")
out, ex = run_tool("freshservice", tool("list_tickets"),
                   [resp(200, body={"tickets": []})])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("Authorization is Basic b64(apiKey + ':X')",
            ex[0].headers.get("authorization") == EXPECTED_AUTH, str(ex[0].headers))
ok &= check("URL is {base}/api/v2/tickets?per_page=30",
            ex[0].url == f"{BASE}/api/v2/tickets?per_page=30", ex[0].url)
ok &= check("method is GET", ex[0].method == "GET", ex[0].method)
ok &= check("Accept: application/json", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("GET sends no body", ex[0].body is None, repr(ex[0].body))

# ------------------------------------------------------------------ 2. HAPPY PATHS
print("[happy path: list_tickets]")
raw_ticket = {"id": 7, "subject": "VPN down", "status": 2, "priority": 4,
              "requester_id": 1001, "group_id": 5, "created_at": "2026-07-01T08:00:00Z",
              "updated_at": "2026-07-02T09:30:00Z",
              "description": "<b>secret raw html</b>", "description_text": "raw text",
              "cc_emails": ["boss@acme.com"], "custom_fields": {"internal": "x"}}
out, ex = run_tool("freshservice",
                   tool("list_tickets", limit=5, updated_since="2026-07-01T00:00:00Z",
                        filter="new_and_my_open"),
                   [resp(200, body={"tickets": [raw_ticket]})])
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("query carries per_page, updated_since, filter",
            "per_page=5" in ex[0].url and "updated_since=2026-07-01T00%3A00%3A00Z" in ex[0].url
            and "filter=new_and_my_open" in ex[0].url, ex[0].url)
t = out["tickets"][0]
ok &= check("status int mapped to name", t.get("status") == "Open", str(t))
ok &= check("priority int mapped to name", t.get("priority") == "Urgent", str(t))
ok &= check("trimmed fields present",
            t.get("id") == 7 and t.get("subject") == "VPN down" and t.get("requester_id") == 1001
            and t.get("group_id") == 5 and t.get("updated_at") == "2026-07-02T09:30:00Z", str(t))
ok &= check("raw payload fields absent",
            "description" not in t and "cc_emails" not in t and "custom_fields" not in t, str(t))

print("[happy path: get_ticket]")
out, ex = run_tool("freshservice", tool("get_ticket", ticketId=42),
                   [resp(200, body={"ticket": {"id": 42, "subject": "Printer",
                                               "description_text": "It smokes",
                                               "description": "<p>It smokes</p>",
                                               "status": 3, "priority": 2, "requester_id": 8,
                                               "responder_id": 3, "group_id": 2,
                                               "created_at": "c", "updated_at": "u",
                                               "due_by": "d", "attachments": [{"big": "blob"}]}}),
                    resp(200, body={"conversations": [
                        {"id": 900, "user_id": 3, "incoming": False, "private": True,
                         "created_at": "c1", "body_text": "note text",
                         "body": "<div>html</div>", "to_emails": ["x@y.z"]}]})])
ok &= check("two requests (ticket + conversations)", len(ex) == 2, repr(ex))
ok &= check("first URL /api/v2/tickets/42", ex[0].url == f"{BASE}/api/v2/tickets/42", ex[0].url)
ok &= check("second URL /api/v2/tickets/42/conversations",
            ex[1].url == f"{BASE}/api/v2/tickets/42/conversations", ex[1].url)
ok &= check("status/priority mapped", out.get("status") == "Pending" and out.get("priority") == "Medium",
            str(out)[:300])
ok &= check("description_text kept, raw html/attachments dropped",
            out.get("description_text") == "It smokes" and "description" not in out
            and "attachments" not in out, str(out)[:300])
conv = out["conversations"][0]
ok &= check("conversation trimmed", conv.get("body_text") == "note text" and "body" not in conv
            and "to_emails" not in conv, str(conv))

print("[happy path: list_changes]")
out, ex = run_tool("freshservice", tool("list_changes", limit=10),
                   [resp(200, body={"changes": [
                       {"id": 1, "subject": "Upgrade DB", "status": 4, "risk": 3,
                        "planned_start_date": "2026-08-01T00:00:00Z",
                        "planned_end_date": "2026-08-02T00:00:00Z", "description": "raw"},
                       {"id": 2, "subject": "Patch OS", "status": 6, "risk": 1,
                        "planned_start_date": None, "planned_end_date": None},
                       {"id": 3, "subject": "Odd", "status": 99, "risk": 2}]})])
ok &= check("changes URL with per_page", ex[0].url == f"{BASE}/api/v2/changes?per_page=10", ex[0].url)
ok &= check("count == 3", out.get("count") == 3, str(out)[:200])
c1, c2, c3 = out["changes"]
ok &= check("change status 4 -> 'Pending Release'", c1.get("status") == "Pending Release", str(c1))
ok &= check("change status 6 -> 'Closed'", c2.get("status") == "Closed", str(c2))
ok &= check("unknown change status passes through", c3.get("status") == 99, str(c3))
ok &= check("risk mapped (3 -> High, 1 -> Low)",
            c1.get("risk") == "High" and c2.get("risk") == "Low", f"{c1} {c2}")
ok &= check("raw change fields absent", "description" not in c1, str(c1))

print("[happy path: search_assets]")
out, ex = run_tool("freshservice", tool("search_assets", query="MacBook Pro", field="asset_tag"),
                   [resp(200, body={"assets": [
                       {"display_id": 55, "name": "MacBook Pro", "asset_tag": "ASSET-55",
                        "asset_type_id": 9, "user_id": 12, "levelfield": "raw",
                        "type_fields": {"serial": "S1"}}]})])
ok &= check("assets search query percent-encoded",
            ex[0].url == f"{BASE}/api/v2/assets?search=%22asset_tag%3A%27MacBook+Pro%27%22&per_page=30",
            ex[0].url)
a = out["assets"][0]
ok &= check("asset shaped", out.get("count") == 1 and a.get("display_id") == 55
            and a.get("asset_tag") == "ASSET-55", str(out)[:200])
ok &= check("raw asset fields absent", "type_fields" not in a and "levelfield" not in a, str(a))

# ------------------------------------------------------------------- 3. WRITE PATHS
print("[write path: create_ticket]")
out, ex = run_tool("freshservice",
                   tool("create_ticket", subject="Laptop broken", description="Screen cracked",
                        email="user@acme.com", priority=3),
                   [resp(201, body={"ticket": {"id": 101, "subject": "Laptop broken",
                                               "status": 2, "priority": 3}})])
ok &= check("POST to /api/v2/tickets",
            ex[0].method == "POST" and ex[0].url == f"{BASE}/api/v2/tickets", repr(ex[0]))
ok &= check("Content-Type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("exact create body",
            ex[0].json == {"subject": "Laptop broken", "description": "Screen cracked",
                           "email": "user@acme.com", "priority": 3, "status": 2, "source": 2},
            str(ex[0].body))
ok &= check("create output shaped", out.get("id") == 101 and out.get("created") is True
            and out.get("priority") == "High", str(out))

print("[write path: update_ticket]")
out, ex = run_tool("freshservice",
                   tool("update_ticket", ticketId=42, status=4, priority=2, groupId=7),
                   [resp(200, body={"ticket": {"id": 42, "subject": "Printer", "status": 4,
                                               "priority": 2, "group_id": 7}})])
ok &= check("PUT to /api/v2/tickets/42",
            ex[0].method == "PUT" and ex[0].url == f"{BASE}/api/v2/tickets/42", repr(ex[0]))
ok &= check("exact update body", ex[0].json == {"status": 4, "priority": 2, "group_id": 7},
            str(ex[0].body))
ok &= check("update output shaped", out.get("updated") is True and out.get("status") == "Resolved"
            and out.get("group_id") == 7, str(out))

out, ex = run_tool("freshservice", tool("update_ticket", ticketId=42), [])
ok &= check("update with nothing to change errors without HTTP",
            "error" in out and "nothing to update" in out["error"] and len(ex) == 0, str(out))

print("[write path: add_note]")
out, ex = run_tool("freshservice", tool("add_note", ticketId=42, body="Investigating now"),
                   [resp(201, body={"conversation": {"id": 501, "ticket_id": 42, "private": True}})])
ok &= check("POST to /api/v2/tickets/42/notes",
            ex[0].method == "POST" and ex[0].url == f"{BASE}/api/v2/tickets/42/notes", repr(ex[0]))
ok &= check("note body with private defaulting true",
            ex[0].json == {"body": "Investigating now", "private": True}, str(ex[0].body))
ok &= check("note output shaped", out.get("id") == 501 and out.get("ticket_id") == 42
            and out.get("private") is True and out.get("created") is True, str(out))

out, ex = run_tool("freshservice", tool("add_note", ticketId=42, body="Public reply",
                                        private=False),
                   [resp(201, body={"conversation": {"id": 502, "ticket_id": 42,
                                                     "private": False}})])
ok &= check("explicit private=false honored",
            ex[0].json == {"body": "Public reply", "private": False}, str(ex[0].body))

# ------------------------------------------------------------------- 4. ERROR PATHS
print("[error paths]")
out, ex = run_tool("freshservice", tool("list_tickets"),
                   [err(401, body={"description": "Authentication failed",
                                   "errors": [{"code": "invalid_credentials",
                                               "message": "bad key"}]})])
ok &= check("401 surfaces friendly error", isinstance(out.get("error"), str), str(out)[:300])
ok &= check("401 error includes HTTP status", "401" in out.get("error", ""), str(out)[:300])
ok &= check("401 error includes API detail", "Authentication failed" in out.get("error", ""),
            str(out)[:300])
ok &= check("no traceback in output", "Traceback" not in str(out), str(out)[:300])

out, ex = run_tool("freshservice", tool("get_ticket", ticketId=42),
                   [err(429, body={"description": "slow down"},
                        headers={"Retry-After": "45"})])
ok &= check("429 mentions rate limit and Retry-After seconds",
            "Rate limit exceeded" in out.get("error", "") and "retry after 45" in out.get("error", ""),
            str(out)[:300])
ok &= check("429 error includes status 429", "429" in out.get("error", ""), str(out)[:300])

out, ex = run_tool("freshservice", tool("search_assets", query="laptop"),
                   [err(403, body={"description": "Access Denied"})])
ok &= check("assets 403 degrades with clear plan/module message",
            "asset management (CMDB) module" in out.get("error", "")
            and "403" in out.get("error", ""), str(out)[:400])

out, ex = run_tool("freshservice", tool("search_assets", query="it's mine"), [])
ok &= check("asset query with quote rejected before HTTP",
            "error" in out and "single quote" in out["error"] and len(ex) == 0, str(out)[:300])

out, ex = run_tool("freshservice",
                   {"tool": "freshservice.list_tickets", "baseUrl": "", "apiKey": ""}, [])
ok &= check("missing creds -> friendly error, no HTTP",
            "credentials" in out.get("error", "") and len(ex) == 0, str(out))

out, ex = run_tool("freshservice", tool("bogus_tool"), [])
ok &= check("unknown tool -> error", "Unknown tool" in out.get("error", ""), str(out))

# --------------------------------------------------------------- 5. SECURITY PROBES
print("[security probes]")
# (a) path-ish id: ticketId is integer-validated, so a path-traversal string must be
# rejected before any HTTP request is made (equivalent protection to percent-encoding).
out, ex = run_tool("freshservice", tool("get_ticket", ticketId="abc/../def?x=1"), [])
ok &= check("path-ish ticketId rejected, zero HTTP requests",
            len(ex) == 0 and "ticketId must be an integer" in out.get("error", ""), str(out))

out, ex = run_tool("freshservice", tool("update_ticket", ticketId="1/../2", status=2), [])
ok &= check("path-ish id rejected on update too", len(ex) == 0 and "error" in out, str(out))

# path-ish values through query params must be percent-encoded (no raw ../ or & injection)
out, ex = run_tool("freshservice", tool("search_assets", query="abc/../def?x=1&y=2"),
                   [resp(200, body={"assets": []})])
ok &= check("path-ish search query fully percent-encoded",
            "abc%2F..%2Fdef%3Fx%3D1%26y%3D2" in ex[0].url and "../" not in ex[0].url
            and "?x=1" not in ex[0].url, ex[0].url)

# (b) secret must never appear in printed output, even on error paths
out, ex = run_tool("freshservice", tool("list_tickets"),
                   [err(500, body="internal error")])
ok &= check("500 error output has status, no secret",
            "500" in out.get("error", "") and KEY not in str(out), str(out)[:300])
out, ex = run_tool("freshservice", tool("list_tickets"),
                   [err(401, body={"description": "denied"})])
ok &= check("apiKey never leaks into output", KEY not in str(out)
            and base64.b64encode(f"{KEY}:X".encode()).decode() not in str(out), str(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
