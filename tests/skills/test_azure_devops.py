"""Offline mock-HTTP integration tests for the azure-devops Sophon skill."""
import base64
import json
import sys
import urllib.parse

from mockhttp import run_tool, resp, err, check

ORG = "https://dev.azure.com/acme"
PAT = "s3cr3t-pat-XYZ"
AUTH = "Basic " + base64.b64encode(f":{PAT}".encode()).decode()
BASE = {"organizationUrl": ORG, "pat": PAT}

ok = True


def qs(url):
    """Parsed query params of a recorded URL, as {key: last_value}."""
    q = urllib.parse.urlparse(url).query
    return {k: v[-1] for k, v in urllib.parse.parse_qs(q, keep_blank_values=True).items()}


def api_version_ok(exchanges, expected_by_index=None):
    """Every recorded URL must carry an exact api-version param."""
    good = True
    for i, e in enumerate(exchanges):
        want = (expected_by_index or {}).get(i, "7.1")
        good &= qs(e.url).get("api-version") == want
    return good


# ---------------------------------------------------------------- 1. query_work_items (flat)
wiql = "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'Active'"
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.query_work_items", "project": "My Project", "wiql": wiql},
    [resp(200, body={"workItems": [{"id": 101}, {"id": 202}]}),
     resp(200, body={"value": [
         {"id": 101, "rev": 3, "fields": {
             "System.Id": 101, "System.WorkItemType": "Bug", "System.Title": "Crash on save",
             "System.State": "Active",
             "System.AssignedTo": {"displayName": "Ann Lee", "uniqueName": "ann@acme.com"}}},
         {"id": 202, "fields": {
             "System.Id": 202, "System.WorkItemType": "Task", "System.Title": "Add tests",
             "System.State": "New"}},
     ]})])
ok &= check("query: two HTTP calls (WIQL POST then workitems GET)", len(ex) == 2, repr(ex))
ok &= check("query: WIQL call is POST", ex[0].method == "POST", ex[0].method)
ok &= check("query: WIQL url path is /{project}/_apis/wit/wiql",
            urllib.parse.urlparse(ex[0].url).path == "/acme/My%20Project/_apis/wit/wiql", ex[0].url)
ok &= check("query: WIQL body is exactly {\"query\": wiql}", ex[0].json == {"query": wiql},
            str(ex[0].body))
ok &= check("query: WIQL POST Content-Type application/json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("query: WIQL call carries $top=50", qs(ex[0].url).get("$top") == "50", ex[0].url)
ok &= check("query: batch call is GET _apis/wit/workitems",
            ex[1].method == "GET"
            and urllib.parse.urlparse(ex[1].url).path == "/acme/_apis/wit/workitems", repr(ex[1]))
ok &= check("query: batch ids param", qs(ex[1].url).get("ids") == "101,202", ex[1].url)
ok &= check("query: batch fields param trims to summary fields",
            qs(ex[1].url).get("fields")
            == "System.Id,System.Title,System.State,System.AssignedTo,System.WorkItemType",
            ex[1].url)
ok &= check("query: auth header byte-exact on both calls",
            ex[0].headers.get("authorization") == AUTH
            and ex[1].headers.get("authorization") == AUTH, str(ex[0].headers))
ok &= check("query: api-version=7.1 on every URL", api_version_ok(ex), repr(ex))
ok &= check("query: output count", out.get("count") == 2, str(out)[:200])
ok &= check("query: items shaped (id/type/title/state/assignedTo)",
            out.get("workItems") == [
                {"id": 101, "type": "Bug", "title": "Crash on save", "state": "Active",
                 "assignedTo": "Ann Lee"},
                {"id": 202, "type": "Task", "title": "Add tests", "state": "New",
                 "assignedTo": None}], str(out)[:400])
ok &= check("query: raw payload fields absent",
            "fields" not in out["workItems"][0] and "rev" not in out["workItems"][0],
            str(out)[:200])

# ---------------------------------------------------------------- 1b. query_work_items (tree, dedupe, empty batch skip)
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.query_work_items", "project": "P1", "wiql": "tree query"},
    [resp(200, body={"workItemRelations": [
        {"target": {"id": 7}}, {"target": {"id": 8}}, {"target": {"id": 7}}, {"rel": "x"}]}),
     resp(200, body={"value": [{"id": 7, "fields": {}}, {"id": 8, "fields": {}}]})])
