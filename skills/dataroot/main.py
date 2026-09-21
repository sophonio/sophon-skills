"""Dataroot integration skill — discover organizations, connections, and data sources,
inspect data-source schema/table metadata and organization members, and check the signed-in
account, via the Dataroot REST API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, emailAddress, password).

Auth is an email/password login: POST {baseUrl}/api/v1/accounts/login with {username, emailAddress,
password} returns an accessToken (JWT) sent as Authorization: Bearer on every call. The live API
requires the username and emailAddress keys to be present (the OpenAPI spec marks them optional,
but the server rejects a body whose username is missing or null with HTTP 400). The connection
only collects an email, so we send an empty-string username alongside the email as emailAddress;
the server then authenticates by emailAddress + password. Sandbox runs are fresh, so the token
is minted per invocation. Nearly every non-account endpoint requires a
required X-Organization-Id header; tools accept an organization by name or id and resolve it via
GET /api/v1/organizations. Secret data-source settings (passwords, access keys, credentials) are
masked before output.
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")

# Credential fields normally arrive flat in `params`, keyed by the manifest's integration.fields
# keys (baseUrl / emailAddress / password). Some runtimes instead nest them under a container
# object (e.g. params["credentials"]["baseUrl"]) or expose them as environment variables, so
# resolve each field defensively across the known shapes before giving up.
_CRED_CONTAINERS = ("credentials", "connection", "connectionFields", "config", "configuration",
                    "context", "integration", "settings", "secrets", "inputs", "fields", "dataroot")
_SERVICE_MAPS = ("connections", "integrations", "services")


def _lookup(name, *env_names):
    """Find a configured field by name across flat params, nested containers, and env vars."""
    if params.get(name):
        return params.get(name)
    for container in _CRED_CONTAINERS:
        cv = params.get(container)
        if isinstance(cv, dict) and cv.get(name):
            return cv.get(name)
    for container in _SERVICE_MAPS:  # e.g. params["connections"]["dataroot"]["baseUrl"]
        cv = params.get(container)
        if isinstance(cv, dict) and isinstance(cv.get("dataroot"), dict) and cv["dataroot"].get(name):
            return cv["dataroot"].get(name)
    for env_name in env_names:
        if os.environ.get(env_name):
            return os.environ.get(env_name)
    return ""


base_url = (_lookup("baseUrl", "DATAROOT_BASE_URL", "DATAROOT_BASEURL") or "").rstrip("/")
email_address = _lookup("emailAddress", "DATAROOT_EMAIL_ADDRESS", "DATAROOT_EMAIL")
password = _lookup("password", "DATAROOT_PASSWORD")

API_PREFIX = "/api/v1"
USER_AGENT = "sophon-dataroot-skill"
MAX_CONNECTIONS_SCAN = 10
METADATA_TABLE_CAP = 50
METADATA_COLUMN_CAP = 100

# Data-source settings keys whose values are secrets. A key is treated as sensitive if it
# contains any of these substrings (case-insensitive) — verified to catch every secret-bearing
# field in DataSourceSettings (password, *SecretKey, *AccessKey, credentialsJson, gcsJsonKey,
# *OAuthClientSecret, restCatalogOAuthToken, sslTrustStorePassword, ...) and no structural field.
SENSITIVE_SUBSTRINGS = ("password", "secret", "key", "token", "credential", "json")
# Free-form maps that may hold secrets under arbitrary keys — mask all their values wholesale.
FULLY_OPAQUE_KEYS = {"extraProperties"}


def quote_seg(value, name):
    """URL-quote a params-derived path segment; reject empty/dot segments outright."""
    s = str(value)
    if not s or s in (".", ".."):
        raise ValueError(f"Invalid {name}: {s!r}")
    return urllib.parse.quote(s, safe="")


def parse_error(detail):
    """Extract a friendly message from an ASP.NET ProblemDetails (or similar) error body."""
    try:
        parsed = json.loads(detail)
    except (ValueError, TypeError):
        return detail
    if isinstance(parsed, dict):
        return (parsed.get("detail") or parsed.get("title") or parsed.get("message")
                or parsed.get("error") or detail)
    return detail


def get_token():
    """Log in with email + password and return a bearer access token (minted per invocation).

    The API requires a `username` key to be present (a null/omitted username is rejected with 400),
    but accepts an empty string and then authenticates by emailAddress + password. An explicit
    `username` param overrides the empty default if one is ever supplied.
    """
    url = f"{base_url}{API_PREFIX}/accounts/login"
    body = json.dumps({
        "username": params.get("username") or "",
        "emailAddress": email_address,
        "password": password,
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
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
        raise RuntimeError(
            f"Login failed ({e.code}): {parse_error(detail)}. "
            "Check baseUrl, emailAddress, and password."
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Dataroot: {e.reason}") from e
    token = data.get("accessToken")
    if not token:
        raise RuntimeError("No accessToken in login response")
    return token


def request(method, path, token, org_id=None, data=None, query=None):
    """Make an authenticated request. Adds Bearer + optional X-Organization-Id. Returns parsed
    JSON (or None for an empty body)."""
    url = f"{base_url}{path}"
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
    if org_id:
        headers["X-Organization-Id"] = str(org_id)
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Dataroot API error {e.code}: {parse_error(detail)}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Dataroot: {e.reason}") from e
    return json.loads(raw) if raw else None


def resolve_org(token, organization):
    """Resolve an organization name or id to an organization id.

    Matches an exact id first, then a unique case-insensitive name. Raises a friendly ValueError
    listing the available organizations on a miss or an ambiguous name.
    """
    if not organization:
        raise ValueError("organization required (an organization name or id)")
    orgs = request("GET", f"{API_PREFIX}/organizations", token) or []
    target = str(organization)
    for o in orgs:
        if str(o.get("id")) == target:
            return o.get("id")
    matches = [o for o in orgs if str(o.get("name") or "").lower() == target.lower()]
    if len(matches) == 1:
        return matches[0].get("id")
    names = ", ".join(sorted(str(o.get("name")) for o in orgs)) or "(none)"
    if len(matches) > 1:
        raise ValueError(f"Organization {organization!r} is ambiguous. Available: {names}")
    raise ValueError(f"Organization {organization!r} not found. Available: {names}")


def _is_sensitive_key(key):
    return any(s in key.lower() for s in SENSITIVE_SUBSTRINGS)


def _mask_map_values(value):
    if isinstance(value, dict):
        return {k: ("***" if v not in (None, "", [], {}) else v) for k, v in value.items()}
    return "***" if value not in (None, "", [], {}) else value


def redact_settings(value):
    """Recursively mask secret values in a data-source settings object, preserving structure."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in FULLY_OPAQUE_KEYS:
                out[k] = _mask_map_values(v)
            elif _is_sensitive_key(k) and v not in (None, "", [], {}):
                out[k] = "***"
            else:
                out[k] = redact_settings(v)
        return out
    if isinstance(value, list):
        return [redact_settings(x) for x in value]
    return value


