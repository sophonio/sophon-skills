"""Offline mock-HTTP integration tests for the jira-service-management skill."""
import base64
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://acme.atlassian.net"
API = f"{BASE}/rest/servicedeskapi"
EMAIL = "agent@acme.com"
TOK = "atlassian-TOKEN-SECRET-9x"
AUTH = "Basic " + base64.b64encode(f"{EMAIL}:{TOK}".encode()).decode()


def creds(**extra):
    p = {"baseUrl": BASE, "email": EMAIL, "apiToken": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. jsm.list_service_desks — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: list_service_desks happy path / auth exactness")
out, ex = run_tool("jira-service-management", creds(tool="jsm.list_service_desks"), [
    resp(200, body={"values": [
        {"id": "1", "projectId": "10001", "projectKey": "ITS",
         "projectName": "IT Support", "_links": {"self": "x"}},
        {"id": "2", "projectId": "10002", "projectKey": "HR",
         "projectName": "HR Requests", "_links": {"self": "y"}},
    ], "size": 2, "start": 0, "limit": 50, "isLastPage": True}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{API}/servicedesk?limit=50", ex[0].url)
ok &= check("Authorization is exactly Basic base64(email:apiToken)",
            ex[0].headers.get("authorization") == AUTH, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("User-Agent set", ex[0].headers.get("user-agent") == "sophon-jira-service-management-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("desks shaped (id/projectKey/projectName only)",
            out["serviceDesks"][0] == {"id": "1", "projectKey": "ITS", "projectName": "IT Support"},
            str(out)[:300])
ok &= check("envelope/raw fields absent",
            "isLastPage" not in out and "values" not in out
            and "_links" not in out["serviceDesks"][0] and "projectId" not in out["serviceDesks"][0],
            str(out)[:300])
ok &= check("token not echoed in output", TOK not in json.dumps(out))

print("scenario: list_service_desks with serviceDeskId lists request types")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_service_desks", serviceDeskId="1"), [
    resp(200, body={"values": [
        {"id": "25", "name": "Get IT help", "description": "Ask for help",
         "helpText": "raw", "serviceDeskId": "1", "groupIds": ["7"], "icon": {}},
    ], "isLastPage": True}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/servicedesk/1/requesttype?limit=50", ex[0].url)
ok &= check("request types shaped",
            out == {"serviceDeskId": "1", "count": 1, "requestTypes": [
                {"id": "25", "name": "Get IT help", "description": "Ask for help"}]},
            str(out))

print("scenario: limit clamps to maximum 100")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_service_desks", limit=9999), [
    resp(200, body={"values": [], "isLastPage": True}),
])
ok &= check("limit=9999 clamped to 100", ex[0].url == f"{API}/servicedesk?limit=100", ex[0].url)

print("scenario: non-numeric limit falls back to default")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_service_desks", limit="abc"), [
    resp(200, body={"values": [], "isLastPage": True}),
])
ok &= check("limit='abc' falls back to 50", ex[0].url == f"{API}/servicedesk?limit=50", ex[0].url)

# ---------------------------------------------------------------------------
# 2. jsm.list_queue_issues — queues list, then issues in a queue
# ---------------------------------------------------------------------------
print("scenario: list_queue_issues without queueId lists queues")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_queue_issues", serviceDeskId="1"), [
    resp(200, body={"values": [
        {"id": "10", "name": "Waiting for support", "jql": "raw jql", "issueCount": 4,
         "fields": ["summary"]},
    ], "isLastPage": True}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/servicedesk/1/queue?limit=25", ex[0].url)
ok &= check("queues shaped (no raw jql)",
            out.get("count") == 1
            and out["queues"][0] == {"id": "10", "name": "Waiting for support", "issueCount": 4},
            str(out))

print("scenario: list_queue_issues with queueId lists shaped issues")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_queue_issues", serviceDeskId="1", queueId="10", limit=5), [
    resp(200, body={"values": [
        {"id": "10100", "key": "ITS-42",
         "fields": {"summary": "Laptop broken",
                    "status": {"name": "Waiting for support", "statusCategory": {"key": "new"}},
                    "reporter": {"displayName": "Dana Cruz", "accountId": "acc-1",
                                 "emailAddress": "dana@acme.com"},
                    "created": "2026-07-10T09:00:00.000+0000",
                    "customfield_10010": {"deep": "raw"}}},
    ], "isLastPage": True}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/servicedesk/1/queue/10/issue?limit=5", ex[0].url)
ok &= check("issue shaped (key/summary/status/requester/created)",
            out == {"count": 1, "issues": [
                {"key": "ITS-42", "summary": "Laptop broken", "status": "Waiting for support",
                 "requester": "Dana Cruz", "created": "2026-07-10T09:00:00.000+0000"}]},
            str(out))

# ---------------------------------------------------------------------------
# 3. jsm.get_request — happy path with expand
# ---------------------------------------------------------------------------
print("scenario: get_request happy path")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.get_request", issueIdOrKey="ITS-42"), [
    resp(200, body={
        "_expands": [], "issueId": "10100", "issueKey": "ITS-42", "requestTypeId": "25",
        "serviceDeskId": "1",
        "requestType": {"id": "25", "name": "Get IT help", "helpText": "raw"},
        "createdDate": {"iso8601": "2026-07-10T09:00:00+0000", "friendly": "Today 9:00 AM",
                        "epochMillis": 1780000000000},
        "reporter": {"accountId": "acc-1", "displayName": "Dana Cruz",
                     "emailAddress": "dana@acme.com", "_links": {"self": "x"}},
        "participant": {"size": 1, "values": [
            {"accountId": "acc-2", "displayName": "Sam Po", "emailAddress": "sam@acme.com"}]},
        "requestFieldValues": [{"fieldId": "summary", "value": "Laptop broken"}],
        "currentStatus": {"status": "Waiting for support", "statusCategory": "NEW",
                          "statusDate": {"iso8601": "2026-07-10T09:05:00+0000"}},
        "_links": {"web": "https://acme.atlassian.net/servicedesk/customer/portal/1/ITS-42"},
    }),
])
ok &= check("URL byte-exact (expand encoded)",
            ex[0].url == f"{API}/request/ITS-42?expand=participant%2CrequestType", ex[0].url)
ok &= check("Basic auth on read", ex[0].headers.get("authorization") == AUTH)
ok &= check("requestType shaped", out.get("requestType") == {"id": "25", "name": "Get IT help"},
            str(out)[:300])
ok &= check("reporter trimmed (no accountId/_links)",
            out.get("reporter") == {"displayName": "Dana Cruz", "emailAddress": "dana@acme.com"},
            str(out)[:300])
ok &= check("participants flattened",
            out.get("participants") == [{"displayName": "Sam Po", "emailAddress": "sam@acme.com"}],
            str(out)[:300])
ok &= check("currentStatus shaped with iso8601 date",
            out.get("currentStatus") == {"status": "Waiting for support",
                                         "statusCategory": "NEW",
                                         "statusDate": "2026-07-10T09:05:00+0000"},
            str(out)[:300])
ok &= check("createdDate flattened to iso8601",
            out.get("createdDate") == "2026-07-10T09:00:00+0000", str(out)[:300])
ok &= check("raw fields absent (_links/requestFieldValues/_expands)",
            "_links" not in out and "requestFieldValues" not in out and "_expands" not in out,
            str(out)[:300])

print("scenario: get_request tolerates plural 'participants' response key")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.get_request", issueIdOrKey="ITS-42"), [
    resp(200, body={
        "issueId": "10100", "issueKey": "ITS-42", "serviceDeskId": "1",
        "requestType": {"id": "25", "name": "Get IT help"},
        "reporter": {"displayName": "Dana Cruz", "emailAddress": "dana@acme.com"},
        "participants": {"size": 1, "values": [
            {"accountId": "acc-2", "displayName": "Sam Po", "emailAddress": "sam@acme.com"}]},
        "currentStatus": {"status": "Waiting for support"},
    }),
])
ok &= check("plural participants flattened",
            out.get("participants") == [{"displayName": "Sam Po", "emailAddress": "sam@acme.com"}],
            str(out)[:300])

