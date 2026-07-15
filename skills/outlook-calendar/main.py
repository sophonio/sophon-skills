"""Outlook Calendar integration skill — Microsoft 365 calendar via Microsoft Graph (app-only).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret, userId).

Auth is app-only (OAuth2 client-credentials): we POST to the tenant token endpoint to obtain an
access token, then call Microsoft Graph as https://graph.microsoft.com/v1.0/users/{userId}/...
with a Bearer token. App-only requires an explicit user mailbox and works only for Microsoft 365
work/school accounts (not consumer outlook.com).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
tenant_id = params.get("tenantId") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""
user_id = params.get("userId") or ""

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def get_token():
    """Obtain an app-only access token via the client-credentials grant."""
    url = f"https://login.microsoftonline.com/{urllib.parse.quote(tenant_id, safe='')}/oauth2/v2.0/token"
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }).encode()
    req = urllib.request.Request(
        url,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "sophon-outlook-calendar-skill",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("error_description") or parsed.get("error") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Token request failed ({e.code}): {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft login endpoint: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    return token


def request(method, path, token, data=None, query=None):
    """Make an authenticated request to Microsoft Graph. Returns parsed JSON (or None for 204)."""
    url = f"{GRAPH_BASE}/users/{urllib.parse.quote(user_id, safe='')}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-outlook-calendar-skill",
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
            msg = ((parsed.get("error") or {}).get("message")) or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Graph API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft Graph: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def event_summary(ev):
    return {
        "id": ev.get("id"),
        "subject": ev.get("subject"),
        "start": ev.get("start"),
        "end": ev.get("end"),
        "organizer": ((ev.get("organizer") or {}).get("emailAddress") or {}).get("address"),
        "location": (ev.get("location") or {}).get("displayName"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_events():
    token = get_token()
    limit = clamp(params.get("limit", 25), 25, 100)
    start = params.get("start")
    end = params.get("end")
    if start and end:
        result = request("GET", "/calendarView", token, query={
            "startDateTime": start,
            "endDateTime": end,
            "$top": limit,
            "$orderby": "start/dateTime",
        })
    else:
        result = request("GET", "/events", token, query={
            "$top": limit,
            "$orderby": "start/dateTime",
        })
    events = [event_summary(e) for e in (result or {}).get("value", [])]
    print(json.dumps({"count": len(events), "events": events}))


def create_event():
    token = get_token()
    tz = params.get("timeZone") or "UTC"
    payload = {
        "subject": params.get("subject", ""),
        "start": {"dateTime": params.get("start", ""), "timeZone": tz},
        "end": {"dateTime": params.get("end", ""), "timeZone": tz},
    }
    attendees = params.get("attendees")
    if attendees:
        payload["attendees"] = [
            {"emailAddress": {"address": addr}, "type": "required"} for addr in attendees
        ]
    if params.get("body"):
        payload["body"] = {"contentType": "text", "content": params["body"]}
    if params.get("location"):
        payload["location"] = {"displayName": params["location"]}
    ev = request("POST", "/events", token, data=payload)
    print(json.dumps({"id": (ev or {}).get("id"), "webLink": (ev or {}).get("webLink"),
                      "subject": (ev or {}).get("subject")}))


def update_event():
    token = get_token()
    event_id = params.get("eventId")
    if not event_id:
        raise ValueError("eventId required")
    payload = {}
    if params.get("subject") is not None:
        payload["subject"] = params["subject"]
    tz = params.get("timeZone") or "UTC"
    if params.get("start"):
        payload["start"] = {"dateTime": params["start"], "timeZone": tz}
    if params.get("end"):
        payload["end"] = {"dateTime": params["end"], "timeZone": tz}
    if not payload:
        raise ValueError("nothing to update: provide subject, start, and/or end")
    ev = request("PATCH", f"/events/{urllib.parse.quote(str(event_id), safe='')}", token, data=payload)
    print(json.dumps({"id": (ev or {}).get("id"), "subject": (ev or {}).get("subject"),
                      "updated": True}))


def delete_event():
    token = get_token()
    event_id = params.get("eventId")
    if not event_id:
        raise ValueError("eventId required")
    request("DELETE", f"/events/{urllib.parse.quote(str(event_id), safe='')}", token)
    print(json.dumps({"id": event_id, "deleted": True}))


def list_calendars():
    token = get_token()
    result = request("GET", "/calendars", token)
    calendars = [{
        "id": c.get("id"),
        "name": c.get("name"),
        "owner": ((c.get("owner") or {}).get("address")),
        "canEdit": c.get("canEdit"),
        "isDefaultCalendar": c.get("isDefaultCalendar"),
    } for c in (result or {}).get("value", [])]
    print(json.dumps({"count": len(calendars), "calendars": calendars}))


HANDLERS = {
    "outlook.list_events": list_events,
    "outlook.create_event": create_event,
    "outlook.update_event": update_event,
    "outlook.delete_event": delete_event,
    "outlook.list_calendars": list_calendars,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret and user_id):
        print(json.dumps({"error": "Missing Microsoft Graph credentials: connect the Outlook Calendar integration first (tenantId, clientId, clientSecret, userId)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
