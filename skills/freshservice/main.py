"""Freshservice integration skill — IT service management via the Freshservice REST API v2.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, apiKey).

Auth is HTTP Basic with the agent's API key as the username and the literal "X" as the password
(same mechanism as Freshdesk): "Authorization: Basic base64(apiKey + ':X')". The key is self-serve
from Profile Settings, provided an admin has enabled API access for the agent. All calls hit
{baseUrl}/api/v2 on the customer's {sub}.freshservice.com domain.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
api_key = params.get("apiKey") or ""

API_PREFIX = "/api/v2"

TICKET_STATUS = {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed"}
TICKET_PRIORITY = {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}
CHANGE_STATUS = {1: "Open", 2: "Planning", 3: "Approval", 4: "Pending Release",
                 5: "Pending Review", 6: "Closed"}
CHANGE_RISK = {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}


def request(method, path, data=None, query=None):
    """Make an authenticated request to Freshservice. Returns parsed JSON (or None for 204)."""
    url = f"{base_url}{API_PREFIX}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    auth = base64.b64encode(f"{api_key}:X".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "User-Agent": "sophon-freshservice-skill",
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
            if not isinstance(parsed, dict):
                parsed = {}
            msg = parsed.get("description") or parsed.get("message") or detail
            errors = parsed.get("errors")
            if isinstance(errors, list) and errors:
                parts = []
                for err in errors:
                    if isinstance(err, dict):
                        field = err.get("field")
                        text = err.get("message") or err.get("code") or ""
                        parts.append(f"{field}: {text}" if field else text)
                if parts:
                    msg = f"{msg} ({'; '.join(parts)})"
        except (ValueError, TypeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                msg = f"Rate limit exceeded; retry after {retry_after} seconds. {msg}".strip()
            else:
                msg = f"Rate limit exceeded. {msg}".strip()
        raise RuntimeError(f"Freshservice API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Freshservice: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def require_int(key):
    value = params.get(key)
    if value in (None, ""):
        raise ValueError(f"{key} required")
    return coerce_int(key, value)


def coerce_int(key, value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be an integer")


def ticket_summary(t):
    return {
        "id": t.get("id"),
        "subject": t.get("subject"),
        "status": TICKET_STATUS.get(t.get("status"), t.get("status")),
        "priority": TICKET_PRIORITY.get(t.get("priority"), t.get("priority")),
        "requester_id": t.get("requester_id"),
        "group_id": t.get("group_id"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
    }


def conversation_summary(c):
    return {
        "id": c.get("id"),
        "user_id": c.get("user_id"),
        "incoming": c.get("incoming"),
        "private": c.get("private"),
        "created_at": c.get("created_at"),
        "body_text": c.get("body_text"),
    }


def change_summary(c):
    return {
        "id": c.get("id"),
        "subject": c.get("subject"),
        "status": CHANGE_STATUS.get(c.get("status"), c.get("status")),
        "risk": CHANGE_RISK.get(c.get("risk"), c.get("risk")),
        "planned_start_date": c.get("planned_start_date"),
        "planned_end_date": c.get("planned_end_date"),
    }


def asset_summary(a):
    return {
        "display_id": a.get("display_id"),
        "name": a.get("name"),
        "asset_tag": a.get("asset_tag"),
        "asset_type_id": a.get("asset_type_id"),
        "user_id": a.get("user_id"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_tickets():
    limit = clamp(params.get("limit", 30), 30, 100)
    ticket_filter = params.get("filter")
    if ticket_filter and ticket_filter not in ("new_and_my_open", "watching", "deleted"):
        raise ValueError("filter must be one of: new_and_my_open, watching, deleted")
    result = request("GET", "/tickets", query={
        "per_page": limit,
        "updated_since": params.get("updated_since"),
        "filter": ticket_filter,
    })
    tickets = [ticket_summary(t) for t in (result or {}).get("tickets", [])]
    print(json.dumps({"count": len(tickets), "tickets": tickets}))


def get_ticket():
    ticket_id = require_int("ticketId")
    ticket = (request("GET", f"/tickets/{ticket_id}") or {}).get("ticket") or {}
    convs = (request("GET", f"/tickets/{ticket_id}/conversations") or {}).get("conversations") or []
    print(json.dumps({
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "description_text": ticket.get("description_text"),
        "status": TICKET_STATUS.get(ticket.get("status"), ticket.get("status")),
        "priority": TICKET_PRIORITY.get(ticket.get("priority"), ticket.get("priority")),
        "requester_id": ticket.get("requester_id"),
        "responder_id": ticket.get("responder_id"),
        "group_id": ticket.get("group_id"),
        "created_at": ticket.get("created_at"),
        "updated_at": ticket.get("updated_at"),
        "due_by": ticket.get("due_by"),
        "conversations": [conversation_summary(c) for c in convs],
    }))


def list_changes():
    limit = clamp(params.get("limit", 30), 30, 100)
    result = request("GET", "/changes", query={"per_page": limit})
    changes = [change_summary(c) for c in (result or {}).get("changes", [])]
    print(json.dumps({"count": len(changes), "changes": changes}))


def search_assets():
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    field = params.get("field") or "name"
    if field not in ("name", "asset_tag", "serial_number"):
        raise ValueError("field must be one of: name, asset_tag, serial_number")
    limit = clamp(params.get("limit", 30), 30, 100)
    if "'" in str(query):
        raise ValueError(
            "query cannot contain a single quote (') — Freshservice asset search has no "
            "quote escaping; try a distinctive part of the value without the quote"
        )
    try:
        result = request("GET", "/assets", query={
            "search": f"\"{field}:'{query}'\"",
            "per_page": limit,
        })
    except RuntimeError as e:
        if "error 403" in str(e) or "error 404" in str(e):
            raise RuntimeError(
                "Asset search is unavailable — your Freshservice plan may not include the "
                f"asset management (CMDB) module, or the API key lacks access. ({e})"
            ) from e
        raise
    assets = [asset_summary(a) for a in (result or {}).get("assets", [])]
    print(json.dumps({"count": len(assets), "assets": assets}))


def create_ticket():
    subject = params.get("subject")
    description = params.get("description")
    email = params.get("email")
    if not (subject and description and email):
        raise ValueError("subject, description, and email are required")
    priority = coerce_int("priority", params.get("priority") or 1)
    if priority not in TICKET_PRIORITY:
        raise ValueError("priority must be one of: 1 (Low), 2 (Medium), 3 (High), 4 (Urgent)")
    status = coerce_int("status", params.get("status") or 2)
    if status not in TICKET_STATUS:
        raise ValueError("status must be one of: 2 (Open), 3 (Pending), 4 (Resolved), 5 (Closed)")
    payload = {
        "subject": subject,
        "description": description,
        "email": email,
        "priority": priority,
        "status": status,
        "source": 2,
    }
    ticket = (request("POST", "/tickets", data=payload) or {}).get("ticket") or {}
    print(json.dumps({
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "status": TICKET_STATUS.get(ticket.get("status"), ticket.get("status")),
        "priority": TICKET_PRIORITY.get(ticket.get("priority"), ticket.get("priority")),
        "created": True,
    }))


def update_ticket():
    ticket_id = require_int("ticketId")
    payload = {}
    if params.get("status") is not None:
        status = coerce_int("status", params["status"])
        if status not in TICKET_STATUS:
            raise ValueError("status must be one of: 2 (Open), 3 (Pending), 4 (Resolved), 5 (Closed)")
        payload["status"] = status
    if params.get("priority") is not None:
        priority = coerce_int("priority", params["priority"])
        if priority not in TICKET_PRIORITY:
            raise ValueError("priority must be one of: 1 (Low), 2 (Medium), 3 (High), 4 (Urgent)")
        payload["priority"] = priority
    if params.get("groupId") is not None:
        payload["group_id"] = coerce_int("groupId", params["groupId"])
    if not payload:
        raise ValueError("nothing to update: provide status, priority, and/or groupId")
    ticket = (request("PUT", f"/tickets/{ticket_id}", data=payload) or {}).get("ticket") or {}
    print(json.dumps({
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "status": TICKET_STATUS.get(ticket.get("status"), ticket.get("status")),
        "priority": TICKET_PRIORITY.get(ticket.get("priority"), ticket.get("priority")),
        "group_id": ticket.get("group_id"),
        "updated": True,
    }))


def add_note():
    ticket_id = require_int("ticketId")
    body = params.get("body")
    if not body:
        raise ValueError("body required")
    private = params.get("private")
    if private is None:
        private = True
    conv = (request("POST", f"/tickets/{ticket_id}/notes",
                    data={"body": body, "private": bool(private)}) or {}).get("conversation") or {}
    print(json.dumps({
        "id": conv.get("id"),
        "ticket_id": conv.get("ticket_id") or ticket_id,
        "private": conv.get("private"),
        "created": True,
    }))


HANDLERS = {
    "freshservice.list_tickets": list_tickets,
    "freshservice.get_ticket": get_ticket,
    "freshservice.list_changes": list_changes,
    "freshservice.search_assets": search_assets,
    "freshservice.create_ticket": create_ticket,
    "freshservice.update_ticket": update_ticket,
    "freshservice.add_note": add_note,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_key):
        print(json.dumps({"error": "Missing Freshservice credentials: connect the Freshservice integration first (baseUrl, apiKey)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
