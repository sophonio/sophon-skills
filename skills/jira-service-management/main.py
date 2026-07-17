"""Jira Service Management integration skill — customer requests, queues, SLAs, and approvals
via the Atlassian Service Desk API ({baseUrl}/rest/servicedeskapi).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, email, apiToken).

Auth is HTTP Basic with an Atlassian account email + API token (created at id.atlassian.com;
tokens now expire — max lifetime one year — so plan rotation). This skill stays strictly on
the Service Desk API; the platform Jira REST API is covered by the separate jira skill.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
email = params.get("email") or ""
api_token = params.get("apiToken") or ""

API_ROOT = "/rest/servicedeskapi"


def seg(value, name):
    """Validate and URL-quote a params-derived path segment."""
    s = str(value if value is not None else "").strip()
    if not s:
        raise ValueError(f"{name} required")
    if s in (".", ".."):
        raise ValueError(f"Invalid {name}: {s!r}")
    return urllib.parse.quote(s, safe="")


def request(method, path, data=None, query=None):
    """Authenticated Service Desk API request. Returns parsed JSON (or None for 204/empty)."""
    url = f"{base_url}{API_ROOT}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
        "User-Agent": "sophon-jira-service-management-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = (parsed.get("errorMessage")
                   or "; ".join(parsed.get("errorMessages") or [])
                   or detail)
        except (ValueError, TypeError, AttributeError):
            msg = detail[:300]
        msg = msg or f"HTTP {e.code}"
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                # Retry-After may be delay-seconds or an HTTP-date (RFC 7231).
                after = f"{retry_after}s" if retry_after.isdigit() else retry_after
                msg = f"{msg} (rate limited; retry after {after})"
        raise RuntimeError(f"Jira Service Management API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Jira Service Management: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def values(result):
    """Unwrap the servicedeskapi paged envelope ({values, isLastPage, start, limit})."""
    return (result or {}).get("values") or []


def iso(date_obj):
    return (date_obj or {}).get("iso8601")


def duration(d):
    return (d or {}).get("friendly")


def user_summary(u):
    return {
        "displayName": (u or {}).get("displayName"),
        "emailAddress": (u or {}).get("emailAddress"),
    }


def queue_issue_summary(issue):
    issue = issue or {}
    fields = issue.get("fields") or {}
    return {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "requester": (fields.get("reporter") or {}).get("displayName"),
        "created": fields.get("created"),
    }


def sla_cycle(c):
    return {
        "breached": c.get("breached"),
        "goalDuration": duration(c.get("goalDuration")),
        "elapsedTime": duration(c.get("elapsedTime")),
        "remainingTime": duration(c.get("remainingTime")),
    }


# --- Tool handlers ---------------------------------------------------------

def list_service_desks():
    service_desk_id = params.get("serviceDeskId")
    limit = clamp(params.get("limit", 50), 50, 100)
    if service_desk_id not in (None, ""):
        result = request(
            "GET",
            f"/servicedesk/{seg(service_desk_id, 'serviceDeskId')}/requesttype",
            query={"limit": limit},
        )
        request_types = [{
            "id": rt.get("id"),
            "name": rt.get("name"),
            "description": rt.get("description"),
        } for rt in values(result)]
        print(json.dumps({"serviceDeskId": str(service_desk_id),
                          "count": len(request_types), "requestTypes": request_types}))
    else:
        result = request("GET", "/servicedesk", query={"limit": limit})
        desks = [{
            "id": d.get("id"),
            "projectKey": d.get("projectKey"),
            "projectName": d.get("projectName"),
        } for d in values(result)]
        print(json.dumps({"count": len(desks), "serviceDesks": desks}))


def list_queue_issues():
    sd = seg(params.get("serviceDeskId"), "serviceDeskId")
    queue_id = params.get("queueId")
    limit = clamp(params.get("limit", 25), 25, 100)
    if queue_id in (None, ""):
        result = request("GET", f"/servicedesk/{sd}/queue", query={"limit": limit})
        queues = [{
            "id": q.get("id"),
            "name": q.get("name"),
            "issueCount": q.get("issueCount"),
        } for q in values(result)]
        print(json.dumps({"count": len(queues), "queues": queues,
                          "note": "Pass queueId to list the issues in a queue."}))
        return
    result = request("GET", f"/servicedesk/{sd}/queue/{seg(queue_id, 'queueId')}/issue",
                     query={"limit": limit})
    issues = [queue_issue_summary(i) for i in values(result)]
    print(json.dumps({"count": len(issues), "issues": issues}))


def get_request():
    key = seg(params.get("issueIdOrKey"), "issueIdOrKey")
    result = request("GET", f"/request/{key}",
                     query={"expand": "participant,requestType"}) or {}
    rt = result.get("requestType") or {}
    participants = result.get("participant") or result.get("participants") or {}
    current = result.get("currentStatus") or {}
    print(json.dumps({
        "issueId": result.get("issueId"),
        "issueKey": result.get("issueKey"),
        "serviceDeskId": result.get("serviceDeskId"),
        "requestType": {"id": rt.get("id") or result.get("requestTypeId"),
                        "name": rt.get("name")},
        "createdDate": iso(result.get("createdDate")),
        "reporter": user_summary(result.get("reporter")),
        "participants": [user_summary(u) for u in (participants.get("values") or [])],
        "currentStatus": {
            "status": current.get("status"),
            "statusCategory": current.get("statusCategory"),
            "statusDate": iso(current.get("statusDate")),
        },
    }))


def get_request_slas():
    key = seg(params.get("issueIdOrKey"), "issueIdOrKey")
    result = request("GET", f"/request/{key}/sla")
    slas = []
    for s in values(result):
        ongoing = s.get("ongoingCycle")
        completed = s.get("completedCycles") or []
        slas.append({
            "name": s.get("name"),
            "breached": bool((ongoing or {}).get("breached")
                             or any(c.get("breached") for c in completed)),
            "ongoingCycle": sla_cycle(ongoing) if ongoing else None,
            "completedCycles": [sla_cycle(c) for c in completed],
        })
    print(json.dumps({"count": len(slas), "slas": slas}))


def create_request():
    service_desk_id = params.get("serviceDeskId")
    request_type_id = params.get("requestTypeId")
    summary = params.get("summary")
    if not service_desk_id:
        raise ValueError("serviceDeskId required")
    if not request_type_id:
        raise ValueError("requestTypeId required")
    if not summary:
        raise ValueError("summary required")
    field_values = {"summary": summary}
    if params.get("description"):
        field_values["description"] = params["description"]
    payload = {
        "serviceDeskId": str(service_desk_id),
        "requestTypeId": str(request_type_id),
        "requestFieldValues": field_values,
    }
    if params.get("raiseOnBehalfOf"):
        payload["raiseOnBehalfOf"] = params["raiseOnBehalfOf"]
    result = request("POST", "/request", data=payload) or {}
    print(json.dumps({
        "issueId": result.get("issueId"),
        "issueKey": result.get("issueKey"),
        "requestTypeId": result.get("requestTypeId"),
        "serviceDeskId": result.get("serviceDeskId"),
        "status": (result.get("currentStatus") or {}).get("status"),
        "webLink": (result.get("_links") or {}).get("web"),
    }))


def add_request_comment():
    key = seg(params.get("issueIdOrKey"), "issueIdOrKey")
    body_text = params.get("body")
    if not body_text:
        raise ValueError("body required")
    public = params.get("public", False)
    if isinstance(public, str):
        lowered = public.strip().lower()
        if lowered not in ("true", "false"):
            raise ValueError("public must be true or false")
        public = lowered == "true"
    elif not isinstance(public, bool):
        raise ValueError("public must be true or false")
    result = request("POST", f"/request/{key}/comment",
                     data={"body": body_text, "public": public}) or {}
    print(json.dumps({
        "id": result.get("id"),
        "public": result.get("public"),
        "author": (result.get("author") or {}).get("displayName"),
        "created": iso(result.get("created")),
    }))


def answer_approval():
    key = seg(params.get("issueIdOrKey"), "issueIdOrKey")
    approval_id = seg(params.get("approvalId"), "approvalId")
    decision = params.get("decision")
    if decision not in ("approve", "decline"):
        raise ValueError("decision must be 'approve' or 'decline'")
    result = request("POST", f"/request/{key}/approval/{approval_id}",
                     data={"decision": decision}) or {}
    print(json.dumps({
        "id": result.get("id"),
        "name": result.get("name"),
        "finalDecision": result.get("finalDecision"),
        "completedDate": iso(result.get("completedDate")),
    }))


HANDLERS = {
    "jsm.list_service_desks": list_service_desks,
    "jsm.list_queue_issues": list_queue_issues,
    "jsm.get_request": get_request,
    "jsm.get_request_slas": get_request_slas,
    "jsm.create_request": create_request,
    "jsm.add_request_comment": add_request_comment,
    "jsm.answer_approval": answer_approval,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and email and api_token):
        print(json.dumps({"error": "Missing Jira Service Management credentials: connect the Jira Service Management integration first (baseUrl, email, apiToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
