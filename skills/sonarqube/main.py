"""SonarQube integration skill — code quality and security via the SonarQube Web API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, token, organization).

Auth is a static user token sent as `Authorization: Bearer <token>` (the scheme used by
SonarQube Server 10.0+ and SonarQube Cloud). The optional `organization` field is appended
as an `organization=` query parameter on every request (needed for SonarQube Cloud).

Note: SonarQube's /api/authentication/validate endpoint returns HTTP 200 with
{"valid": false} for bad tokens, so token validity must be judged from the response body,
never from the HTTP status alone.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
token = params.get("token") or ""
organization = params.get("organization") or ""

DEFAULT_METRICS = ("coverage,duplicated_lines_density,ncloc,complexity,"
                   "reliability_rating,security_rating,sqale_rating")
DEFAULT_HISTORY_METRICS = "coverage,ncloc"


def request(method, path, query=None, form=None):
    """Make an authenticated request to the SonarQube Web API.

    Query params that are None or "" are dropped; the organization (when configured) is
    appended last. POST bodies on the classic API are application/x-www-form-urlencoded,
    not JSON. Returns parsed JSON, or None for 204/empty responses.
    """
    clean = {k: v for k, v in (query or {}).items() if v not in (None, "")}
    if organization:
        clean["organization"] = organization
    url = f"{base_url}{path}"
    if clean:
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = urllib.parse.urlencode(form).encode() if form is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-sonarqube-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = "; ".join(x.get("msg", "") for x in (parsed.get("errors") or [])
                            if x.get("msg")) or detail
        except (ValueError, TypeError, AttributeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = (f"rate limited — back off and retry after {retry_after} seconds"
                    if retry_after else "rate limited — back off and retry later")
            raise RuntimeError(
                f"SonarQube API error 429: {msg or 'too many requests'} ({hint})") from e
        raise RuntimeError(f"SonarQube API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach SonarQube: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def csv(value):
    """Accept a list or a comma-separated string; return a comma-separated string."""
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return value


def project_summary(c):
    # search_projects only includes the analysis date when f=analysisDate is requested,
    # and names the response field "analysisDate"; keep the output key name from the spec.
    return {
        "key": c.get("key"),
        "name": c.get("name"),
        "lastAnalysisDate": c.get("analysisDate"),
    }


def issue_summary(i):
    return {
        "key": i.get("key"),
        "rule": i.get("rule"),
        "severity": i.get("severity"),
        "type": i.get("type"),
        "component": i.get("component"),
        "line": i.get("line"),
        "message": i.get("message"),
        "status": i.get("status"),
    }


def hotspot_summary(h):
    return {
        "key": h.get("key"),
        "securityCategory": h.get("securityCategory"),
        "vulnerabilityProbability": h.get("vulnerabilityProbability"),
        "component": h.get("component"),
        "line": h.get("line"),
        "message": h.get("message"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_projects():
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/api/components/search_projects", query={
        "filter": params.get("filter"),
        "ps": limit,
        "p": params.get("page"),
        "f": "analysisDate",
    })
    projects = [project_summary(c) for c in (result or {}).get("components", [])]
    print(json.dumps({"count": len(projects), "projects": projects}))


def get_quality_gate_status():
    project_key = params.get("projectKey")
    if not project_key:
        raise ValueError("projectKey required")
    branch = params.get("branch")
    result = request("GET", "/api/qualitygates/project_status", query={
        "projectKey": project_key,
        "branch": branch,
    })
    status = (result or {}).get("projectStatus") or {}
    failing = [{
        "metric": c.get("metricKey"),
        "status": c.get("status"),
        "actual": c.get("actualValue"),
        "threshold": c.get("errorThreshold") or c.get("warningThreshold"),
        "comparator": c.get("comparator"),
    } for c in status.get("conditions", []) if c.get("status") not in (None, "OK", "NO_VALUE")]
    out = {"projectKey": project_key, "status": status.get("status"),
           "failingConditions": failing}
    if branch:
        out["branch"] = branch
    print(json.dumps(out))


def search_issues():
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/api/issues/search", query={
        "componentKeys": params.get("projectKey"),
        "severities": csv(params.get("severities")),
        "types": csv(params.get("types")),
        "statuses": csv(params.get("statuses")),
        "assignees": csv(params.get("assignees")),
        "ps": limit,
        "p": params.get("page"),
    })
    issues = [issue_summary(i) for i in (result or {}).get("issues", [])]
    total = ((result or {}).get("paging") or {}).get("total")
    if total is None:
        total = (result or {}).get("total")
    print(json.dumps({"count": len(issues), "total": total, "issues": issues}))


def search_hotspots():
    project_key = params.get("projectKey")
    if not project_key:
        raise ValueError("projectKey required")
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/api/hotspots/search", query={
        "projectKey": project_key,
        "status": params.get("status"),
        "ps": limit,
        "p": params.get("page"),
    })
    hotspots = [hotspot_summary(h) for h in (result or {}).get("hotspots", [])]
    print(json.dumps({"count": len(hotspots), "hotspots": hotspots}))


def get_measures():
    component = params.get("component")
    if not component:
        raise ValueError("component required")
    metric_keys = csv(params.get("metricKeys")) or DEFAULT_METRICS
    result = request("GET", "/api/measures/component", query={
        "component": component,
        "metricKeys": metric_keys,
    })
    comp = (result or {}).get("component") or {}
    measures = {}
    for m in comp.get("measures", []):
        value = m.get("value")
        if value is None:
            value = (m.get("period") or {}).get("value")
        if value is None:  # SonarQube Cloud / pre-8.x servers use a "periods" array
            value = (m.get("periods") or [{}])[0].get("value")
        measures[m.get("metric")] = value
    print(json.dumps({"component": comp.get("key") or component, "measures": measures}))


def get_analysis_history():
    component = params.get("component")
    if not component:
        raise ValueError("component required")
    limit = clamp(params.get("limit", 25), 25, 100)
    metrics = csv(params.get("metrics")) or DEFAULT_HISTORY_METRICS
    result = request("GET", "/api/measures/search_history", query={
        "component": component,
        "metrics": metrics,
        "ps": limit,
        "p": params.get("page"),
    })
    series = [{
        "metric": m.get("metric"),
        "history": [{"date": h.get("date"), "value": h.get("value")}
                    for h in m.get("history", [])],
    } for m in (result or {}).get("measures", [])]
    print(json.dumps({"component": component, "metrics": series}))


def assign_issue():
    issue = params.get("issue")
    if not issue:
        raise ValueError("issue required")
    assignee = params.get("assignee")
    form = {"issue": issue}
    if assignee:
        form["assignee"] = assignee
    request("POST", "/api/issues/assign", form=form)
    print(json.dumps({"issue": issue, "assignee": assignee or None, "updated": True}))


HANDLERS = {
    "sonar.search_projects": search_projects,
    "sonar.get_quality_gate_status": get_quality_gate_status,
    "sonar.search_issues": search_issues,
    "sonar.search_hotspots": search_hotspots,
    "sonar.get_measures": get_measures,
    "sonar.get_analysis_history": get_analysis_history,
    "sonar.assign_issue": assign_issue,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and token):
        print(json.dumps({"error": "Missing SonarQube credentials: connect the SonarQube integration first (baseUrl, token)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
