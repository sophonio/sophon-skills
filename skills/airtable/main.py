"""Airtable integration skill — talks to the Airtable REST API v0 with a personal access token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (apiToken, baseId).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_token = params.get("apiToken", "")
base_id = params.get("baseId", "")

API_BASE = "https://api.airtable.com/v0"

HEADERS = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
    "User-Agent": "sophon-airtable-skill",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Airtable API. Returns parsed JSON (or None for 204)."""
    url = f"{API_BASE}{path}"
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
        raise RuntimeError(f"Airtable API error {e.code}: {detail}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def table_path(table, record_id=None):
    """Build a base-scoped path with the table name URL-encoded (and optional record id)."""
    if not table:
        raise ValueError("table is required")
    encoded = urllib.parse.quote(str(table), safe="")
    path = f"/{base_id}/{encoded}"
    if record_id:
        path += f"/{urllib.parse.quote(str(record_id), safe='')}"
    return path


def record_summary(record):
    return {
        "id": record.get("id"),
        "fields": record.get("fields", {}),
        "createdTime": record.get("createdTime"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_records():
    table = params.get("table")
    query = {
        "filterByFormula": params.get("filterByFormula"),
        "view": params.get("view"),
        "offset": params.get("offset"),
    }
    if params.get("maxRecords") is not None:
        query["maxRecords"] = clamp(params.get("maxRecords"), None, 100000)
    if params.get("pageSize") is not None:
        query["pageSize"] = clamp(params.get("pageSize"), 100, 100)
    result = request("GET", table_path(table), query=query) or {}
    records = [record_summary(r) for r in result.get("records", [])]
    out = {"records": records}
    if result.get("offset"):
        out["offset"] = result["offset"]
    print(json.dumps(out))


def get_record():
    table = params.get("table")
    record_id = params.get("recordId", "")
    record = request("GET", table_path(table, record_id))
    print(json.dumps(record_summary(record)))


def create_record():
    table = params.get("table")
    fields = params.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("create_record requires a 'fields' object")
    record = request("POST", table_path(table), data={"fields": fields})
    print(json.dumps(record_summary(record)))


def update_record():
    table = params.get("table")
    record_id = params.get("recordId", "")
    fields = params.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("update_record requires a 'fields' object")
    record = request("PATCH", table_path(table, record_id), data={"fields": fields})
    print(json.dumps(record_summary(record)))


def delete_record():
    table = params.get("table")
    record_id = params.get("recordId", "")
    if not record_id:
        raise ValueError("delete_record requires a 'recordId'")
    result = request("DELETE", table_path(table, record_id)) or {}
    print(json.dumps({"id": result.get("id", record_id), "deleted": result.get("deleted", True)}))


HANDLERS = {
    "airtable.list_records": list_records,
    "airtable.get_record": get_record,
    "airtable.create_record": create_record,
    "airtable.update_record": update_record,
    "airtable.delete_record": delete_record,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_token or not base_id:
        print(json.dumps({"error": "Missing Airtable credential: connect the Airtable integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
