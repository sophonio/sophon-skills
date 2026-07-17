"""Artifactory integration skill — repositories, artifact search, storage info, builds, and
properties via the JFrog Artifactory REST API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, accessToken).

Auth is a static JFrog access (identity) token sent as `Authorization: Bearer {accessToken}`
against {baseUrl}/artifactory/api/... . AQL search bodies are constructed server-side from
structured parameters (never raw caller-supplied AQL) and posted as text/plain. On HTTP 429 the
error message includes the Retry-After header when present.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
access_token = params.get("accessToken") or ""

AQL_LIMIT_MAX = 100


class ApiError(RuntimeError):
    """RuntimeError carrying the HTTP status code so handlers can special-case 403/404."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def request(method, path, data=None, query=None, raw_query=None, text_body=None):
    """Make an authenticated request to the Artifactory API. Returns parsed JSON (or None for 204).

    `path` must already be safely quoted. `query` is a dict (None/"" values dropped);
    `raw_query` is a pre-encoded query string appended verbatim. `text_body` sends a
    text/plain body (used for AQL); `data` sends JSON.
    """
    url = f"{base_url}/artifactory/api{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    if raw_query:
        url = f"{url}{'&' if '?' in url else '?'}{raw_query}"
    if text_body is not None:
        body = text_body.encode()
        content_type = "text/plain"
    elif data is not None:
        body = json.dumps(data).encode()
        content_type = "application/json"
    else:
        body = None
        content_type = None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "sophon-artifactory-skill",
    }
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            body_json = json.loads(detail)
            msgs = [err.get("message", "") for err in (body_json.get("errors") or [])
                    if err.get("message")]
            msg = "; ".join(msgs) if msgs else (body_json.get("message") or detail)
        except (ValueError, TypeError, AttributeError):
            msg = detail
        if not msg:
            msg = str(e.reason) if e.reason else "(no error body)"
        if e.code == 429:
            retry_after = e.headers.get("Retry-After")
            # Retry-After may be delta-seconds or an HTTP-date; only add "s" for seconds.
            unit = "s" if retry_after and retry_after.strip().isdigit() else ""
            suffix = f" (retry after {retry_after}{unit})" if retry_after else ""
            raise ApiError(429, f"Artifactory API error 429: {msg}{suffix}") from e
        raise ApiError(e.code, f"Artifactory API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Artifactory: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def quote_seg(value):
    return urllib.parse.quote(str(value), safe="")


def prop_component(value):
    """Encode a property key/value for the Set Item Properties matrix query.

    JFrog parses ',', '\\', '|', and '=' as separators even after URL-decoding, so each
    must be preceded by a (percent-encoded) backslash to be taken literally; everything
    is then percent-encoded as usual.
    """
    return urllib.parse.quote(re.sub(r"([,\\|=])", r"\\\1", str(value)), safe="")


def check_no_dots(value, label):
    """Reject '.' / '..' path segments in params-derived path material."""
    for seg in str(value).split("/"):
        if seg in (".", ".."):
            raise ValueError(f"{label} must not contain '.' or '..' path segments")


def storage_path(repo, path):
    """Build a safely-quoted /storage/{repo}/{path} suffix from caller-supplied values."""
    if not repo or not path:
        raise ValueError("repo and path required")
    check_no_dots(repo, "repo")
    check_no_dots(path, "path")
    segments = [quote_seg(s) for s in str(path).split("/") if s != ""]
    if not segments:
        raise ValueError("path required")
    return f"/storage/{quote_seg(repo)}/" + "/".join(segments)


def repo_summary(r):
    return {
        "key": r.get("key"),
        "type": r.get("type"),
        "packageType": r.get("packageType"),
        "url": r.get("url"),
    }


def aql_item_summary(item):
    return {
        "repo": item.get("repo"),
        "path": item.get("path"),
        "name": item.get("name"),
        "size": item.get("size"),
        "created": item.get("created"),
    }


def quick_hit_summary(hit):
    """Shape a quick-search hit; derive repo/path/name from the storage-API uri."""
    uri = hit.get("uri") or ""
    out = {"uri": uri, "repo": None, "path": None, "name": None}
    marker = "/api/storage/"
    if marker in uri:
        rest = uri.split(marker, 1)[1]
        repo, _, path = rest.partition("/")
        out["repo"] = urllib.parse.unquote(repo)
        out["path"] = urllib.parse.unquote(path)
        if path:
            out["name"] = urllib.parse.unquote(path.rsplit("/", 1)[-1])
    return out


def storage_repo_summary(r):
    return {
        "repoKey": r.get("repoKey"),
        "usedSpace": r.get("usedSpace"),
        "itemsCount": r.get("itemsCount"),
        "packageType": r.get("packageType"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_repositories():
    repo_type = params.get("type")
    if repo_type and repo_type not in ("local", "remote", "virtual", "federated"):
        raise ValueError("type must be one of: local, remote, virtual, federated")
    result = request("GET", "/repositories", query={"type": repo_type})
    repos = [repo_summary(r) for r in (result or [])]
    print(json.dumps({"count": len(repos), "repositories": repos}))


def search_artifacts():
    limit = clamp(params.get("limit", 50), 50, AQL_LIMIT_MAX)
    name = params.get("name")
    if name:
        # Quick search: GET /search/artifact?name=&repos= (local/remote repos only, not
        # virtual). Accept `repo` as a fallback for `repos` so a mixed-up caller does not
        # silently search every repository.
        result = request("GET", "/search/artifact",
                         query={"name": name,
                                "repos": params.get("repos") or params.get("repo")})
        hits = [quick_hit_summary(h) for h in (result or {}).get("results", [])][:limit]
        print(json.dumps({"count": len(hits), "results": hits}))
        return
    # AQL search built ONLY from structured params — never raw AQL from the caller.
    criteria = {}
    if params.get("repo"):
        criteria["repo"] = params["repo"]
    if params.get("pathPattern"):
        criteria["path"] = {"$match": params["pathPattern"]}
    if params.get("namePattern"):
        criteria["name"] = {"$match": params["namePattern"]}
    if params.get("createdAfter"):
        criteria["created"] = {"$gt": params["createdAfter"]}
    if not criteria:
        raise ValueError(
            "provide name (quick search) or at least one of repo, pathPattern, "
            "namePattern, createdAfter (AQL search)")
    aql = (
        "items.find(" + json.dumps(criteria, separators=(",", ":")) + ")"
        '.include("repo","path","name","size","created")'
        f".limit({limit})"
    )
    result = request("POST", "/search/aql", text_body=aql)
    items = [aql_item_summary(i) for i in (result or {}).get("results", [])]
    print(json.dumps({"count": len(items), "results": items}))


def get_artifact_info():
    repo = params.get("repo")
    path = params.get("path")
    suffix = storage_path(repo, path)
    info = request("GET", suffix) or {}
    checksums = info.get("checksums") or {}
    size = info.get("size")
    try:
        size = int(size)
    except (TypeError, ValueError):
        pass
    out = {
        "repo": info.get("repo"),
        "path": info.get("path"),
        "size": size,
        "mimeType": info.get("mimeType"),
        "created": info.get("created"),
        "lastModified": info.get("lastModified"),
        "downloadUri": info.get("downloadUri"),
        "checksums": {
            "sha256": checksums.get("sha256"),
            "sha1": checksums.get("sha1"),
            "md5": checksums.get("md5"),
        },
    }
    if str(params.get("stats")).lower() == "true":
        stats = request("GET", suffix, raw_query="stats") or {}
        out["downloadCount"] = stats.get("downloadCount")
        out["lastDownloaded"] = stats.get("lastDownloaded")
    print(json.dumps(out))


def get_item_properties():
    repo = params.get("repo")
    path = params.get("path")
    suffix = storage_path(repo, path)
    try:
        result = request("GET", suffix, raw_query="properties") or {}
    except ApiError as e:
        # 404 covers both "item has no properties" and "item does not exist" — only the
        # former gets the friendly empty result; a missing item stays an error.
        if e.code == 404 and "propert" in str(e).lower():
            print(json.dumps({"repo": repo, "path": path, "properties": {},
                              "note": "no properties set"}))
            return
        raise
    print(json.dumps({"repo": repo, "path": path,
                      "properties": result.get("properties") or {}}))


def list_builds():
    build_name = params.get("buildName")
    if build_name:
        check_no_dots(build_name, "buildName")
        result = request("GET", f"/build/{quote_seg(build_name)}") or {}
        builds = [{
            "number": urllib.parse.unquote((b.get("uri") or "").lstrip("/")),
            "started": b.get("started"),
        } for b in result.get("buildsNumbers") or []]
        print(json.dumps({"buildName": build_name, "count": len(builds), "builds": builds}))
        return
    try:
        result = request("GET", "/build") or {}
    except ApiError as e:
        if e.code == 404:  # Artifactory returns 404 when no builds exist
            print(json.dumps({"count": 0, "builds": []}))
            return
        raise
    builds = [{
        "name": urllib.parse.unquote((b.get("uri") or "").lstrip("/")),
        "lastBuildTime": b.get("lastBuildTime"),
    } for b in result.get("builds") or []]
    print(json.dumps({"count": len(builds), "builds": builds}))


def get_storage_summary():
    try:
        result = request("GET", "/storageinfo") or {}
    except ApiError as e:
        if e.code == 403:
            raise RuntimeError(
                "storage summary requires an admin or system:info-scoped token") from e
        raise
    repos = [storage_repo_summary(r) for r in result.get("repositoriesSummaryList") or []]
    print(json.dumps({"count": len(repos), "repositories": repos}))


def set_item_properties():
    repo = params.get("repo")
    path = params.get("path")
    properties = params.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise ValueError("properties required (object of key/value pairs)")
    suffix = storage_path(repo, path)
    pairs = ";".join(
        f"{prop_component(k)}={prop_component(v)}" for k, v in properties.items()
    )
    # Artifactory applies folder properties recursively by default; opt out unless asked.
    recursive = "1" if str(params.get("recursive")).lower() == "true" else "0"
    request("PUT", suffix, raw_query=f"properties={pairs}&recursive={recursive}")
    print(json.dumps({"set": True, "repo": repo, "path": path, "properties": properties}))


HANDLERS = {
    "artifactory.list_repositories": list_repositories,
    "artifactory.search_artifacts": search_artifacts,
    "artifactory.get_artifact_info": get_artifact_info,
    "artifactory.get_item_properties": get_item_properties,
    "artifactory.list_builds": list_builds,
    "artifactory.get_storage_summary": get_storage_summary,
    "artifactory.set_item_properties": set_item_properties,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and access_token):
        print(json.dumps({"error": "Missing Artifactory credentials: connect the Artifactory integration first (baseUrl, accessToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
