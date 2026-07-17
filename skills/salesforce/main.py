"""Salesforce integration skill — SOQL/SOSL, records, and Task activities via the REST API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (myDomainUrl, clientId, clientSecret).

Auth is OAuth2 client-credentials: we POST to {myDomainUrl}/services/oauth2/token (the org's
My Domain URL is required — login.salesforce.com does not support this flow). The response
provides both an access_token and the instance_url, which we use as the REST API base
({instance_url}/services/data/v62.0/...). No refresh token — a token is minted per invocation.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
my_domain_url = (params.get("myDomainUrl") or "").rstrip("/")
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""

API_VERSION = "v62.0"
USER_AGENT = "sophon-salesforce-skill"
MAX_QUERY_PAGES = 5


def api_path(suffix):
    return f"/services/data/{API_VERSION}{suffix}"


def parse_error_detail(detail):
    """Parse a Salesforce error body into (message, errorCode).

    REST API errors are JSON ARRAYS of {message, errorCode}; the token endpoint returns an
    object with error/error_description.
    """
    try:
        parsed = json.loads(detail)
    except (ValueError, TypeError):
        return detail, None
    if isinstance(parsed, list):
        items = [item for item in parsed if isinstance(item, dict)]
        msg = "; ".join(m for m in (item.get("message") or "" for item in items) if m) or detail
        code = next((item.get("errorCode") for item in items if item.get("errorCode")), None)
        return msg, code
    if isinstance(parsed, dict):
        msg = parsed.get("error_description") or parsed.get("message") or parsed.get("error") or detail
        return msg, parsed.get("errorCode")
    return detail, None


def get_token():
    """Obtain an access token (and instance_url) via the client-credentials grant."""
    url = f"{my_domain_url}/services/oauth2/token"
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
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        msg, _ = parse_error_detail(detail)
        raise RuntimeError(
            f"Token request failed ({e.code}): {msg}. Make sure myDomainUrl is your org's "
            "My Domain URL (not login.salesforce.com) and the External Client App has "
            "'Enable Client Credentials Flow' turned on with a run-as user assigned."
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Salesforce: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    instance_url = (data.get("instance_url") or my_domain_url).rstrip("/")
    return token, instance_url


def request(method, path, token, instance_url, data=None, query=None):
    """Make an authenticated request to the Salesforce REST API. Returns parsed JSON (or None for 204)."""
    url = f"{instance_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
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
        msg, code = parse_error_detail(detail)
        if code == "REQUEST_LIMIT_EXCEEDED":
            raise RuntimeError(
                "Salesforce daily API request limit reached — the org has used up its 24-hour "
                "API request allocation. Try again after the rolling window resets."
            ) from e
        raise RuntimeError(f"Salesforce API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Salesforce: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def quote_seg(value):
    return urllib.parse.quote(str(value), safe="")


def record_summary(record):
    """Trim a Salesforce record: drop the attributes envelope but keep the object type."""
    if not isinstance(record, dict):
        return record
    out = {}
    obj_type = (record.get("attributes") or {}).get("type")
    if obj_type:
        out["type"] = obj_type
    for key, value in record.items():
        if key == "attributes":
            continue
        if isinstance(value, dict) and "records" in value:
            # Child relationship subquery result.
            out[key] = {
                "totalSize": value.get("totalSize"),
                "records": [record_summary(r) for r in value.get("records") or []],
            }
        elif isinstance(value, dict) and "attributes" in value:
            # Parent relationship lookup.
            out[key] = record_summary(value)
        else:
            out[key] = value
    return out


# --- Tool handlers ---------------------------------------------------------

def soql_query():
    token, instance_url = get_token()
    soql = params.get("soql")
    if not soql:
        raise ValueError("soql required")
    limit = clamp(params.get("limit", 100), 100, 500)
    result = request("GET", api_path("/query"), token, instance_url, query={"q": soql}) or {}
    records = list(result.get("records") or [])
    total_size = result.get("totalSize", len(records))
    done = result.get("done", True)
    pages = 1
    while not done and len(records) < limit and pages < MAX_QUERY_PAGES:
        next_url = result.get("nextRecordsUrl")
        if not next_url:
            break
        result = request("GET", next_url, token, instance_url) or {}
        records.extend(result.get("records") or [])
        done = result.get("done", True)
        pages += 1
    records = records[:limit]
    print(json.dumps({
        "totalSize": total_size,
        "done": done,
        "count": len(records),
        "records": [record_summary(r) for r in records],
    }))


def search():
    token, instance_url = get_token()
    sosl = params.get("sosl")
    if not sosl:
        raise ValueError("sosl required")
    result = request("GET", api_path("/search/"), token, instance_url, query={"q": sosl}) or {}
    records = [record_summary(r) for r in result.get("searchRecords") or []]
    print(json.dumps({"count": len(records), "records": records}))


def get_record():
    token, instance_url = get_token()
    object_type = params.get("objectType")
    record_id = params.get("recordId")
    if not object_type or not record_id:
        raise ValueError("objectType and recordId required")
    fields = params.get("fields")
    query = {"fields": ",".join(str(f) for f in fields)} if fields else None
    record = request(
        "GET",
        api_path(f"/sobjects/{quote_seg(object_type)}/{quote_seg(record_id)}"),
        token, instance_url, query=query,
    )
    print(json.dumps(record_summary(record or {})))


def describe_object():
    token, instance_url = get_token()
    object_type = params.get("objectType")
    if not object_type:
        raise ValueError("objectType required")
    desc = request(
        "GET",
        api_path(f"/sobjects/{quote_seg(object_type)}/describe"),
        token, instance_url,
    ) or {}
    fields = []
    for f in desc.get("fields") or []:
        entry = {"name": f.get("name"), "label": f.get("label"), "type": f.get("type")}
        picklist = f.get("picklistValues") or []
        if picklist:
            entry["picklistValues"] = [
                {"value": p.get("value"), "label": p.get("label")}
                for p in picklist if p.get("active", True)
            ]
        fields.append(entry)
    print(json.dumps({
        "name": desc.get("name"),
        "label": desc.get("label"),
        "custom": desc.get("custom"),
        "count": len(fields),
        "fields": fields,
    }))


def create_record():
    token, instance_url = get_token()
    object_type = params.get("objectType")
    fields = params.get("fields")
    if not object_type:
        raise ValueError("objectType required")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields object required (field name -> value)")
    result = request(
        "POST",
        api_path(f"/sobjects/{quote_seg(object_type)}"),
        token, instance_url, data=fields,
    )
    print(json.dumps({"id": (result or {}).get("id"), "objectType": object_type, "created": True}))


def update_record():
    token, instance_url = get_token()
    object_type = params.get("objectType")
    record_id = params.get("recordId")
    fields = params.get("fields")
    if not object_type or not record_id:
        raise ValueError("objectType and recordId required")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields object required (field name -> value)")
    request(
        "PATCH",
        api_path(f"/sobjects/{quote_seg(object_type)}/{quote_seg(record_id)}"),
        token, instance_url, data=fields,
    )
    print(json.dumps({"id": record_id, "objectType": object_type, "updated": True}))


def add_task():
    token, instance_url = get_token()
    subject = params.get("subject")
    if not subject:
        raise ValueError("subject required")
    payload = {"Subject": subject}
    if params.get("whoId"):
        payload["WhoId"] = params["whoId"]
    if params.get("whatId"):
        payload["WhatId"] = params["whatId"]
    if params.get("activityDate"):
        payload["ActivityDate"] = params["activityDate"]
    if params.get("description"):
        payload["Description"] = params["description"]
    result = request("POST", api_path("/sobjects/Task"), token, instance_url, data=payload)
    print(json.dumps({"id": (result or {}).get("id"), "subject": subject, "created": True}))


HANDLERS = {
    "sf.soql_query": soql_query,
    "sf.search": search,
    "sf.get_record": get_record,
    "sf.describe_object": describe_object,
    "sf.create_record": create_record,
    "sf.update_record": update_record,
    "sf.add_task": add_task,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (my_domain_url and client_id and client_secret):
        print(json.dumps({"error": "Missing Salesforce credentials: connect the Salesforce integration first (myDomainUrl, clientId, clientSecret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
