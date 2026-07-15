"""Dependency audit skill — scan lockfiles for known vulnerabilities via the OSV.dev API.

Pure standard library (json, tomllib, urllib) so it runs unchanged in the alpine Python
sandbox with no pip dependencies and no authentication. `params` is injected as a global by the
Sophon runtime and carries the tool name plus the tool's call arguments.
"""

import json
import tomllib
import urllib.request
import urllib.error

tool_name = params.get("tool", "")

OSV_BASE = "https://api.osv.dev"
MAX_QUERIES = 200

# Map the filename hint to a parser key + default OSV ecosystem.
FILE_ECOSYSTEM = {
    "requirements.txt": "PyPI",
    "package-lock.json": "npm",
    "cargo.lock": "crates.io",
    "go.mod": "Go",
}


def post_json(path, payload):
    """POST a JSON body to the OSV API and return the parsed JSON response."""
    url = f"{OSV_BASE}{path}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "sophon-dependency-audit-skill",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"OSV API error {e.code}: {detail}") from e


# --- Lockfile parsers ------------------------------------------------------
# Each returns a list of {"name": ..., "version": ...} dicts.

def parse_requirements(content):
    """Parse a pip requirements.txt: lines like name==version (skip comments/-e/URLs/options)."""
    packages = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Drop inline comments and environment markers.
        line = line.split(" #", 1)[0].strip()
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        # Skip options (-e, -r, -c, --hash, ...), editables, and direct URLs/VCS.
        if line.startswith("-") or "://" in line or line.startswith("git+"):
            continue
        if "==" not in line:
            continue
        name_part, version = line.split("==", 1)
        version = version.strip().split(" ", 1)[0].strip()
        # Strip extras and env-marker leftovers from the name: e.g. requests[security]
        name = name_part.split("[", 1)[0].strip()
        if name and version:
            packages.append({"name": name, "version": version})
    return packages


def parse_package_lock(content):
    """Parse an npm package-lock.json (v2/3 'packages' map, or v1 'dependencies' tree)."""
    data = json.loads(content)
    packages = []
    seen = set()

    def add(name, version):
        if name and version and (name, version) not in seen:
            seen.add((name, version))
            packages.append({"name": name, "version": version})

    pkgs = data.get("packages")
    if isinstance(pkgs, dict):
        # lockfileVersion 2/3: keys are paths like "node_modules/foo"; "" is the root project.
        for path, meta in pkgs.items():
            if not path or not isinstance(meta, dict):
                continue
            marker = "node_modules/"
            idx = path.rfind(marker)
            name = path[idx + len(marker):] if idx != -1 else path
            add(name, meta.get("version"))
    deps = data.get("dependencies")
    if isinstance(deps, dict):
        # lockfileVersion 1: nested dependency tree.
        def walk(tree):
            for name, meta in tree.items():
                if isinstance(meta, dict):
                    add(name, meta.get("version"))
                    sub = meta.get("dependencies")
                    if isinstance(sub, dict):
                        walk(sub)
        walk(deps)
    return packages


def parse_cargo_lock(content):
    """Parse a Cargo.lock via tomllib: [[package]] entries with name/version."""
    data = tomllib.loads(content)
    packages = []
    for pkg in data.get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
        if name and version:
            packages.append({"name": name, "version": version})
    return packages


def parse_go_mod(content):
    """Parse a go.mod: single-line `require mod ver` and `require ( ... )` blocks."""
    packages = []
    in_block = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        # Strip inline comments (e.g. "// indirect").
        line = line.split("//", 1)[0].strip()
        if not line:
            continue
        if in_block:
            if line == ")":
                in_block = False
                continue
            _add_go_require(packages, line)
            continue
        if line.startswith("require"):
            rest = line[len("require"):].strip()
            if rest == "(":
                in_block = True
            elif rest.startswith("("):
                # e.g. "require ( mod ver" on one line
                _add_go_require(packages, rest[1:].strip())
            elif rest:
                _add_go_require(packages, rest)
    return packages


def _add_go_require(packages, line):
    parts = line.split()
    if len(parts) >= 2:
        name = parts[0]
        version = parts[1]  # keep original, incl. leading 'v'
        if name and version:
            packages.append({"name": name, "version": version})


PARSERS = {
    "requirements.txt": parse_requirements,
    "package-lock.json": parse_package_lock,
    "cargo.lock": parse_cargo_lock,
    "go.mod": parse_go_mod,
}


def detect_kind(filename):
    """Return the lockfile kind key from a filename hint, or None if unrecognized."""
    if not filename:
        return None
    base = filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return base if base in PARSERS else None


# --- Tool handlers ---------------------------------------------------------

def audit():
    content = params.get("content")
    if not content or not str(content).strip():
        print(json.dumps({"error": "content is required (the lockfile text to scan)"}))
        return
    filename = params.get("filename", "")
    kind = detect_kind(filename)
    if kind is None:
        print(json.dumps({"error": (
            "Unrecognized filename. Supported: requirements.txt, package-lock.json, "
            "Cargo.lock, go.mod"
        )}))
        return

    try:
        packages = PARSERS[kind](content)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, ValueError) as e:
        print(json.dumps({"error": f"Failed to parse {kind}: {e}"}))
        return

    ecosystem = params.get("ecosystem") or FILE_ECOSYSTEM[kind]

    truncated = False
    if len(packages) > MAX_QUERIES:
        packages = packages[:MAX_QUERIES]
        truncated = True

    if not packages:
        print(json.dumps({"scanned": 0, "vulnerable": 0, "packages": [], "truncated": False}))
        return

    queries = [
        {"package": {"name": p["name"], "ecosystem": ecosystem}, "version": p["version"]}
        for p in packages
    ]
    result = post_json("/v1/querybatch", {"queries": queries})
    batch = result.get("results", [])

    vulnerable = []
    for pkg, res in zip(packages, batch):
        vulns = (res or {}).get("vulns") or []
        if not vulns:
            continue
        vulnerable.append({
            "name": pkg["name"],
            "version": pkg["version"],
            "vulns": [{
                "id": v.get("id"),
                "modified": v.get("modified"),
            } for v in vulns],
        })

    out = {
        "ecosystem": ecosystem,
        "scanned": len(packages),
        "vulnerable": len(vulnerable),
        "packages": vulnerable,
        "truncated": truncated,
    }
    if truncated:
        out["note"] = f"Only the first {MAX_QUERIES} packages were queried."
    print(json.dumps(out))


def query_package():
    ecosystem = params.get("ecosystem", "")
    name = params.get("name", "")
    version = params.get("version", "")
    if not ecosystem or not name or not version:
        print(json.dumps({"error": "ecosystem, name, and version are all required"}))
        return
    payload = {"package": {"name": name, "ecosystem": ecosystem}, "version": version}
    result = post_json("/v1/query", payload)
    vulns = result.get("vulns") or []
    print(json.dumps({
        "name": name,
        "version": version,
        "ecosystem": ecosystem,
        "vulnerable": len(vulns) > 0,
        "vulns": [{
            "id": v.get("id"),
            "summary": v.get("summary"),
            "aliases": v.get("aliases"),
            "modified": v.get("modified"),
        } for v in vulns],
    }))


HANDLERS = {
    "deps.audit": audit,
    "deps.query_package": query_package,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