ok &= check("query-tree: dedupes relation targets into ids=7,8",
            qs(ex[1].url).get("ids") == "7,8", ex[1].url)
ok &= check("query-tree: count 2", out.get("count") == 2, str(out)[:200])

out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.query_work_items", "project": "P1", "wiql": "empty"},
    [resp(200, body={"workItems": []})])
ok &= check("query-empty: no second HTTP call when no matches", len(ex) == 1, repr(ex))
ok &= check("query-empty: {count: 0, workItems: []}",
            out == {"count": 0, "workItems": []}, str(out)[:200])

# ---------------------------------------------------------------- 2. get_work_item (with comments)
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.get_work_item", "id": 101, "commentLimit": 5},
    [resp(200, body={
        "id": 101, "rev": 4,
        "fields": {
            "System.WorkItemType": "Bug", "System.Title": "Crash on save",
            "System.State": "Active", "System.Reason": "New defect reported",
            "System.AssignedTo": {"displayName": "Ann Lee"},
            "System.CreatedBy": {"displayName": "Bob"},
            "System.CreatedDate": "2026-07-01T10:00:00Z",
            "System.ChangedDate": "2026-07-02T10:00:00Z",
            "System.TeamProject": "My Project",
            "System.AreaPath": "My Project\\Web",
            "System.IterationPath": "My Project\\Sprint 9",
            "System.Tags": "urgent; frontend",
            "System.Description": "<div>It crashes</div>"},
        "relations": [{"rel": "AttachedFile", "url": "https://x/att/1",
                       "attributes": {"name": "log.txt", "resourceSize": 12345}}],
        "_links": {"html": {"href": "https://dev.azure.com/acme/wi/101"}}}),
     resp(200, body={"totalCount": 1, "count": 1, "comments": [
         {"id": 9, "text": "fixed?", "createdBy": {"displayName": "Cara"},
          "createdDate": "2026-07-03T00:00:00Z", "url": "https://x/comments/9",
          "version": 1}]})])
ok &= check("get_wi: two calls (item then comments)", len(ex) == 2, repr(ex))
ok &= check("get_wi: item GET path", urllib.parse.urlparse(ex[0].url).path
            == "/acme/_apis/wit/workitems/101", ex[0].url)
ok &= check("get_wi: $expand=relations", qs(ex[0].url).get("$expand") == "relations", ex[0].url)
ok &= check("get_wi: comments path under project",
            urllib.parse.urlparse(ex[1].url).path
            == "/acme/My%20Project/_apis/wit/workItems/101/comments", ex[1].url)
ok &= check("get_wi: comments api-version is 7.1-preview.4 exactly",
            api_version_ok(ex, {1: "7.1-preview.4"}), repr([e.url for e in ex]))
ok &= check("get_wi: comments $top=5 and order=desc",
            qs(ex[1].url).get("$top") == "5" and qs(ex[1].url).get("order") == "desc", ex[1].url)
ok &= check("get_wi: auth exact on both", all(e.headers.get("authorization") == AUTH for e in ex),
            str(ex[1].headers))
ok &= check("get_wi: shaped core fields",
            out.get("id") == 101 and out.get("type") == "Bug" and out.get("state") == "Active"
            and out.get("assignedTo") == "Ann Lee" and out.get("project") == "My Project"
            and out.get("url") == "https://dev.azure.com/acme/wi/101", str(out)[:300])
ok &= check("get_wi: relations trimmed (no attributes blob)",
            out.get("relations") == [{"rel": "AttachedFile", "url": "https://x/att/1",
                                      "name": "log.txt"}], str(out.get("relations")))
ok &= check("get_wi: comments trimmed (no version/url keys)",
            out.get("comments") == [{"id": 9, "text": "fixed?", "createdBy": "Cara",
                                     "createdDate": "2026-07-03T00:00:00Z"}],
            str(out.get("comments")))
