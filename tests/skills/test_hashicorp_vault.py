"""Offline mock-HTTP integration tests for the hashicorp-vault skill."""
import contextlib
import io
import json
import ssl
import sys
import urllib.error
import urllib.request

from mockhttp import run_tool, resp, err, check, patched, MockTransport, REPO


def _read_skill_source():
    with open(f"{REPO}/skills/hashicorp-vault/main.py", encoding="utf-8") as f:
        return f.read()


def run_tool_neterr(params):
    """Run the skill with every HTTP request raising URLError (network unreachable)."""
    src = _read_skill_source()

    def transport(req, *a, **k):
        raise urllib.error.URLError("connection refused")

    buf = io.StringIO()
    with patched(transport), contextlib.redirect_stdout(buf):
        exec(compile(src, "hashicorp-vault/main.py", "exec"), {"params": params})
    return json.loads(buf.getvalue().strip())


def run_tool_capture_ctx(params, steps):
    """Like run_tool, but also captures the ssl.SSLContext the skill's opener carries."""
    src = _read_skill_source()
    transport = MockTransport(steps)
    contexts = []
    real_urlopen = urllib.request.urlopen
    real_open = urllib.request.OpenerDirector.open

    def opener_open(self, req, *a, **k):
        for h in self.handlers:
            if isinstance(h, urllib.request.HTTPSHandler):
                contexts.append(getattr(h, "_context", None))
        return transport(req)

    urllib.request.urlopen = transport
    urllib.request.OpenerDirector.open = opener_open
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "hashicorp-vault/main.py", "exec"), {"params": params})
    finally:
        urllib.request.urlopen = real_urlopen
        urllib.request.OpenerDirector.open = real_open
    return json.loads(buf.getvalue().strip()), transport.exchanges, contexts

BASE = "https://vault.example.com:8200"
TOK = "hvs.SECRET-TOKEN-VALUE"
ROLE_ID = "role-1234"
SECRET_ID = "sid-SECRET-VALUE"
CLIENT_TOK = "hvs.approle-client-token"
UA = "sophon-hashicorp-vault-skill"


def creds(**extra):
    p = {"baseUrl": BASE, "token": TOK}
    p.update(extra)
    return p


def approle_creds(**extra):
    p = {"baseUrl": BASE, "roleId": ROLE_ID, "secretId": SECRET_ID}
    p.update(extra)
    return p


def login_resp():
    return resp(200, body={"auth": {"client_token": CLIENT_TOK,
                                    "accessor": "acc1", "policies": ["default"]}})


ok = True

