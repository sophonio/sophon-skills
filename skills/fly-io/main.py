"""Fly.io integration skill — talks to the Fly.io Machines REST API with an app-scoped API token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (token, appName).

Image-building deploys are intentionally not supported: creating a machine from source requires a
remote builder, which is outside the scope of this stdlib-only skill. Provision machines from a
prebuilt image with the Fly CLI or the raw API, then manage their lifecycle here.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")
API_BASE = "https://api.machines.dev/v1"

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "sophon-fly-io-skill",
    "Accept": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Fly Machines API. Returns parsed JSON (or None for 204)."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Fly API error {e.code}: {detail}") from e


def resolve_app():
    app = params.get("appName") or ""
    if not app:
        raise ValueError("appName required (pass it or configure it on the connection)")
    return app


def require_machine_id():
    machine_id = params.get("machineId") or ""
    if not machine_id:
        raise ValueError("machineId required")
    return machine_id


def machine_summary(machine):
    machine = machine or {}
    config = machine.get("config") or {}
    return {
        "id": machine.get("id"),
        "name": machine.get("name"),
        "state": machine.get("state"),
        "region": machine.get("region"),
        "image": (machine.get("image_ref") or {}).get("tag") or config.get("image"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_machines():
    app = resolve_app()
    result = request("GET", f"/apps/{urllib.parse.quote(app)}/machines")
    machines = [machine_summary(m) for m in (result or [])]
    print(json.dumps({"count": len(machines), "machines": machines}))


def get_machine():
    app = resolve_app()
    machine_id = require_machine_id()
    machine = request("GET", f"/apps/{urllib.parse.quote(app)}/machines/{urllib.parse.quote(machine_id)}")
    print(json.dumps(machine_summary(machine)))


def start_machine():
    app = resolve_app()
    machine_id = require_machine_id()
    result = request("POST", f"/apps/{urllib.parse.quote(app)}/machines/{urllib.parse.quote(machine_id)}/start")
    print(json.dumps({"id": machine_id, "requested": "start", "result": result}))


def stop_machine():
    app = resolve_app()
    machine_id = require_machine_id()
    result = request("POST", f"/apps/{urllib.parse.quote(app)}/machines/{urllib.parse.quote(machine_id)}/stop")
    print(json.dumps({"id": machine_id, "requested": "stop", "result": result}))


def restart_machine():
    app = resolve_app()
    machine_id = require_machine_id()
    result = request("POST", f"/apps/{urllib.parse.quote(app)}/machines/{urllib.parse.quote(machine_id)}/restart")
    print(json.dumps({"id": machine_id, "requested": "restart", "result": result}))


def destroy_machine():
    app = resolve_app()
    machine_id = require_machine_id()
    query = {}
    if params.get("force"):
        query["force"] = "true"
    request("DELETE", f"/apps/{urllib.parse.quote(app)}/machines/{urllib.parse.quote(machine_id)}", query=query)
    print(json.dumps({"id": machine_id, "destroyed": True}))


HANDLERS = {
    "fly.list_machines": list_machines,
    "fly.get_machine": get_machine,
    "fly.start_machine": start_machine,
    "fly.stop_machine": stop_machine,
    "fly.restart_machine": restart_machine,
    "fly.destroy_machine": destroy_machine,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not token:
        print(json.dumps({"error": "Missing Fly credential: connect the Fly.io integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