ok &= check("get_wi: raw 'fields'/'_links' absent from output",
            "fields" not in out and "_links" not in out, str(out.keys()))

# ---------------------------------------------------------------- 3. list_builds
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.list_builds", "project": "P1", "resultFilter": "failed"},
    [resp(200, body={"count": 1, "value": [
        {"id": 55, "buildNumber": "20260716.2", "status": "completed", "result": "failed",
         "startTime": "2026-07-16T08:00:00Z", "sourceBranch": "refs/heads/main",
         "definition": {"id": 3, "name": "CI"}, "queue": {"id": 1}, "priority": "normal",
         "orchestrationPlan": {"planId": "xx"}}]})])
ok &= check("builds: GET path", urllib.parse.urlparse(ex[0].url).path
            == "/acme/P1/_apis/build/builds", ex[0].url)
ok &= check("builds: default $top=25 and resultFilter passed, statusFilter dropped",
            qs(ex[0].url).get("$top") == "25" and qs(ex[0].url).get("resultFilter") == "failed"
            and "statusFilter" not in qs(ex[0].url), ex[0].url)
ok &= check("builds: api-version=7.1", api_version_ok(ex), ex[0].url)
ok &= check("builds: shaped output", out == {"count": 1, "builds": [
    {"id": 55, "buildNumber": "20260716.2", "definition": "CI", "status": "completed",
     "result": "failed", "startTime": "2026-07-16T08:00:00Z",
     "sourceBranch": "refs/heads/main"}]}, str(out)[:400])

# ---------------------------------------------------------------- 4. list_pull_requests (repo-scoped)
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.list_pull_requests", "project": "P1", "repository": "web app",
     "status": "active", "limit": 300},
    [resp(200, body={"value": [
        {"pullRequestId": 42, "title": "Fix login", "status": "active",
         "createdBy": {"displayName": "Dev One"}, "sourceRefName": "refs/heads/fix",
         "targetRefName": "refs/heads/main", "creationDate": "2026-07-10T00:00:00Z",
         "repository": {"id": "r1", "name": "web app"}, "mergeStatus": "succeeded",
         "lastMergeSourceCommit": {"commitId": "abc"}}]})])
ok &= check("prs: repo-scoped path with encoded repo name",
            urllib.parse.urlparse(ex[0].url).path
            == "/acme/P1/_apis/git/repositories/web%20app/pullrequests", ex[0].url)
ok &= check("prs: searchCriteria.status=active and $top clamped to 100",
            qs(ex[0].url).get("searchCriteria.status") == "active"
            and qs(ex[0].url).get("$top") == "100", ex[0].url)
ok &= check("prs: shaped output", out == {"count": 1, "pullRequests": [
    {"id": 42, "title": "Fix login", "createdBy": "Dev One", "sourceBranch": "refs/heads/fix",
     "targetBranch": "refs/heads/main", "status": "active", "repository": "web app",
     "creationDate": "2026-07-10T00:00:00Z"}]}, str(out)[:400])

# ---------------------------------------------------------------- 5. get_build (timeline failures)
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.get_build", "project": "P1", "buildId": 55},
    [resp(200, body={"id": 55, "buildNumber": "20260716.2", "status": "completed",
                     "result": "failed", "startTime": "s", "finishTime": "f",
                     "sourceBranch": "refs/heads/main", "sourceVersion": "abc123",
                     "definition": {"name": "CI"}, "requestedFor": {"displayName": "Dev One"},
                     "_links": {"web": {"href": "https://x/build/55"}}}),
     resp(200, body={"records": [
         {"name": "Build job", "type": "Job", "result": "failed",
          "issues": [{"type": "error", "message": "tests failed"}, {"type": "warning"}]},
         {"name": "Publish", "type": "Task", "result": "succeeded"}]})])
ok &= check("get_build: build then timeline URLs",
            urllib.parse.urlparse(ex[0].url).path == "/acme/P1/_apis/build/builds/55"
            and urllib.parse.urlparse(ex[1].url).path == "/acme/P1/_apis/build/builds/55/timeline",
            repr(ex))