# ---------------------------------------------------------------------------
# 1. vault.lookup_token — static-token auth exactness + shaping
# ---------------------------------------------------------------------------
print("scenario: lookup_token static-token auth exactness")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.lookup_token"), [
    resp(200, body={"data": {"id": TOK, "accessor": "acc-raw",
                             "display_name": "token-sophon", "policies": ["default", "ro"],
                             "ttl": 3600, "expire_time": "2026-08-01T00:00:00Z",
                             "num_uses": 0, "meta": None}}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/v1/auth/token/lookup-self", ex[0].url)
ok &= check("X-Vault-Token header exact", ex[0].headers.get("x-vault-token") == TOK,
            str(ex[0].headers))
ok &= check("no namespace header when unset", "x-vault-namespace" not in ex[0].headers,
            str(ex[0].headers))
ok &= check("User-Agent", ex[0].headers.get("user-agent") == UA, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("shaped fields",
            out == {"display_name": "token-sophon", "policies": ["default", "ro"],
                    "ttl": 3600, "expire_time": "2026-08-01T00:00:00Z"}, str(out))
ok &= check("token value never echoed (id/accessor stripped)",
            TOK not in json.dumps(out) and "acc-raw" not in json.dumps(out), json.dumps(out))

# ---------------------------------------------------------------------------
# 2. AppRole login flow — POST body byte-exact, client_token reused (write body)
# ---------------------------------------------------------------------------
print("scenario: AppRole login then list_mounts")
out, ex = run_tool("hashicorp-vault", approle_creds(tool="vault.list_mounts"), [
    login_resp(),
    resp(200, body={"request_id": "r1", "data": {
        "secret/": {"type": "kv", "description": "KV v2 store",
                    "config": {"default_lease_ttl": 0, "max_lease_ttl": 0},
                    "options": {"version": "2"}, "accessor": "kv_123"},
        "cubbyhole/": {"type": "cubbyhole", "description": "per-token private secret storage",
                       "config": {}},
    }}),
])
ok &= check("two requests (login + mounts)", len(ex) == 2, repr(ex))
ok &= check("login POST to approle endpoint",
            ex[0].method == "POST" and ex[0].url == f"{BASE}/v1/auth/approle/login",
            f"{ex[0].method} {ex[0].url}")
ok &= check("login body byte-exact",
            ex[0].body == '{"role_id": "role-1234", "secret_id": "sid-SECRET-VALUE"}',
            str(ex[0].body))
ok &= check("login Content-Type json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("no X-Vault-Token on login", "x-vault-token" not in ex[0].headers,
            str(ex[0].headers))
ok &= check("mounts GET uses client_token from login",
            ex[1].headers.get("x-vault-token") == CLIENT_TOK, str(ex[1].headers))
ok &= check("mounts URL byte-exact", ex[1].url == f"{BASE}/v1/sys/mounts", ex[1].url)
ok &= check("count == 2", out.get("count") == 2, str(out))
ok &= check("mounts shaped (config noise trimmed)",
            {"path": "secret/", "type": "kv", "description": "KV v2 store"} in out["mounts"]
            and all("config" not in m and "accessor" not in m and "options" not in m
                    for m in out["mounts"]), str(out))
ok &= check("secretId not leaked in output", SECRET_ID not in json.dumps(out),
            json.dumps(out))

# ---------------------------------------------------------------------------
# 3. Namespace header on every call (including AppRole login)
# ---------------------------------------------------------------------------
print("scenario: namespace header sent on login and API call")
out, ex = run_tool("hashicorp-vault",
                   approle_creds(tool="vault.lookup_token", namespace="admin/team1"), [
    login_resp(),
    resp(200, body={"data": {"display_name": "t", "policies": [], "ttl": 1,
                             "expire_time": None}}),
])
ok &= check("namespace on login", ex[0].headers.get("x-vault-namespace") == "admin/team1",
            str(ex[0].headers))
ok &= check("namespace on API call", ex[1].headers.get("x-vault-namespace") == "admin/team1",
            str(ex[1].headers))

print("scenario: namespace header on static-token call")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.lookup_token", namespace="ns1"), [
    resp(200, body={"data": {"display_name": "t", "policies": [], "ttl": 1,
                             "expire_time": None}}),
])
ok &= check("namespace on static-token call",
            ex[0].headers.get("x-vault-namespace") == "ns1", str(ex[0].headers))

# ---------------------------------------------------------------------------
# 4. vault.list_secrets — happy path (?list=true) + mount default
# ---------------------------------------------------------------------------
print("scenario: list_secrets happy path")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_secrets", path="apps"), [
    resp(200, body={"request_id": "r2", "data": {"keys": ["web/", "db", "api-key"]}}),
])
ok &= check("URL byte-exact (default mount, list=true)",
            ex[0].url == f"{BASE}/v1/secret/metadata/apps?list=true", ex[0].url)
ok &= check("shaped keys-only result",
            out == {"count": 3, "keys": ["web/", "db", "api-key"]}, str(out))

print("scenario: list_secrets at mount root with custom mount")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_secrets", mount="kv"), [
    resp(200, body={"data": {"keys": ["a"]}}),
])
ok &= check("root listing URL", ex[0].url == f"{BASE}/v1/kv/metadata?list=true", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out))

# ---------------------------------------------------------------------------
# 5. vault.get_secret_metadata — metadata only, NO values
# ---------------------------------------------------------------------------
print("scenario: get_secret_metadata happy path")
out, ex = run_tool("hashicorp-vault",
                   creds(tool="vault.get_secret_metadata", path="apps/web/db"), [
    resp(200, body={"data": {"created_time": "2026-01-01T00:00:00Z",
                             "updated_time": "2026-07-01T00:00:00Z",
                             "current_version": 4, "max_versions": 10,
                             "oldest_version": 1, "cas_required": False,
                             "custom_metadata": {"owner": "platform"},
                             "versions": {"4": {"created_time": "x", "destroyed": False}}}}),
])
ok &= check("URL byte-exact (nested path kept)",
            ex[0].url == f"{BASE}/v1/secret/metadata/apps/web/db", ex[0].url)
ok &= check("shaped metadata",
            out == {"path": "apps/web/db", "created_time": "2026-01-01T00:00:00Z",
                    "updated_time": "2026-07-01T00:00:00Z", "current_version": 4,
                    "max_versions": 10, "custom_metadata": {"owner": "platform"}},
            str(out))
