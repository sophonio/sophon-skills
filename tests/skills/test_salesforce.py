"""Offline mock-HTTP integration tests for the salesforce Sophon skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

MY_DOMAIN = "https://acme.my.salesforce.com"
INSTANCE = "https://acme.instance.my.salesforce.example"  # deliberately != MY_DOMAIN
BASE = {"myDomainUrl": MY_DOMAIN, "clientId": "cid123", "clientSecret": "s3cr3t-XYZ"}
TOKEN_OK = resp(200, body={"access_token": "sftok-abc", "instance_url": INSTANCE,
                           "token_type": "Bearer"})
API = f"{INSTANCE}/services/data/v62.0"

ok = True


def sf_record(obj_type, **fields):
    rec = {"attributes": {"type": obj_type, "url": f"/services/data/v62.0/sobjects/{obj_type}/x"}}
    rec.update(fields)
    return rec


# ---------------------------------------------------------------- 1. auth exactness
print("scenario 1: auth exactness (token POST form-encoded; API uses token instance_url + Bearer)")
out, ex = run_tool("salesforce", {**BASE, "tool": "sf.soql_query", "soql": "SELECT Id FROM Account"},
                   [TOKEN_OK,
                    resp(200, body={"totalSize": 0, "done": True, "records": []})])
ok &= check("two requests (token + api)", len(ex) == 2, repr(ex))
ok &= check("token POST to {myDomainUrl}/services/oauth2/token",
            ex[0].method == "POST" and ex[0].url == f"{MY_DOMAIN}/services/oauth2/token", repr(ex[0]))
ok &= check("token body byte-exact form encoding",
            ex[0].body == "grant_type=client_credentials&client_id=cid123&client_secret=s3cr3t-XYZ",
            repr(ex[0].body))
ok &= check("token content-type is x-www-form-urlencoded",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("API call targets instance_url from token response (NOT myDomainUrl)",
            ex[1].url.startswith(INSTANCE + "/") and MY_DOMAIN not in ex[1].url, ex[1].url)
ok &= check("API call carries Bearer header",
            ex[1].headers.get("authorization") == "Bearer sftok-abc", str(ex[1].headers))
ok &= check("no auth header on token request", "authorization" not in ex[0].headers,
            str(ex[0].headers))

# ---------------------------------------------------------------- 2. soql_query pagination
print("scenario 2: sf.soql_query follows nextRecordsUrl pagination + shaping")
next_path = "/services/data/v62.0/query/01gXX0000012345-2000"
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.soql_query",
                   "soql": "SELECT Id, Name FROM Account", "limit": 10},
    [TOKEN_OK,
     resp(200, body={"totalSize": 3, "done": False, "nextRecordsUrl": next_path,
                     "records": [sf_record("Account", Id="001A", Name="Acme"),
                                 sf_record("Account", Id="001B", Name="Beta")]}),
     resp(200, body={"totalSize": 3, "done": True,
                     "records": [sf_record("Account", Id="001C", Name="Gamma")]})])
ok &= check("three requests (token + 2 pages)", len(ex) == 3, repr(ex))
ok &= check("first query URL is /services/data/v62.0/query?q=...",
            ex[1].url == f"{API}/query?q=SELECT+Id%2C+Name+FROM+Account", ex[1].url)
ok &= check("second page fetched at instance_url + nextRecordsUrl",
            ex[2].url == f"{INSTANCE}{next_path}", ex[2].url)
ok &= check("page 2 still Bearer", ex[2].headers.get("authorization") == "Bearer sftok-abc",
            str(ex[2].headers))
ok &= check("count is 3 across pages", out.get("count") == 3, str(out)[:300])
ok &= check("totalSize and done surfaced", out.get("totalSize") == 3 and out.get("done") is True,
            str(out)[:300])
ok &= check("records trimmed: type kept, attributes envelope dropped",
            out["records"][0].get("type") == "Account" and "attributes" not in out["records"][0],
            str(out["records"][0]))
ok &= check("record fields present", [r["Name"] for r in out["records"]] == ["Acme", "Beta", "Gamma"],
            str(out["records"]))

# ---------------------------------------------------------------- 3. soql_query limit stops pagination
print("scenario 3: sf.soql_query stops paging once limit reached")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.soql_query", "soql": "SELECT Id FROM Lead", "limit": 2},
    [TOKEN_OK,
     resp(200, body={"totalSize": 4000, "done": False, "nextRecordsUrl": next_path,
                     "records": [sf_record("Lead", Id="00Q1"), sf_record("Lead", Id="00Q2")]})])
ok &= check("no extra page fetched when limit satisfied", len(ex) == 2, repr(ex))
ok &= check("records truncated to limit", out.get("count") == 2 and len(out["records"]) == 2,
            str(out)[:300])
ok &= check("totalSize reflects server total", out.get("totalSize") == 4000, str(out)[:200])

# ---------------------------------------------------------------- 4. sf.search happy path
print("scenario 4: sf.search happy path")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.search", "sosl": "FIND {Acme} IN NAME FIELDS RETURNING Account(Id, Name)"},
    [TOKEN_OK,
     resp(200, body={"searchRecords": [sf_record("Account", Id="001A", Name="Acme Corp"),
                                       sf_record("Contact", Id="003B", Name="Acme Contact")]})])
ok &= check("search URL targets /search/ with encoded q",
            ex[1].url.startswith(f"{API}/search/?q=FIND+%7BAcme%7D") , ex[1].url)
ok &= check("search count", out.get("count") == 2, str(out)[:300])
ok &= check("search records trimmed (type kept, attributes dropped)",
            out["records"][1].get("type") == "Contact" and
            all("attributes" not in r for r in out["records"]), str(out["records"]))

# ---------------------------------------------------------------- 5. sf.get_record happy path
print("scenario 5: sf.get_record with field list")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.get_record", "objectType": "Opportunity",
                   "recordId": "006XXAAA", "fields": ["Name", "StageName", "Amount"]},
    [TOKEN_OK,
     resp(200, body=sf_record("Opportunity", Name="Big Deal", StageName="Prospecting",
                              Amount=5000.0,
                              Account={"attributes": {"type": "Account", "url": "/x"},
                                       "Name": "Acme"}))])
ok &= check("get_record URL and fields param",
            ex[1].url == f"{API}/sobjects/Opportunity/006XXAAA?fields=Name%2CStageName%2CAmount",
            ex[1].url)
ok &= check("get_record method GET", ex[1].method == "GET", ex[1].method)
ok &= check("record shaped: type + fields, no attributes",
            out.get("type") == "Opportunity" and out.get("Name") == "Big Deal"
            and "attributes" not in out, str(out)[:300])
ok &= check("parent lookup also trimmed",
            out.get("Account", {}).get("type") == "Account"
            and "attributes" not in out.get("Account", {}), str(out.get("Account")))

# ---------------------------------------------------------------- 6. sf.describe_object happy path
print("scenario 6: sf.describe_object trims fields and filters inactive picklists")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.describe_object", "objectType": "Opportunity"},
    [TOKEN_OK,
     resp(200, body={"name": "Opportunity", "label": "Opportunity", "custom": False,
                     "urls": {"sobject": "/x"}, "keyPrefix": "006",
                     "fields": [
                         {"name": "StageName", "label": "Stage", "type": "picklist",
                          "soapType": "xsd:string", "byteLength": 120,
                          "picklistValues": [
                              {"value": "Prospecting", "label": "Prospecting", "active": True},
                              {"value": "OldStage", "label": "Old Stage", "active": False}]},
                         {"name": "Amount", "label": "Amount", "type": "currency",
                          "soapType": "xsd:double", "picklistValues": []}]})])
ok &= check("describe URL", ex[1].url == f"{API}/sobjects/Opportunity/describe", ex[1].url)
ok &= check("describe output header fields",
            out.get("name") == "Opportunity" and out.get("custom") is False
            and out.get("count") == 2, str(out)[:200])
ok &= check("raw payload fields absent (urls/keyPrefix/soapType)",
            "urls" not in out and "keyPrefix" not in out
            and all("soapType" not in f and "byteLength" not in f for f in out["fields"]),
            str(out)[:400])
ok &= check("inactive picklist values filtered",
            out["fields"][0]["picklistValues"] == [{"value": "Prospecting", "label": "Prospecting"}],
            str(out["fields"][0]))
ok &= check("field without picklist omits picklistValues",
            "picklistValues" not in out["fields"][1], str(out["fields"][1]))

# ---------------------------------------------------------------- 7. write path: create_record
print("scenario 7: sf.create_record exact POST body")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.create_record", "objectType": "Account",
                   "fields": {"Name": "Acme Corp", "Industry": "Technology"}},
    [TOKEN_OK,
     resp(201, body={"id": "001NEW", "success": True, "errors": []})])
ok &= check("create POST to /sobjects/Account",
            ex[1].method == "POST" and ex[1].url == f"{API}/sobjects/Account", repr(ex[1]))
ok &= check("create body is exact JSON of fields",
            ex[1].json == {"Name": "Acme Corp", "Industry": "Technology"}, str(ex[1].body))
ok &= check("create content-type json",
            ex[1].headers.get("content-type") == "application/json", str(ex[1].headers))
ok &= check("create output shaped",
            out == {"id": "001NEW", "objectType": "Account", "created": True}, str(out))

# ---------------------------------------------------------------- 8. write path: update_record PATCH
print("scenario 8: sf.update_record exact PATCH body (204 no content)")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.update_record", "objectType": "Opportunity",
                   "recordId": "006XXAAA", "fields": {"StageName": "Closed Won"}},
    [TOKEN_OK, resp(204, body=b"")])
ok &= check("update PATCH to /sobjects/Opportunity/006XXAAA",
            ex[1].method == "PATCH" and ex[1].url == f"{API}/sobjects/Opportunity/006XXAAA",
            repr(ex[1]))
ok &= check("update body exact", ex[1].json == {"StageName": "Closed Won"}, str(ex[1].body))
ok &= check("update output shaped",
            out == {"id": "006XXAAA", "objectType": "Opportunity", "updated": True}, str(out))

# ---------------------------------------------------------------- 9. write path: add_task payload
print("scenario 9: sf.add_task builds Task payload with optional links")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.add_task", "subject": "Follow up on renewal",
                   "whoId": "003ABC", "whatId": "006DEF", "activityDate": "2026-08-01"},
    [TOKEN_OK, resp(201, body={"id": "00TNEW", "success": True, "errors": []})])
ok &= check("task POST to /sobjects/Task",
            ex[1].method == "POST" and ex[1].url == f"{API}/sobjects/Task", repr(ex[1]))
ok &= check("task body exact",
            ex[1].json == {"Subject": "Follow up on renewal", "WhoId": "003ABC",
                           "WhatId": "006DEF", "ActivityDate": "2026-08-01"}, str(ex[1].body))
ok &= check("task output shaped",
            out == {"id": "00TNEW", "subject": "Follow up on renewal", "created": True}, str(out))

# ---------------------------------------------------------------- 10. API 401 error (JSON array body)
print("scenario 10: API 401 — Salesforce JSON-array error parsed, friendly output")
out, _ = run_tool(
    "salesforce", {**BASE, "tool": "sf.search", "sosl": "FIND {x}"},
    [TOKEN_OK,
     err(401, body=[{"message": "Session expired or invalid",
                     "errorCode": "INVALID_SESSION_ID"}])])
printed = json.dumps(out)
ok &= check("401 surfaces {'error': ...}", isinstance(out.get("error"), str), str(out)[:300])
ok &= check("401 error includes HTTP status", "401" in out.get("error", ""), out.get("error"))
ok &= check("401 error includes parsed array message",
            "Session expired or invalid" in out.get("error", ""), out.get("error"))
ok &= check("no traceback in output", "Traceback" not in printed, printed[:300])
ok &= check("client secret not leaked in output", "s3cr3t-XYZ" not in printed, printed[:300])

# ---------------------------------------------------------------- 11. token endpoint 401
print("scenario 11: token 401 — friendly error, status shown, secret not leaked")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.soql_query", "soql": "SELECT Id FROM Account"},
    [err(401, body={"error": "invalid_client_id",
                    "error_description": "client identifier invalid"})])
printed = json.dumps(out)
ok &= check("token failure surfaces {'error': ...}", isinstance(out.get("error"), str), str(out)[:300])
ok &= check("token error includes status and description",
            "401" in out["error"] and "client identifier invalid" in out["error"], out["error"])
ok &= check("no traceback", "Traceback" not in printed, printed[:300])
ok &= check("secret and token absent from output",
            "s3cr3t-XYZ" not in printed and "cid123" not in printed, printed[:300])

# ---------------------------------------------------------------- 12. REQUEST_LIMIT_EXCEEDED
print("scenario 12: REQUEST_LIMIT_EXCEEDED gets the dedicated daily-limit message")
out, _ = run_tool(
    "salesforce", {**BASE, "tool": "sf.soql_query", "soql": "SELECT Id FROM Account"},
    [TOKEN_OK,
     err(403, body=[{"message": "TotalRequests Limit exceeded.",
                     "errorCode": "REQUEST_LIMIT_EXCEEDED"}])])
ok &= check("daily-limit dedicated message",
            "daily API request limit" in out.get("error", ""), str(out)[:300])
ok &= check("no generic 'API error 403' wording for limit case",
            "API error 403" not in out.get("error", ""), out.get("error"))

# ---------------------------------------------------------------- 13. security probe: path-ish id
print("scenario 13: path-ish recordId/objectType are percent-encoded (no path escape)")
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.get_record", "objectType": "Account",
                   "recordId": "abc/../def?x=1"},
    [TOKEN_OK, resp(200, body=sf_record("Account", Id="001A"))])
ok &= check("recordId percent-encoded in URL",
            "abc%2F..%2Fdef%3Fx%3D1" in ex[1].url, ex[1].url)
ok &= check("no raw traversal or query injection in URL",
            "abc/../def" not in ex[1].url and "?x=1" not in ex[1].url, ex[1].url)
out, ex = run_tool(
    "salesforce", {**BASE, "tool": "sf.describe_object", "objectType": "Account/../../oops"},
    [TOKEN_OK, resp(200, body={"name": "x", "fields": []})])
ok &= check("objectType percent-encoded in describe URL",
            "Account%2F..%2F..%2Foops" in ex[1].url and "/../" not in ex[1].url, ex[1].url)

# ---------------------------------------------------------------- 14. guardrails
print("scenario 14: unknown tool and missing credentials do not make HTTP calls")
out, ex = run_tool("salesforce", {**BASE, "tool": "sf.nope"}, [])
ok &= check("unknown tool -> error, zero requests",
            "Unknown tool" in out.get("error", "") and len(ex) == 0, str(out))
out, ex = run_tool("salesforce", {"tool": "sf.soql_query", "soql": "SELECT Id FROM Account",
                                  "myDomainUrl": MY_DOMAIN, "clientId": "cid123"}, [])
ok &= check("missing secret -> credential error, zero requests",
            "credentials" in out.get("error", "").lower() and len(ex) == 0, str(out))
out, ex = run_tool("salesforce", {**BASE, "tool": "sf.soql_query"}, [TOKEN_OK])
ok &= check("missing soql -> validation error after auth only",
            out.get("error") == "soql required" and len(ex) == 1, str(out))

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
