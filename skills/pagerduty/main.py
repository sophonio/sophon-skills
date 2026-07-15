"""PagerDuty integration skill — talks to the PagerDuty REST API (v2) with an API token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (apiToken, fromEmail).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_token = params.get("apiToken", "")
from_email = params.get("fromEmail", "")
base = "https://api.pagerduty.com"

HEADERS = {
    "Authorization": f"Token token={api_token}",
    "Accept": "application/vnd.pagerduty+json;version=2",
    "Content-Type": "application/json",
    "User-Agent": "sophon-pagerduty-skill",
}


def request(method, path, data=None, query=None, write=False):
    """Make an authenticated request to the PagerDuty API. Returns parsed JSON (or None for 204)."""
    url = f"{base}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "", [])}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean, doseq=True)}"
    headers = dict(HEADERS)
    if write:
        headers["From"] = from_email
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"PagerDuty API error {e.code}: {detail}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def require(key):
    value = params.get(key)
    if value in (None, ""):
        raise ValueError(f"Missing required parameter: {key}")
    return value


def require_from():
    if not from_email:
        raise ValueError(
            "This action requires a From email. Set 'From Email' on the PagerDuty integration "
            "to the email of a valid PagerDuty user."
        )


def as_list(value):
    if value in (None, ""):
        return None
    if isinstance(value, list):
        return value
    return [value]


def incident_summary(incident):
    return {
        "id": incident.get("id"),
        "incident_number": incident.get("incident_number"),
        "title": incident.get("title"),
        "status": incident.get("status"),
        "urgency": incident.get("urgency"),
        "html_url": incident.get("html_url"),
    }


def oncall_summary(oncall):
    user = oncall.get("user") or {}
    schedule = oncall.get("schedule") or {}
    policy = oncall.get("escalation_policy") or {}
    return {
        "user": user.get("summary"),
        "userId": user.get("id"),
        "schedule": schedule.get("summary"),
        "scheduleId": schedule.get("id"),
        "escalationPolicy": policy.get("summary"),
        "escalationLevel": oncall.get("escalation_level"),
        "start": oncall.get("start"),
        "end": oncall.get("end"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_incidents():
    result = request("GET", "/incidents", query={
        "statuses[]": as_list(params.get("statuses")),
        "urgencies[]": as_list(params.get("urgencies")),
        "limit": clamp(params.get("limit", 25), 25, 100),
    })
    incidents = [incident_summary(i) for i in (result or {}).get("incidents", [])]
    print(json.dumps({"count": len(incidents), "incidents": incidents}))


def get_incident():
    incident_id = require("incidentId")
    result = request("GET", f"/incidents/{incident_id}")
    incident = (result or {}).get("incident", {})
    data = incident_summary(incident)
    data["service"] = (incident.get("service") or {}).get("summary")
    data["created_at"] = incident.get("created_at")
    data["assignments"] = [
        (a.get("assignee") or {}).get("summary")
        for a in incident.get("assignments", [])
    ]
    print(json.dumps(data))


def _set_status(status):
    incident_id = require("incidentId")
    require_from()
    payload = {"incident": {"type": "incident_reference", "status": status}}
    result = request("PUT", f"/incidents/{incident_id}", data=payload, write=True)
    incident = (result or {}).get("incident", {})
    print(json.dumps(incident_summary(incident)))


def acknowledge_incident():
    _set_status("acknowledged")


def resolve_incident():
    _set_status("resolved")


def create_incident():
    service_id = require("serviceId")
    title = require("title")
    require_from()
    incident = {
        "type": "incident",
        "title": title,
        "service": {"id": service_id, "type": "service_reference"},
        "urgency": params.get("urgency") or "high",
    }
    if params.get("body"):
        incident["body"] = {"type": "incident_body", "details": params["body"]}
    result = request("POST", "/incidents", data={"incident": incident}, write=True)
    created = (result or {}).get("incident", {})
    print(json.dumps(incident_summary(created)))


def list_oncalls():
    result = request("GET", "/oncalls", query={
        "schedule_ids[]": as_list(params.get("scheduleIds")),
        "limit": clamp(params.get("limit", 25), 25, 100),
    })
    oncalls = [oncall_summary(o) for o in (result or {}).get("oncalls", [])]
    print(json.dumps({"count": len(oncalls), "oncalls": oncalls}))


HANDLERS = {
    "pagerduty.list_incidents": list_incidents,
    "pagerduty.get_incident": get_incident,
    "pagerduty.acknowledge_incident": acknowledge_incident,
    "pagerduty.resolve_incident": resolve_incident,
    "pagerduty.create_incident": create_incident,
    "pagerduty.list_oncalls": list_oncalls,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_token:
        print(json.dumps({"error": "Missing PagerDuty credential: connect the PagerDuty integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