ok &= check("raw versions map absent", "versions" not in out, str(out))

# ---------------------------------------------------------------------------
# 6. vault.read_secret — data.data + version info; version query param
# ---------------------------------------------------------------------------
print("scenario: read_secret happy path")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.read_secret", path="apps/web/db"), [
    resp(200, body={"data": {"data": {"username": "svc", "password": "p@ss"},
                             "metadata": {"version": 4,
                                          "created_time": "2026-07-01T00:00:00Z",
                                          "destroyed": False,
                                          "custom_metadata": None}}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/v1/secret/data/apps/web/db", ex[0].url)
ok &= check("secret values returned",
            out.get("data") == {"username": "svc", "password": "p@ss"}, str(out))
ok &= check("version info included",
            out.get("version") == 4 and out.get("created_time") == "2026-07-01T00:00:00Z"
            and out.get("destroyed") is False, str(out))

print("scenario: read_secret with explicit version")
out, ex = run_tool("hashicorp-vault",
                   creds(tool="vault.read_secret", path="apps/db", version=2), [
    resp(200, body={"data": {"data": {"k": "v"}, "metadata": {"version": 2}}}),
])
ok &= check("version query param",
            ex[0].url == f"{BASE}/v1/secret/data/apps/db?version=2", ex[0].url)

# ---------------------------------------------------------------------------
# 7. vault.list_policies — list mode and single-policy mode
# ---------------------------------------------------------------------------
print("scenario: list_policies list mode")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_policies"), [
    resp(200, body={"data": {"keys": ["default", "root", "ci-readonly"]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/v1/sys/policies/acl?list=true", ex[0].url)
ok &= check("policy names shaped",
            out == {"count": 3, "policies": ["default", "root", "ci-readonly"]}, str(out))

print("scenario: list_policies single-policy mode")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_policies", name="ci-readonly"), [
    resp(200, body={"data": {"name": "ci-readonly",
                             "policy": 'path "secret/metadata/*" { capabilities = ["read"] }'}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/v1/sys/policies/acl/ci-readonly",
            ex[0].url)
ok &= check("name + policy HCL returned",
            out == {"name": "ci-readonly",
                    "policy": 'path "secret/metadata/*" { capabilities = ["read"] }'},
            str(out))

# ---------------------------------------------------------------------------
# 8. vault.health — the by-design non-200 quirk
# ---------------------------------------------------------------------------
print("scenario: health 200 active node")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.health"), [
    resp(200, body={"initialized": True, "sealed": False, "standby": False,
                    "version": "1.17.2", "cluster_name": "vault-cluster-1",
                    "cluster_id": "raw-id", "server_time_utc": 1789000000}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/v1/sys/health", ex[0].url)
ok &= check("shaped with http_status 200",
            out == {"http_status": 200, "initialized": True, "sealed": False,
                    "standby": False, "version": "1.17.2",
                    "cluster_name": "vault-cluster-1"}, str(out))

print("scenario: health 503 sealed is a NORMAL result, not an error")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.health"), [
    err(503, body={"initialized": True, "sealed": True, "standby": False,
                   "version": "1.17.2", "cluster_name": "vault-cluster-1"}),
])
ok &= check("no error key", "error" not in out, str(out))
ok &= check("sealed body + status surfaced",
            out.get("http_status") == 503 and out.get("sealed") is True
            and out.get("initialized") is True, str(out))

print("scenario: health 429 unsealed standby is a NORMAL result")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.health"), [
    err(429, body={"initialized": True, "sealed": False, "standby": True,
                   "version": "1.17.2"}),
])
ok &= check("standby surfaced with status 429",
            "error" not in out and out.get("http_status") == 429
            and out.get("standby") is True, str(out))

print("scenario: health 501 not initialized is a NORMAL result")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.health"), [
    err(501, body={"initialized": False, "sealed": True, "standby": False}),
])
ok &= check("uninitialized surfaced with status 501",
            "error" not in out and out.get("http_status") == 501
            and out.get("initialized") is False, str(out))

print("scenario: health 472 DR secondary is a NORMAL result")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.health"), [
    err(472, body={"initialized": True, "sealed": False, "standby": False,
                   "replication_dr_mode": "secondary", "version": "1.17.2"}),
])
ok &= check("DR secondary surfaced with status 472",
            "error" not in out and out.get("http_status") == 472, str(out))

