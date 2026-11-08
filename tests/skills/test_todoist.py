"""Offline mock-HTTP integration tests for the todoist skill.

Pinned against the Todoist API v1 contract: the former /rest/v2 endpoints now answer HTTP 410
"This endpoint is deprecated". The three v1 differences that shape these assertions are the
{"results": [...]} list envelope, the dedicated GET /tasks/filter?query= endpoint, and the absence
of a `url` field on tasks and projects.
"""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://api.todoist.com/api/v1"
TASK_URL = "https://app.todoist.com/app/task"
PROJECT_URL = "https://app.todoist.com/app/project"
INBOX_URL = "https://app.todoist.com/app/inbox"
TOK = "todoist-tok-SECRET-VALUE"


def page(items, next_cursor=None):
    """A v1 paginated list response."""
    return {"results": items, "next_cursor": next_cursor}


def creds(**extra):
    p = {"apiToken": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. todoist.list_tasks — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: list_tasks happy path / auth exactness")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks"), [
    resp(200, body=page([
        {"id": "t1", "content": "Write spec", "due": {"string": "today"}, "priority": 4,
         "project_id": "p1", "is_completed": False, "labels": ["work"], "comment_count": 2},
        {"id": "t2", "content": "Buy milk", "due": None, "priority": 1, "project_id": "p2"},
    ])),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("hits the v1 base, not the retired /rest/v2",
            ex[0].url.startswith(f"{BASE}/tasks") and "/rest/v2" not in ex[0].url, ex[0].url)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/tasks?limit=30", ex[0].url)
ok &= check("Authorization is exactly 'Bearer <token>'",
            ex[0].headers.get("authorization") == f"Bearer {TOK}", str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("User-Agent header",
            ex[0].headers.get("user-agent") == "sophon-todoist-skill", str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("unwraps the v1 results envelope", len(out.get("tasks", [])) == 2, str(out)[:200])
ok &= check("due flattened from object to string",
            out["tasks"][0]["due"] == "today", str(out["tasks"][0]))
ok &= check("due is None when API omits it", out["tasks"][1]["due"] is None, str(out["tasks"][1]))
ok &= check("project_id renamed to projectId",
            out["tasks"][0]["projectId"] == "p1", str(out["tasks"][0]))
ok &= check("url derived from the id (v1 no longer returns one)",
            out["tasks"][0]["url"] == f"{TASK_URL}/t1", str(out["tasks"][0]))
ok &= check("raw fields absent (project_id/labels/comment_count/is_completed)",
            all(k not in out["tasks"][0] for k in
                ("project_id", "labels", "comment_count", "is_completed")),
            str(out["tasks"][0]))
ok &= check("token not echoed in output", TOK not in json.dumps(out))

print("scenario: a bare array is still tolerated")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks"), [
    resp(200, body=[{"id": "t1", "content": "c", "priority": 1, "project_id": "p"}]),
])
ok &= check("bare array falls back cleanly", out.get("count") == 1, str(out)[:200])

# ---------------------------------------------------------------------------
# 2. todoist.list_tasks — filters, param order, clamping
# ---------------------------------------------------------------------------
print("scenario: list_tasks by project")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", projectId="p1"), [
    resp(200, body=page([])),
])
ok &= check("project_id passed to /tasks",
            ex[0].url == f"{BASE}/tasks?project_id=p1&limit=30", ex[0].url)
ok &= check("empty result count 0", out.get("count") == 0, str(out))

print("scenario: a filter query uses the dedicated v1 endpoint")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", filter="today | overdue"), [
    resp(200, body=page([])),
])
ok &= check("filtering hits /tasks/filter with query=, not /tasks with filter=",
            ex[0].url == f"{BASE}/tasks/filter?query=today+%7C+overdue&limit=30", ex[0].url)

print("scenario: filter plus project narrows client-side")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", projectId="p1", filter="today"), [
    resp(200, body=page([
        {"id": "t1", "content": "keep", "priority": 1, "project_id": "p1"},
        {"id": "t2", "content": "drop", "priority": 1, "project_id": "p2"},
    ])),
])
ok &= check("filter endpoint used (it takes no project_id)",
            ex[0].url == f"{BASE}/tasks/filter?query=today&limit=30", ex[0].url)
ok &= check("results narrowed to the requested project",
            out["count"] == 1 and out["tasks"][0]["id"] == "t1", str(out)[:200])

print("scenario: list_tasks omits blank filters entirely")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", projectId="", filter=None), [
    resp(200, body=page([])),
])
ok &= check("blank project/filter leave only the limit",
            ex[0].url == f"{BASE}/tasks?limit=30", ex[0].url)

