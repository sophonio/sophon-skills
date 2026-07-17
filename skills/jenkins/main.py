"""Jenkins integration skill — jobs, builds, console logs, and the build queue via the Jenkins
remote access API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, username, apiToken).

Auth is a per-user Jenkins API token sent as HTTP Basic auth (base64(username:apiToken)). API-token
requests are CSRF-exempt, so POSTs need no crumb. Object endpoints get `/api/json` appended and are
always bounded with `tree=` field selection and `{0,N}` array slices (the Jenkins API has no
pagination). Jobs nest under folders: full paths like "team-a/service-x" are converted to
/job/team-a/job/service-x with each segment URL-quoted.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
username = params.get("username") or ""
api_token = params.get("apiToken") or ""


def request(method, path, query=None, form=None, raw=False):
    """Make an authenticated request to Jenkins.

    Returns parsed JSON (or None for 204/empty bodies). With raw=True, returns
    (body_text, response_headers) instead — used for console logs and queue Locations.
    """
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = urllib.parse.urlencode(form).encode() if form else None
    auth = base64.b64encode(f"{username}:{api_token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "User-Agent": "sophon-jenkins-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode(errors="replace")
            if raw:
                return text, resp.headers
            if not text:
                return None
            try:
                return json.loads(text)
            except ValueError:
                raise RuntimeError("Unexpected non-JSON response — check baseUrl points at Jenkins")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace") if e.fp else ""
        msg = e.headers.get("X-Error") or ""
        if not msg:
            try:
                parsed = json.loads(detail)
                msg = parsed.get("message") or detail
            except (ValueError, TypeError):
                # Jenkins error pages are usually HTML — keep only a short hint.
                msg = detail[:200]
        if e.code == 401:
            msg = msg or "authentication failed — check username and apiToken"
        elif e.code == 404:
            msg = msg or "not found — check the job path and build number"
        elif e.code == 429:
            retry_after = e.headers.get("Retry-After")
            if retry_after:
                msg = f"{msg or 'rate limited'} (retry after {retry_after}s)"
        raise RuntimeError(f"Jenkins API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not reach your Jenkins instance (is it reachable from Sophon?): {e.reason}"
        ) from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def job_path(job):
    """Convert a full job path like 'team-a/service-x' to '/job/team-a/job/service-x'."""
    segments = [s for s in str(job or "").strip("/").split("/") if s]
    if not segments:
        raise ValueError("job path required (e.g. my-job or team-a/service-x)")
    return "".join(f"/job/{urllib.parse.quote(seg, safe='')}" for seg in segments)


COLOR_STATUS = {
    "blue": "success",
    "green": "success",
    "red": "failed",
    "yellow": "unstable",
    "aborted": "aborted",
    "disabled": "disabled",
    "notbuilt": "not_built",
    "grey": "unknown",
}


def job_summary(j):
    color = j.get("color") or ""
    building = color.endswith("_anime")
    base = color[: -len("_anime")] if building else color
    return {
        "name": j.get("name"),
        "url": j.get("url"),
        "status": COLOR_STATUS.get(base, base or "unknown"),
        "building": building,
        "isFolder": "Folder" in (j.get("_class") or ""),
    }


def queue_item_summary(item):
    task = item.get("task") or {}
    return {
        "id": item.get("id"),
        "why": item.get("why"),
        "inQueueSince": item.get("inQueueSince"),
        "task": {"name": task.get("name"), "url": task.get("url")},
    }


# --- Tool handlers ---------------------------------------------------------

def list_jobs():
    folder = params.get("folder")
    prefix = job_path(folder) if folder else ""
    result = request("GET", f"{prefix}/api/json",
                     query={"tree": "jobs[name,url,color]{0,50}"})
    jobs = [job_summary(j) for j in (result or {}).get("jobs", [])]
    print(json.dumps({"count": len(jobs), "jobs": jobs}))


def get_job():
    job = params.get("job")
    tree = ("name,description,buildable,inQueue,healthReport[description,score],"
            "lastBuild[number,result,timestamp,duration],"
            "lastSuccessfulBuild[number],lastFailedBuild[number]")
    result = request("GET", f"{job_path(job)}/api/json", query={"tree": tree}) or {}
    print(json.dumps({
        "name": result.get("name"),
        "description": result.get("description"),
        "buildable": result.get("buildable"),
        "inQueue": result.get("inQueue"),
        "healthReport": [
            {"description": h.get("description"), "score": h.get("score")}
            for h in (result.get("healthReport") or [])
        ],
        "lastBuild": result.get("lastBuild"),
        "lastSuccessfulBuild": result.get("lastSuccessfulBuild"),
        "lastFailedBuild": result.get("lastFailedBuild"),
    }))


def get_build():
    job = params.get("job")
    number = params.get("number")
    if number in (None, ""):
        raise ValueError("number required (the build number)")
    try:
        number = int(number)
    except (TypeError, ValueError):
        raise ValueError("number must be an integer build number")
    # Freestyle builds expose changeSet (singular); Pipeline (WorkflowRun) builds expose
    # changeSets (plural, an array of changeset objects). Jenkins silently ignores unknown
    # tree fields, so request both and merge.
    tree = ("number,result,timestamp,duration,building,"
            "actions[parameters[name,value],causes[shortDescription]],"
            "changeSet[items[msg,author[fullName]]{0,20}],"
            "changeSets[items[msg,author[fullName]]{0,20}]{0,5}")
    result = request("GET", f"{job_path(job)}/{number}/api/json",
                     query={"tree": tree}) or {}
    parameters = []
    causes = []
    for action in result.get("actions") or []:
        for p in action.get("parameters") or []:
            parameters.append({"name": p.get("name"), "value": p.get("value")})
        for c in action.get("causes") or []:
            causes.append(c.get("shortDescription"))
    change_items = list((result.get("changeSet") or {}).get("items") or [])
    for cs in result.get("changeSets") or []:
        change_items.extend((cs or {}).get("items") or [])
    changes = [
        {"msg": item.get("msg"), "author": (item.get("author") or {}).get("fullName")}
        for item in change_items
    ]
    print(json.dumps({
        "number": result.get("number"),
        "result": result.get("result"),
        "building": result.get("building"),
        "timestamp": result.get("timestamp"),
        "duration": result.get("duration"),
        "parameters": parameters,
        "causes": causes,
        "changes": changes,
    }))


def get_console_log():
    job = params.get("job")
    number = params.get("number")
    if number in (None, ""):
        raise ValueError("number required (the build number)")
    try:
        number = int(number)
    except (TypeError, ValueError):
        raise ValueError("number must be an integer build number")
    path = f"{job_path(job)}/{number}/logText/progressiveText"
    tail_kb = params.get("tailKb")
    if tail_kb is not None:
        # Simple approach (spec-sanctioned): fetch the full log from start=0 and keep only
        # the last tailKb of the text. For extremely large logs this downloads the whole
        # log; the sandbox timeout/memory caps bound the worst case.
        start = 0
    else:
        try:
            start = max(0, int(params.get("start") or 0))
        except (TypeError, ValueError):
            start = 0
    text, headers = request("GET", path, query={"start": start}, raw=True)
    truncated = False
    if tail_kb is not None:
        tail_bytes = clamp(tail_kb, 64, 256) * 1024
        if len(text) > tail_bytes:
            text = text[-tail_bytes:]
            truncated = True
    text_size = headers.get("X-Text-Size")
    result = {
        "text": text,
        "textSize": int(text_size) if text_size and str(text_size).isdigit() else None,
        "hasMore": (headers.get("X-More-Data") or "").lower() == "true",
        "truncated": truncated,
    }
    print(json.dumps(result))


def get_queue():
    result = request("GET", "/queue/api/json",
                     query={"tree": "items[id,why,inQueueSince,task[name,url]]{0,50}"})
    items = [queue_item_summary(i) for i in (result or {}).get("items", [])]
    print(json.dumps({"count": len(items), "items": items}))


def trigger_build():
    job = params.get("job")
    parameters = params.get("parameters")
    if parameters:
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be an object of name/value pairs")
        form = {k: "" if v is None else str(v) for k, v in parameters.items()}
        path = f"{job_path(job)}/buildWithParameters"
    else:
        form = None
        path = f"{job_path(job)}/build"
    _, headers = request("POST", path, form=form, raw=True)
    print(json.dumps({"queued": True, "queueUrl": headers.get("Location")}))


HANDLERS = {
    "jenkins.list_jobs": list_jobs,
    "jenkins.get_job": get_job,
    "jenkins.get_build": get_build,
    "jenkins.get_console_log": get_console_log,
    "jenkins.get_queue": get_queue,
    "jenkins.trigger_build": trigger_build,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and username and api_token):
        print(json.dumps({"error": "Missing Jenkins credentials: connect the Jenkins integration first (baseUrl, username, apiToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