print("scenario: health 473 performance standby is a NORMAL result")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.health"), [
    err(473, body={"initialized": True, "sealed": False, "standby": True,
                   "performance_standby": True}),
])
ok &= check("performance standby surfaced with status 473",
            "error" not in out and out.get("http_status") == 473
            and out.get("standby") is True, str(out))

print("scenario: health under AppRole creds against a SEALED cluster -> no login attempted")
out, ex = run_tool("hashicorp-vault", approle_creds(tool="vault.health"), [
    err(503, body={"initialized": True, "sealed": True, "standby": False,
                   "version": "1.17.2", "cluster_name": "vault-cluster-1"}),
])
ok &= check("exactly one request (no AppRole login first)", len(ex) == 1, repr(ex))
ok &= check("request went straight to /v1/sys/health",
            ex[0].url == f"{BASE}/v1/sys/health", ex[0].url)
ok &= check("health is unauthenticated (no X-Vault-Token header)",
            "x-vault-token" not in ex[0].headers, str(ex[0].headers))
ok &= check("sealed state is a NORMAL result under AppRole",
            "error" not in out and out.get("http_status") == 503
            and out.get("sealed") is True, str(out))

print("scenario: health when Vault is unreachable -> friendly network error")
out = run_tool_neterr(creds(tool="vault.health"))
ok &= check("friendly 'Could not reach Vault' message",
            "Could not reach Vault" in out.get("error", ""), str(out))
ok &= check("no traceback leaked in network error",
            "Traceback" not in json.dumps(out) and "URLError" not in json.dumps(out),
            json.dumps(out))

# ---------------------------------------------------------------------------
# 9. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error with joined Vault errors")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_mounts"), [
    err(401, body={"errors": ["permission denied", "invalid token"]}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw)
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("Vault errors[] joined",
            "permission denied" in out["error"] and "invalid token" in out["error"],
            out.get("error", ""))
ok &= check("no traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw)
ok &= check("token not leaked in error output", TOK not in raw, raw)

print("scenario: 403 hints at missing capability")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.read_secret", path="apps/db"), [
    err(403, body={"errors": ["1 error occurred:\n\t* permission denied\n\n"]}),
])
ok &= check("403 with capability hint",
            "403" in out["error"] and "lacks capability" in out["error"],
            out.get("error", ""))

