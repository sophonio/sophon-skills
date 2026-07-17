"""HashiCorp Vault integration skill — read-only visibility into a Vault cluster.

Pure standard library (urllib + ssl) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, token, roleId, secretId, namespace,
insecureSkipTlsVerify).

Auth supports two paths: a static token (sent as X-Vault-Token) or AppRole — we POST
role_id/secret_id to /v1/auth/approle/login and use the returned auth.client_token as
X-Vault-Token thereafter. An optional Vault Enterprise namespace is sent as X-Vault-Namespace on
every call. insecureSkipTlsVerify ('true') disables TLS verification for self-signed private
deployments (not recommended).

Quirk: GET /v1/sys/health returns non-200 status codes BY DESIGN (429 unsealed standby, 472 DR
secondary, 473 performance standby, 501 not initialized, 503 sealed) — vault.health treats those
as normal results and includes the HTTP status code.
"""

import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
static_token = params.get("token") or ""
role_id = params.get("roleId") or ""
secret_id = params.get("secretId") or ""
namespace = params.get("namespace") or ""
insecure = str(params.get("insecureSkipTlsVerify") or "").strip().lower() == "true"

USER_AGENT = "sophon-hashicorp-vault-skill"
HEALTH_STATUSES = (429, 472, 473, 501, 503)