def data_source_summary(dto, connection_id=None, connection_name=None):
    """Trim a DataSourceDto to a compact, settings-free list entry."""
    return {
        "id": dto.get("id"),
        "name": dto.get("name"),
        "type": dto.get("type"),
        "category": dto.get("category"),
        "status": dto.get("status"),
        "tags": dto.get("tags") or [],
        "connectionId": connection_id,
        "connectionName": connection_name,
    }


# --- Tool handlers ---------------------------------------------------------

def list_organizations():
    token = get_token()
    orgs = request("GET", f"{API_PREFIX}/organizations", token) or []
    organizations = [{"id": o.get("id"), "name": o.get("name")} for o in orgs]
    print(json.dumps({"count": len(organizations), "organizations": organizations}))


def list_connections():
    token = get_token()
    org_id = resolve_org(token, params.get("organization"))
    result = request("GET", f"{API_PREFIX}/connections", token, org_id) or {}
    connections = []
    for c in result.get("items") or []:
        connections.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "description": c.get("description"),
            "status": c.get("status"),
            "dataSourceCount": len(c.get("dataSources") or []),
        })
    print(json.dumps({"count": len(connections), "connections": connections}))


def list_data_sources():
    token = get_token()
    org_id = resolve_org(token, params.get("organization"))
    conn_id = params.get("connectionId")
    truncated = False
    if conn_id:
        conns = [{"id": conn_id, "name": None}]
    else:
        result = request("GET", f"{API_PREFIX}/connections", token, org_id) or {}
        items = result.get("items") or []
        if len(items) > MAX_CONNECTIONS_SCAN:
            items = items[:MAX_CONNECTIONS_SCAN]
            truncated = True
        conns = [{"id": c.get("id"), "name": c.get("name")} for c in items]
    sources = []
    for c in conns:
        res = request(
            "GET",
            f"{API_PREFIX}/connections/{quote_seg(c['id'], 'connectionId')}/sources",
            token, org_id,
        ) or {}
        for dto in res.get("items") or []:
            sources.append(data_source_summary(dto, c["id"], c.get("name")))
    print(json.dumps({
        "count": len(sources),
        "truncated": truncated,
        "connectionsScanned": len(conns),
        "dataSources": sources,
    }))


def get_data_source():
    token = get_token()
    org_id = resolve_org(token, params.get("organization"))
    conn_id = params.get("connectionId")
    source_id = params.get("sourceId")
    if not conn_id or not source_id:
        raise ValueError("connectionId and sourceId required")
    res = request(
        "GET",
        f"{API_PREFIX}/connections/{quote_seg(conn_id, 'connectionId')}"
        f"/sources/{quote_seg(source_id, 'sourceId')}",
        token, org_id,
    ) or {}
    dto = res.get("dataSource") or {}
    print(json.dumps({
        "id": dto.get("id"),
        "organizationId": dto.get("organizationId"),
        "name": dto.get("name"),
        "type": dto.get("type"),
        "category": dto.get("category"),
        "status": dto.get("status"),
        "tags": dto.get("tags") or [],
        "settings": redact_settings(dto.get("settings") or {}),
    }))