print("scenario: non-health 429 is an error including Retry-After")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_secrets", path="apps"), [
    err(429, body={"errors": ["rate limit exceeded"]}, headers={"Retry-After": "17"}),
])
ok &= check("429 surfaced as error", "error" in out and "429" in out["error"], str(out))
ok &= check("Retry-After included", "17" in out["error"], out.get("error", ""))
ok &= check("rate limit message included", "rate limit exceeded" in out["error"],
            out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_mounts"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out))

print("scenario: AppRole login failure -> friendly error, secret_id not leaked")
out, ex = run_tool("hashicorp-vault", approle_creds(tool="vault.lookup_token"), [
    err(400, body={"errors": ["invalid role or secret ID"]}),
])
raw = json.dumps(out)
ok &= check("login failure friendly",
            "AppRole login failed" in out.get("error", "") and "400" in out["error"]
            and "invalid role or secret ID" in out["error"], raw)
ok &= check("secretId not leaked", SECRET_ID not in raw, raw)

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.read_secret"), [])
ok &= check("path required error", out.get("error") == "path required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("hashicorp-vault", {"tool": "vault.list_mounts", "baseUrl": BASE}, [])
ok &= check("connect-first message names fields",
            "connect the HashiCorp Vault integration" in out.get("error", "")
            and "roleId" in out["error"] and "token" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: roleId without secretId is not enough")
out, ex = run_tool("hashicorp-vault",
                   {"tool": "vault.list_mounts", "baseUrl": BASE, "roleId": ROLE_ID}, [])
ok &= check("partial AppRole creds rejected", "error" in out and "connect" in out["error"],
            str(out))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: vault.nope", str(out))

# ---------------------------------------------------------------------------
# 10. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal secret path is rejected, no HTTP call")
out, ex = run_tool("hashicorp-vault",
                   creds(tool="vault.list_secrets", path="abc/../def?x=1"), [])
ok &= check("traversal path rejected",
            "error" in out and "'.' or '..'" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

out, ex = run_tool("hashicorp-vault",
                   creds(tool="vault.read_secret", path="abc/../def?x=1"), [])
ok &= check("read_secret traversal rejected too",
            "error" in out and "'.' or '..'" in out["error"] and len(ex) == 0, str(out))

print("scenario: special chars in path segments are percent-encoded")
out, ex = run_tool("hashicorp-vault",
                   creds(tool="vault.read_secret", path="team a/app#1"), [
    resp(200, body={"data": {"data": {}, "metadata": {"version": 1}}}),
])
ok &= check("segments quoted, slash separator kept",
            ex[0].url == f"{BASE}/v1/secret/data/team%20a/app%231", ex[0].url)

print("scenario: evil mount is rejected/encoded")
out, ex = run_tool("hashicorp-vault",
                   creds(tool="vault.list_secrets", mount="..", path="x"), [])
ok &= check("mount '..' rejected, no HTTP call",
            "error" in out and "'.' or '..'" in out["error"] and len(ex) == 0, str(out))

print("scenario: evil policy name is percent-encoded (no path escape)")
out, ex = run_tool("hashicorp-vault",
                   creds(tool="vault.list_policies", name="abc/../def?x=1"), [
    resp(200, body={"data": {"name": "x", "policy": "p"}}),
])
ok &= check("policy name fully quoted",
            ex[0].url == f"{BASE}/v1/sys/policies/acl/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' or '?' in URL",
            "../" not in ex[0].url and "?" not in ex[0].url, ex[0].url)

print("scenario: secrets never appear in error output")
out, ex = run_tool("hashicorp-vault", creds(tool="vault.list_policies"), [
    err(403, body={"errors": ["permission denied"]}),
])
ok &= check("token absent from error output", TOK not in json.dumps(out), json.dumps(out))

# ---------------------------------------------------------------------------
# 11. TLS verification toggle
# ---------------------------------------------------------------------------
print("scenario: default TLS context verifies certificates")
out, ex, ctxs = run_tool_capture_ctx(creds(tool="vault.lookup_token"), [
    resp(200, body={"data": {"display_name": "t", "policies": [], "ttl": 1,
                             "expire_time": None}}),
])
ok &= check("call still works with default context", "error" not in out, str(out))
ok &= check("ssl context captured", len(ctxs) == 1 and ctxs[0] is not None, repr(ctxs))
ok &= check("default verify_mode is CERT_REQUIRED",
            ctxs[0].verify_mode == ssl.CERT_REQUIRED, str(ctxs[0].verify_mode))
ok &= check("default check_hostname is True", ctxs[0].check_hostname is True,
            str(ctxs[0].check_hostname))

print("scenario: insecureSkipTlsVerify='true' disables verification")
out, ex, ctxs = run_tool_capture_ctx(
    creds(tool="vault.lookup_token", insecureSkipTlsVerify="true"), [
        resp(200, body={"data": {"display_name": "t", "policies": [], "ttl": 1,
                                 "expire_time": None}}),
    ])
ok &= check("call still works with verification skipped", "error" not in out, str(out))
ok &= check("verify_mode is CERT_NONE", ctxs and ctxs[0].verify_mode == ssl.CERT_NONE,
            repr(ctxs))
ok &= check("check_hostname is False", ctxs[0].check_hostname is False,
            str(ctxs[0].check_hostname))

# ---------------------------------------------------------------------------
# 12. Redirect guard — a 307 off the base host must not re-send the token
# ---------------------------------------------------------------------------
print("scenario: cross-host redirect is refused; same-host redirect is allowed")
src = _read_skill_source()
g = {"params": creds(tool="vault.nope")}  # unknown tool: defines module without HTTP calls
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, "hashicorp-vault/main.py", "exec"), g)
guard = g["_RedirectGuard"]()
redirect_req = urllib.request.Request(f"{BASE}/v1/sys/health",
                                      headers={"X-Vault-Token": TOK})
try:
    guard.redirect_request(redirect_req, None, 307, "Temporary Redirect", {},
                           "https://evil.example.com/v1/sys/health")
    cross_host_refused = False
    cross_host_msg = ""
except RuntimeError as e:
    cross_host_refused = True
    cross_host_msg = str(e)
ok &= check("cross-host redirect raises", cross_host_refused, "redirect was followed")
ok &= check("refusal message names the foreign host and is friendly",
            "evil.example.com" in cross_host_msg and TOK not in cross_host_msg,
            cross_host_msg)
same_host = guard.redirect_request(redirect_req, None, 307, "Temporary Redirect", {},
                                   f"{BASE}/v1/sys/health")
ok &= check("same-host redirect still followed",
            same_host is not None and same_host.full_url == f"{BASE}/v1/sys/health",
            repr(same_host))

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