def ssl_context():
    """Build an SSL context; skip verification only when explicitly requested."""
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class _RedirectGuard(urllib.request.HTTPRedirectHandler):
    """Refuse redirects that leave the Vault base host.

    Vault standby nodes emit 307 redirects to the active node; urllib would re-send every
    header — including X-Vault-Token — to whatever Location the server returns. Only follow
    redirects that stay on the configured baseUrl host so the token can never leak elsewhere.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlparse(urllib.parse.urljoin(req.full_url, newurl))
        if target.netloc != urllib.parse.urlparse(base_url).netloc:
            raise RuntimeError(
                f"Vault redirected ({code}) off the configured base host to "
                f"'{target.netloc or newurl}' — refusing to follow. If this is a standby "
                "node, point baseUrl at the active node (or a load balancer).")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(req):
    """Open a request with our SSL context and the cross-host redirect guard."""
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl_context()), _RedirectGuard())
    return opener.open(req)


def vault_error_message(detail):
    """Vault errors come as {"errors": ["..."]} — parse and join for a friendly message."""
    try:
        parsed = json.loads(detail)
        errors = parsed.get("errors") if isinstance(parsed, dict) else None
        if isinstance(errors, list) and errors:
            return "; ".join(str(x) for x in errors)
    except (ValueError, TypeError):
        pass
    return detail


def get_token():
    """Return the static token, or log in via AppRole to obtain a client token."""
    if static_token:
        return static_token
    url = f"{base_url}/v1/auth/approle/login"
    body = json.dumps({"role_id": role_id, "secret_id": secret_id}).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if namespace:
        headers["X-Vault-Namespace"] = namespace
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with open_url(req) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(
            f"AppRole login failed ({e.code}): {vault_error_message(detail)}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Vault: {e.reason}") from e
    client_token = (data.get("auth") or {}).get("client_token")
    if not client_token:
        raise RuntimeError("No client_token in AppRole login response")
    return client_token


def request(method, path, token, data=None, query=None, tolerate=()):
    """Make a request to the Vault HTTP API.

    `token` may be None for unauthenticated endpoints (/v1/sys/health) — then no X-Vault-Token
    header is sent. Returns parsed JSON (or None for 204/empty). When `tolerate` statuses are
    given (used by vault.health, whose non-200 codes are by design), returns
    (parsed_body, http_status) instead.
    """
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["X-Vault-Token"] = token
    if namespace:
        headers["X-Vault-Namespace"] = namespace
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with open_url(req) as resp:
            raw = resp.read().decode()
            parsed = json.loads(raw) if raw else None
            return (parsed, resp.status) if tolerate else parsed
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        if e.code in tolerate:
            try:
                parsed = json.loads(detail) if detail else None
            except (ValueError, TypeError):
                parsed = None
            return (parsed, e.code)
        msg = vault_error_message(detail)
        if e.code == 403:
            msg = f"{msg} (the token lacks capability on this path)" if msg else \
                "permission denied (the token lacks capability on this path)"
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                msg = f"{msg} (Retry-After: {retry_after}s)"
        raise RuntimeError(f"Vault API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Vault: {e.reason}") from e


def seg(value, label):
    """URL-encode a single path segment, rejecting traversal segments."""
    s = str(value)
    if s in (".", ".."):
        raise ValueError(f"{label} must not be '.' or '..'")
    return urllib.parse.quote(s, safe="")


def secret_path(value, label):
    """Quote a slash-separated Vault path segment-by-segment, rejecting '.'/'..' segments."""
    parts = [p for p in str(value).split("/") if p != ""]
    if not parts:
        raise ValueError(f"{label} is required")
    for p in parts:
        if p in (".", ".."):
            raise ValueError(f"{label} must not contain '.' or '..' segments")
    return "/".join(urllib.parse.quote(p, safe="") for p in parts)


# --- Tool handlers ---------------------------------------------------------

def health():
    # /v1/sys/health is unauthenticated by design — never acquire a token first, or an AppRole
    # login against a sealed/uninitialized cluster would fail before we could report exactly
    # the state this tool exists to report.
    body, status = request("GET", "/v1/sys/health", None, tolerate=HEALTH_STATUSES)
    body = body if isinstance(body, dict) else {}
    print(json.dumps({
        "http_status": status,
        "initialized": body.get("initialized"),
        "sealed": body.get("sealed"),
        "standby": body.get("standby"),
        "version": body.get("version"),
        "cluster_name": body.get("cluster_name"),
    }))


def list_mounts():
    token = get_token()
    result = request("GET", "/v1/sys/mounts", token) or {}
    data = result.get("data")
    if not isinstance(data, dict):
        data = {k: v for k, v in result.items() if isinstance(v, dict) and "type" in v}
    mounts = [{
        "path": path,
        "type": m.get("type"),
        "description": m.get("description"),
    } for path, m in data.items()]
    print(json.dumps({"count": len(mounts), "mounts": mounts}))


def list_secrets():
    # Validate params-derived input BEFORE acquiring a token: under AppRole, a rejected call
    # must not burn a login (and possibly a limited-use secret_id) on a doomed request.
    mount = secret_path(params.get("mount") or "secret", "mount")
    raw_path = str(params.get("path") or "")
    suffix = f"/{secret_path(raw_path, 'path')}" if raw_path.strip("/") else ""
    token = get_token()
    result = request("GET", f"/v1/{mount}/metadata{suffix}", token, query={"list": "true"})
    keys = ((result or {}).get("data") or {}).get("keys") or []
    print(json.dumps({"count": len(keys), "keys": keys}))


def get_secret_metadata():
    mount = secret_path(params.get("mount") or "secret", "mount")
    raw_path = params.get("path")
    if not raw_path:
        raise ValueError("path required")
    quoted_path = secret_path(raw_path, "path")
    token = get_token()
    result = request("GET", f"/v1/{mount}/metadata/{quoted_path}", token)
    d = (result or {}).get("data") or {}
    print(json.dumps({
        "path": raw_path,
        "created_time": d.get("created_time"),
        "updated_time": d.get("updated_time"),
        "current_version": d.get("current_version"),
        "max_versions": d.get("max_versions"),
        "custom_metadata": d.get("custom_metadata"),
    }))


def read_secret():
    mount = secret_path(params.get("mount") or "secret", "mount")
    raw_path = params.get("path")
    if not raw_path:
        raise ValueError("path required")
    quoted_path = secret_path(raw_path, "path")
    token = get_token()
    result = request("GET", f"/v1/{mount}/data/{quoted_path}", token,
                     query={"version": params.get("version")})
    d = (result or {}).get("data") or {}
    meta = d.get("metadata") or {}
    print(json.dumps({
        "path": raw_path,
        "data": d.get("data") or {},
        "version": meta.get("version"),
        "created_time": meta.get("created_time"),
        "destroyed": meta.get("destroyed"),
    }))


def list_policies():
    name = params.get("name")
    if name:
        quoted_name = seg(name, "name")
        token = get_token()
        result = request("GET", f"/v1/sys/policies/acl/{quoted_name}", token)
        d = (result or {}).get("data") or {}
        print(json.dumps({"name": d.get("name") or name, "policy": d.get("policy")}))
    else:
        token = get_token()
        result = request("GET", "/v1/sys/policies/acl", token, query={"list": "true"})
        keys = ((result or {}).get("data") or {}).get("keys") or []
        print(json.dumps({"count": len(keys), "policies": keys}))


def lookup_token():
    token = get_token()
    result = request("GET", "/v1/auth/token/lookup-self", token)
    d = (result or {}).get("data") or {}
    # Never echo the token itself (or its accessor) back into the agent context.
    print(json.dumps({
        "display_name": d.get("display_name"),
        "policies": d.get("policies"),
        "ttl": d.get("ttl"),
        "expire_time": d.get("expire_time"),
    }))


HANDLERS = {
    "vault.health": health,
    "vault.list_mounts": list_mounts,
    "vault.list_secrets": list_secrets,
    "vault.get_secret_metadata": get_secret_metadata,
    "vault.read_secret": read_secret,
    "vault.list_policies": list_policies,
    "vault.lookup_token": lookup_token,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and (static_token or (role_id and secret_id))):
        print(json.dumps({"error": "Missing Vault credentials: connect the HashiCorp Vault "
                                   "integration first (baseUrl plus either token, or roleId "
                                   "and secretId)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
