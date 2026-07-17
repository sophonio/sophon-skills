"""Azure DevOps integration skill — work items, builds, pull requests, and pipelines.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (organizationUrl, pat).

Auth is a Personal Access Token sent as HTTP Basic with an EMPTY username:
Authorization: Basic base64(":" + pat). All endpoints live under
{organizationUrl}/{project}/_apis/... and require ?api-version=7.1 (work item comments are
still preview: 7.1-preview.4). Work-item create/update use JSON Patch bodies with
Content-Type application/json-patch+json.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
organization_url = (params.get("organizationUrl") or "").rstrip("/")
pat = params.get("pat") or ""

API_VERSION = "7.1"
COMMENTS_API_VERSION = "7.1-preview.4"
WORK_ITEM_FIELDS = "System.Id,System.Title,System.State,System.AssignedTo,System.WorkItemType"


def request(method, path, data=None, query=None, api_version=API_VERSION, content_type="application/json"):
    """Make an authenticated request to Azure DevOps. Returns parsed JSON (or None for 204/empty).

    `path` is appended to the organization URL and must already be URL-encoded.
    `api-version` is always added; query params that are None or "" are dropped.
    """
    q = {"api-version": api_version}
    if query:
        q.update({k: v for k, v in query.items() if v not in (None, "")})
    url = f"{organization_url}{path}?{urllib.parse.urlencode(q)}"
    body = json.dumps(data).encode() if data is not None else None
    auth = base64.b64encode(f":{pat}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "User-Agent": "sophon-azure-devops-skill",
    }
    if body is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 203:
                # Azure DevOps answers 203 with a sign-in page when the PAT is rejected.
                raise RuntimeError(
                    "Azure DevOps did not accept the credentials (got a sign-in page). "
                    "Check your PAT: it may be expired, inactive, or missing scopes — "
                    "sign in to Azure DevOps and create/renew an org-scoped token."
                )
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = (parsed.get("message") or detail) if isinstance(parsed, dict) else detail
        except (ValueError, TypeError):
            msg = detail
        if e.code == 401:
            msg = (f"{msg} " if msg else "") + (
                "Authentication failed — check your PAT (org-scoped, correct scopes, not expired; "
                "PATs go inactive if you have not signed in to Azure DevOps for a while)."
            )
        retry_after = e.headers.get("Retry-After") if e.headers else None
        if retry_after:
            msg = f"{msg} Rate limited by Azure DevOps — retry after {retry_after} seconds."
        raise RuntimeError(f"Azure DevOps API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Azure DevOps: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def enc(segment):
    """Percent-encode a single URL path segment."""
    return urllib.parse.quote(str(segment), safe="")


def identity_name(identity):
    return (identity or {}).get("displayName") or (identity or {}).get("uniqueName")


def work_item_summary(item):
    fields = item.get("fields") or {}
    return {
        "id": item.get("id"),
        "type": fields.get("System.WorkItemType"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "assignedTo": identity_name(fields.get("System.AssignedTo")),
    }


def build_summary(build):
    return {
        "id": build.get("id"),
        "buildNumber": build.get("buildNumber"),
        "definition": (build.get("definition") or {}).get("name"),
        "status": build.get("status"),
        "result": build.get("result"),
        "startTime": build.get("startTime"),
        "sourceBranch": build.get("sourceBranch"),
    }


def pull_request_summary(pr):
    return {
        "id": pr.get("pullRequestId"),
        "title": pr.get("title"),
        "createdBy": identity_name(pr.get("createdBy")),
        "sourceBranch": pr.get("sourceRefName"),
        "targetBranch": pr.get("targetRefName"),
        "status": pr.get("status"),
        "repository": (pr.get("repository") or {}).get("name"),
        "creationDate": pr.get("creationDate"),
    }


# --- Tool handlers ---------------------------------------------------------

def query_work_items():
    project = params.get("project")
    wiql = params.get("wiql")
    if not project:
        raise ValueError("project required")
    if not wiql:
        raise ValueError("wiql required")
    # $top makes the server cap flat-query results, so queries matching >20000 items
    # don't fail with VS402337. Tree queries (workItemRelations) are not covered by
    # $top, hence the local ids[:50] cap below stays.
    result = request("POST", f"/{enc(project)}/_apis/wit/wiql", data={"query": wiql},
                     query={"$top": 50}) or {}
    if result.get("workItems") is not None:  # flat query
        ids = [wi.get("id") for wi in result.get("workItems", [])]
    else:  # tree / one-hop queries return workItemRelations
        ids = []
        for rel in result.get("workItemRelations", []):
            target = rel.get("target") or {}
            if target.get("id") is not None and target["id"] not in ids:
                ids.append(target["id"])
    ids = ids[:50]
    if not ids:
        print(json.dumps({"count": 0, "workItems": []}))
        return
    batch = request("GET", "/_apis/wit/workitems", query={
        "ids": ",".join(str(i) for i in ids),
        "fields": WORK_ITEM_FIELDS,
    }) or {}
    items = [work_item_summary(it) for it in batch.get("value", [])]
    print(json.dumps({"count": len(items), "workItems": items}))


def get_work_item():
    work_item_id = params.get("id")
    if not work_item_id:
        raise ValueError("id required")
    item = request("GET", f"/_apis/wit/workitems/{enc(work_item_id)}",
                   query={"$expand": "relations"}) or {}
    fields = item.get("fields") or {}
    relations = [{
        "rel": r.get("rel"),
        "url": r.get("url"),
        "name": (r.get("attributes") or {}).get("name"),
    } for r in (item.get("relations") or [])]
    comments = []
    project = fields.get("System.TeamProject")
    if project:
        try:
            comment_limit = clamp(params.get("commentLimit", 10), 10, 50)
            result = request(
                "GET",
                f"/{enc(project)}/_apis/wit/workItems/{enc(work_item_id)}/comments",
                query={"$top": comment_limit, "order": "desc"},
                api_version=COMMENTS_API_VERSION,
            ) or {}
            comments = [{
                "id": c.get("id"),
                "text": c.get("text"),
                "createdBy": identity_name(c.get("createdBy")),
                "createdDate": c.get("createdDate"),
            } for c in result.get("comments", [])]
        except RuntimeError:
            comments = []  # comments are best-effort; the work item itself is the payload
    print(json.dumps({
        "id": item.get("id"),
        "rev": item.get("rev"),
        "type": fields.get("System.WorkItemType"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "reason": fields.get("System.Reason"),
        "assignedTo": identity_name(fields.get("System.AssignedTo")),
        "createdBy": identity_name(fields.get("System.CreatedBy")),
        "createdDate": fields.get("System.CreatedDate"),
        "changedDate": fields.get("System.ChangedDate"),
        "project": project,
        "areaPath": fields.get("System.AreaPath"),
        "iterationPath": fields.get("System.IterationPath"),
        "tags": fields.get("System.Tags"),
        "description": fields.get("System.Description"),
        "url": ((item.get("_links") or {}).get("html") or {}).get("href"),
        "relations": relations,
        "comments": comments,
    }))


def create_work_item():
    project = params.get("project")
    work_item_type = params.get("type")
    title = params.get("title")
    if not project:
        raise ValueError("project required")
    if not work_item_type:
        raise ValueError("type required")
    if not title:
        raise ValueError("title required")
    ops = [{"op": "add", "path": "/fields/System.Title", "value": title}]
    if params.get("description"):
        ops.append({"op": "add", "path": "/fields/System.Description", "value": params["description"]})
    if params.get("assignedTo"):
        ops.append({"op": "add", "path": "/fields/System.AssignedTo", "value": params["assignedTo"]})
    if params.get("tags"):
        ops.append({"op": "add", "path": "/fields/System.Tags", "value": params["tags"]})
    # The work item type is addressed as a literal "$" + type in the path (e.g. workitems/$Bug);
    # the "$" itself must stay a dollar sign while the type name is percent-encoded.
    item = request("POST", f"/{enc(project)}/_apis/wit/workitems/${enc(work_item_type)}",
                   data=ops, content_type="application/json-patch+json") or {}
    fields = item.get("fields") or {}
    print(json.dumps({
        "id": item.get("id"),
        "type": fields.get("System.WorkItemType"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "url": ((item.get("_links") or {}).get("html") or {}).get("href"),
    }))


def update_work_item():
    work_item_id = params.get("id")
    if not work_item_id:
        raise ValueError("id required")
    # "add" acts as add-or-replace for work item fields, so it is safe whether or
    # not the field currently has a value (a bare "replace" fails on unset fields).
    ops = []
    if params.get("state"):
        ops.append({"op": "add", "path": "/fields/System.State", "value": params["state"]})
    if params.get("assignedTo"):
        ops.append({"op": "add", "path": "/fields/System.AssignedTo", "value": params["assignedTo"]})
    if params.get("title"):
        ops.append({"op": "add", "path": "/fields/System.Title", "value": params["title"]})
    for field, value in (params.get("fields") or {}).items():
        ops.append({"op": "add", "path": f"/fields/{field}", "value": value})
    if not ops:
        raise ValueError("nothing to update: provide state, assignedTo, title, and/or fields")
    item = request("PATCH", f"/_apis/wit/workitems/{enc(work_item_id)}",
                   data=ops, content_type="application/json-patch+json") or {}
    fields = item.get("fields") or {}
    print(json.dumps({
        "id": item.get("id"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "assignedTo": identity_name(fields.get("System.AssignedTo")),
        "updated": True,
    }))


def list_builds():
    project = params.get("project")
    if not project:
        raise ValueError("project required")
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", f"/{enc(project)}/_apis/build/builds", query={
        "$top": limit,
        "statusFilter": params.get("statusFilter"),
        "resultFilter": params.get("resultFilter"),
    }) or {}
    builds = [build_summary(b) for b in result.get("value", [])]
    print(json.dumps({"count": len(builds), "builds": builds}))


def get_build():
    project = params.get("project")
    build_id = params.get("buildId")
    if not project:
        raise ValueError("project required")
    if not build_id:
        raise ValueError("buildId required")
    build = request("GET", f"/{enc(project)}/_apis/build/builds/{enc(build_id)}") or {}
    failures = []
    try:
        timeline = request("GET", f"/{enc(project)}/_apis/build/builds/{enc(build_id)}/timeline") or {}
        for record in timeline.get("records", []):
            if record.get("result") == "failed":
                failures.append({
                    "name": record.get("name"),
                    "type": record.get("type"),
                    "issues": [
                        (issue.get("message") or "")
                        for issue in (record.get("issues") or [])
                        if issue.get("message")
                    ],
                })
    except RuntimeError:
        failures = []  # timeline may not exist yet for queued builds
    summary = build_summary(build)
    summary.update({
        "finishTime": build.get("finishTime"),
        "requestedFor": identity_name(build.get("requestedFor")),
        "sourceVersion": build.get("sourceVersion"),
        "url": ((build.get("_links") or {}).get("web") or {}).get("href"),
        "failedJobs": failures,
    })
    print(json.dumps(summary))


def list_pull_requests():
    project = params.get("project")
    if not project:
        raise ValueError("project required")
    repository = params.get("repository")
    limit = clamp(params.get("limit", 25), 25, 100)
    if repository:
        path = f"/{enc(project)}/_apis/git/repositories/{enc(repository)}/pullrequests"
    else:
        path = f"/{enc(project)}/_apis/git/pullrequests"
    result = request("GET", path, query={
        "searchCriteria.status": params.get("status"),
        "$top": limit,
    }) or {}
    prs = [pull_request_summary(pr) for pr in result.get("value", [])]
    print(json.dumps({"count": len(prs), "pullRequests": prs}))


def run_pipeline():
    project = params.get("project")
    pipeline_id = params.get("pipelineId")
    if not project:
        raise ValueError("project required")
    if not pipeline_id:
        raise ValueError("pipelineId required")
    payload = {}
    branch = params.get("branch")
    if branch:
        ref = branch if branch.startswith("refs/") else f"refs/heads/{branch}"
        payload = {"resources": {"repositories": {"self": {"refName": ref}}}}
    run = request("POST", f"/{enc(project)}/_apis/pipelines/{enc(pipeline_id)}/runs",
                  data=payload) or {}
    print(json.dumps({
        "id": run.get("id"),
        "name": run.get("name"),
        "state": run.get("state"),
        "pipeline": (run.get("pipeline") or {}).get("name"),
        "createdDate": run.get("createdDate"),
        "url": ((run.get("_links") or {}).get("web") or {}).get("href") or run.get("url"),
    }))


HANDLERS = {
    "devops.query_work_items": query_work_items,
    "devops.get_work_item": get_work_item,
    "devops.create_work_item": create_work_item,
    "devops.update_work_item": update_work_item,
    "devops.list_builds": list_builds,
    "devops.get_build": get_build,
    "devops.list_pull_requests": list_pull_requests,
    "devops.run_pipeline": run_pipeline,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (organization_url and pat):
        print(json.dumps({"error": "Missing Azure DevOps credentials: connect the Azure DevOps integration first (organizationUrl, pat)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
