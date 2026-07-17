"""Offline mock-HTTP integration tests for the pipedrive skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

DOMAIN = "acme"
BASE = f"https://{DOMAIN}.pipedrive.com"
TOK = "pd-token-SECRET-VALUE"


def creds(**extra):
    p = {"companyDomain": DOMAIN, "apiToken": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. pipedrive.search — happy path + auth exactness (x-api-token header, v2)
# ---------------------------------------------------------------------------
print("scenario: search happy path / auth exactness")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.search", term="acme corp"), [
    resp(200, body={"success": True, "data": {"items": [
        {"result_score": 0.9, "item": {"id": 42, "type": "deal", "title": "Acme Corp deal",
                                       "status": "open", "owner": {"id": 1}}},
        {"result_score": 0.5, "item": {"id": 7, "type": "person", "name": "Anna Acme",
                                       "phones": ["555"], "emails": ["a@acme.co"]}},
    ]}}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (v2 itemSearch, encoded item_types, clamped limit)",
            ex[0].url == f"{BASE}/api/v2/itemSearch?term=acme+corp"
                         "&item_types=deal%2Cperson%2Corganization%2Clead&limit=20",
            ex[0].url)
ok &= check("x-api-token header is exactly the token",
            ex[0].headers.get("x-api-token") == TOK, str(ex[0].headers))
ok &= check("no legacy api_token query param", "api_token" not in ex[0].url, ex[0].url)
ok &= check("no Authorization header", "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("User-Agent", ex[0].headers.get("user-agent") == "sophon-pipedrive-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("deal item shaped (title from title)",
            out["items"][0] == {"type": "deal", "id": 42, "title": "Acme Corp deal",
                                "result_score": 0.9}, str(out["items"][0]))
ok &= check("person item shaped (title from name), raw fields absent",
            out["items"][1]["title"] == "Anna Acme" and "owner" not in json.dumps(out)
            and "phones" not in out["items"][1], str(out["items"][1]))
ok &= check("token not echoed in output", TOK not in json.dumps(out))

print("scenario: search limit clamped to 50, custom item_types")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.search", term="xy",
                                      item_types="person", limit=500), [
    resp(200, body={"success": True, "data": {"items": []}}),
])
ok &= check("limit clamped to 50 and item_types honored",
            ex[0].url == f"{BASE}/api/v2/itemSearch?term=xy&item_types=person&limit=50",
            ex[0].url)
ok &= check("empty result count 0", out == {"count": 0, "items": []}, str(out))

print("scenario: search term too short -> friendly error, no HTTP call")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.search", term="a"), [])
ok &= check("term-length error", out.get("error") == "term required (at least 2 characters)",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 2. pipedrive.list_deals — happy path, filters, cursor pagination
# ---------------------------------------------------------------------------
print("scenario: list_deals filters + cursor returned")
DEAL = {"id": 42, "title": "Acme Corp deal", "value": 5000, "currency": "USD",
        "status": "open", "stage_id": 3, "pipeline_id": 1, "owner_id": 9,
        "person_id": 7, "org_id": 4, "expected_close_date": "2026-08-01",
        "add_time": "2026-01-01T00:00:00Z", "custom_fields": {"secret": "raw"},
        "visible_to": "3", "probability": 80}
out, ex = run_tool("pipedrive", creds(tool="pipedrive.list_deals", pipeline_id=1,
                                      status="open", limit=2), [
    resp(200, body={"success": True, "data": [DEAL],
                    "additional_data": {"next_cursor": "cur2"}}),
])
ok &= check("URL byte-exact (v2 deals, None filters dropped)",
            ex[0].url == f"{BASE}/api/v2/deals?pipeline_id=1&status=open&limit=2", ex[0].url)
ok &= check("x-api-token on list", ex[0].headers.get("x-api-token") == TOK)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("deal summary shaped",
            out["deals"][0] == {"id": 42, "title": "Acme Corp deal", "value": 5000,
                                "currency": "USD", "status": "open", "stage_id": 3,
                                "pipeline_id": 1, "owner_id": 9, "person_id": 7, "org_id": 4,
                                "expected_close_date": "2026-08-01"}, str(out["deals"][0]))
ok &= check("raw fields absent (custom_fields/add_time/probability)",
            "custom_fields" not in json.dumps(out) and "add_time" not in json.dumps(out),
            str(out)[:300])
ok &= check("next_cursor returned", out.get("next_cursor") == "cur2", str(out)[:200])

print("scenario: list_deals second page passes cursor; no next page -> null cursor")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.list_deals", pipeline_id=1,
                                      status="open", limit=2, cursor="cur2"), [
    resp(200, body={"success": True, "data": [], "additional_data": {"next_cursor": None}}),
])
ok &= check("cursor appended to URL",
            ex[0].url == f"{BASE}/api/v2/deals?pipeline_id=1&status=open&limit=2&cursor=cur2",
            ex[0].url)
ok &= check("single request only (skill never auto-follows pages)", len(ex) == 1, repr(ex))
ok &= check("null next_cursor surfaced",
            out.get("count") == 0 and out.get("next_cursor") is None, str(out))

print("scenario: list_deals invalid status enum -> friendly error, no HTTP call")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.list_deals", status="closed"), [])
ok &= check("status enum error", out.get("error") == "status must be one of: open, won, lost",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 3. pipedrive.get_deal / get_person — happy paths
# ---------------------------------------------------------------------------
print("scenario: get_deal happy path")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.get_deal", dealId=42), [
    resp(200, body={"success": True, "data": DEAL}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v2/deals/42", ex[0].url)
ok &= check("deal fields per spec",
            out == {"id": 42, "title": "Acme Corp deal", "value": 5000, "currency": "USD",
                    "status": "open", "stage_id": 3, "pipeline_id": 1, "owner_id": 9,
                    "person_id": 7, "org_id": 4, "expected_close_date": "2026-08-01"},
            str(out))

print("scenario: get_person happy path (v2 emails/phones arrays)")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.get_person", personId=7), [
    resp(200, body={"success": True, "data": {
        "id": 7, "name": "Anna Acme", "org_id": 4, "owner_id": 9,
        "emails": [{"value": "anna@acme.co", "label": "work", "primary": True}],
        "phones": [{"value": "+1 555 0100", "label": "mobile", "primary": True}],
        "add_time": "2026-01-01T00:00:00Z", "custom_fields": {}}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v2/persons/7", ex[0].url)
ok &= check("person shaped (name/emails/phones/org_id)",
            out == {"id": 7, "name": "Anna Acme",
                    "emails": [{"value": "anna@acme.co", "label": "work", "primary": True}],
                    "phones": [{"value": "+1 555 0100", "label": "mobile", "primary": True}],
                    "org_id": 4, "owner_id": 9}, str(out))

print("scenario: get_deal missing dealId -> friendly error, no HTTP call")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.get_deal"), [])
ok &= check("dealId required error", out.get("error") == "dealId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 4. WRITE PATHS — update_deal (PATCH v2), add_note (POST v1), create_activity (POST v2)
# ---------------------------------------------------------------------------
print("scenario: update_deal PATCH body")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.update_deal", dealId=42,
                                      stage_id=5, status="won"), [
    resp(200, body={"success": True, "data": dict(DEAL, stage_id=5, status="won")}),
])
ok &= check("method PATCH", ex[0].method == "PATCH", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v2/deals/42", ex[0].url)
ok &= check("JSON body exactly the changed fields",
            ex[0].json == {"stage_id": 5, "status": "won"}, str(ex[0].body))
ok &= check("Content-Type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("x-api-token on write", ex[0].headers.get("x-api-token") == TOK)
ok &= check("updated summary returned",
            out.get("updated") is True and out.get("stage_id") == 5 and out.get("status") == "won",
            str(out)[:300])

print("scenario: update_deal with nothing to change -> error, no HTTP call")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.update_deal", dealId=42), [])
ok &= check("nothing-to-update error",
            out.get("error") == "nothing to update: provide stage_id, status, value, and/or owner_id",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: add_note POSTs to v1 (not v2)")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.add_note",
                                      content="Contract sent", deal_id=42), [
    resp(201, body={"success": True, "data": {"id": 900, "content": "Contract sent",
                                              "deal_id": 42, "person_id": None,
                                              "org_id": None, "user_id": 9}}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL is v1 notes byte-exact", ex[0].url == f"{BASE}/api/v1/notes", ex[0].url)
ok &= check("JSON body exact", ex[0].json == {"content": "Contract sent", "deal_id": 42},
            str(ex[0].body))
ok &= check("created output shaped",
            out == {"id": 900, "deal_id": 42, "person_id": None, "org_id": None,
                    "created": True}, str(out))

print("scenario: add_note without a target -> error, no HTTP call")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.add_note", content="orphan"), [])
ok &= check("no-target error",
            out.get("error") == "provide at least one of deal_id, person_id, org_id to attach the note to",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: create_activity POST v2 body")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.create_activity", subject="Intro call",
                                      type="call", due_date="2026-07-20",
                                      due_time="14:30", deal_id=42), [
    resp(201, body={"success": True, "data": {"id": 77, "subject": "Intro call",
                                              "type": "call", "due_date": "2026-07-20",
                                              "due_time": "14:30", "deal_id": 42,
                                              "done": False, "busy": True}}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL is v2 activities byte-exact", ex[0].url == f"{BASE}/api/v2/activities",
            ex[0].url)
ok &= check("JSON body exact",
            ex[0].json == {"subject": "Intro call", "type": "call", "due_date": "2026-07-20",
                           "due_time": "14:30", "deal_id": 42}, str(ex[0].body))
ok &= check("created output shaped, raw fields absent",
            out == {"id": 77, "subject": "Intro call", "type": "call",
                    "due_date": "2026-07-20", "due_time": "14:30", "deal_id": 42,
                    "created": True}, str(out))

print("scenario: create_activity invalid type -> error, no HTTP call")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.create_activity", subject="Party",
                                      type="party", due_date="2026-07-20"), [])
ok &= check("type enum error",
            out.get("error") == "type must be one of: call, meeting, task, deadline, email, lunch",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 5. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.get_deal", dealId=42), [
    err(401, body={"success": False, "error": "Invalid API token",
                   "error_info": "Please check the api documentation"}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API error message", "Invalid API token" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("token not leaked in error output", TOK not in raw, raw[:300])

print("scenario: 429 explains the daily token budget and includes Retry-After")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.list_deals"), [
    err(429, body={"success": False, "error": "Rate limit exceeded"},
        headers={"Retry-After": "12"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("daily token budget explained",
            "token budget" in out["error"] and "midnight" in out["error"], out.get("error", ""))
ok &= check("Retry-After included", "12" in out["error"], out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.get_person", personId=7), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing credentials -> connect-first error, no HTTP call")
out, ex = run_tool("pipedrive", {"tool": "pipedrive.search", "companyDomain": "",
                                 "apiToken": ""}, [])
ok &= check("connect-first message names the fields",
            out.get("error") == "Missing Pipedrive credentials: connect the Pipedrive "
                                "integration first (companyDomain, apiToken).", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: pipedrive.nope", str(out))

# ---------------------------------------------------------------------------
# 6. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal dealId is percent-encoded")
evil = "abc/../def?x=1"
out, ex = run_tool("pipedrive", creds(tool="pipedrive.get_deal", dealId=evil), [
    resp(200, body={"success": True, "data": {"id": 1}}),
])
ok &= check("id fully quoted in URL (no path escape)",
            ex[0].url == f"{BASE}/api/v2/deals/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' or '?' in path", "../" not in ex[0].url and "?" not in ex[0].url,
            ex[0].url)

print("scenario: bare '..' segment rejected outright, no HTTP call")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.update_deal", dealId="..",
                                      status="won"), [])
ok &= check("'..' rejected", "error" in out and "invalid dealId" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("pipedrive", creds(tool="pipedrive.get_person", personId="."), [])
ok &= check("'.' personId rejected", "error" in out and "invalid personId" in out["error"],
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: companyDomain that is not a bare subdomain is rejected, no HTTP call")
out, ex = run_tool("pipedrive", {"tool": "pipedrive.get_deal", "dealId": 1,
                                 "companyDomain": "evil.com/pwn", "apiToken": TOK}, [])
ok &= check("host-injection domain rejected",
            "error" in out and "subdomain" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
ok &= check("token not leaked in domain error", TOK not in json.dumps(out))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("pipedrive", creds(tool="pipedrive.list_deals"), [
    err(403, body={"success": False, "error": "forbidden"}),
])
ok &= check("apiToken absent from error output", TOK not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
