"""Microsoft Entra ID integration skill — directory users, groups, roles, sign-in logs, and app
registrations via Microsoft Graph (app-only).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret).

Auth is app-only (OAuth2 client-credentials): we POST to the tenant token endpoint to obtain an
access token, then call Microsoft Graph directory-wide at https://graph.microsoft.com/v1.0 with a
Bearer token. Requires the Directory.Read.All application permission with admin consent, plus
AuditLog.Read.All for sign-in logs (which also need an Entra ID P1/P2 license).
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

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

USER_SELECT = "id,displayName,mail,userPrincipalName,jobTitle,department,accountEnabled"


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
            "User-Agent": "sophon-entra-id-skill",
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


def request(method, path, token, data=None, query=None, headers=None):
    """Make an authenticated request to Microsoft Graph. Returns parsed JSON (or None for 204).

    `path` may be a Graph-relative path or an absolute @odata.nextLink URL.
    """
    url = path if path.startswith("http") else f"{GRAPH_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    all_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-entra-id-skill",
    }
    if headers:
        all_headers.update(headers)
    if body is not None:
        all_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        code = ""
        try:
            parsed = json.loads(detail)
            err = parsed.get("error") or {}
            code = err.get("code") or ""
            msg = err.get("message") or detail
        except (ValueError, TypeError):
            msg = detail
        if code == "Authentication_RequestFromNonPremiumTenantOrB2CTenant":
            raise RuntimeError("Sign-in logs require an Entra ID P1/P2 license (this tenant does not have one).") from e
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            raise RuntimeError(
                f"Graph API throttled (429): retry after {retry_after or 'a few'} seconds. {msg}"
            ) from e
        raise RuntimeError(f"Graph API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft Graph: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def odata_quote(value):
    """Escape single quotes for OData string literals."""
    return str(value).replace("'", "''")


def kql_term(value):
    """Sanitize a user query for use inside a KQL $search phrase.

    Strips characters that are significant to KQL syntax (quotes, colons,
    parentheses) so a query like 'name:x (test)' cannot produce a raw
    Graph 400 syntax error.
    """
    term = re.sub(r'["\':()]', " ", str(value))
    term = " ".join(term.split())
    if not term:
        raise ValueError("query contains no searchable characters; try a plain name or email term")
    return term


def user_summary(u):
    return {
        "id": u.get("id"),
        "displayName": u.get("displayName"),
        "mail": u.get("mail"),
        "userPrincipalName": u.get("userPrincipalName"),
        "jobTitle": u.get("jobTitle"),
        "department": u.get("department"),
        "accountEnabled": u.get("accountEnabled"),
    }


def group_summary(g):
    return {
        "id": g.get("id"),
        "displayName": g.get("displayName"),
        "mail": g.get("mail"),
        "groupTypes": g.get("groupTypes"),
        "securityEnabled": g.get("securityEnabled"),
    }


def member_summary(m):
    return {
        "id": m.get("id"),
        "displayName": m.get("displayName"),
        "mail": m.get("mail"),
        "userPrincipalName": m.get("userPrincipalName"),
        "type": (m.get("@odata.type") or "").replace("#microsoft.graph.", ""),
    }


def signin_summary(s):
    status = s.get("status") or {}
    location = s.get("location") or {}
    return {
        "id": s.get("id"),
        "createdDateTime": s.get("createdDateTime"),
        "userPrincipalName": s.get("userPrincipalName"),
        "userDisplayName": s.get("userDisplayName"),
        "appDisplayName": s.get("appDisplayName"),
        "ipAddress": s.get("ipAddress"),
        "clientAppUsed": s.get("clientAppUsed"),
        "status": {
            "errorCode": status.get("errorCode"),
            "failureReason": status.get("failureReason"),
        },
        "location": {
            "city": location.get("city"),
            "countryOrRegion": location.get("countryOrRegion"),
        },
    }


def application_summary(a):
    return {
        "appId": a.get("appId"),
        "displayName": a.get("displayName"),
        "passwordCredentials": [
            {"endDateTime": c.get("endDateTime")} for c in (a.get("passwordCredentials") or [])
        ],
    }


# --- Tool handlers ---------------------------------------------------------

def search_users():
    token = get_token()
    query = (params.get("query") or "").strip()
    if not query:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 25), 25, 100)
    if params.get("prefix"):
        esc = odata_quote(query)
        odata = {
            "$filter": (
                f"startswith(displayName,'{esc}') or startswith(mail,'{esc}') "
                f"or startswith(userPrincipalName,'{esc}')"
            ),
            "$count": "true",
            "$top": limit,
            "$select": USER_SELECT,
        }
    else:
        term = kql_term(query)
        odata = {
            "$search": f'"displayName:{term}" OR "mail:{term}"',
            "$count": "true",
            "$top": limit,
            "$select": USER_SELECT,
        }
    result = request("GET", "/users", token, query=odata,
                     headers={"ConsistencyLevel": "eventual"})
    users = [user_summary(u) for u in (result or {}).get("value", [])]
    print(json.dumps({"count": len(users), "users": users}))


def get_user():
    token = get_token()
    user_id = params.get("userId")
    if not user_id:
        raise ValueError("userId required")
    # App-only GET /users/{id}/manager is not supported; $expand=manager is.
    result = request(
        "GET",
        f"/users/{urllib.parse.quote(str(user_id), safe='')}",
        token,
        query={
            "$select": USER_SELECT + ",officeLocation,mobilePhone,createdDateTime,userType",
            "$expand": "manager($select=id,displayName,mail)",
        },
    )
    result = result or {}
    user = user_summary(result)
    user.update({
        "officeLocation": result.get("officeLocation"),
        "mobilePhone": result.get("mobilePhone"),
        "createdDateTime": result.get("createdDateTime"),
        "userType": result.get("userType"),
    })
    manager = result.get("manager")
    user["manager"] = {
        "id": manager.get("id"),
        "displayName": manager.get("displayName"),
        "mail": manager.get("mail"),
    } if manager else None
    print(json.dumps(user))


def list_user_groups():
    token = get_token()
    user_id = params.get("userId")
    if not user_id:
        raise ValueError("userId required")
    limit = clamp(params.get("limit", 25), 25, 100)
    # OData cast so only groups count toward $top (directory roles/admin units excluded server-side).
    result = request(
        "GET",
        f"/users/{urllib.parse.quote(str(user_id), safe='')}/memberOf/microsoft.graph.group",
        token,
        query={"$top": limit, "$select": "id,displayName,groupTypes"},
    )
    groups = [
        {"id": g.get("id"), "displayName": g.get("displayName"), "groupTypes": g.get("groupTypes")}
        for g in (result or {}).get("value", [])
    ]
    print(json.dumps({"count": len(groups), "groups": groups}))


def search_groups():
    token = get_token()
    query = (params.get("query") or "").strip()
    if not query:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 25), 25, 100)
    select = "id,displayName,mail,groupTypes,securityEnabled"
    if params.get("prefix"):
        odata = {
            "$filter": f"startswith(displayName,'{odata_quote(query)}')",
            "$count": "true",
            "$top": limit,
            "$select": select,
        }
    else:
        term = kql_term(query)
        odata = {
            "$search": f'"displayName:{term}"',
            "$count": "true",
            "$top": limit,
            "$select": select,
        }
    result = request("GET", "/groups", token, query=odata,
                     headers={"ConsistencyLevel": "eventual"})
    groups = [group_summary(g) for g in (result or {}).get("value", [])]
    print(json.dumps({"count": len(groups), "groups": groups}))


def list_group_members():
    token = get_token()
    group_id = params.get("groupId")
    if not group_id:
        raise ValueError("groupId required")
    limit = clamp(params.get("limit", 25), 25, 200)
    members = []
    result = request(
        "GET",
        f"/groups/{urllib.parse.quote(str(group_id), safe='')}/members",
        token,
        query={"$top": min(limit, 100)},
    )
    pages = 1
    truncated = False
    while True:
        members.extend(member_summary(m) for m in (result or {}).get("value", []))
        next_link = (result or {}).get("@odata.nextLink")
        if not next_link:
            break
        if len(members) >= limit or pages >= 5:
            truncated = True
            break
        result = request("GET", next_link, token)
        pages += 1
    if len(members) > limit:
        members = members[:limit]
        truncated = True
    print(json.dumps({"count": len(members), "members": members, "truncated": truncated}))


def list_role_members():
    token = get_token()
    role_name = (params.get("roleName") or "").strip()
    if not role_name:
        raise ValueError("roleName required")
    result = request("GET", "/directoryRoles", token)
    roles = (result or {}).get("value", [])
    match = next(
        (r for r in roles if (r.get("displayName") or "").lower() == role_name.lower()), None
    )
    if match is None:
        activated = sorted(r.get("displayName") or "" for r in roles)
        print(json.dumps({
            "message": (
                f"Role '{role_name}' is not activated in this tenant (or does not exist). "
                "A directory role only appears once it has been assigned at least once."
            ),
            "activatedRoles": activated,
        }))
        return
    limit = clamp(params.get("limit", 100), 100, 200)
    members = []
    members_result = request(
        "GET",
        f"/directoryRoles/{urllib.parse.quote(str(match.get('id')), safe='')}/members",
        token,
        query={"$top": min(limit, 100)},
    )
    pages = 1
    truncated = False
    while True:
        members.extend(member_summary(m) for m in (members_result or {}).get("value", []))
        next_link = (members_result or {}).get("@odata.nextLink")
        if not next_link:
            break
        if len(members) >= limit or pages >= 5:
            truncated = True
            break
        members_result = request("GET", next_link, token)
        pages += 1
    if len(members) > limit:
        members = members[:limit]
        truncated = True
    print(json.dumps({
        "role": match.get("displayName"),
        "roleId": match.get("id"),
        "count": len(members),
        "members": members,
        "truncated": truncated,
    }))


def list_signin_logs():
    token = get_token()
    since = (params.get("since") or "").strip()
    if not since:
        raise ValueError("since required (ISO 8601, e.g. 2026-07-16T00:00:00Z)")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", since):
        raise ValueError("since must be ISO 8601 UTC, e.g. 2026-07-16T00:00:00Z")
    limit = clamp(params.get("limit", 25), 25, 50)
    filters = [f"createdDateTime ge {since}"]
    if params.get("userPrincipalName"):
        filters.append(f"userPrincipalName eq '{odata_quote(params['userPrincipalName'])}'")
    if params.get("appDisplayName"):
        filters.append(f"appDisplayName eq '{odata_quote(params['appDisplayName'])}'")
    if params.get("errorCode") is not None:
        try:
            filters.append(f"status/errorCode eq {int(params['errorCode'])}")
        except (TypeError, ValueError):
            raise ValueError("errorCode must be an integer (0 = success)")
    result = request("GET", "/auditLogs/signIns", token, query={
        "$filter": " and ".join(filters),
        "$top": limit,
    })
    logs = [signin_summary(s) for s in (result or {}).get("value", [])]
    print(json.dumps({"count": len(logs), "signIns": logs}))


def list_applications():
    token = get_token()
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/applications", token, query={
        "$top": limit,
        "$select": "id,appId,displayName,passwordCredentials",
    })
    apps = [application_summary(a) for a in (result or {}).get("value", [])]
    print(json.dumps({"count": len(apps), "applications": apps}))


HANDLERS = {
    "entra.search_users": search_users,
    "entra.get_user": get_user,
    "entra.list_user_groups": list_user_groups,
    "entra.search_groups": search_groups,
    "entra.list_group_members": list_group_members,
    "entra.list_role_members": list_role_members,
    "entra.list_signin_logs": list_signin_logs,
    "entra.list_applications": list_applications,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret):
        print(json.dumps({"error": "Missing Microsoft Graph credentials: connect the Microsoft Entra ID integration first (tenantId, clientId, clientSecret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