# ---------------------------------------------------------------------------
# 4. jsm.get_request_slas — happy path
# ---------------------------------------------------------------------------
print("scenario: get_request_slas happy path")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.get_request_slas", issueIdOrKey="ITS-42"), [
    resp(200, body={"values": [
        {"id": "1", "name": "Time to resolution",
         "ongoingCycle": {"breached": False, "paused": False, "withinCalendarHours": True,
                          "goalDuration": {"millis": 14400000, "friendly": "4h"},
                          "elapsedTime": {"millis": 3600000, "friendly": "1h"},
                          "remainingTime": {"millis": 10800000, "friendly": "3h"},
                          "breachTime": {"iso8601": "2026-07-10T13:00:00+0000"}},
         "completedCycles": []},
        {"id": "2", "name": "Time to first response", "completedCycles": [
            {"breached": True, "goalDuration": {"millis": 1800000, "friendly": "30m"},
             "elapsedTime": {"millis": 4000000, "friendly": "1h 6m"},
             "remainingTime": {"millis": -2200000, "friendly": "-36m"}}]},
    ], "isLastPage": True}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/request/ITS-42/sla", ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("ongoing sla shaped, not breached",
            out["slas"][0] == {"name": "Time to resolution", "breached": False,
                              "ongoingCycle": {"breached": False, "goalDuration": "4h",
                                               "elapsedTime": "1h", "remainingTime": "3h"},
                              "completedCycles": []},
            str(out["slas"][0]))
