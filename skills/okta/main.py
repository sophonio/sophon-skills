"""Okta integration skill — user, group, app-assignment, and system-log queries via the Okta API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, apiToken).

Auth is a static SSWS admin API token sent as `Authorization: SSWS {apiToken}` against
{baseUrl}/api/v1/... . List endpoints use Okta's cursor pagination (Link header, rel="next"
with an `after` cursor). On HTTP 429 the error message includes the X-Rate-Limit-Reset epoch.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
api_token = params.get("apiToken") or ""


def request(method, path, data=None, query=None, with_headers=False):
    """Make an authenticated request to the Okta API. Returns parsed JSON (or None for 204).

    With with_headers=True, returns (parsed_json, response_headers) so callers can follow
    Link-header cursor pagination.
    """
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"SSWS {api_token}",
        "Accept": "application/json",
        "User-Agent": "sophon-okta-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            parsed = json.loads(raw) if raw else None
            if with_headers:
                return parsed, resp.headers
            return parsed
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            body_json = json.loads(detail)
            msg = body_json.get("errorSummary") or detail
            causes = "; ".join(
                c.get("errorSummary", "") for c in (body_json.get("errorCauses") or [])
                if c.get("errorSummary")
            )
            if causes:
                msg = f"{msg} ({causes})"
        except (ValueError, TypeError, AttributeError):
            msg = detail
        if not msg:
            msg = str(e.reason) if e.reason else "(no error body)"
        if e.code == 429:
            reset = e.headers.get("X-Rate-Limit-Reset") or "unknown"
            raise RuntimeError(
                f"Okta API error 429: rate limit exceeded, retry after epoch {reset}. {msg}"
            ) from e
        raise RuntimeError(f"Okta API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Okta: {e.reason}") from e


def next_after(headers):
    """Extract the `after` cursor from a Link header with rel="next", if any."""
    for link in headers.get_all("Link") or []:
        for part in link.split(","):
            if 'rel="next"' in part:
                start, end = part.find("<"), part.find(">")
                if start == -1 or end == -1:
                    continue
                next_url = part[start + 1:end]
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(next_url).query)
                return (qs.get("after") or [None])[0]
    return None


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def quote_seg(value):
    return urllib.parse.quote(str(value), safe="")


def user_summary(u):
    profile = u.get("profile") or {}
    return {
        "id": u.get("id"),
        "status": u.get("status"),
        "firstName": profile.get("firstName"),
        "lastName": profile.get("lastName"),
        "email": profile.get("email"),
        "login": profile.get("login"),
        "lastLogin": u.get("lastLogin"),
    }


def group_summary(g):
    profile = g.get("profile") or {}
    return {
        "id": g.get("id"),
        "name": profile.get("name"),
        "description": profile.get("description"),
        "type": g.get("type"),
    }


def app_summary(a):
    return {
        "id": a.get("id"),
        "label": a.get("label"),
        "status": a.get("status"),
        "signOnMode": a.get("signOnMode"),
    }


def target_summary(t):
    return {
        "type": t.get("type"),
        "displayName": t.get("displayName"),
        "alternateId": t.get("alternateId"),
    }


def event_summary(ev):
    actor = ev.get("actor") or {}
    return {
        "eventType": ev.get("eventType"),
        "published": ev.get("published"),
        "displayMessage": ev.get("displayMessage"),
        "actor": {
            "displayName": actor.get("displayName"),
            "alternateId": actor.get("alternateId"),
        },
        "outcome": (ev.get("outcome") or {}).get("result"),
        "targets": [target_summary(t) for t in (ev.get("target") or [])],
    }


# --- Tool handlers ---------------------------------------------------------

def search_users():
    limit = clamp(params.get("limit", 25), 25, 100)
    query = {"limit": limit}
    if params.get("search"):
        query["search"] = params["search"]
    elif params.get("q"):
        query["q"] = params["q"]
    result = request("GET", "/api/v1/users", query=query)
    users = [user_summary(u) for u in (result or [])]
    print(json.dumps({"count": len(users), "users": users}))


def get_user():
    user_id = params.get("userId")
    if not user_id:
        raise ValueError("userId required")
    u = request("GET", f"/api/v1/users/{quote_seg(user_id)}") or {}
    print(json.dumps({
        "id": u.get("id"),
        "status": u.get("status"),
        "created": u.get("created"),
        "activated": u.get("activated"),
        "statusChanged": u.get("statusChanged"),
        "lastLogin": u.get("lastLogin"),
        "lastUpdated": u.get("lastUpdated"),
        "passwordChanged": u.get("passwordChanged"),
        "profile": u.get("profile"),
        "provider": ((u.get("credentials") or {}).get("provider") or {}).get("type"),
    }))


def list_groups():
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/api/v1/groups", query={"q": params.get("q"), "limit": limit})
    groups = [group_summary(g) for g in (result or [])]
    print(json.dumps({"count": len(groups), "groups": groups}))


def list_group_members():
    group_id = params.get("groupId")
    if not group_id:
        raise ValueError("groupId required")
    cap = clamp(params.get("limit", 200), 200, 1000)
    members = []
    after = None
    while len(members) < cap:
        page, headers = request(
            "GET",
            f"/api/v1/groups/{quote_seg(group_id)}/users",
            query={"limit": min(200, cap - len(members)), "after": after},
            with_headers=True,
        )
        if not page:
            break
        members.extend(user_summary(u) for u in page)
        after = next_after(headers)
        if not after:
            break
    members = members[:cap]
    print(json.dumps({"count": len(members), "members": members}))


def list_user_apps():
    user_id = params.get("userId")
    if not user_id:
        raise ValueError("userId required")
    limit = clamp(params.get("limit", 50), 50, 100)
    safe_user_id = str(user_id).replace('"', "")
    result = request("GET", "/api/v1/apps", query={
        "filter": f'user.id eq "{safe_user_id}"',
        "limit": limit,
    })
    apps = [app_summary(a) for a in (result or [])]
    print(json.dumps({"count": len(apps), "apps": apps}))


def query_system_log():
    limit = clamp(params.get("limit", 50), 50, 100)
    result = request("GET", "/api/v1/logs", query={
        "since": params.get("since"),
        "until": params.get("until"),
        "filter": params.get("filter"),
        "q": params.get("q"),
        "limit": limit,
    })
    events = [event_summary(ev) for ev in (result or [])]
    print(json.dumps({"count": len(events), "events": events}))


def add_user_to_group():
    group_id = params.get("groupId")
    user_id = params.get("userId")
    if not group_id or not user_id:
        raise ValueError("groupId and userId required")
    request("PUT", f"/api/v1/groups/{quote_seg(group_id)}/users/{quote_seg(user_id)}")
    print(json.dumps({"added": True, "groupId": group_id, "userId": user_id}))


def suspend_user():
    user_id = params.get("userId")
    if not user_id:
        raise ValueError("userId required")
    request("POST", f"/api/v1/users/{quote_seg(user_id)}/lifecycle/suspend")
    print(json.dumps({"suspended": True, "userId": user_id}))


HANDLERS = {
    "okta.search_users": search_users,
    "okta.get_user": get_user,
    "okta.list_groups": list_groups,
    "okta.list_group_members": list_group_members,
    "okta.list_user_apps": list_user_apps,
    "okta.query_system_log": query_system_log,
    "okta.add_user_to_group": add_user_to_group,
    "okta.suspend_user": suspend_user,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_token):
        print(json.dumps({"error": "Missing Okta credentials: connect the Okta integration first (baseUrl, apiToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
