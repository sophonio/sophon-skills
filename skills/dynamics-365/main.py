"""Dynamics 365 integration skill — Microsoft Dataverse Web API (app-only).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret,
environmentUrl).

Auth is app-only (OAuth2 client-credentials): we POST to the tenant token endpoint with scope
"{environmentUrl}/.default" (the Dataverse environment, NOT Microsoft Graph) to obtain an access
token (~60 min lifetime, minted per invocation), then call the Dataverse Web API at
{environmentUrl}/api/data/v9.2 with a Bearer token. The app registration needs NO API
permissions; access is granted by creating an Application User for the client ID in the Power
Platform admin center and assigning it a Dataverse security role.

Every request carries OData-Version/OData-MaxVersion 4.0; reads add a Prefer header so responses
include OData.Community.Display.V1.FormattedValue annotations (returned alongside raw values as
"<field>@formatted"). Dataverse service-protection limits surface as HTTP 429 with Retry-After,
which is included in the error message.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
tenant_id = params.get("tenantId") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""
environment_url = (params.get("environmentUrl") or "").strip().rstrip("/")

API_BASE = f"{environment_url}/api/data/v9.2"
ENV_HOST = urllib.parse.urlparse(environment_url).netloc
FORMATTED_PREFER = 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
FORMATTED_SUFFIX = "@OData.Community.Display.V1.FormattedValue"
ENTITY_RE = re.compile(r"^[A-Za-z0-9_]+$")
GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
MAX_PAGES = 5


def get_token():
    """Obtain an app-only access token via the client-credentials grant (Dataverse scope)."""
    url = f"https://login.microsoftonline.com/{urllib.parse.quote(tenant_id, safe='')}/oauth2/v2.0/token"
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": f"{environment_url}/.default",
    }).encode()
    req = urllib.request.Request(
        url,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "sophon-dynamics-365-skill",
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
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            msg = parsed.get("error_description") or parsed.get("error") or detail
        else:
            msg = detail
        raise RuntimeError(f"Token request failed ({e.code}): {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft login endpoint: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    return token


def request(method, path, token, data=None, query=None, formatted=False, extra_headers=None):
    """Make an authenticated request to the Dataverse Web API.

    `path` is either a path under the API base or a full https URL (already host-validated, e.g.
    an @odata.nextLink). Returns (parsed JSON or None for 204/empty, response headers).
    """
    if path.startswith("https://"):
        url = path
    else:
        url = f"{API_BASE}{path}"
        if query:
            clean = {k: v for k, v in query.items() if v not in (None, "")}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-Version": "4.0",
        "OData-MaxVersion": "4.0",
        "User-Agent": "sophon-dynamics-365-skill",
    }
    if formatted:
        headers["Prefer"] = FORMATTED_PREFER
    if extra_headers:
        headers.update(extra_headers)
    body = json.dumps(data).encode() if data is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return (json.loads(raw) if raw else None), resp.headers
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            err = parsed.get("error")
            if isinstance(err, dict):
                msg = err.get("message") or detail
            elif isinstance(err, str):
                msg = parsed.get("error_description") or err
            else:
                msg = detail
        else:
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            suffix = f" (Retry-After: {retry_after}s)" if retry_after else ""
            raise RuntimeError(
                f"Dynamics 365 API error 429: service protection limit reached — {msg}{suffix}"
            ) from e
        raise RuntimeError(f"Dynamics 365 API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Dynamics 365: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return default if value < 1 else min(value, maximum)


def require_name(value, label):
    """Validate an entity set / logical name: letters, digits, underscores only."""
    if not value:
        raise ValueError(f"{label} required")
    name = str(value)
    if name in (".", "..") or not ENTITY_RE.match(name):
        raise ValueError(f"Invalid {label}: only letters, digits, and underscores are allowed")
    return name


def require_guid(value, label="recordId"):
    if not value:
        raise ValueError(f"{label} required")
    guid = str(value)
    if not GUID_RE.match(guid):
        raise ValueError(f"Invalid {label}: must be a GUID "
                         f"(e.g. 00000000-0000-0000-0000-000000000000)")
    return guid


def singularize(entity_set):
    """Best-effort entity logical name from an entity set name (accounts -> account)."""
    if entity_set.endswith("ies"):
        return entity_set[:-3] + "y"
    if entity_set.endswith(("ses", "xes", "zes", "ches", "shes")):
        return entity_set[:-2]
    if entity_set.endswith("s"):
        return entity_set[:-1]
    return entity_set


def record_summary(rec):
    """Keep raw fields plus formatted-value annotations (as <field>@formatted); drop the rest."""
    out = {}
    for key, value in (rec or {}).items():
        if key.endswith(FORMATTED_SUFFIX):
            out[key[: -len(FORMATTED_SUFFIX)] + "@formatted"] = value
        elif "@" not in key:
            out[key] = value
    return out


def extract_entity_id(headers):
    """Pull the created record GUID out of the OData-EntityId response header."""
    entity_id = headers.get("OData-EntityId") if headers else None
    if entity_id:
        m = re.search(r"\(([0-9a-fA-F-]{36})\)", entity_id)
        if m:
            return m.group(1)
    raise RuntimeError("Record created but no OData-EntityId header returned")


# --- Tool handlers ---------------------------------------------------------

def query_records():
    entity_set = require_name(params.get("entitySet"), "entitySet")
    top = clamp(params.get("top", 25), 25, 50)
    token = get_token()
    data, _ = request("GET", f"/{entity_set}", token, query={
        "$select": params.get("select"),
        "$filter": params.get("filter"),
        "$orderby": params.get("orderby"),
        "$top": top,
    }, formatted=True)
    records = [record_summary(r) for r in (data or {}).get("value", [])]
    next_link = (data or {}).get("@odata.nextLink")
    pages = 1
    while next_link and pages < MAX_PAGES and len(records) < top:
        parsed = urllib.parse.urlparse(str(next_link))
        if parsed.scheme != "https" or parsed.netloc != ENV_HOST:
            break  # never follow pagination links that leave the environment host
        data, _ = request("GET", str(next_link), token, formatted=True)
        records.extend(record_summary(r) for r in (data or {}).get("value", []))
        next_link = (data or {}).get("@odata.nextLink")
        pages += 1
    records = records[:top]
    print(json.dumps({"count": len(records), "records": records}))


def get_record():
    entity_set = require_name(params.get("entitySet"), "entitySet")
    record_id = require_guid(params.get("recordId"))
    token = get_token()
    data, _ = request("GET", f"/{entity_set}({record_id})", token, query={
        "$select": params.get("select"),
    }, formatted=True)
    print(json.dumps(record_summary(data)))


def whoami():
    token = get_token()
    data, _ = request("GET", "/WhoAmI", token, formatted=True)
    data = data or {}
    print(json.dumps({
        "userId": data.get("UserId"),
        "businessUnitId": data.get("BusinessUnitId"),
        "organizationId": data.get("OrganizationId"),
    }))


def list_entity_fields():
    entity = require_name(params.get("entity"), "entity")
    token = get_token()
    data, _ = request("GET", f"/EntityDefinitions(LogicalName='{entity}')/Attributes", token,
                      query={
                          "$select": "LogicalName,AttributeType,DisplayName",
                          "$filter": "IsValidForRead eq true",
                      }, formatted=True)
    fields = [{
        "logicalName": a.get("LogicalName"),
        "type": a.get("AttributeType"),
        "displayName": ((a.get("DisplayName") or {}).get("UserLocalizedLabel") or {}).get("Label"),
    } for a in (data or {}).get("value", [])]
    print(json.dumps({"count": len(fields), "fields": fields}))


def create_record():
    entity_set = require_name(params.get("entitySet"), "entitySet")
    fields = params.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields object required (attribute name -> value)")
    token = get_token()
    _, headers = request("POST", f"/{entity_set}", token, data=fields)
    print(json.dumps({"id": extract_entity_id(headers), "entitySet": entity_set,
                      "created": True}))


def update_record():
    entity_set = require_name(params.get("entitySet"), "entitySet")
    record_id = require_guid(params.get("recordId"))
    fields = params.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields object required (attribute name -> value)")
    token = get_token()
    request("PATCH", f"/{entity_set}({record_id})", token, data=fields,
            extra_headers={"If-Match": "*"})
    print(json.dumps({"id": record_id, "entitySet": entity_set, "updated": True}))


def add_annotation():
    entity_set = require_name(params.get("entitySet"), "entitySet")
    record_id = require_guid(params.get("recordId"))
    note_text = params.get("noteText")
    if not note_text:
        raise ValueError("noteText required")
    logical = params.get("entityLogicalName")
    logical = require_name(logical, "entityLogicalName") if logical else singularize(entity_set)
    payload = {"notetext": note_text}
    if params.get("subject"):
        payload["subject"] = params["subject"]
    payload[f"objectid_{logical}@odata.bind"] = f"/{entity_set}({record_id})"
    token = get_token()
    _, headers = request("POST", "/annotations", token, data=payload)
    print(json.dumps({"annotationId": extract_entity_id(headers), "entitySet": entity_set,
                      "recordId": record_id, "created": True}))


HANDLERS = {
    "dynamics.query_records": query_records,
    "dynamics.get_record": get_record,
    "dynamics.whoami": whoami,
    "dynamics.list_entity_fields": list_entity_fields,
    "dynamics.create_record": create_record,
    "dynamics.update_record": update_record,
    "dynamics.add_annotation": add_annotation,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret and environment_url):
        print(json.dumps({"error": "Missing Dynamics 365 credentials: connect the Dynamics 365 integration first (tenantId, clientId, clientSecret, environmentUrl)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
