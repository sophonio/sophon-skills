"""Package registry skill — query npm and PyPI package metadata over urllib.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies and no authentication. `params` is injected as a global by the Sophon runtime and
carries the tool name plus the tool's call arguments.

Network hosts: registry.npmjs.org (npm registry) and pypi.org (PyPI JSON API).
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")

USER_AGENT = "sophon-package-registry-skill/1.0 (+https://buildersoft.io)"
NPM_BASE = "https://registry.npmjs.org/"
PYPI_BASE = "https://pypi.org/pypi/"

VERSION_PART_RE = re.compile(r"(\d+)")


def get_json(url):
    """GET a URL and return parsed JSON. Raises RuntimeError on HTTP/URL errors."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Request failed: {e.reason}") from e


def require_name():
    name = params.get("name")
    if not name or not str(name).strip():
        raise ValueError("name is required")
    return str(name).strip()


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def version_key(version):
    """Loose natural-sort key for a version string (numeric parts compared numerically)."""
    parts = VERSION_PART_RE.split(str(version))
    key = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # numeric capture group
            key.append((1, int(part), ""))
        elif part:
            # Non-numeric chunk: pre-release markers sort before release padding.
            key.append((0, 0, part))
    return key


def recent_versions(versions, times, limit):
    """Sort versions oldest->newest (by publish time when available) and return the last N."""
    if times:
        def sort_key(v):
            t = times.get(v)
            return (0, t) if t else (1, version_key(v))
        ordered = sorted(versions, key=sort_key)
    else:
        ordered = sorted(versions, key=version_key)
    if limit and len(ordered) > limit:
        return ordered[-limit:]
    return ordered


def homepage_from_project_urls(project_urls, fallback):
    if isinstance(project_urls, dict):
        for label in ("Homepage", "homepage", "Home", "Documentation", "Source", "Repository"):
            if project_urls.get(label):
                return project_urls[label]
    return fallback


# --- npm handlers ----------------------------------------------------------

def fetch_npm(name):
    url = NPM_BASE + urllib.parse.quote(name, safe="")
    try:
        return get_json(url)
    except RuntimeError as e:
        if "404" in str(e):
            raise LookupError(f"package not found: {name}")
        raise


def npm_info():
    name = require_name()
    doc = fetch_npm(name)
    latest = ((doc.get("dist-tags") or {}).get("latest"))
    versions = doc.get("versions") or {}
    latest_meta = versions.get(latest) or {}

    lic = doc.get("license") or latest_meta.get("license")
    if isinstance(lic, dict):
        lic = lic.get("type") or lic.get("name")
    elif isinstance(lic, list):
        lic = ", ".join(str(x.get("type") if isinstance(x, dict) else x) for x in lic) or None

    print(json.dumps({
        "name": doc.get("name") or name,
        "latest": latest,
        "description": latest_meta.get("description") or doc.get("description"),
        "license": lic,
        "homepage": doc.get("homepage") or latest_meta.get("homepage"),
        "deprecated": latest_meta.get("deprecated") if "deprecated" in latest_meta else None,
        "maintainers": len(doc.get("maintainers") or []),
    }))


def npm_versions():
    name = require_name()
    limit = clamp(params.get("limit", 20), 20, 100)
    doc = fetch_npm(name)
    versions = list((doc.get("versions") or {}).keys())
    times = doc.get("time") or {}
    result = recent_versions(versions, times, limit)
    print(json.dumps({
        "name": doc.get("name") or name,
        "count": len(versions),
        "versions": result,
    }))


# --- PyPI handlers ---------------------------------------------------------

def fetch_pypi(name):
    url = PYPI_BASE + urllib.parse.quote(name, safe="") + "/json"
    try:
        return get_json(url)
    except RuntimeError as e:
        if "404" in str(e):
            raise LookupError(f"package not found: {name}")
        raise


def pypi_info():
    name = require_name()
    doc = fetch_pypi(name)
    info = doc.get("info") or {}
    homepage = info.get("home_page") or homepage_from_project_urls(info.get("project_urls"), None)
    print(json.dumps({
        "name": info.get("name") or name,
        "latest": info.get("version"),
        "summary": info.get("summary"),
        "license": info.get("license") or None,
        "homepage": homepage,
        "requires_python": info.get("requires_python") or None,
        "yanked": bool(info.get("yanked", False)),
    }))


def pypi_versions():
    name = require_name()
    limit = clamp(params.get("limit", 20), 20, 100)
    doc = fetch_pypi(name)
    releases = doc.get("releases") or {}
    # Keep only versions that have at least one published file.
    versions = [v for v, files in releases.items() if files]

    # Prefer publish-time ordering using the earliest file upload per version.
    times = {}
    for v in versions:
        stamps = [f.get("upload_time_iso8601") or f.get("upload_time")
                  for f in releases[v] if f.get("upload_time_iso8601") or f.get("upload_time")]
        if stamps:
            times[v] = min(stamps)
    result = recent_versions(versions, times if len(times) == len(versions) else None, limit)
    print(json.dumps({
        "name": (doc.get("info") or {}).get("name") or name,
        "count": len(versions),
        "versions": result,
    }))


HANDLERS = {
    "pkg.npm_info": npm_info,
    "pkg.npm_versions": npm_versions,
    "pkg.pypi_info": pypi_info,
    "pkg.pypi_versions": pypi_versions,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except LookupError as e:
    print(json.dumps({"error": str(e)}))
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