print("scenario: list_tasks limit clamping")
five = [{"id": f"t{i}", "content": f"c{i}", "priority": 1, "project_id": "p"} for i in range(5)]
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", limit=2), [resp(200, body=page(five))])
ok &= check("limit forwarded to the API", ex[0].url == f"{BASE}/tasks?limit=2", ex[0].url)
ok &= check("limit trims the list", out["count"] == 2, str(out)[:200])
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", limit="abc"), [resp(200, body=page(five))])
ok &= check("non-numeric limit falls back to default 30", out["count"] == 5, str(out)[:200])
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", limit=0), [resp(200, body=page(five))])
ok &= check("limit 0 floors to 1", out["count"] == 1, str(out)[:200])
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks", limit=999), [resp(200, body=page(five))])
ok &= check("limit above max is capped at 200", ex[0].url == f"{BASE}/tasks?limit=200", ex[0].url)

# ---------------------------------------------------------------------------
# 3. todoist.list_projects
# ---------------------------------------------------------------------------
print("scenario: list_projects happy path")
out, ex = run_tool("todoist", creds(tool="todoist.list_projects"), [
    resp(200, body=page([
        {"id": "p1", "name": "Work", "color": "blue", "is_favorite": True,
         "inbox_project": False, "order": 3},
    ])),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/projects?limit=200", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("is_favorite renamed to isFavorite",
            out["projects"][0]["isFavorite"] is True, str(out["projects"][0]))
ok &= check("v1 'inbox_project' read as isInboxProject",
            out["projects"][0]["isInboxProject"] is False, str(out["projects"][0]))
ok &= check("project url derived from the id",
            out["projects"][0]["url"] == f"{PROJECT_URL}/p1", str(out["projects"][0]))
ok &= check("raw snake_case keys absent",
            all(k not in out["projects"][0] for k in ("is_favorite", "inbox_project", "is_inbox_project")),
            str(out["projects"][0]))

print("scenario: the inbox project gets the inbox url, and the v2 key spelling still works")
out, ex = run_tool("todoist", creds(tool="todoist.list_projects"), [
    resp(200, body=page([
        {"id": "p0", "name": "Inbox", "color": "grey", "is_favorite": False,
         "is_inbox_project": True},
    ])),
])
ok &= check("legacy is_inbox_project still honoured",
            out["projects"][0]["isInboxProject"] is True, str(out["projects"][0]))
ok &= check("inbox url used", out["projects"][0]["url"] == INBOX_URL, str(out["projects"][0]))

# ---------------------------------------------------------------------------
# 4. todoist.add_task — write path, body byte-exact
# ---------------------------------------------------------------------------
print("scenario: add_task full body")
out, ex = run_tool("todoist", creds(tool="todoist.add_task", content="Write spec",
                                    projectId=12345, dueString="tomorrow at 4pm",
                                    priority=4, description="notes"), [
    resp(200, body={"id": "t9", "content": "Write spec", "due": {"string": "tomorrow at 4pm"},
                    "priority": 4, "project_id": "12345"}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/tasks", ex[0].url)
ok &= check("Content-Type header",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("body maps camelCase args to snake_case and stringifies projectId",
            ex[0].json == {"content": "Write spec", "project_id": "12345",
                           "due_string": "tomorrow at 4pm", "priority": 4,
                           "description": "notes"}, str(ex[0].json))
ok &= check("output shaped through task_summary", out.get("id") == "t9"
            and out.get("due") == "tomorrow at 4pm" and out.get("projectId") == "12345", str(out))

print("scenario: add_task omits unset optional fields")
out, ex = run_tool("todoist", creds(tool="todoist.add_task", content="Just this"), [
    resp(200, body={"id": "t10", "content": "Just this", "priority": 1, "project_id": "p"}),
])
ok &= check("body carries only content", ex[0].json == {"content": "Just this"}, str(ex[0].json))

# ---------------------------------------------------------------------------
# 5. todoist.complete_task
# ---------------------------------------------------------------------------
print("scenario: complete_task")
out, ex = run_tool("todoist", creds(tool="todoist.complete_task", taskId="t9"), [resp(204)])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/tasks/t9/close", ex[0].url)
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("output", out == {"id": "t9", "closed": True}, str(out))

print("scenario: complete_task stringifies an integer id in the output")
out, ex = run_tool("todoist", creds(tool="todoist.complete_task", taskId=9), [resp(204)])
ok &= check("id stringified", out == {"id": "9", "closed": True}, str(out))

# ---------------------------------------------------------------------------
# 6. todoist.update_task — both response shapes
# ---------------------------------------------------------------------------
print("scenario: update_task with a returned body")
out, ex = run_tool("todoist", creds(tool="todoist.update_task", taskId="t9",
                                    content="Rewrite spec", priority=2), [
    resp(200, body={"id": "t9", "content": "Rewrite spec", "due": None, "priority": 2,
                    "project_id": "p1"}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/tasks/t9", ex[0].url)
ok &= check("body carries only supplied fields",
            ex[0].json == {"content": "Rewrite spec", "priority": 2}, str(ex[0].json))
ok &= check("output shaped through task_summary",
            out.get("content") == "Rewrite spec" and out.get("projectId") == "p1", str(out))

print("scenario: update_task with an empty 204 response")
out, ex = run_tool("todoist", creds(tool="todoist.update_task", taskId="t9",
                                    dueString="next Friday"), [resp(204)])
ok &= check("body maps dueString to due_string",
            ex[0].json == {"due_string": "next Friday"}, str(ex[0].json))
ok &= check("falls back to an updated marker", out == {"id": "t9", "updated": True}, str(out))

# ---------------------------------------------------------------------------
# 7. Validation errors — no HTTP call is made
# ---------------------------------------------------------------------------
print("scenario: validation errors short-circuit before any request")
for label, params, expected in [
    ("add_task without content", {"tool": "todoist.add_task"}, "content is required"),
    ("complete_task without taskId", {"tool": "todoist.complete_task"}, "taskId is required"),
    ("update_task without taskId", {"tool": "todoist.update_task"}, "taskId is required"),
    ("update_task with nothing to change", {"tool": "todoist.update_task", "taskId": "t9"},
     "Provide at least one field to update"),
]:
    out, ex = run_tool("todoist", creds(**params), [])
    ok &= check(f"{label} errors", expected in out.get("error", ""), str(out))
    ok &= check(f"{label} makes no request", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 8. HTTP error paths
# ---------------------------------------------------------------------------
print("scenario: HTTP errors are reported without leaking internals")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks"), [
    err(401, body="Invalid token"),
])
raw = json.dumps(out)
ok &= check("401 surfaced with status code",
            "401" in out.get("error", "") and "Invalid token" in out["error"], str(out))
ok &= check("no traceback in output", "Traceback" not in raw)
ok &= check("no urllib internals in output", "urllib" not in raw and "HTTPError" not in raw)
ok &= check("token not leaked on the error path", TOK not in raw, raw[:300])

print("scenario: non-JSON error body is tolerated")
out, ex = run_tool("todoist", creds(tool="todoist.list_projects"), [
    err(502, body="<html>Bad Gateway</html>"),
])
ok &= check("502 surfaced as a string error", "502" in out.get("error", ""), str(out))

print("scenario: rate limiting surfaces cleanly")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks"), [
    err(429, body={"error": "Rate limit exceeded"}),
])
ok &= check("429 surfaced", "429" in out.get("error", ""), str(out))

# ---------------------------------------------------------------------------
# 9. Credential and dispatch paths (the reported bug)
# ---------------------------------------------------------------------------
print("scenario: missing credential is reported, and no request is attempted")
out, ex = run_tool("todoist", {"tool": "todoist.list_tasks"}, [])
ok &= check("missing apiToken reports connect-first",
            "connect the Todoist integration" in out.get("error", ""), str(out))
ok &= check("no request attempted without a credential", len(ex) == 0, repr(ex))

out, ex = run_tool("todoist", {"tool": "todoist.list_tasks", "apiToken": ""}, [])
ok &= check("empty apiToken reports connect-first",
            "connect the Todoist integration" in out.get("error", ""), str(out))
ok &= check("no request attempted for an empty credential", len(ex) == 0, repr(ex))

print("scenario: no tool ever touches the retired /rest/v2 API")
for tool, extra, responses in [
    ("todoist.list_tasks", {}, [resp(200, body=page([]))]),
    ("todoist.list_tasks", {"filter": "today"}, [resp(200, body=page([]))]),
    ("todoist.list_projects", {}, [resp(200, body=page([]))]),
    ("todoist.add_task", {"content": "x"}, [resp(200, body={"id": "t1", "content": "x"})]),
    ("todoist.complete_task", {"taskId": "t1"}, [resp(204)]),
    ("todoist.update_task", {"taskId": "t1", "content": "y"}, [resp(204)]),
]:
    out, ex = run_tool("todoist", creds(tool=tool, **extra), responses)
    ok &= check(f"{tool} uses /api/v1",
                len(ex) == 1 and ex[0].url.startswith(f"{BASE}/") and "/rest/v2" not in ex[0].url,
                repr(ex))

print("scenario: a 410 from a retired endpoint is surfaced verbatim")
out, ex = run_tool("todoist", creds(tool="todoist.list_tasks"), [
    err(410, body="This endpoint is deprecated."),
])
ok &= check("410 surfaced with its message",
            "410" in out.get("error", "") and "deprecated" in out["error"], str(out))

print("scenario: unknown tool is rejected before the credential check")
out, ex = run_tool("todoist", creds(tool="todoist.nope"), [])
ok &= check("unknown tool with credentials", out.get("error") == "Unknown tool: todoist.nope", str(out))
ok &= check("unknown tool makes no request", len(ex) == 0, repr(ex))

out, ex = run_tool("todoist", {"tool": "todoist.nope"}, [])
ok &= check("unknown tool without credentials reports the tool, not the credential",
            out.get("error") == "Unknown tool: todoist.nope", str(out))

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