ok &= check("get_build: failed jobs surfaced with messages only",
            out.get("failedJobs") == [{"name": "Build job", "type": "Job",
                                       "issues": ["tests failed"]}], str(out.get("failedJobs")))
ok &= check("get_build: summary merged", out.get("result") == "failed"
            and out.get("requestedFor") == "Dev One" and out.get("url") == "https://x/build/55",
            str(out)[:300])

# ---------------------------------------------------------------- 6. create_work_item (write path)
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.create_work_item", "project": "My Project", "type": "User Story",
     "title": "As a user...", "description": "<p>body</p>", "assignedTo": "ann@acme.com",
     "tags": "frontend; urgent"},
    [resp(200, body={"id": 303, "fields": {"System.WorkItemType": "User Story",
                                           "System.Title": "As a user...",
                                           "System.State": "New"},
                     "_links": {"html": {"href": "https://x/wi/303"}}})])
ok &= check("create: POST method", ex[0].method == "POST", ex[0].method)
ok &= check("create: path keeps literal $ and encodes type",
            urllib.parse.urlparse(ex[0].url).path
            == "/acme/My%20Project/_apis/wit/workitems/$User%20Story", ex[0].url)
ok &= check("create: Content-Type application/json-patch+json",
            ex[0].headers.get("content-type") == "application/json-patch+json",
            str(ex[0].headers))
ok &= check("create: body is exact JSON Patch array",
            ex[0].json == [
                {"op": "add", "path": "/fields/System.Title", "value": "As a user..."},
                {"op": "add", "path": "/fields/System.Description", "value": "<p>body</p>"},
                {"op": "add", "path": "/fields/System.AssignedTo", "value": "ann@acme.com"},
                {"op": "add", "path": "/fields/System.Tags", "value": "frontend; urgent"}],
            str(ex[0].body))
ok &= check("create: api-version=7.1", api_version_ok(ex), ex[0].url)
ok &= check("create: shaped output", out == {"id": 303, "type": "User Story",
                                             "title": "As a user...", "state": "New",
                                             "url": "https://x/wi/303"}, str(out)[:300])

# ---------------------------------------------------------------- 7. update_work_item (write path)
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.update_work_item", "id": 101, "state": "Resolved",
     "fields": {"Microsoft.VSTS.Common.Priority": 1}},
    [resp(200, body={"id": 101, "fields": {"System.Title": "Crash on save",
                                           "System.State": "Resolved",
                                           "System.AssignedTo": {"displayName": "Ann Lee"}}})])
ok &= check("update: PATCH method", ex[0].method == "PATCH", ex[0].method)
ok &= check("update: path", urllib.parse.urlparse(ex[0].url).path
            == "/acme/_apis/wit/workitems/101", ex[0].url)
ok &= check("update: json-patch content type",
            ex[0].headers.get("content-type") == "application/json-patch+json",
            str(ex[0].headers))
ok &= check("update: exact JSON Patch array incl. arbitrary field",
            ex[0].json == [
                {"op": "add", "path": "/fields/System.State", "value": "Resolved"},
                {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": 1}],
            str(ex[0].body))
ok &= check("update: shaped output", out == {"id": 101, "title": "Crash on save",
                                             "state": "Resolved", "assignedTo": "Ann Lee",
                                             "updated": True}, str(out)[:300])

# ---------------------------------------------------------------- 8. run_pipeline
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.run_pipeline", "project": "P1", "pipelineId": 12,
     "branch": "main"},
    [resp(200, body={"id": 900, "name": "20260717.1", "state": "inProgress",
                     "pipeline": {"id": 12, "name": "CI"},
                     "createdDate": "2026-07-17T00:00:00Z",
                     "_links": {"web": {"href": "https://x/run/900"}},
                     "url": "https://x/api/run/900"})])
ok &= check("pipeline: POST to /{project}/_apis/pipelines/{id}/runs",
            ex[0].method == "POST" and urllib.parse.urlparse(ex[0].url).path
            == "/acme/P1/_apis/pipelines/12/runs", repr(ex[0]))
ok &= check("pipeline: branch expanded to refs/heads/main in body",
            ex[0].json == {"resources": {"repositories": {"self":
                          {"refName": "refs/heads/main"}}}}, str(ex[0].body))
