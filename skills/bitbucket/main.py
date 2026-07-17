"""Bitbucket Cloud integration skill — repositories, pull requests, and pipelines via the
Bitbucket Cloud REST API 2.0.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (email, apiToken, workspace).

Auth is HTTP Basic with a scoped Atlassian API token: "Authorization: Basic
base64(email:apiToken)". The username MUST be the Atlassian account email (not the Bitbucket
username) — app passwords were retired on 2026-07-28. Some endpoints (PR diff, file source)
return raw text rather than JSON, so the request helper supports raw responses with size caps.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
email = params.get("email") or ""
api_token = params.get("apiToken") or ""
workspace = params.get("workspace") or ""

API_BASE = "https://api.bitbucket.org/2.0"
PAGE_CAP = 5  # max "next" pages to follow per list call

DIFF_MAX_BYTES = 100 * 1024   # ~100 KB
FILE_MAX_BYTES = 256 * 1024   # ~256 KB


def request(method, path, data=None, query=None, expect_json=True, max_bytes=None):
    """Make an authenticated request to the Bitbucket Cloud API.

    Returns parsed JSON (or None for 204/empty) when expect_json is True; otherwise returns
    (raw_bytes, truncated) where raw_bytes is capped at max_bytes when given. `path` may be a
    full URL (used when following pagination "next" links).
    """
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json" if expect_json else "*/*",
        "User-Agent": "sophon-bitbucket-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            if not expect_json:
                if max_bytes is not None:
                    raw = resp.read(max_bytes + 1)
                    return raw[:max_bytes], len(raw) > max_bytes
                return resp.read(), False
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        msg = detail
        try:
            parsed = json.loads(detail)
            if isinstance(parsed, dict):
                err = parsed.get("error")
                msg = (err.get("message") if isinstance(err, dict) else None) or detail
        except (ValueError, TypeError):
            pass
        if e.code == 429:
            retry_after = e.headers.get("Retry-After")
            limit_info = e.headers.get("X-RateLimit-Limit")
            extra = "Rate limit exceeded (1000 requests/hour)."
            if retry_after:
                extra += f" Retry after {retry_after} seconds."
            if limit_info:
                extra += f" Limit: {limit_info}."
            msg = f"{extra} {msg}".strip()
        raise RuntimeError(f"Bitbucket API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Bitbucket: {e.reason}") from e


def paged_values(path, query=None, limit=50):
    """GET a paginated list endpoint, following "next" links up to PAGE_CAP pages."""
    items = []
    next_url = path
    pages = 0
    while next_url and len(items) < limit and pages < PAGE_CAP:
        data = request("GET", next_url, query=query if pages == 0 else None) or {}
        items.extend(data.get("values", []))
        next_url = data.get("next")
        if next_url and not str(next_url).startswith(f"{API_BASE}/"):
            next_url = None  # never follow (or send credentials to) an off-API "next" link
        pages += 1
    return items[:limit]


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def repo_path(repo):
    if not repo:
        raise ValueError("repo required")
    return (f"/repositories/{urllib.parse.quote(workspace, safe='')}"
            f"/{urllib.parse.quote(str(repo), safe='')}")


def branch_name(endpoint):
    return ((endpoint or {}).get("branch") or {}).get("name")


def repo_summary(r):
    return {
        "slug": r.get("slug"),
        "name": r.get("name"),
        "mainbranch": (r.get("mainbranch") or {}).get("name"),
        "updated_on": r.get("updated_on"),
        "is_private": r.get("is_private"),
    }


def pr_summary(pr):
    return {
        "id": pr.get("id"),
        "title": pr.get("title"),
        "author": (pr.get("author") or {}).get("display_name"),
        "source_branch": branch_name(pr.get("source")),
        "destination_branch": branch_name(pr.get("destination")),
        "state": pr.get("state"),
    }


def participant_summary(p):
    return {
        "name": ((p.get("user") or {}).get("display_name")),
        "role": p.get("role"),
        "approved": p.get("approved"),
        "state": p.get("state"),
    }


def pipeline_summary(p):
    state = p.get("state") or {}
    return {
        "build_number": p.get("build_number"),
        "state": state.get("name"),
        "result": (state.get("result") or {}).get("name"),
        "branch": (p.get("target") or {}).get("ref_name"),
        "created_on": p.get("created_on"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_repos():
    limit = clamp(params.get("limit", 25), 25, 50)
    path = f"/repositories/{urllib.parse.quote(workspace, safe='')}"
    repos = paged_values(path, query={
        "q": params.get("query"),
        "sort": "-updated_on",
        "pagelen": limit,
    }, limit=limit)
    print(json.dumps({"count": len(repos), "repositories": [repo_summary(r) for r in repos]}))


def list_pull_requests():
    limit = clamp(params.get("limit", 25), 25, 50)
    path = f"{repo_path(params.get('repo'))}/pullrequests"
    prs = paged_values(path, query={
        "state": params.get("state"),
        "pagelen": limit,
    }, limit=limit)
    print(json.dumps({"count": len(prs), "pull_requests": [pr_summary(p) for p in prs]}))


def get_pull_request():
    pr_id = params.get("id")
    if pr_id in (None, ""):
        raise ValueError("id required")
    pr = request("GET", f"{repo_path(params.get('repo'))}/pullrequests/"
                        f"{urllib.parse.quote(str(pr_id), safe='')}") or {}
    participants = [participant_summary(p) for p in (pr.get("participants") or [])]
    reviewers = [((r.get("user") or r).get("display_name")) for r in (pr.get("reviewers") or [])]
    result = pr_summary(pr)
    result.update({
        "description": pr.get("description"),
        "created_on": pr.get("created_on"),
        "updated_on": pr.get("updated_on"),
        "comment_count": pr.get("comment_count"),
        "task_count": pr.get("task_count"),
        "close_source_branch": pr.get("close_source_branch"),
        "reviewers": reviewers,
        "participants": participants,
        "approval_count": sum(1 for p in participants if p.get("approved")),
        "url": ((pr.get("links") or {}).get("html") or {}).get("href"),
    })
    print(json.dumps(result))


def get_pr_diff():
    pr_id = params.get("id")
    if pr_id in (None, ""):
        raise ValueError("id required")
    raw, truncated = request(
        "GET",
        f"{repo_path(params.get('repo'))}/pullrequests/{urllib.parse.quote(str(pr_id), safe='')}/diff",
        expect_json=False,
        max_bytes=DIFF_MAX_BYTES,
    )
    print(json.dumps({
        "id": pr_id,
        "diff": (raw or b"").decode(errors="replace"),
        "truncated": truncated,
    }))


def get_file():
    ref = params.get("ref")
    file_path = params.get("path")
    if not ref:
        raise ValueError("ref required")
    if not file_path:
        raise ValueError("path required")
    if any(seg == ".." for seg in str(file_path).split("/")):
        raise ValueError("path must not contain '..' segments")
    raw, truncated = request(
        "GET",
        f"{repo_path(params.get('repo'))}/src/{urllib.parse.quote(str(ref), safe='')}"
        f"/{urllib.parse.quote(str(file_path), safe='/')}",
        expect_json=False,
        max_bytes=FILE_MAX_BYTES,
    )
    print(json.dumps({
        "path": file_path,
        "ref": ref,
        "content": (raw or b"").decode(errors="replace"),
        "truncated": truncated,
    }))


def list_pipeline_runs():
    limit = clamp(params.get("limit", 25), 25, 50)
    path = f"{repo_path(params.get('repo'))}/pipelines/"
    runs = paged_values(path, query={
        "sort": "-created_on",
        "pagelen": limit,
    }, limit=limit)
    print(json.dumps({"count": len(runs), "pipelines": [pipeline_summary(p) for p in runs]}))


def add_pr_comment():
    pr_id = params.get("id")
    text = params.get("text")
    if pr_id in (None, ""):
        raise ValueError("id required")
    if not text:
        raise ValueError("text required")
    comment = request(
        "POST",
        f"{repo_path(params.get('repo'))}/pullrequests/"
        f"{urllib.parse.quote(str(pr_id), safe='')}/comments",
        data={"content": {"raw": text}},
    ) or {}
    print(json.dumps({
        "id": comment.get("id"),
        "created_on": comment.get("created_on"),
        "url": ((comment.get("links") or {}).get("html") or {}).get("href"),
    }))


HANDLERS = {
    "bitbucket.list_repos": list_repos,
    "bitbucket.list_pull_requests": list_pull_requests,
    "bitbucket.get_pull_request": get_pull_request,
    "bitbucket.get_pr_diff": get_pr_diff,
    "bitbucket.get_file": get_file,
    "bitbucket.list_pipeline_runs": list_pipeline_runs,
    "bitbucket.add_pr_comment": add_pr_comment,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (email and api_token and workspace):
        print(json.dumps({"error": "Missing Bitbucket credentials: connect the Bitbucket integration first (email, apiToken, workspace)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
