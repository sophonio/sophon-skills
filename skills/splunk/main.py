"""Splunk integration skill — SPL searches, jobs, saved searches, and indexes via the management REST API.

Pure standard library (urllib + ssl) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, authToken, insecureSkipTlsVerify).

Auth is a static Splunk authentication token (JWT) sent as "Authorization: Bearer {authToken}"
against the management API (typically port 8089). Self-signed TLS is common on the management
port, so an insecure-skip-verify toggle is provided. Every request passes output_mode=json
because the Splunk REST API defaults to Atom/XML output.
"""

import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
auth_token = params.get("authToken") or ""
insecure = str(params.get("insecureSkipTlsVerify") or "").strip().lower() == "true"

HEADERS = {
    "Authorization": f"Bearer {auth_token}",
    "Accept": "application/json",
    "User-Agent": "sophon-splunk-skill",
}


def ssl_context():
    """Build an SSL context; optionally skip verification for self-signed management certs."""
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Splunk management API.

    `data` is a dict sent as application/x-www-form-urlencoded (the shape the Splunk REST API
    expects). output_mode=json is always appended to the query string. Returns parsed JSON,
    or None for 204/empty bodies.
    """
    q = {"output_mode": "json"}
    if query:
        q.update({k: v for k, v in query.items() if v not in (None, "")})
    url = f"{base_url}{path}?{urllib.parse.urlencode(q)}"
    headers = dict(HEADERS)
    body = None
    if data is not None:
        clean = {k: v for k, v in data.items() if v not in (None, "")}
        body = urllib.parse.urlencode(clean).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ssl_context()) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        message = detail
        try:
            parsed = json.loads(detail)
            msgs = parsed.get("messages") or []
            if isinstance(msgs, list) and msgs:
                joined = "; ".join(m.get("text", "") for m in msgs if isinstance(m, dict))
                message = joined or detail
        except (ValueError, TypeError):
            pass
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                message = f"{message} (Retry-After: {retry_after})"
        raise RuntimeError(f"Splunk API error {e.code}: {message}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Splunk at {base_url}: {e.reason}") from e


def seg(value):
    """URL-encode a single path segment (e.g. a saved-search name or job sid)."""
    return urllib.parse.quote(str(value), safe="")


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def spl(query):
    """Normalize an SPL query: prefix 'search ' unless it starts with a generating command."""
    q = (query or "").strip()
    if not q:
        raise ValueError("query is required")
    if q.startswith("|") or q.lower() == "search" or q.lower().startswith("search "):
        return q
    return f"search {q}"


# --- summaries -------------------------------------------------------------

def saved_search_summary(entry):
    content = entry.get("content") or {}
    return {
        "name": entry.get("name"),
        "search": content.get("search"),
        "cronSchedule": content.get("cron_schedule"),
        "isScheduled": content.get("is_scheduled"),
        "disabled": content.get("disabled"),
    }


def index_summary(entry):
    content = entry.get("content") or {}
    return {
        "name": entry.get("name"),
        "totalEventCount": content.get("totalEventCount"),
        "currentDBSizeMB": content.get("currentDBSizeMB"),
        "maxTotalDataSizeMB": content.get("maxTotalDataSizeMB"),
        "disabled": content.get("disabled"),
    }


# --- tool handlers ---------------------------------------------------------

def oneshot_search():
    count = clamp(params.get("count", 50), 50, 100)
    result = request("POST", "/services/search/v2/jobs", data={
        "search": spl(params.get("query")),
        "exec_mode": "oneshot",
        "earliest_time": params.get("earliestTime"),
        "latest_time": params.get("latestTime"),
        "count": count,
    })
    results = (result or {}).get("results", [])
    print(json.dumps({
        "count": len(results),
        "fields": (result or {}).get("fields", []),
        "results": results,
    }))


def create_search_job():
    result = request("POST", "/services/search/v2/jobs", data={
        "search": spl(params.get("query")),
        "earliest_time": params.get("earliestTime"),
        "latest_time": params.get("latestTime"),
    })
    sid = (result or {}).get("sid")
    if not sid:
        raise RuntimeError("Splunk did not return a search job sid")
    print(json.dumps({"sid": sid}))


def get_job_status():
    sid = params.get("sid")
    if not sid:
        raise ValueError("sid is required")
    result = request("GET", f"/services/search/v2/jobs/{seg(sid)}")
    entries = (result or {}).get("entry") or []
    if not entries:
        # Splunk returns 204 No Content while a job is still QUEUED/PARSING.
        print(json.dumps({
            "sid": sid,
            "dispatchState": "QUEUED",
            "isDone": False,
            "message": "Job is not ready yet — poll again shortly.",
        }))
        return
    content = (entries[0].get("content") if entries else {}) or {}
    print(json.dumps({
        "sid": sid,
        "dispatchState": content.get("dispatchState"),
        "doneProgress": content.get("doneProgress"),
        "isDone": content.get("isDone"),
        "eventCount": content.get("eventCount"),
        "resultCount": content.get("resultCount"),
        "runDuration": content.get("runDuration"),
    }))


def get_job_results():
    sid = params.get("sid")
    if not sid:
        raise ValueError("sid is required")
    count = clamp(params.get("count", 50), 50, 100)
    try:
        offset = max(0, int(params.get("offset", 0)))
    except (TypeError, ValueError):
        offset = 0
    result = request("GET", f"/services/search/v2/jobs/{seg(sid)}/results", query={
        "count": count,
        "offset": offset,
    })
    if result is None:
        print(json.dumps({
            "sid": sid,
            "count": 0,
            "results": [],
            "message": "No results available yet — the job may still be running (check splunk.get_job_status).",
        }))
        return
    results = result.get("results", [])
    print(json.dumps({
        "sid": sid,
        "count": len(results),
        "fields": result.get("fields", []),
        "results": results,
    }))


def list_saved_searches():
    count = clamp(params.get("count", 30), 30, 100)
    result = request("GET", "/services/saved/searches", query={"count": count})
    searches = [saved_search_summary(e) for e in (result or {}).get("entry", [])]
    print(json.dumps({"count": len(searches), "savedSearches": searches}))


def run_saved_search():
    name = params.get("name")
    if not name:
        raise ValueError("name is required")
    result = request("POST", f"/services/saved/searches/{seg(name)}/dispatch", data={})
    sid = (result or {}).get("sid")
    if not sid:
        raise RuntimeError("Splunk did not return a search job sid")
    print(json.dumps({"name": name, "sid": sid}))


def list_indexes():
    count = clamp(params.get("count", 30), 30, 100)
    result = request("GET", "/services/data/indexes", query={"count": count})
    indexes = [index_summary(e) for e in (result or {}).get("entry", [])]
    print(json.dumps({"count": len(indexes), "indexes": indexes}))


HANDLERS = {
    "splunk.oneshot_search": oneshot_search,
    "splunk.create_search_job": create_search_job,
    "splunk.get_job_status": get_job_status,
    "splunk.get_job_results": get_job_results,
    "splunk.list_saved_searches": list_saved_searches,
    "splunk.run_saved_search": run_saved_search,
    "splunk.list_indexes": list_indexes,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and auth_token):
        print(json.dumps({"error": "Missing Splunk credentials: connect the Splunk integration first (baseUrl, authToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
