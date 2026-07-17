"""ServiceNow integration skill — Table API access to a ServiceNow instance.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, username, password, clientId,
clientSecret).

Auth is dual-path: if clientId + clientSecret are set we use OAuth2 client-credentials
(POST {baseUrl}/oauth_token.do, then "Authorization: Bearer {access_token}"); otherwise we fall
back to HTTP basic auth with username + password. All data access goes through the ServiceNow
Table API (https://{instance}.service-now.com/api/now/table/{table}).
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
username = params.get("username") or ""
password = params.get("password") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""


def get_token():
    """Obtain an access token via the OAuth2 client-credentials grant."""
    url = f"{base_url}/oauth_token.do"
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    req = urllib.request.Request(
        url,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "sophon-servicenow-skill",
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
        raise RuntimeError(f"Could not reach ServiceNow: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response — check that the client-credentials "
                           "grant is enabled on the instance and the client id/secret are correct")
    return token


def auth_header():
    """Build the Authorization header — OAuth if a client id/secret is set, else basic auth."""
    if client_id and client_secret:
        return f"Bearer {get_token()}"
    raw = f"{username}:{password}".encode()
    return f"Basic {base64.b64encode(raw).decode()}"


def request(method, path, data=None, query=None):
    """Make an authenticated request to the ServiceNow REST API. Returns parsed JSON (or None)."""
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": auth_header(),
        "Accept": "application/json",
        "User-Agent": "sophon-servicenow-skill",
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
            err = parsed.get("error") or {}
            msg = err.get("message") or detail
            if err.get("detail"):
                msg = f"{msg} — {err['detail']}"
        except (ValueError, TypeError, AttributeError):
            msg = detail
        if e.code == 429:
            msg = msg or "rate limit exceeded; the instance is throttling API requests, retry later"
        raise RuntimeError(f"ServiceNow API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach ServiceNow: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def record_summary(rec):
    """Trim a record to its non-empty fields (the field set is already narrowed server-side)."""
    return {k: v for k, v in rec.items() if v not in ("", None)}


DEFAULT_FIELDS = "sys_id,number,name,short_description,state,priority,assigned_to,sys_updated_on"


# --- Tool handlers ---------------------------------------------------------

def search_records():
    table = params.get("table")
    if not table:
        raise ValueError("table required")
    limit = clamp(params.get("limit", 20), 20, 100)
    result = request("GET", f"/api/now/table/{urllib.parse.quote(str(table), safe='')}", query={
        "sysparm_query": params.get("sysparm_query"),
        "sysparm_fields": params.get("fields") or DEFAULT_FIELDS,
        "sysparm_limit": limit,
        "sysparm_offset": params.get("offset"),
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    })
    records = [record_summary(r) for r in (result or {}).get("result", [])]
    print(json.dumps({"count": len(records), "records": records}))


def get_record():
    table = params.get("table")
    sys_id = params.get("sys_id")
    if not table or not sys_id:
        raise ValueError("table and sys_id required")
    path = (f"/api/now/table/{urllib.parse.quote(str(table), safe='')}"
            f"/{urllib.parse.quote(str(sys_id), safe='')}")
    result = request("GET", path, query={
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    })
    print(json.dumps(record_summary((result or {}).get("result") or {})))


def search_knowledge():
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    # '^' is the encoded-query operator separator; strip it so user text cannot alter the query.
    query = str(query).replace("^", " ").strip()
    if not query:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 10), 10, 50)
    encoded_query = (f"workflow_state=published"
                     f"^short_descriptionLIKE{query}^ORtextLIKE{query}")
    result = request("GET", "/api/now/table/kb_knowledge", query={
        "sysparm_query": encoded_query,
        "sysparm_fields": "sys_id,number,short_description,kb_category,kb_knowledge_base,"
                          "workflow_state,sys_view_count,sys_updated_on",
        "sysparm_limit": limit,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    })
    articles = [record_summary(a) for a in (result or {}).get("result", [])]
    print(json.dumps({"count": len(articles), "articles": articles}))


def get_user():
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    # '^' is the encoded-query operator separator; strip it so user text cannot alter the query.
    query = str(query).replace("^", " ").strip()
    if not query:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 10), 10, 50)
    if (params.get("type") or "user") == "group":
        table = "sys_user_group"
        encoded_query = f"name={query}^ORnameLIKE{query}^ORemail={query}"
        fields = "sys_id,name,email,description,manager,active"
        key = "groups"
    else:
        table = "sys_user"
        encoded_query = f"user_name={query}^ORemail={query}^ORnameLIKE{query}"
        fields = "sys_id,user_name,name,email,title,department,active"
        key = "users"
    result = request("GET", f"/api/now/table/{table}", query={
        "sysparm_query": encoded_query,
        "sysparm_fields": fields,
        "sysparm_limit": limit,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    })
    matches = [record_summary(r) for r in (result or {}).get("result", [])]
    print(json.dumps({"count": len(matches), key: matches}))


def create_incident():
    short_description = params.get("short_description")
    if not short_description:
        raise ValueError("short_description required")
    payload = {"short_description": short_description}
    for field in ("description", "caller_id", "urgency", "impact", "assignment_group"):
        if params.get(field):
            payload[field] = params[field]
    result = request("POST", "/api/now/table/incident", data=payload, query={
        "sysparm_fields": "sys_id,number,short_description,state,priority,urgency,impact,"
                          "assignment_group,opened_at",
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    })
    print(json.dumps(record_summary((result or {}).get("result") or {})))


def update_record():
    table = params.get("table")
    sys_id = params.get("sys_id")
    fields = params.get("fields")
    if not table or not sys_id:
        raise ValueError("table and sys_id required")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields required: an object of field name -> new value")
    path = (f"/api/now/table/{urllib.parse.quote(str(table), safe='')}"
            f"/{urllib.parse.quote(str(sys_id), safe='')}")
    result = request("PATCH", path, data=fields, query={
        "sysparm_fields": "sys_id,number,short_description,state,sys_updated_on",
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    })
    rec = record_summary((result or {}).get("result") or {})
    rec["updated"] = True
    print(json.dumps(rec))


def add_work_note():
    sys_id = params.get("sys_id")
    work_notes = params.get("work_notes")
    if not sys_id:
        raise ValueError("sys_id required")
    if not work_notes:
        raise ValueError("work_notes required")
    path = f"/api/now/table/incident/{urllib.parse.quote(str(sys_id), safe='')}"
    result = request("PATCH", path, data={"work_notes": work_notes}, query={
        "sysparm_fields": "sys_id,number,short_description,state,sys_updated_on",
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    })
    rec = record_summary((result or {}).get("result") or {})
    rec["work_note_added"] = True
    print(json.dumps(rec))


HANDLERS = {
    "snow.search_records": search_records,
    "snow.get_record": get_record,
    "snow.search_knowledge": search_knowledge,
    "snow.get_user": get_user,
    "snow.create_incident": create_incident,
    "snow.update_record": update_record,
    "snow.add_work_note": add_work_note,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and ((username and password) or (client_id and client_secret))):
        print(json.dumps({"error": "Missing ServiceNow credentials: connect the ServiceNow integration first (baseUrl plus either username + password or clientId + clientSecret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
