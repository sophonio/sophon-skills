"""GitHub integration skill — talks to the GitHub REST API v3 with a personal access token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (token, apiBaseUrl).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")
api_base = (params.get("apiBaseUrl") or "https://api.github.com").rstrip("/")

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "sophon-github-skill",
    "Content-Type": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the GitHub API. Returns parsed JSON (or None for 204)."""
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
        raise RuntimeError(f"GitHub API error {e.code}: {detail}") from e


def split_repo(value):
    parts = (value or "").split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("repo must be in 'owner/name' form, e.g. octocat/hello-world")
    return parts[0], parts[1]


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def issue_summary(issue):
    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "user": (issue.get("user") or {}).get("login"),
        "labels": [lbl.get("name") for lbl in issue.get("labels", [])],
        "comments": issue.get("comments"),
        "url": issue.get("html_url"),
        "isPullRequest": "pull_request" in issue,
    }


def pr_summary(pr):
    return {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "user": (pr.get("user") or {}).get("login"),
        "head": (pr.get("head") or {}).get("ref"),
        "base": (pr.get("base") or {}).get("ref"),
        "draft": pr.get("draft"),
        "merged": pr.get("merged"),
        "mergeable": pr.get("mergeable"),
        "url": pr.get("html_url"),
    }


def run_summary(run):
    return {
        "id": run.get("id"),
        "name": run.get("name"),
        "displayTitle": run.get("display_title"),
        "branch": run.get("head_branch"),
        "event": run.get("event"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "createdAt": run.get("created_at"),
        "url": run.get("html_url"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_issues():
    owner, repo = split_repo(params.get("repo"))
    result = request("GET", f"/repos/{owner}/{repo}/issues", query={
        "state": params.get("state", "open"),
        "labels": params.get("labels"),
        "per_page": clamp(params.get("limit", 30), 30, 100),
    })
    # /issues also returns PRs; expose only true issues here.
    issues = [issue_summary(i) for i in (result or []) if "pull_request" not in i]
    print(json.dumps({"count": len(issues), "issues": issues}))


def get_issue():
    owner, repo = split_repo(params.get("repo"))
    number = int(params.get("number"))
    issue = request("GET", f"/repos/{owner}/{repo}/issues/{number}")
    data = issue_summary(issue)
    data["body"] = issue.get("body")
    print(json.dumps(data))


def create_issue():
    owner, repo = split_repo(params.get("repo"))
    payload = {"title": params.get("title", "")}
    if params.get("body"):
        payload["body"] = params["body"]
    if params.get("labels"):
        payload["labels"] = params["labels"]
    if params.get("assignees"):
        payload["assignees"] = params["assignees"]
    issue = request("POST", f"/repos/{owner}/{repo}/issues", data=payload)
    print(json.dumps({"number": issue.get("number"), "url": issue.get("html_url")}))


def comment():
    owner, repo = split_repo(params.get("repo"))
    number = int(params.get("number"))
    result = request("POST", f"/repos/{owner}/{repo}/issues/{number}/comments",
                     data={"body": params.get("body", "")})
    print(json.dumps({"id": result.get("id"), "url": result.get("html_url")}))


def list_pull_requests():
    owner, repo = split_repo(params.get("repo"))
    result = request("GET", f"/repos/{owner}/{repo}/pulls", query={
        "state": params.get("state", "open"),
        "per_page": clamp(params.get("limit", 30), 30, 100),
    })
    prs = [pr_summary(p) for p in (result or [])]
    print(json.dumps({"count": len(prs), "pullRequests": prs}))


def get_pull_request():
    owner, repo = split_repo(params.get("repo"))
    number = int(params.get("number"))
    pr = request("GET", f"/repos/{owner}/{repo}/pulls/{number}")
    data = pr_summary(pr)
    data["body"] = pr.get("body")
    data["additions"] = pr.get("additions")
    data["deletions"] = pr.get("deletions")
    data["changedFiles"] = pr.get("changed_files")
    print(json.dumps(data))


def create_pull_request():
    owner, repo = split_repo(params.get("repo"))
    payload = {
        "title": params.get("title", ""),
        "head": params.get("head", ""),
        "base": params.get("base", ""),
    }
    if params.get("body"):
        payload["body"] = params["body"]
    if params.get("draft"):
        payload["draft"] = bool(params["draft"])
    pr = request("POST", f"/repos/{owner}/{repo}/pulls", data=payload)
    print(json.dumps({"number": pr.get("number"), "url": pr.get("html_url")}))


def merge_pull_request():
    owner, repo = split_repo(params.get("repo"))
    number = int(params.get("number"))
    payload = {"merge_method": params.get("method", "merge")}
    if params.get("commitTitle"):
        payload["commit_title"] = params["commitTitle"]
    result = request("PUT", f"/repos/{owner}/{repo}/pulls/{number}/merge", data=payload)
    print(json.dumps({"merged": result.get("merged"), "sha": result.get("sha"),
                      "message": result.get("message")}))


def list_workflow_runs():
    owner, repo = split_repo(params.get("repo"))
    result = request("GET", f"/repos/{owner}/{repo}/actions/runs", query={
        "branch": params.get("branch"),
        "status": params.get("status"),
        "per_page": clamp(params.get("limit", 20), 20, 100),
    })
    runs = [run_summary(r) for r in (result or {}).get("workflow_runs", [])]
    print(json.dumps({"count": len(runs), "runs": runs}))


def get_workflow_run():
    owner, repo = split_repo(params.get("repo"))
    run_id = int(params.get("runId"))
    run = request("GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}")
    jobs = request("GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs")
    data = run_summary(run)
    data["jobs"] = [{
        "name": j.get("name"),
        "status": j.get("status"),
        "conclusion": j.get("conclusion"),
    } for j in (jobs or {}).get("jobs", [])]
    print(json.dumps(data))


def raw_api():
    method = (params.get("method") or "GET").upper()
    path = params.get("path", "")
    if not path.startswith("/"):
        raise ValueError("path must begin with '/', e.g. /repos/octocat/hello-world")
    result = request(method, path, data=params.get("body"))
    print(json.dumps({"status": "ok", "data": result}))


HANDLERS = {
    "github.list_issues": list_issues,
    "github.get_issue": get_issue,
    "github.create_issue": create_issue,
    "github.comment": comment,
    "github.list_pull_requests": list_pull_requests,
    "github.get_pull_request": get_pull_request,
    "github.create_pull_request": create_pull_request,
    "github.merge_pull_request": merge_pull_request,
    "github.list_workflow_runs": list_workflow_runs,
    "github.get_workflow_run": get_workflow_run,
    "github.api": raw_api,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not token:
        print(json.dumps({"error": "Missing GitHub credential: connect the GitHub integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
