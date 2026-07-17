"""Offline mock-HTTP integration tests for the planner Sophon skill."""
import json
import sys
import urllib.parse

from mockhttp import run_tool, resp, err, check

ok = True

CREDS = {
    "tenantId": "11111111-2222-3333-4444-555555555555",
    "clientId": "app-client-id",
    "clientSecret": "s3cr3t-value-XYZ",
    "defaultGroupId": "grp-default-1",
}
TOKEN_URL = ("https://login.microsoftonline.com/"
             "11111111-2222-3333-4444-555555555555/oauth2/v2.0/token")
TOKEN_BODY = urllib.parse.urlencode({
    "grant_type": "client_credentials",
    "client_id": CREDS["clientId"],
    "client_secret": CREDS["clientSecret"],
    "scope": "https://graph.microsoft.com/.default",
})
TOKEN_OK = resp(200, body={"access_token": "graph-tok-123", "token_type": "Bearer"})
GRAPH = "https://graph.microsoft.com/v1.0"

ASSIGNMENT = {"@odata.type": "#microsoft.graph.plannerAssignment", "orderHint": " !"}


def p(tool, **kw):
    d = dict(CREDS)
    d["tool"] = tool
    d.update(kw)
    return d


# ---------------------------------------------------------------- 1. AUTH EXACTNESS
print("[auth exactness — token flow + Bearer, list_plans w/ defaultGroupId fallback]")
out, ex = run_tool("planner", p("planner.list_plans"), [
    TOKEN_OK,
    resp(200, body={"value": [
        {"@odata.etag": 'W/"JzEtag"', "id": "plan-1", "title": "Sprint 12",
         "owner": "grp-default-1", "createdDateTime": "2026-01-01T00:00:00Z",
         "createdBy": {"user": {"id": "u0"}},
         "container": {"containerId": "grp-default-1", "type": "group"}},
        {"id": "plan-2", "title": "Backlog", "owner": "grp-default-1"},
    ]}),
])
ok &= check("exactly two requests (token + graph)", len(ex) == 2, repr(ex))
ok &= check("token: POST method", ex[0].method == "POST", ex[0].method)
ok &= check("token: exact tenant token URL", ex[0].url == TOKEN_URL, ex[0].url)
ok &= check("token: byte-exact form body", ex[0].body == TOKEN_BODY, str(ex[0].body))
ok &= check("token: form-urlencoded content type",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("token: skill user-agent",
            ex[0].headers.get("user-agent") == "sophon-planner-skill", str(ex[0].headers))
ok &= check("graph: URL uses defaultGroupId fallback (byte-exact)",
            ex[1].url == f"{GRAPH}/groups/grp-default-1/planner/plans", ex[1].url)
ok &= check("graph: Bearer token header",
            ex[1].headers.get("authorization") == "Bearer graph-tok-123", str(ex[1].headers))
ok &= check("graph: Accept json", ex[1].headers.get("accept") == "application/json",
            str(ex[1].headers))
ok &= check("graph: skill user-agent",
            ex[1].headers.get("user-agent") == "sophon-planner-skill", str(ex[1].headers))
ok &= check("graph: no request body on GET", ex[1].body is None, str(ex[1].body))
ok &= check("list_plans: count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("list_plans: plan shaped to id/title/owner",
            out["plans"][0] == {"id": "plan-1", "title": "Sprint 12", "owner": "grp-default-1"},
            str(out["plans"][0]))
ok &= check("list_plans: raw fields absent (etag/createdBy/container)",
            "createdBy" not in json.dumps(out) and "@odata.etag" not in json.dumps(out)
            and "container" not in json.dumps(out), str(out)[:300])
ok &= check("secret not echoed in output", CREDS["clientSecret"] not in json.dumps(out))

print("[list_plans — explicit groupId overrides default]")
out, ex = run_tool("planner", p("planner.list_plans", groupId="grp-other 2"), [
    TOKEN_OK, resp(200, body={"value": []}),
])
ok &= check("groupId override quoted in URL",
            ex[1].url == f"{GRAPH}/groups/grp-other%202/planner/plans", ex[1].url)
ok &= check("empty result count 0", out == {"count": 0, "plans": []}, str(out))

# ---------------------------------------------------------------- 2. READ HAPPY PATHS
print("[happy path — planner.list_buckets]")
out, ex = run_tool("planner", p("planner.list_buckets", planId="plan-1"), [
    TOKEN_OK,
    resp(200, body={"value": [
        {"@odata.etag": 'W/"b1etag"', "id": "bkt-1", "name": "To do",
         "orderHint": "8585", "planId": "plan-1"},
        {"id": "bkt-2", "name": "Done", "orderHint": "8586", "planId": "plan-1"},
    ]}),
])
ok &= check("buckets URL byte-exact",
            ex[1].url == f"{GRAPH}/planner/plans/plan-1/buckets", ex[1].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("bucket shaped to id/name/orderHint",
            out["buckets"][0] == {"id": "bkt-1", "name": "To do", "orderHint": "8585"},
            str(out["buckets"][0]))
ok &= check("raw planId/etag absent from buckets",
            "planId" not in json.dumps(out) and "@odata.etag" not in json.dumps(out),
            str(out)[:300])

print("[happy path — planner.list_tasks by plan]")
RAW_TASK = {
    "@odata.etag": 'W/"t1etag"', "id": "task-1", "title": "Draft budget",
    "percentComplete": 50, "dueDateTime": "2026-07-31T17:00:00Z", "bucketId": "bkt-1",
    "planId": "plan-1", "priority": 5, "orderHint": "8585",
    "assignments": {"user-2": {"@odata.type": "#microsoft.graph.plannerAssignment"},
                    "user-1": {"@odata.type": "#microsoft.graph.plannerAssignment"}},
    "createdBy": {"user": {"id": "u0"}}, "referenceCount": 0,
}
out, ex = run_tool("planner", p("planner.list_tasks", planId="plan-1"), [
    TOKEN_OK,
    resp(200, body={"value": [RAW_TASK, {"id": "task-2", "title": "Review",
                                         "percentComplete": 0, "assignments": {}}]}),
])
ok &= check("plan tasks URL byte-exact",
            ex[1].url == f"{GRAPH}/planner/plans/plan-1/tasks", ex[1].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
t = out["tasks"][0]
ok &= check("task shaped (id/title/percentComplete/dueDateTime/bucketId/priority)",
            t["id"] == "task-1" and t["title"] == "Draft budget" and t["percentComplete"] == 50
            and t["dueDateTime"] == "2026-07-31T17:00:00Z" and t["bucketId"] == "bkt-1"
            and t["priority"] == 5, str(t))
ok &= check("assignments flattened to sorted user ids",
            t["assignments"] == ["user-1", "user-2"], str(t))
ok &= check("raw fields absent (etag/createdBy/orderHint)",
            "@odata.etag" not in json.dumps(out) and "createdBy" not in json.dumps(out)
            and "orderHint" not in json.dumps(out), str(out)[:300])

print("[planner.list_tasks — bucketId variant + limit cap]")
out, ex = run_tool("planner", p("planner.list_tasks", bucketId="bkt-9", limit=1), [
    TOKEN_OK,
    resp(200, body={"value": [RAW_TASK, {"id": "task-2", "title": "Review"}]}),
])
ok &= check("bucket tasks URL byte-exact",
            ex[1].url == f"{GRAPH}/planner/buckets/bkt-9/tasks", ex[1].url)
ok &= check("limit=1 trims client-side", out.get("count") == 1 and len(out["tasks"]) == 1,
            str(out)[:200])

print("[happy path — planner.get_task (task + details)]")
out, ex = run_tool("planner", p("planner.get_task", taskId="task-1"), [
    TOKEN_OK,
    resp(200, body=RAW_TASK),
    resp(200, body={"@odata.etag": 'W/"d1etag"', "id": "task-1",
                    "description": "Prepare the Q3 draft",
                    "previewType": "automatic",
                    "checklist": {
                        "chk-guid-1": {"@odata.type": "#microsoft.graph.plannerChecklistItem",
                                       "title": "Collect numbers", "isChecked": True,
                                       "orderHint": "8585"},
                        "chk-guid-2": {"@odata.type": "#microsoft.graph.plannerChecklistItem",
                                       "title": "Write summary", "isChecked": False,
                                       "orderHint": "8586"}},
                    "references": {}}),
])
ok &= check("three requests (token + task + details)", len(ex) == 3, repr(ex))
ok &= check("task URL byte-exact", ex[1].url == f"{GRAPH}/planner/tasks/task-1", ex[1].url)
ok &= check("details URL byte-exact",
            ex[2].url == f"{GRAPH}/planner/tasks/task-1/details", ex[2].url)
ok &= check("task fields present",
            out["id"] == "task-1" and out["title"] == "Draft budget"
            and out["planId"] == "plan-1" and out["assignments"] == ["user-1", "user-2"],
            str(out)[:300])
ok &= check("description merged in", out.get("description") == "Prepare the Q3 draft",
            str(out)[:300])
ok &= check("checklist shaped to title/isChecked",
            out.get("checklist") == [{"title": "Collect numbers", "isChecked": True},
                                     {"title": "Write summary", "isChecked": False}],
            str(out.get("checklist")))
ok &= check("raw fields absent (etag/previewType/references/orderHint)",
            all(k not in json.dumps(out) for k in
                ("@odata.etag", "previewType", "references", "orderHint")), str(out)[:400])

# ---------------------------------------------------------------- 3. WRITE PATHS
print("[write path — planner.create_task body byte-exact]")
out, ex = run_tool("planner", p("planner.create_task", planId="plan-1",
                                title="Draft budget", bucketId="bkt-1",
                                dueDateTime="2026-07-31T17:00:00Z",
                                assigneeIds=["user-7"]), [
    TOKEN_OK,
    resp(201, body={"@odata.etag": 'W/"new"', "id": "task-new", "title": "Draft budget",
                    "planId": "plan-1", "bucketId": "bkt-1"}),
])
ok &= check("method POST", ex[1].method == "POST", ex[1].method)
ok &= check("create URL byte-exact", ex[1].url == f"{GRAPH}/planner/tasks", ex[1].url)
ok &= check("json content type", ex[1].headers.get("content-type") == "application/json",
            str(ex[1].headers))
ok &= check("create body exact (incl. plannerAssignment object)",
            ex[1].json == {"planId": "plan-1", "title": "Draft budget", "bucketId": "bkt-1",
                           "dueDateTime": "2026-07-31T17:00:00Z",
                           "assignments": {"user-7": ASSIGNMENT}},
            str(ex[1].json))
ok &= check("create output shaped",
            out == {"id": "task-new", "title": "Draft budget", "planId": "plan-1",
                    "bucketId": "bkt-1"}, str(out))

print("[planner.create_task — string assigneeIds treated as a single user id]")
out, ex = run_tool("planner", p("planner.create_task", planId="plan-1", title="T",
                                assigneeIds="user-7"), [
    TOKEN_OK,
    resp(201, body={"id": "task-new2", "title": "T", "planId": "plan-1"}),
])
ok &= check("string assigneeIds builds exactly one assignment (not per-character)",
            ex[1].json.get("assignments") == {"user-7": ASSIGNMENT}, str(ex[1].json))

print("[planner.create_task — non-list assigneeIds rejected before any HTTP]")
out, ex = run_tool("planner", p("planner.create_task", planId="plan-1", title="T",
                                assigneeIds={"user-7": True}), [])
ok &= check("non-list assigneeIds error",
            out.get("error") == "assigneeIds must be a list of user ids", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("[write path — planner.update_task GET-then-PATCH with If-Match ETag]")
ETAG1 = 'W/"JzEtag-one"'
ETAG2 = 'W/"JzEtag-two"'
UPDATED = dict(RAW_TASK)
UPDATED.update({"title": "Draft budget v2", "percentComplete": 100})
out, ex = run_tool("planner", p("planner.update_task", taskId="task-1",
                                title="Draft budget v2", percentComplete=100), [
    TOKEN_OK,
    resp(200, body={"@odata.etag": ETAG1, "id": "task-1"}),
    resp(200, body=UPDATED),
])
ok &= check("three requests (token + GET + PATCH)", len(ex) == 3, repr(ex))
ok &= check("pre-GET URL", ex[1].url == f"{GRAPH}/planner/tasks/task-1", ex[1].url)
ok &= check("PATCH method/URL", ex[2].method == "PATCH"
            and ex[2].url == f"{GRAPH}/planner/tasks/task-1", f"{ex[2].method} {ex[2].url}")
ok &= check("If-Match carries current ETag byte-exact",
            ex[2].headers.get("if-match") == ETAG1, str(ex[2].headers))
ok &= check("Prefer return=representation on PATCH",
            ex[2].headers.get("prefer") == "return=representation", str(ex[2].headers))
ok &= check("PATCH body only provided fields",
            ex[2].json == {"title": "Draft budget v2", "percentComplete": 100},
            str(ex[2].json))
ok &= check("update output shaped from returned representation",
            out.get("updated") is True and out.get("title") == "Draft budget v2"
            and out.get("percentComplete") == 100 and "@odata.etag" not in json.dumps(out),
            str(out)[:300])

print("[planner.update_task — 412 conflict re-GETs once and retries]")
out, ex = run_tool("planner", p("planner.update_task", taskId="task-1", title="X"), [
    TOKEN_OK,
    resp(200, body={"@odata.etag": ETAG1, "id": "task-1"}),
    err(412, body={"error": {"code": "", "message": "The attempted changes conflicted."}}),
    resp(200, body={"@odata.etag": ETAG2, "id": "task-1"}),
    resp(200, body={"@odata.etag": 'W/"final"', "id": "task-1", "title": "X"}),
])
ok &= check("five requests (token + GET + PATCH + re-GET + retry PATCH)", len(ex) == 5,
            repr(ex))
ok &= check("first PATCH used stale ETag", ex[2].headers.get("if-match") == ETAG1,
            str(ex[2].headers))
ok &= check("retry re-GET then PATCH with fresh ETag",
            ex[3].method == "GET" and ex[4].method == "PATCH"
            and ex[4].headers.get("if-match") == ETAG2, str(ex[4].headers))
ok &= check("retry succeeds, output updated", out.get("updated") is True
            and out.get("title") == "X", str(out))

print("[planner.update_task — second conflict surfaces the error]")
out, ex = run_tool("planner", p("planner.update_task", taskId="task-1", title="X"), [
    TOKEN_OK,
    resp(200, body={"@odata.etag": ETAG1, "id": "task-1"}),
    err(412, body={"error": {"code": "", "message": "The attempted changes conflicted."}}),
    resp(200, body={"@odata.etag": ETAG2, "id": "task-1"}),
    err(412, body={"error": {"code": "", "message": "The attempted changes conflicted."}}),
])
ok &= check("conflict error surfaced with 412",
            "error" in out and "412" in out["error"] and "conflicted" in out["error"],
            str(out))
ok &= check("no traceback on conflict", "Traceback" not in json.dumps(out), str(out)[:300])

print("[write path — planner.assign_task add/remove assignment map]")
out, ex = run_tool("planner", p("planner.assign_task", taskId="task-1", userId="user-9"), [
    TOKEN_OK,
    resp(200, body={"@odata.etag": ETAG1, "id": "task-1"}),
    resp(200, body={"@odata.etag": 'W/"final"', "id": "task-1",
                    "assignments": {"user-9": {}, "user-1": {}}}),
])
ok &= check("assign PATCH body is assignment object keyed by userId",
            ex[2].json == {"assignments": {"user-9": ASSIGNMENT}}, str(ex[2].json))
ok &= check("assign If-Match present", ex[2].headers.get("if-match") == ETAG1,
            str(ex[2].headers))
ok &= check("assign output", out == {"id": "task-1", "userId": "user-9", "action": "add",
                                     "assignments": ["user-1", "user-9"]}, str(out))

out, ex = run_tool("planner", p("planner.assign_task", taskId="task-1", userId="user-9",
                                action="remove"), [
    TOKEN_OK,
    resp(200, body={"@odata.etag": ETAG1, "id": "task-1"}),
    resp(200, body={"@odata.etag": 'W/"final"', "id": "task-1",
                    "assignments": {"user-1": {}}}),
])
ok &= check("remove PATCH body is null value for userId",
            ex[2].json == {"assignments": {"user-9": None}}, str(ex[2].json))
ok &= check("remove output", out == {"id": "task-1", "userId": "user-9", "action": "remove",
                                     "assignments": ["user-1"]}, str(out))

# ---------------------------------------------------------------- 4. ERROR PATHS
print("[error path — 401 friendly, no traceback, no secret]")
out, ex = run_tool("planner", p("planner.list_buckets", planId="plan-1"), [
    TOKEN_OK,
    err(401, body={"error": {"code": "InvalidAuthenticationToken",
                             "message": "Access token has expired."}}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes Graph code and message",
            "InvalidAuthenticationToken" in out["error"]
            and "Access token has expired." in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw,
            raw[:300])
ok &= check("client secret not leaked in error output",
            CREDS["clientSecret"] not in raw, raw[:300])

print("[error path — 429 includes Retry-After]")
out, ex = run_tool("planner", p("planner.list_tasks", planId="plan-1"), [
    TOKEN_OK,
    err(429, body={"error": {"code": "TooManyRequests", "message": "Too many requests"}},
        headers={"Retry-After": "27"}),
])
ok &= check("429 surfaced", "error" in out and "429" in out["error"], str(out))
ok &= check("Retry-After value included", "27" in out["error"], out.get("error", ""))

print("[error path — Planner 403 limit code surfaced plainly]")
out, ex = run_tool("planner", p("planner.create_task", planId="plan-1", title="one more"), [
    TOKEN_OK,
    err(403, body={"error": {"code": "MaximumTasksInProject",
                             "message": "Maximum number of tasks in the plan reached."}}),
])
ok &= check("403 with limit code in message",
            "403" in out["error"] and "MaximumTasksInProject" in out["error"],
            out.get("error", ""))

print("[error path — bad token endpoint credentials]")
out, ex = run_tool("planner", p("planner.list_plans"), [
    err(401, body={"error": "invalid_client",
                   "error_description": "AADSTS7000215: Invalid client secret provided."}),
])
ok &= check("token failure friendly",
            "error" in out and "Token request failed (401)" in out["error"]
            and "AADSTS7000215" in out["error"], str(out)[:300])
ok &= check("secret absent from token failure", CREDS["clientSecret"] not in json.dumps(out))

print("[error path — missing required param, no HTTP call]")
out, ex = run_tool("planner", p("planner.list_buckets"), [])
ok &= check("planId required error", out.get("error") == "planId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("planner", p("planner.list_tasks"), [])
ok &= check("planId-or-bucketId required error",
            out.get("error") == "planId or bucketId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("[error path — missing credentials, no HTTP call]")
out, ex = run_tool("planner", {"tool": "planner.list_plans"}, [])
ok &= check("connect-first message names the integration and fields",
            "connect the Planner integration first" in out.get("error", "")
            and "defaultGroupId" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("[error path — unknown tool]")
out, ex = run_tool("planner", p("planner.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: planner.nope", str(out))

# ---------------------------------------------------------------- 5. SECURITY PROBES
print("[security — path-traversal id percent-encoded]")
evil = "abc/../def?x=1"
out, ex = run_tool("planner", p("planner.list_buckets", planId=evil), [
    TOKEN_OK, resp(200, body={"value": []}),
])
ok &= check("planId fully quoted in URL (no path escape)",
            ex[1].url == f"{GRAPH}/planner/plans/abc%2F..%2Fdef%3Fx%3D1/buckets", ex[1].url)
ok &= check("no raw '../' or '?' in URL", "../" not in ex[1].url and "?" not in ex[1].url,
            ex[1].url)
out, ex = run_tool("planner", p("planner.get_task", taskId=evil), [
    TOKEN_OK,
    resp(200, body={"id": "x"}),
    resp(200, body={"id": "x", "checklist": {}}),
])
ok &= check("taskId quoted on get_task",
            ex[1].url == f"{GRAPH}/planner/tasks/abc%2F..%2Fdef%3Fx%3D1", ex[1].url)

print("[security — bare '..' segment rejected before any HTTP]")
out, ex = run_tool("planner", p("planner.update_task", taskId="..", title="X"), [])
ok &= check("'..' taskId rejected with ValueError message",
            out.get("error", "").startswith("Invalid taskId"), str(out))
ok &= check("no HTTP request made (not even token)", len(ex) == 0, repr(ex))
out, ex = run_tool("planner", p("planner.list_plans", groupId="."), [])
ok &= check("'.' groupId rejected", out.get("error", "").startswith("Invalid groupId"),
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("[security — secret absent from outputs on error paths]")
out, ex = run_tool("planner", p("planner.list_plans"), [
    TOKEN_OK, err(403, body={"error": {"code": "Forbidden", "message": "forbidden"}}),
])
ok &= check("clientSecret absent from 403 output",
            CREDS["clientSecret"] not in json.dumps(out), json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
