"""GitLab integration skill — talks to the GitLab REST API v4 with a personal access token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (token, host).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")
api_base = (params.get("host") or "https://gitlab.com").rstrip("/") + "/api/v4"

HEADERS = {
    "PRIVATE-TOKEN": token,
    "User-Agent": "sophon-gitlab-skill",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the GitLab API. Returns parsed JSON (or None for 204)."""
    url = f"{api_base}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"GitLab API error {e.code}: {detail}") from e


def project_ref(value):
    """Resolve a project id or path into a URL path segment.

    A numeric id is used as-is; a 'group/project' path is URL-encoded (the slash becomes %2F).
    """
    value = str(value or "").strip()
    if not value:
        raise ValueError("project is required (numeric id or 'group/project' path)")
    if value.isdigit():
        return value
    return urllib.parse.quote(value, safe="")


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def issue_summary(issue):
    return {
        "iid": issue.get("iid"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "author": (issue.get("author") or {}).get("username"),
        "labels": issue.get("labels", []),
        "userNotesCount": issue.get("user_notes_count"),
        "webUrl": issue.get("web_url"),
    }


def mr_summary(mr):
    return {
        "iid": mr.get("iid"),
        "title": mr.get("title"),
        "state": mr.get("state"),
        "author": (mr.get("author") or {}).get("username"),
        "sourceBranch": mr.get("source_branch"),
        "targetBranch": mr.get("target_branch"),
        "draft": mr.get("draft"),
        "mergeStatus": mr.get("merge_status"),
        "webUrl": mr.get("web_url"),
    }


def pipeline_summary(pipe):
    return {
        "id": pipe.get("id"),
        "iid": pipe.get("iid"),
        "ref": pipe.get("ref"),
        "sha": pipe.get("sha"),
        "status": pipe.get("status"),
        "source": pipe.get("source"),
        "createdAt": pipe.get("created_at"),
        "updatedAt": pipe.get("updated_at"),
        "webUrl": pipe.get("web_url"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_issues():
    proj = project_ref(params.get("project"))
    result = request("GET", f"/projects/{proj}/issues", query={
        "state": params.get("state", "opened"),
        "labels": params.get("labels"),
        "per_page": clamp(params.get("limit", 30), 30, 100),
    })
    issues = [issue_summary(i) for i in (result or [])]
    print(json.dumps({"count": len(issues), "issues": issues}))


def get_issue():
    proj = project_ref(params.get("project"))
    iid = int(params.get("iid"))
    issue = request("GET", f"/projects/{proj}/issues/{iid}")
    data = issue_summary(issue)
    data["description"] = issue.get("description")
    print(json.dumps(data))


def create_issue():
    proj = project_ref(params.get("project"))
    payload = {"title": params.get("title", "")}
    if params.get("description"):
        payload["description"] = params["description"]
    if params.get("labels"):
        payload["labels"] = params["labels"]
    issue = request("POST", f"/projects/{proj}/issues", data=payload)
    print(json.dumps({"iid": issue.get("iid"), "webUrl": issue.get("web_url")}))


def list_merge_requests():
    proj = project_ref(params.get("project"))
    result = request("GET", f"/projects/{proj}/merge_requests", query={
        "state": params.get("state", "opened"),
        "per_page": clamp(params.get("limit", 30), 30, 100),
    })
    mrs = [mr_summary(m) for m in (result or [])]
    print(json.dumps({"count": len(mrs), "mergeRequests": mrs}))


def get_merge_request():
    proj = project_ref(params.get("project"))
    iid = int(params.get("iid"))
    mr = request("GET", f"/projects/{proj}/merge_requests/{iid}")
    data = mr_summary(mr)
    data["description"] = mr.get("description")
    print(json.dumps(data))


def create_merge_request():
    proj = project_ref(params.get("project"))
    payload = {
        "source_branch": params.get("sourceBranch", ""),
        "target_branch": params.get("targetBranch", ""),
        "title": params.get("title", ""),
    }
    if params.get("description"):
        payload["description"] = params["description"]
    mr = request("POST", f"/projects/{proj}/merge_requests", data=payload)
    print(json.dumps({"iid": mr.get("iid"), "webUrl": mr.get("web_url")}))


def list_pipelines():
    proj = project_ref(params.get("project"))
    result = request("GET", f"/projects/{proj}/pipelines", query={
        "ref": params.get("ref"),
        "status": params.get("status"),
        "per_page": clamp(params.get("limit", 20), 20, 100),
    })
    pipes = [pipeline_summary(p) for p in (result or [])]
    print(json.dumps({"count": len(pipes), "pipelines": pipes}))


def raw_api():
    method = (params.get("method") or "GET").upper()
    path = params.get("path", "")
    if not path.startswith("/"):
        raise ValueError("path must begin with '/', e.g. /projects/123/releases")
    result = request(method, path, data=params.get("body"))
    print(json.dumps({"status": "ok", "data": result}))


HANDLERS = {
    "gitlab.list_issues": list_issues,
    "gitlab.get_issue": get_issue,
    "gitlab.create_issue": create_issue,
    "gitlab.list_merge_requests": list_merge_requests,
    "gitlab.get_merge_request": get_merge_request,
    "gitlab.create_merge_request": create_merge_request,
    "gitlab.list_pipelines": list_pipelines,
    "gitlab.api": raw_api,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not token:
        print(json.dumps({"error": "Missing GitLab credential: connect the GitLab integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