ok &= check("completed breach sets breached flag",
            out["slas"][1]["breached"] is True and out["slas"][1]["ongoingCycle"] is None
            and out["slas"][1]["completedCycles"][0]["remainingTime"] == "-36m",
            str(out["slas"][1]))
ok &= check("raw millis absent", "millis" not in json.dumps(out), str(out)[:300])

# ---------------------------------------------------------------------------
# 5. WRITE PATHS
# ---------------------------------------------------------------------------
print("scenario: create_request body byte-exact")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.create_request", serviceDeskId="1", requestTypeId="25",
                         summary="Laptop broken", description="Battery swelling",
                         raiseOnBehalfOf="dana@acme.com"), [
    resp(201, body={"issueId": "10100", "issueKey": "ITS-43", "requestTypeId": "25",
                    "serviceDeskId": "1",
                    "currentStatus": {"status": "Waiting for support"},
                    "reporter": {"accountId": "acc-1"},
                    "_links": {"web": "https://acme.atlassian.net/portal/1/ITS-43"}}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{API}/request", ex[0].url)
ok &= check("Content-Type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("body byte-exact",
            ex[0].body == json.dumps({"serviceDeskId": "1", "requestTypeId": "25",
                                      "requestFieldValues": {"summary": "Laptop broken",
                                                             "description": "Battery swelling"},
                                      "raiseOnBehalfOf": "dana@acme.com"}),
            str(ex[0].body))
ok &= check("create output shaped",
            out == {"issueId": "10100", "issueKey": "ITS-43", "requestTypeId": "25",
                    "serviceDeskId": "1", "status": "Waiting for support",
                    "webLink": "https://acme.atlassian.net/portal/1/ITS-43"},
            str(out))

print("scenario: add_request_comment defaults to internal (public false)")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.add_request_comment", issueIdOrKey="ITS-42",
                         body="Working on it"), [
    resp(201, body={"id": "1001", "body": "Working on it", "public": False,
                    "author": {"accountId": "acc-9", "displayName": "Agent Ann"},
                    "created": {"iso8601": "2026-07-17T10:00:00+0000"}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/request/ITS-42/comment", ex[0].url)
ok &= check("body byte-exact with public:false default",
            ex[0].body == json.dumps({"body": "Working on it", "public": False}), str(ex[0].body))
ok &= check("comment output shaped",
            out == {"id": "1001", "public": False, "author": "Agent Ann",
                    "created": "2026-07-17T10:00:00+0000"}, str(out))

print("scenario: add_request_comment parses string 'false' as internal, not public")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.add_request_comment", issueIdOrKey="ITS-42",
                         body="Working on it", public="false"), [
    resp(201, body={"id": "1002", "public": False,
                    "author": {"displayName": "Agent Ann"},
                    "created": {"iso8601": "2026-07-17T10:01:00+0000"}}),
])
ok &= check("string 'false' stays internal",
            ex[0].body == json.dumps({"body": "Working on it", "public": False}), str(ex[0].body))

print("scenario: add_request_comment rejects non-boolean public, no HTTP")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.add_request_comment", issueIdOrKey="ITS-42",
                         body="Working on it", public="yes"), [])
