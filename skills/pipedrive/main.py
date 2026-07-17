"""Pipedrive CRM integration skill — deals, contacts, notes, and activities.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (companyDomain, apiToken).

Auth is a static personal API token sent as the `x-api-token` header, which works on both v1 and
v2 endpoints (the legacy `api_token` query parameter is deliberately NOT used). The base URL is
https://{companyDomain}.pipedrive.com. Per Pipedrive's current migration state, deals, persons,
activities, and itemSearch are called on /api/v2 while notes (and users) remain on /api/v1.
Pipedrive rate limiting is a daily token budget: once spent, every request returns 429 until the
budget resets at midnight.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
company_domain = params.get("companyDomain") or ""
api_token = params.get("apiToken") or ""

DEAL_STATUSES = ("open", "won", "lost")
ACTIVITY_TYPES = ("call", "meeting", "task", "deadline", "email", "lunch")


def base_url():
    if not re.fullmatch(r"[a-z0-9-]+", company_domain):
        raise ValueError(
            "companyDomain must be just your Pipedrive subdomain (lowercase letters, digits, "
            "hyphens) — e.g. 'acme' for https://acme.pipedrive.com"
        )
    return f"https://{company_domain}.pipedrive.com"


def seg(value, label):
    """Quote a params-derived path segment; reject traversal segments outright."""
    s = str(value)
    if s in (".", ".."):
        raise ValueError(f"invalid {label}: {s!r}")
    return urllib.parse.quote(s, safe="")


def request(method, path, data=None, query=None):
    """Make an authenticated request to Pipedrive. Returns parsed JSON (or None for 204/empty)."""
    url = f"{base_url()}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "x-api-token": api_token,
        "Accept": "application/json",
        "User-Agent": "sophon-pipedrive-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace") if e.fp else ""
        try:
            parsed = json.loads(detail)
            if isinstance(parsed, dict):
                msg = parsed.get("error") or parsed.get("message") or detail
                if parsed.get("error_info"):
                    msg = f"{msg} ({parsed['error_info']})"
            else:
                msg = detail
        except (ValueError, TypeError):
            msg = detail
        if e.code == 429:
            hint = ("Pipedrive rate limiting is a daily API token budget — once it is spent, "
                    "requests return 429 until the budget resets at midnight.")
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                unit = "s" if retry_after.isdigit() else ""
                hint += f" Retry-After: {retry_after}{unit}."
            raise RuntimeError(
                f"Pipedrive API error 429: {msg or 'rate limit exceeded'}. {hint}") from e
        raise RuntimeError(f"Pipedrive API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Pipedrive: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def deal_summary(d):
    return {
        "id": d.get("id"),
        "title": d.get("title"),
        "value": d.get("value"),
        "currency": d.get("currency"),
        "status": d.get("status"),
        "stage_id": d.get("stage_id"),
        "pipeline_id": d.get("pipeline_id"),
        "owner_id": d.get("owner_id"),
        "person_id": d.get("person_id"),
        "org_id": d.get("org_id"),
        "expected_close_date": d.get("expected_close_date"),
    }


def contact_points(entries):
    return [{"value": e.get("value"), "label": e.get("label"), "primary": e.get("primary")}
            for e in (entries or []) if isinstance(e, dict)]


def person_summary(p):
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "emails": contact_points(p.get("emails")),
        "phones": contact_points(p.get("phones")),
        "org_id": p.get("org_id"),
        "owner_id": p.get("owner_id"),
    }


# --- Tool handlers ---------------------------------------------------------

def search():
    term = (params.get("term") or "").strip()
    if len(term) < 2:
        raise ValueError("term required (at least 2 characters)")
    item_types = params.get("item_types") or "deal,person,organization,lead"
    limit = clamp(params.get("limit", 20), 20, 50)
    result = request("GET", "/api/v2/itemSearch", query={
        "term": term,
        "item_types": item_types,
        "limit": limit,
    })
    items = ((result or {}).get("data") or {}).get("items") or []
    shaped = []
    for entry in items:
        item = entry.get("item") or {}
        shaped.append({
            "type": item.get("type"),
            "id": item.get("id"),
            "title": item.get("title") or item.get("name"),
            "result_score": entry.get("result_score"),
        })
    print(json.dumps({"count": len(shaped), "items": shaped}))


def list_deals():
    status = params.get("status")
    if status not in (None, "") and status not in DEAL_STATUSES:
        raise ValueError("status must be one of: open, won, lost")
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/api/v2/deals", query={
        "pipeline_id": params.get("pipeline_id"),
        "stage_id": params.get("stage_id"),
        "status": status,
        "owner_id": params.get("owner_id"),
        "limit": limit,
        "cursor": params.get("cursor"),
    })
    deals = [deal_summary(d) for d in ((result or {}).get("data") or [])]
    next_cursor = ((result or {}).get("additional_data") or {}).get("next_cursor")
    print(json.dumps({"count": len(deals), "deals": deals, "next_cursor": next_cursor}))


def get_deal():
    deal_id = params.get("dealId")
    if deal_id in (None, ""):
        raise ValueError("dealId required")
    result = request("GET", f"/api/v2/deals/{seg(deal_id, 'dealId')}")
    print(json.dumps(deal_summary((result or {}).get("data") or {})))


def get_person():
    person_id = params.get("personId")
    if person_id in (None, ""):
        raise ValueError("personId required")
    result = request("GET", f"/api/v2/persons/{seg(person_id, 'personId')}")
    print(json.dumps(person_summary((result or {}).get("data") or {})))


def update_deal():
    deal_id = params.get("dealId")
    if deal_id in (None, ""):
        raise ValueError("dealId required")
    payload = {}
    if params.get("stage_id") is not None:
        payload["stage_id"] = params["stage_id"]
    if params.get("status") is not None:
        if params["status"] not in DEAL_STATUSES:
            raise ValueError("status must be one of: open, won, lost")
        payload["status"] = params["status"]
    if params.get("value") is not None:
        payload["value"] = params["value"]
    if params.get("owner_id") is not None:
        payload["owner_id"] = params["owner_id"]
    if not payload:
        raise ValueError("nothing to update: provide stage_id, status, value, and/or owner_id")
    result = request("PATCH", f"/api/v2/deals/{seg(deal_id, 'dealId')}", data=payload)
    out = deal_summary((result or {}).get("data") or {})
    out["updated"] = True
    print(json.dumps(out))


def add_note():
    content = params.get("content")
    if not content:
        raise ValueError("content required")
    payload = {"content": content}
    for key in ("deal_id", "person_id", "org_id"):
        if params.get(key) is not None:
            payload[key] = params[key]
    if len(payload) == 1:
        raise ValueError("provide at least one of deal_id, person_id, org_id to attach the note to")
    result = request("POST", "/api/v1/notes", data=payload)
    d = (result or {}).get("data") or {}
    print(json.dumps({
        "id": d.get("id"),
        "deal_id": d.get("deal_id"),
        "person_id": d.get("person_id"),
        "org_id": d.get("org_id"),
        "created": True,
    }))


def create_activity():
    subject = params.get("subject")
    if not subject:
        raise ValueError("subject required")
    activity_type = params.get("type")
    if activity_type not in ACTIVITY_TYPES:
        raise ValueError("type must be one of: call, meeting, task, deadline, email, lunch")
    due_date = params.get("due_date")
    if not due_date:
        raise ValueError("due_date required (YYYY-MM-DD)")
    payload = {"subject": subject, "type": activity_type, "due_date": due_date}
    for key in ("due_time", "deal_id", "person_id"):
        if params.get(key) not in (None, ""):
            payload[key] = params[key]
    result = request("POST", "/api/v2/activities", data=payload)
    d = (result or {}).get("data") or {}
    print(json.dumps({
        "id": d.get("id"),
        "subject": d.get("subject"),
        "type": d.get("type"),
        "due_date": d.get("due_date"),
        "due_time": d.get("due_time"),
        "deal_id": d.get("deal_id"),
        "created": True,
    }))


HANDLERS = {
    "pipedrive.search": search,
    "pipedrive.list_deals": list_deals,
    "pipedrive.get_deal": get_deal,
    "pipedrive.get_person": get_person,
    "pipedrive.update_deal": update_deal,
    "pipedrive.add_note": add_note,
    "pipedrive.create_activity": create_activity,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (company_domain and api_token):
        print(json.dumps({"error": "Missing Pipedrive credentials: connect the Pipedrive integration first (companyDomain, apiToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
