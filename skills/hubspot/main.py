"""HubSpot CRM integration skill — contacts, companies, deals, tickets via the CRM v3 API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (accessToken).

Auth is a static private-app access token sent as "Authorization: Bearer {accessToken}" against
https://api.hubapi.com. Private apps are HubSpot's "legacy" track but remain fully supported
with no announced sunset.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
access_token = params.get("accessToken") or ""

API_BASE = "https://api.hubapi.com"

OBJECT_TYPES = ("contacts", "companies", "deals", "tickets")
PIPELINE_OBJECT_TYPES = ("deals", "tickets")

# HUBSPOT_DEFINED note -> object association type ids (per HubSpot association docs).
NOTE_ASSOCIATION_TYPE_IDS = {
    "contacts": 202,
    "companies": 190,
    "deals": 214,
    "tickets": 228,
}


def seg(value, name):
    """Validate and URL-quote a params-derived path segment."""
    s = str(value if value is not None else "").strip()
    if not s:
        raise ValueError(f"{name} required")
    if s in (".", ".."):
        raise ValueError(f"Invalid {name}: {s!r}")
    return urllib.parse.quote(s, safe="")


def object_type(allowed=OBJECT_TYPES):
    ot = str(params.get("objectType") or "").strip().lower()
    if ot not in allowed:
        raise ValueError(f"objectType must be one of: {', '.join(allowed)}")
    return ot


def request(method, path, data=None, query=None):
    """Make an authenticated request to the HubSpot API. Returns parsed JSON (or None for 204)."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "sophon-hubspot-skill",
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
        except (ValueError, TypeError):
            parsed = None
        msg = (parsed.get("message") or detail) if isinstance(parsed, dict) else detail
        if e.code == 403:
            msg = (f"{msg} (a 403 from HubSpot usually means the private app is missing a "
                   "required scope — review the app's scopes under Settings > Development)")
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                msg = f"{msg} (rate limited; retry after {retry_after}s)"
        raise RuntimeError(f"HubSpot API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach HubSpot: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def csv_param(value):
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return str(value)


def object_summary(obj):
    return {
        "id": obj.get("id"),
        "properties": obj.get("properties") or {},
        "createdAt": obj.get("createdAt"),
        "updatedAt": obj.get("updatedAt"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_objects():
    ot = object_type()
    limit = clamp(params.get("limit", 20), 20, 100)
    payload = {"limit": limit}
    q = params.get("query")
    if q not in (None, ""):
        payload["query"] = str(q)
    prop_name = params.get("propertyName")
    if prop_name:
        flt = {
            "propertyName": str(prop_name),
            "operator": str(params.get("operator") or "EQ").upper(),
        }
        if params.get("value") is not None:
            flt["value"] = str(params["value"])
        payload["filterGroups"] = [{"filters": [flt]}]
    elif params.get("operator") is not None or params.get("value") is not None:
        raise ValueError("propertyName required when operator/value are given")
    props = params.get("properties")
    if props:
        payload["properties"] = [str(p) for p in props] if isinstance(props, (list, tuple)) else [str(props)]
    after = params.get("after")
    if after not in (None, ""):
        payload["after"] = str(after)
    result = request("POST", f"/crm/v3/objects/{ot}/search", data=payload) or {}
    items = [object_summary(o) for o in result.get("results", [])]
    out = {"count": len(items), "total": result.get("total"), "results": items}
    next_after = ((result.get("paging") or {}).get("next") or {}).get("after")
    if next_after:
        out["nextAfter"] = next_after
    print(json.dumps(out))


def get_object():
    ot = object_type()
    oid = seg(params.get("objectId"), "objectId")
    query = {}
    if params.get("properties"):
        query["properties"] = csv_param(params["properties"])
    if params.get("associations"):
        query["associations"] = csv_param(params["associations"])
    result = request("GET", f"/crm/v3/objects/{ot}/{oid}", query=query) or {}
    out = {
        "id": result.get("id"),
        "objectType": ot,
        "properties": result.get("properties") or {},
        "createdAt": result.get("createdAt"),
        "updatedAt": result.get("updatedAt"),
        "archived": result.get("archived"),
    }
    associations = {}
    for name, block in (result.get("associations") or {}).items():
        associations[name] = [r.get("id") for r in ((block or {}).get("results") or [])]
    if associations:
        out["associations"] = associations
    print(json.dumps(out))


def list_pipelines():
    ot = object_type(PIPELINE_OBJECT_TYPES)
    result = request("GET", f"/crm/v3/pipelines/{ot}") or {}
    pipelines = [{
        "id": p.get("id"),
        "label": p.get("label"),
        "stages": [{
            "id": s.get("id"),
            "label": s.get("label"),
            "displayOrder": s.get("displayOrder"),
        } for s in (p.get("stages") or [])],
    } for p in result.get("results", [])]
    print(json.dumps({"count": len(pipelines), "pipelines": pipelines}))


def list_owners():
    limit = clamp(params.get("limit", 100), 100, 500)
    result = request("GET", "/crm/v3/owners", query={"limit": limit}) or {}
    owners = [{
        "id": o.get("id"),
        "email": o.get("email"),
        "firstName": o.get("firstName"),
        "lastName": o.get("lastName"),
    } for o in result.get("results", [])]
    print(json.dumps({"count": len(owners), "owners": owners}))


def create_object():
    ot = object_type()
    props = params.get("properties")
    if not isinstance(props, dict) or not props:
        raise ValueError("properties (a non-empty object of property name -> value) required")
    result = request("POST", f"/crm/v3/objects/{ot}", data={"properties": props}) or {}
    print(json.dumps({
        "id": result.get("id"),
        "objectType": ot,
        "createdAt": result.get("createdAt"),
        "properties": result.get("properties") or {},
    }))


def update_object():
    ot = object_type()
    oid = seg(params.get("objectId"), "objectId")
    props = params.get("properties")
    if not isinstance(props, dict) or not props:
        raise ValueError("properties (a non-empty object of property name -> value) required")
    result = request("PATCH", f"/crm/v3/objects/{ot}/{oid}", data={"properties": props}) or {}
    print(json.dumps({
        "id": result.get("id"),
        "objectType": ot,
        "updated": True,
        "updatedAt": result.get("updatedAt"),
    }))


def add_note():
    ot = object_type()
    oid = params.get("objectId")
    if oid is None or str(oid).strip() == "":
        raise ValueError("objectId required")
    body_text = params.get("body")
    if not body_text:
        raise ValueError("body required")
    timestamp = params.get("timestamp")
    if not timestamp:
        raise ValueError("timestamp required (ISO 8601, e.g. 2026-07-18T12:00:00Z)")
    payload = {
        "properties": {
            "hs_note_body": str(body_text),
            "hs_timestamp": str(timestamp),
        },
        "associations": [{
            "to": {"id": str(oid)},
            "types": [{
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": NOTE_ASSOCIATION_TYPE_IDS[ot],
            }],
        }],
    }
    result = request("POST", "/crm/v3/objects/notes", data=payload) or {}
    print(json.dumps({
        "id": result.get("id"),
        "objectType": ot,
        "objectId": str(oid),
        "createdAt": result.get("createdAt"),
    }))


HANDLERS = {
    "hubspot.search_objects": search_objects,
    "hubspot.get_object": get_object,
    "hubspot.list_pipelines": list_pipelines,
    "hubspot.list_owners": list_owners,
    "hubspot.create_object": create_object,
    "hubspot.update_object": update_object,
    "hubspot.add_note": add_note,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not access_token:
        print(json.dumps({"error": "Missing HubSpot credentials: connect the HubSpot integration first (accessToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