ok &= check("invalid public rejected",
            out.get("error") == "public must be true or false", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: answer_approval approve")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.answer_approval", issueIdOrKey="ITS-42", approvalId="77",
                         decision="approve"), [
    resp(200, body={"id": "77", "name": "Hardware approval", "finalDecision": "approved",
                    "canAnswerApproval": False, "approvers": [{"approver": {"accountId": "a"}}],
                    "completedDate": {"iso8601": "2026-07-17T10:30:00+0000"}}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{API}/request/ITS-42/approval/77", ex[0].url)
ok &= check("body byte-exact", ex[0].body == json.dumps({"decision": "approve"}), str(ex[0].body))
ok &= check("approval output shaped",
            out == {"id": "77", "name": "Hardware approval", "finalDecision": "approved",
                    "completedDate": "2026-07-17T10:30:00+0000"}, str(out))

print("scenario: answer_approval rejects invalid decision, no HTTP")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.answer_approval", issueIdOrKey="ITS-42", approvalId="77",
                         decision="maybe"), [])
ok &= check("invalid decision error",
            out.get("error") == "decision must be 'approve' or 'decline'", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 6. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.get_request", issueIdOrKey="ITS-42"), [
    err(401, body={"errorMessages": ["Client must be authenticated to access this resource."]}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API message",
            "Client must be authenticated" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("token not leaked in error output", TOK not in raw and AUTH not in raw, raw[:300])

print("scenario: 429 includes Retry-After")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_service_desks"), [
    err(429, body={"errorMessage": "Rate limit exceeded"}, headers={"Retry-After": "42"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After included", "42" in out["error"], out.get("error", ""))
ok &= check("message included", "Rate limit exceeded" in out["error"], out.get("error", ""))

print("scenario: servicedeskapi errorMessage body parsed, non-JSON tolerated")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.get_request_slas", issueIdOrKey="ITS-42"), [
    err(404, body={"errorMessage": "The request was not found",
                   "i18nErrorMessage": {"i18nKey": "x", "parameters": []}}),
])
ok &= check("404 errorMessage surfaced",
            "404" in out["error"] and "The request was not found" in out["error"],
            out.get("error", ""))
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.get_request", issueIdOrKey="ITS-42"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("jira-service-management", creds(tool="jsm.get_request"), [])
ok &= check("issueIdOrKey required error", out.get("error") == "issueIdOrKey required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("jira-service-management",
                   {"tool": "jsm.list_service_desks", "baseUrl": "", "email": "", "apiToken": ""},
                   [])
ok &= check("connect-first message names the fields",
            "connect the Jira Service Management integration first" in out.get("error", "")
            and "apiToken" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("jira-service-management", creds(tool="jsm.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: jsm.nope", str(out))

# ---------------------------------------------------------------------------
# 7. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal issueIdOrKey is percent-encoded")
evil = "abc/../def?x=1"
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.get_request", issueIdOrKey=evil), [
    resp(200, body={"issueKey": "x"}),
])
ok &= check("id fully quoted in URL (no path escape)",
            ex[0].url == f"{API}/request/abc%2F..%2Fdef%3Fx%3D1?expand=participant%2CrequestType",
            ex[0].url)
ok &= check("no raw '../' in URL", "../" not in ex[0].url, ex[0].url)

print("scenario: bare '..' path segment rejected outright, no HTTP")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_queue_issues", serviceDeskId=".."), [])
ok &= check("dot-dot serviceDeskId rejected",
            out.get("error") == "Invalid serviceDeskId: '..'", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: traversal in write-tool segments percent-encoded")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.answer_approval", issueIdOrKey="a/b c", approvalId="7#7",
                         decision="decline"), [
    resp(200, body={"id": "7#7", "finalDecision": "declined"}),
])
ok &= check("both segments quoted",
            ex[0].url == f"{API}/request/a%2Fb%20c/approval/7%237", ex[0].url)

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("jira-service-management",
                   creds(tool="jsm.list_queue_issues", serviceDeskId="1"), [
    err(403, body={"errorMessage": "The calling user does not have permission (agent seat required)"}),
])
ok &= check("friendly 403 for non-agent", "403" in out.get("error", ""), str(out))
ok &= check("apiToken absent from error output",
            TOK not in json.dumps(out) and AUTH not in json.dumps(out), json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