def get_data_source_metadata():
    token = get_token()
    org_id = resolve_org(token, params.get("organization"))
    ds = params.get("dataSourceId")
    if not ds:
        raise ValueError("dataSourceId required")
    res = request(
        "GET",
        f"{API_PREFIX}/data-sources/{quote_seg(ds, 'dataSourceId')}/metadata",
        token, org_id,
    ) or {}
    md = res.get("metadata") or {}
    schemas_in = md.get("schemas")
    schemas_out = []
    truncated = False
    if isinstance(schemas_in, dict):
        for sname, sval in schemas_in.items():
            sval = sval or {}
            tables_in = sval.get("tables") or {}
            table_names = list(tables_in.keys())
            capped_names = table_names[:METADATA_TABLE_CAP]
            if len(table_names) > METADATA_TABLE_CAP:
                truncated = True
            tables_out = []
            for tname in capped_names:
                t = tables_in.get(tname) or {}
                cols = t.get("columns") or {}
                col_items = list(cols.items())[:METADATA_COLUMN_CAP]
                if len(cols) > METADATA_COLUMN_CAP:
                    truncated = True
                tables_out.append({
                    "name": t.get("name") or tname,
                    "columnCount": len(cols),
                    "columns": [
                        {"name": (col or {}).get("name") or cname, "type": (col or {}).get("type")}
                        for cname, col in col_items
                    ],
                })
            schemas_out.append({
                "name": sval.get("name") or sname,
                "tableCount": len(tables_in),
                "tables": tables_out,
            })
    print(json.dumps({
        "dataSourceId": md.get("dataSourceId"),
        "schemaCount": len(schemas_out),
        "truncated": truncated,
        "schemas": schemas_out,
    }))


def list_members():
    token = get_token()
    org_id = resolve_org(token, params.get("organization"))
    members_in = request("GET", f"{API_PREFIX}/organizations/members", token, org_id) or []
    members = []
    for m in members_in:
        members.append({
            "id": m.get("id"),
            "firstName": m.get("firstName"),
            "lastName": m.get("lastName"),
            "email": m.get("email"),
            "isOwner": m.get("isOwner"),
            "status": m.get("status"),
            "joinedAt": m.get("joinedAt"),
        })
    print(json.dumps({"count": len(members), "members": members}))


def whoami():
    token = get_token()
    info = request("GET", f"{API_PREFIX}/accounts/manage/info", token) or {}
    profile = {
        "userId": info.get("userId"),
        "email": info.get("email"),
        "userName": info.get("userName"),
        "firstName": info.get("firstName"),
        "lastName": info.get("lastName"),
        "roles": info.get("roles") or [],
        "isActive": info.get("isActive"),
        "timezone": info.get("timezone"),
        "locale": info.get("locale"),
    }
    quota = None
    try:
        q = request("GET", f"{API_PREFIX}/quota/status", token) or {}
        if q:
            quota = {
                "planName": q.get("planName"),
                "remainingRequests": q.get("remainingRequests"),
                "usedRequests": q.get("usedRequests"),
                "monthlyLimit": q.get("monthlyLimit"),
                "usagePercentage": q.get("usagePercentage"),
                "periodEndsAt": q.get("periodEndsAt"),
                "payAsYouGoEnabled": q.get("payAsYouGoEnabled"),
            }
    except RuntimeError:
        quota = None  # quota is best-effort — don't fail whoami if it's unavailable
    print(json.dumps({"profile": profile, "quota": quota}))


HANDLERS = {
    "dataroot.list_organizations": list_organizations,
    "dataroot.list_connections": list_connections,
    "dataroot.list_data_sources": list_data_sources,
    "dataroot.get_data_source": get_data_source,
    "dataroot.get_data_source_metadata": get_data_source_metadata,
    "dataroot.list_members": list_members,
    "dataroot.whoami": whoami,
}


def _param_shape(p):
    """A structural sketch of params for diagnostics: top-level key names, each value's TYPE, and
    the key names of nested objects. It never emits any value, so it is safe to return even though
    params may hold credentials — it reveals HOW the runtime delivered data, not WHAT."""
    if not isinstance(p, dict):
        return {"_type": type(p).__name__}
    shape = {}
    for k, v in p.items():
        if isinstance(v, dict):
            shape[str(k)] = {"object_keys": sorted(str(x) for x in v.keys())}
        elif isinstance(v, list):
            shape[str(k)] = {"array_len": len(v)}
        else:
            shape[str(k)] = type(v).__name__
    return shape


try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and email_address and password):
        missing = [n for n, v in (("baseUrl", base_url), ("emailAddress", email_address),
                                   ("password", password)) if not v]
        print(json.dumps({
            "error": "Missing Dataroot credentials: " + ", ".join(missing)
                     + " not received by the skill. Connect or re-save the Dataroot integration "
                       "(baseUrl, emailAddress, password).",
            "receivedParamShape": _param_shape(params),
        }))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
