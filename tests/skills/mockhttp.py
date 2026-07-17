"""Mock-HTTP harness for Sophon skills.

Patches urllib.request.urlopen AND urllib.request.OpenerDirector.open so every HTTP call a
skill makes is served from a scripted response queue (order-based) while the full request
(method, URL, headers, body) is recorded for assertions. No network, no credentials.

Usage in a test file:

    from mockhttp import run_tool, resp, err

    out, ex = run_tool("okta", {"tool": "okta.search_users", "baseUrl": "https://acme.okta.com",
                                "apiToken": "tok"},
                       [resp(200, body=[{"id": "u1", "status": "ACTIVE",
                                         "profile": {"firstName": "A", "lastName": "B",
                                                     "email": "a@b.c", "login": "a@b.c"}}])])
    assert ex[0].headers["authorization"] == "SSWS tok"
    assert out["count"] == 1

resp(status, body=..., headers={...}) — body may be dict/list (JSON-encoded), str, or bytes.
err(status, body=..., headers={...})  — raises urllib.error.HTTPError with that payload.
Each queue entry serves exactly one request, in order. Extra/missing requests fail loudly.
"""
import contextlib
import email.message
import io
import json
import urllib.error
import urllib.request

import pathlib

REPO = str(pathlib.Path(__file__).resolve().parents[2])


class Exchange:
    def __init__(self, req):
        self.method = req.get_method()
        self.url = req.full_url
        self.headers = {k.lower(): v for k, v in req.header_items()}
        self.body = req.data.decode("utf-8", "replace") if req.data else None

    @property
    def json(self):
        return json.loads(self.body) if self.body else None

    def __repr__(self):
        return f"<{self.method} {self.url}>"


def _encode_body(body):
    if body is None:
        return b""
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode()
    return json.dumps(body).encode()


def _headers_obj(headers):
    msg = email.message.Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    return msg


def resp(status=200, body=None, headers=None):
    return {"kind": "resp", "status": status, "body": _encode_body(body),
            "headers": _headers_obj(headers)}


def err(status, body=None, headers=None):
    return {"kind": "err", "status": status, "body": _encode_body(body),
            "headers": _headers_obj(headers)}


class _FakeResponse:
    def __init__(self, step, url):
        self._buf = io.BytesIO(step["body"])
        self.status = self.code = step["status"]
        self.headers = step["headers"]
        self.url = url

    def read(self, *a):
        return self._buf.read(*a)

    def getcode(self):
        return self.code

    def info(self):
        return self.headers

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class MockTransport:
    def __init__(self, steps):
        self.steps = list(steps)
        self.exchanges = []

    def __call__(self, req, *args, **kwargs):
        if isinstance(req, str):
            req = urllib.request.Request(req)
        self.exchanges.append(Exchange(req))
        if not self.steps:
            raise AssertionError(f"Unexpected extra HTTP request: {self.exchanges[-1]!r}")
        step = self.steps.pop(0)
        if step["kind"] == "err":
            raise urllib.error.HTTPError(req.full_url, step["status"], f"HTTP {step['status']}",
                                         step["headers"], io.BytesIO(step["body"]))
        return _FakeResponse(step, req.full_url)


@contextlib.contextmanager
def patched(transport):
    real_urlopen = urllib.request.urlopen
    real_open = urllib.request.OpenerDirector.open

    def opener_open(self, req, *a, **k):
        return transport(req)

    urllib.request.urlopen = transport
    urllib.request.OpenerDirector.open = opener_open
    try:
        yield
    finally:
        urllib.request.urlopen = real_urlopen
        urllib.request.OpenerDirector.open = real_open


def run_tool(skill, params, steps, expect_all_consumed=True):
    """Execute a skill tool with scripted HTTP. Returns (stdout_parsed, exchanges)."""
    src = open(f"{REPO}/skills/{skill}/main.py", encoding="utf-8").read()
    transport = MockTransport(steps)
    buf = io.StringIO()
    with patched(transport), contextlib.redirect_stdout(buf):
        exec(compile(src, f"{skill}/main.py", "exec"), {"params": params})
    raw = buf.getvalue().strip()
    try:
        out = json.loads(raw)
    except ValueError:
        raise AssertionError(f"skill printed non-JSON: {raw[:400]}")
    if expect_all_consumed and transport.steps:
        raise AssertionError(
            f"{len(transport.steps)} scripted response(s) never requested; "
            f"exchanges made: {transport.exchanges!r}")
    return out, transport.exchanges


def check(label, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + (f" — {detail}" if not cond and detail else ""))
    return bool(cond)