ok &= check("pipeline: api-version=7.1", api_version_ok(ex), ex[0].url)
ok &= check("pipeline: queued info returned",
            out == {"id": 900, "name": "20260717.1", "state": "inProgress", "pipeline": "CI",
                    "createdDate": "2026-07-17T00:00:00Z", "url": "https://x/run/900"},
            str(out)[:300])

# refs/-prefixed branch passes through unchanged
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.run_pipeline", "project": "P1", "pipelineId": 12,
     "branch": "refs/tags/v1"},
    [resp(200, body={"id": 901, "state": "inProgress"})])
ok &= check("pipeline: refs/ branch not double-prefixed",
            ex[0].json["resources"]["repositories"]["self"]["refName"] == "refs/tags/v1",
            str(ex[0].body))

# ---------------------------------------------------------------- 9. error paths
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.list_builds", "project": "P1"},
    [err(401, body={"message": "TF400813: not authorized"})])
ok &= check("401: friendly error object", isinstance(out.get("error"), str), str(out)[:300])
ok &= check("401: includes HTTP status and API message",
            "401" in out.get("error", "") and "TF400813" in out.get("error", ""),
            str(out)[:300])
ok &= check("401: includes PAT guidance", "PAT" in out.get("error", ""), str(out)[:300])
ok &= check("401: no traceback leaked", "Traceback" not in json.dumps(out), str(out)[:300])
ok &= check("401: PAT secret not leaked in output", PAT not in json.dumps(out), str(out)[:300])

out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.get_work_item", "id": 101},
    [err(429, body={"message": "Request was blocked due to exceeding usage of resource."},
         headers={"Retry-After": "42"})])
ok &= check("429: status surfaced", "429" in out.get("error", ""), str(out)[:300])
ok &= check("429: Retry-After surfaced in message",
            "retry after 42 seconds" in out.get("error", ""), str(out)[:300])

# non-JSON error body must not crash the error path
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.list_builds", "project": "P1"},
    [err(500, body="<html>oops</html>")])
ok &= check("500 html: still a JSON error with status",
            "500" in out.get("error", "") and "Traceback" not in json.dumps(out), str(out)[:300])

# missing credentials: no HTTP call at all
out, ex = run_tool(
    "azure-devops",
    {"tool": "devops.list_builds", "project": "P1", "organizationUrl": ORG},
    [])
ok &= check("no pat: friendly error, zero HTTP calls",
            "credentials" in out.get("error", "").lower() and len(ex) == 0, str(out)[:300])

# unknown tool
out, ex = run_tool("azure-devops", {**BASE, "tool": "devops.nope"}, [])
ok &= check("unknown tool: error mentions tool name", "devops.nope" in out.get("error", ""),
            str(out)[:200])

# missing required param -> ValueError surfaced as {"error": ...}, no HTTP
out, ex = run_tool("azure-devops", {**BASE, "tool": "devops.query_work_items", "project": "P1"}, [])
ok &= check("missing wiql: validation error, zero HTTP calls",
            "wiql" in out.get("error", "") and len(ex) == 0, str(out)[:200])

# ---------------------------------------------------------------- 10. security probes
evil = "abc/../def?x=1"
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.get_work_item", "id": evil},
    [resp(200, body={"id": 0, "fields": {}})])  # no TeamProject -> no comments call
path = urllib.parse.urlparse(ex[0].url).path
ok &= check("probe: path-ish id fully percent-encoded (no path escape)",
            path == "/acme/_apis/wit/workitems/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok &= check("probe: raw traversal string absent from URL", "abc/../def" not in ex[0].url
            and "?x=1" not in ex[0].url.split("?", 1)[1].replace("%3Fx%3D1", ""), ex[0].url)

evil_proj = "proj/../../other"
out, ex = run_tool(
    "azure-devops",
    {**BASE, "tool": "devops.list_builds", "project": evil_proj},
    [resp(200, body={"value": []})])
ok &= check("probe: project segment percent-encoded",
            urllib.parse.urlparse(ex[0].url).path
            == "/acme/proj%2F..%2F..%2Fother/_apis/build/builds", ex[0].url)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
