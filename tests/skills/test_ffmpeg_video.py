"""Offline tests for the ffmpeg-video skill: no FFmpeg needed.

Covers the tool surface, the bootstrap's constraints (Sophon prepends a preamble and pip-installs
whatever an import line names), the Docker and unknown-backend refusals, skill-home discovery
with decoys and tampering, interpreter selection and the re-exec path, the path policy, argument
handling, argv parity between the pre-filled and the full upstream contract, failure mapping,
result compaction and the generator check.

Plain script (no pytest), `ok  ` / `FAIL` lines, exit 1 on any failure: python tests/skills/test_ffmpeg_video.py
"""
import ast
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sandboxsim import PREAMBLE, REPO, FakeDataDir, base_env, resolver_packages, run_process  # noqa: E402

SKILL = REPO / "skills" / "ffmpeg-video"
MAIN = SKILL / "main.py"
VENDOR = SKILL / "vendor" / "ffmpeg-skill"
MANIFEST = json.loads((SKILL / "manifest.json").read_text(encoding="utf-8"))
TOOL_MAP = json.loads((SKILL / "lib" / "tool-map.json").read_text(encoding="utf-8"))
WINDOWS = os.name == "nt"

GROUP_RISK = {
    "inspect": {"probe": "none", "cropdetect": "none", "check": "none", "scenes": "low", "look": "low", "report": "low"},
    "make": dict.fromkeys(["insert", "background", "sequence", "waveform"], "low"),
    "edit": dict.fromkeys(["cut", "join", "silence", "broll", "multicam", "sync", "grid", "pad", "freeze", "loop",
                           "metadata"], "low"),
    "adjust": dict.fromkeys(["fit", "crop", "color", "speedramp", "reverse", "straighten", "sphere", "stabilize",
                             "deinterlace", "denoise", "redact"], "low"),
    "layer": dict.fromkeys(["caption", "graphics", "overlay"], "low"),
    "mix": dict.fromkeys(["audio", "loudness"], "low"),
    "deliver": dict.fromkeys(["export", "proxy"], "low"),
    "project": dict.fromkeys(["render", "batch"], "medium"),
    "setup": {"doctor": "none", "contract": "none", "verify": "low"},
}
AGENT_PINS = ["ffmpeg.inspect.check", "ffmpeg.inspect.look", "ffmpeg.inspect.probe", "ffmpeg.make.insert",
              "ffmpeg.project.render", "ffmpeg.setup.doctor"]

ok = True


def check(name, cond, detail=""):
    global ok
    print(f"{'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  -- {str(detail)[:600]}"))
    ok &= bool(cond)
    return bool(cond)


def load_bridge():
    spec = importlib.util.spec_from_file_location("ffvideo_bridge", SKILL / "lib" / "bridge.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ffvideo_bridge"] = module
    spec.loader.exec_module(module)
    return module


bridge = load_bridge()


def sim_env(data, **extra):
    """A hermetic child environment: the user profile points into the fake data folder."""
    home = data.root / "userhome"
    home.mkdir(exist_ok=True)
    env = base_env({"HOME": str(home), "USERPROFILE": str(home)})
    env.update({k: str(v) for k, v in extra.items()})
    return env


def where_home(doc):
    for key in ("doctor", "result"):
        block = (doc or {}).get(key) or {}
        if isinstance(block, dict) and block.get("skillHome"):
            return block["skillHome"]
    return None


@contextlib.contextmanager
def call(tool, params, data, env=None):
    """An in-process bridge Call set up against the repo skill folder and a fake data folder."""
    saved = dict(os.environ)
    os.environ.update(env or {})
    c = bridge.Call(tool, params, str(SKILL), str(data.root), time.time(), os.getcwd(), "process")
    try:
        c.setup()
        c.server = bridge.load_server(c.home)
        bridge.prefill_specs(c.server, c.map)
        yield c
    finally:
        c.finish()
        os.environ.clear()
        os.environ.update(saved)


def outcome(tool, params, data, env=None, steps=("validate", "paths")):
    """Run validation and the path policy in-process; returns (args, None) or (None, BridgeError)."""
    with call(tool, params, data, env) as c:
        try:
            args = c.validate()
            if "paths" in steps:
                handler = c.entry.get("handler")
                if handler == "render":
                    args = c.prepare_render(args)
                elif handler == "batch":
                    args = c.prepare_batch(args)
                elif handler == "verify":
                    args = c.prepare_verify(args)
                else:
                    args = c.resolve_paths(args)
                c.check_overwrite(args)
            return args, None, c
        except bridge.BridgeError as exc:
            return None, exc, c


def code_of(result):
    return result[1].code if result[1] else None


def reason_of(result):
    return (result[1].extra or {}).get("reason") if result[1] else None


# ---------------------------------------------------------------------------------------------
print("scenario: tool surface")
tools = MANIFEST["tools"]
names = [t["name"] for t in tools]
check("44 tools", len(tools) == 44, len(tools))
check("names unique", len(set(names)) == len(names))
check("names are ffmpeg.<group>.<script>", all(re.fullmatch(r"ffmpeg\.[a-z]+\.[a-z]+", n) for n in names))
groups = {}
for t in tools:
    groups.setdefault(t["name"].split(".")[1], []).append(t)
check("every group has 15 or fewer tools", all(len(v) <= 15 for v in groups.values()), {k: len(v) for k, v in groups.items()})
risk_ok = all(GROUP_RISK.get(t["name"].split(".")[1], {}).get(t["name"].split(".")[2]) == t["riskLevel"] for t in tools)
check("group and risk match the plan's table", risk_ok and sum(len(v) for v in GROUP_RISK.values()) == 44,
      [(t["name"], t["riskLevel"]) for t in tools if GROUP_RISK.get(t["name"].split(".")[1], {}).get(t["name"].split(".")[2]) != t["riskLevel"]])
counts = {r: sum(1 for t in tools if t["riskLevel"] == r) for r in ("none", "low", "medium")}
check("risk totals 5 none / 37 low / 2 medium", counts == {"none": 5, "low": 37, "medium": 2}, counts)
check("agent pins exist", all(p in names for p in AGENT_PINS))
main_tree = ast.parse(MAIN.read_text(encoding="utf-8"))
consts = {}
for node in main_tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        try:
            consts[node.targets[0].id] = ast.literal_eval(node.value)
        except ValueError:
            pass
check("main.py TOOLS == manifest == tool map", consts.get("TOOLS") == names == list(TOOL_MAP["byName"]),
      (len(consts.get("TOOLS") or []), len(TOOL_MAP["byName"])))
check("SKILL_VERSION equals the manifest version", consts.get("SKILL_VERSION") == MANIFEST["version"])
wire = [n.replace(".", "_") for n in names]
check("wire names unique and at most 64 characters", len(set(wire)) == 44 and all(len(w) <= 64 for w in wire))
check("no tool collides with a Sophon built-in name",
      not set(names) & {"media.video", "media.image", "video.generate", "image.generate", "music.generate", "tts.file"})


def schema_problems(node, where):
    found = []
    if isinstance(node, dict):
        for bad in ("oneOf", "anyOf", "allOf", "$ref", "not"):
            if bad in node:
                found.append(f"{where}: {bad}")
        if isinstance(node.get("type"), list):
            found.append(f"{where}: type list")
        if node.get("type") == "array" and "items" not in node:
            found.append(f"{where}: array without items")
        if "enum" in node and not all(isinstance(v, str) for v in node["enum"]):
            found.append(f"{where}: non-string enum")
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                found += schema_problems(value, f"{where}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += schema_problems(value, f"{where}[{i}]")
    return found


problems = []
for t in tools:
    schema = t.get("parameters") or t.get("inputSchema") or t.get("schema") or {}
    problems += schema_problems(schema, t["name"])
    props = schema.get("properties") or {}
    if "tool" in props:
        problems.append(f"{t['name']}: a parameter named tool")
    if not set(schema.get("required") or []) <= set(props):
        problems.append(f"{t['name']}: required names a missing property")
    if schema.get("type") != "object":
        problems.append(f"{t['name']}: top-level type is not object")
check("schemas stay in Sophon's safe subset", not problems, problems[:5])
check("manifest has no type key and no permissions block", "type" not in MANIFEST and "permissions" not in MANIFEST)
check("requirements stays empty", MANIFEST.get("requirements") == [])
check("sandbox block as designed", MANIFEST.get("sandbox") == {"network": False, "timeoutSeconds": 1800,
                                                                 "maxMemoryMb": 2048, "maxCpuPercent": 100})

# ---------------------------------------------------------------------------------------------
print("scenario: bootstrap constraints")
main_text = MAIN.read_text(encoding="utf-8")
check("main.py needs no pip install (PythonImportResolver replay)", resolver_packages(main_text) == [],
      resolver_packages(main_text))
check("preamble + main.py needs no pip install either", resolver_packages(PREAMBLE + main_text) == [])
try:
    ast.parse(main_text, feature_version=(3, 6))
    parsed36 = True
except SyntaxError as exc:
    parsed36 = exc
check("main.py parses as Python 3.6", parsed36 is True, parsed36)
try:
    compile(PREAMBLE + main_text, "script.py", "exec")
    compiled = True
except SyntaxError as exc:
    compiled = exc
check("preamble + main.py compiles", compiled is True, compiled)
check("no __future__ import", "__future__" not in "".join(line for line in main_text.splitlines(True) if not line.lstrip().startswith("#")))
docstrings = [n for n in ast.walk(main_tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
              and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant)
              and isinstance(n.body[0].value.value, str)]
check("no docstrings", not docstrings)
check("no multi-line strings", '"""' not in main_text and "'''" not in main_text)
imported = set()
for node in ast.walk(main_tree):
    if isinstance(node, ast.Import):
        imported.update(a.name for a in node.names)
    elif isinstance(node, ast.ImportFrom):
        imported.add(node.module)
check("imports only the bootstrap's stdlib set",
      imported <= {"sys", "os", "re", "json", "time", "hashlib", "subprocess", "importlib.util"}, imported)
check("no walrus, match or positional-only syntax",
      not any(isinstance(n, (getattr(ast, "NamedExpr", ()), getattr(ast, "Match", ()))) for n in ast.walk(main_tree)))
bridge_text = (SKILL / "lib" / "bridge.py").read_text(encoding="utf-8")
bridge_imports = set()
for node in ast.walk(ast.parse(bridge_text)):
    if isinstance(node, ast.Import):
        bridge_imports.update(a.name.split(".")[0] for a in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        bridge_imports.add(node.module.split(".")[0])
check("lib/bridge.py imports the standard library only", not [m for m in bridge_imports if resolver_packages(f"import {m}")],
      bridge_imports)

# ---------------------------------------------------------------------------------------------
print("scenario: errors before any work")
with FakeDataDir() as data:
    home = data.install("ffmpeg-video")
    doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.nope"}, env=sim_env(data))
    check("unknown tool: exact repo-convention error", doc == {"error": "Unknown tool: ffmpeg.nope"}, out)
    check("unknown tool: exit 0, one line", rc == 0 and len(out.strip().splitlines()) == 1)
    doc, out, err, rc = run_process(data, home, {}, env=sim_env(data))
    check("missing tool name is an unknown tool", doc == {"error": "Unknown tool: None"}, out)

    outside = pathlib.Path(tempfile.mkdtemp(prefix="ffv-outside-"))
    try:
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.setup.doctor"}, env=sim_env(data), cwd=outside)
        check("unknown cwd shape: BACKEND_UNSUPPORTED (backend unknown)",
              doc and doc.get("code") == "BACKEND_UNSUPPORTED" and doc.get("backend") == "unknown", out)
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.setup.contract"},
                                        env=sim_env(data, FFMPEG_VIDEO_SKILL_ROOT=home), cwd=outside)
        check("FFMPEG_VIDEO_SKILL_ROOT lets a development cwd through", doc and doc.get("ok") is True, out[:300])
    finally:
        shutil.rmtree(outside, ignore_errors=True)

# The Docker backend's cwd is /workspace: refused before any process starts (exec in-process,
# with os.getcwd and subprocess patched).
spawned = []
real_getcwd, real_popen = os.getcwd, subprocess.Popen


class NoPopen:
    def __init__(self, *a, **k):
        spawned.append(a)
        raise AssertionError("a subprocess was started")


buf = io.StringIO()
os.getcwd = lambda: "/workspace"
subprocess.Popen = NoPopen
try:
    with contextlib.redirect_stdout(buf):
        exec(compile(main_text, "main.py", "exec"), {"params": {"tool": "ffmpeg.project.render", "project": "/x.json"}})
finally:
    os.getcwd, subprocess.Popen = real_getcwd, real_popen
docker = json.loads(buf.getvalue().strip().splitlines()[-1])
check("/workspace cwd: BACKEND_UNSUPPORTED with backend docker",
      docker.get("code") == "BACKEND_UNSUPPORTED" and docker.get("backend") == "docker", docker)
check("/workspace cwd: no subprocess started", not spawned, spawned)
check("refusal hint names process fallback and the Pro image",
      "AllowProcessFallback" in docker.get("hint", "") and "prebuilt" in docker.get("hint", ""))
check("refusal wording avoids injection-guard words",
      not re.search(r"\b(override|bypass|ignore|disable)\b", json.dumps(docker), re.I))

# ---------------------------------------------------------------------------------------------
print("scenario: data folder and skill-home discovery")
with FakeDataDir() as data:
    real = data.install("ffmpeg-video", folder="video-toolkit-copy")
    doc, out, err, rc = run_process(data, real, {"tool": "ffmpeg.setup.doctor"}, env=sim_env(data))
    check("a folder name that differs from the slug is found", where_home(doc) and
          os.path.normcase(where_home(doc)) == os.path.normcase(str(real)), out[:400])

    decoy = data.install("ffmpeg-video", patch_manifest=lambda m: m.update(version="0.9.0"))
    doc, out, err, rc = run_process(data, real, {"tool": "ffmpeg.setup.doctor"}, env=sim_env(data))
    check("a version decoy at installed/ffmpeg-video is skipped",
          where_home(doc) and os.path.normcase(where_home(doc)) == os.path.normcase(str(real)), out[:400])
    shutil.rmtree(decoy)

    # dataDir from SOPHON_DATA_DIR / SOPHON__DataDirectory when the cwd's parent holds no skills/
    bare = pathlib.Path(tempfile.mkdtemp(prefix="ffv-bare-"))
    try:
        ws = bare / "sandbox" / "workspaces" / ("a" * 32)
        ws.mkdir(parents=True)
        for var in ("SOPHON_DATA_DIR", "SOPHON__DataDirectory"):
            doc, out, err, rc = run_process(data, real, {"tool": "ffmpeg.setup.doctor"},
                                            env=sim_env(data, **{var: data.root}), cwd=ws)
            check(f"dataDir from {var}", where_home(doc) and
                  os.path.normcase(where_home(doc)) == os.path.normcase(str(real)), out[:400])
        doc, out, err, rc = run_process(data, real, {"tool": "ffmpeg.setup.doctor"}, env=sim_env(data), cwd=ws)
        check("no data folder with the skill: VENDOR_NOT_FOUND", doc and doc.get("code") == "VENDOR_NOT_FOUND", out[:400])
    finally:
        shutil.rmtree(bare, ignore_errors=True)

    tampered = data.install("ffmpeg-video", folder="tampered")
    shutil.rmtree(real)
    with open(tampered / "vendor" / "ffmpeg-skill" / "scripts" / "cut.py", "ab") as fh:
        fh.write(b"\n# changed\n")
    doc, out, err, rc = run_process(data, tampered, {"tool": "ffmpeg.setup.contract"}, env=sim_env(data))
    check("a changed vendored file: VENDOR_CORRUPT", doc and doc.get("code") == "VENDOR_CORRUPT"
          and any("cut.py" in p for p in doc.get("problems") or []), out[:400])
    check("VENDOR_CORRUPT is retryable", doc and doc.get("retryable") is True)
    shutil.rmtree(tampered)

    extra = data.install("ffmpeg-video", folder="extra")
    (extra / "vendor" / "ffmpeg-skill" / "scripts" / "evil.py").write_text("print('x')\n", encoding="utf-8")
    doc, out, err, rc = run_process(data, extra, {"tool": "ffmpeg.setup.contract"}, env=sim_env(data))
    check("an extra .py under vendor/: VENDOR_CORRUPT", doc and doc.get("code") == "VENDOR_CORRUPT"
          and any("evil.py" in p for p in doc.get("problems") or []), out[:400])
    shutil.rmtree(extra)

    wrong = data.install("ffmpeg-video", folder="wronglock")
    lock = wrong / "vendor.lock.json"
    lock.write_bytes(lock.read_bytes().replace(b'"schemaVersion": 1', b'"schemaVersion":  1'))
    doc, out, err, rc = run_process(data, wrong, {"tool": "ffmpeg.setup.contract"}, env=sim_env(data))
    check("a lock that is not this release's: VENDOR_NOT_FOUND",
          doc and doc.get("code") == "VENDOR_NOT_FOUND"
          and any("vendor.lock.json does not match" in c.get("reason", "") for c in doc.get("candidates") or []), out[:500])
    check("VENDOR_NOT_FOUND lists the data folder", doc and doc.get("dataDir"))
    shutil.rmtree(wrong)

    # The lock pins vendor/ and the tool map; BRIDGE_SHA256 pins the bridge itself.
    evil = data.install("ffmpeg-video", folder="evilbridge")
    with open(evil / "lib" / "bridge.py", "ab") as fh:
        fh.write(b"\nraise SystemExit('loaded a changed bridge')\n")
    doc, out, err, rc = run_process(data, evil, {"tool": "ffmpeg.setup.contract"}, env=sim_env(data))
    check("a changed lib/bridge.py is never loaded: VENDOR_NOT_FOUND",
          doc and doc.get("code") == "VENDOR_NOT_FOUND" and "loaded a changed bridge" not in out + err
          and any("lib/bridge.py does not match" in c.get("reason", "") for c in doc.get("candidates") or []), out[:500])
    shutil.rmtree(evil)

    authored = data.install("ffmpeg-video", folder="ffmpeg-video", root="self-authored")
    doc, out, err, rc = run_process(data, authored, {"tool": "ffmpeg.setup.doctor"}, env=sim_env(data))
    check("a copy under skills/self-authored is not used", doc and doc.get("code") == "VENDOR_NOT_FOUND"
          and not any("self-authored" in c.get("path", "") for c in doc.get("candidates") or []), out[:400])
    shutil.rmtree(authored)

# ---------------------------------------------------------------------------------------------
print("scenario: interpreter selection")
boot_src = main_text.split("\ntry:\n    RESULT = main(")[0]


def boot_namespace():
    ns = {"__name__": "ffvideo_boot"}
    exec(compile(boot_src, "main.py", "exec"), ns)
    return ns


fakes = pathlib.Path(tempfile.mkdtemp(prefix="ffv-py-"))
try:
    if WINDOWS:
        old_py = fakes / "oldpython.cmd"
        old_py.write_text("@exit /b 3\r\n", encoding="utf-8", newline="")
        new_py = fakes / "newpython.cmd"
        new_py.write_text(f'@"{sys.executable}" %*\r\n', encoding="utf-8", newline="")
    else:
        old_py = fakes / "oldpython"
        old_py.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
        new_py = fakes / "newpython"
        new_py.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        for f in (old_py, new_py):
            f.chmod(0o755)
    ns = boot_namespace()
    check("a too-old candidate does not qualify", ns["python_qualifies"]([str(old_py)]) is False)
    check("a 3.10+ candidate qualifies", ns["python_qualifies"]([str(new_py)]) is True)
    saved = dict(os.environ)
    os.environ["FFMPEG_VIDEO_PYTHON"] = str(new_py)
    try:
        check("FFMPEG_VIDEO_PYTHON is tried first", ns["python_candidates"]()[0] == [str(new_py)])
        command, tried = ns["find_python"]()
        check("find_python picks the first qualifying candidate", command == [str(new_py)], (command, tried))
    finally:
        os.environ.clear()
        os.environ.update(saved)

    with FakeDataDir() as data:
        home = data.install("ffmpeg-video")
        ws = data.workspace()
        env_saved = dict(os.environ)
        cwd_saved = os.getcwd()
        os.environ.update({"HOME": str(data.root / "userhome"), "USERPROFILE": str(data.root / "userhome")})
        os.chdir(ws)
        try:
            ns = boot_namespace()
            ns["MIN_PYTHON"] = (99, 0)        # pretend this interpreter is too old
            ns["python_candidates"] = lambda: [[str(old_py)]]
            doc = ns["main"]({"tool": "ffmpeg.setup.contract"})
            check("nothing newer found: PYTHON_UNSUPPORTED", doc.get("code") == "PYTHON_UNSUPPORTED"
                  and doc.get("tried") == [str(old_py)], doc)
            ns["python_candidates"] = lambda: [[str(old_py)], [sys.executable]]
            doc = ns["main"]({"tool": "ffmpeg.setup.contract"})
            check("re-exec under a newer Python runs lib/bridge.py --stdin", doc.get("ok") is True
                  and len(doc.get("result", {}).get("tools", [])) == 44, str(doc)[:300])
            doc = ns["main"]({"tool": "ffmpeg.edit.cut", "input": "missing.mp4", "output": "x.mp4"})
            check("re-exec carries the params", doc.get("code") == "INVALID_ARGUMENT", str(doc)[:300])
        finally:
            os.chdir(cwd_saved)
            os.environ.clear()
            os.environ.update(env_saved)
finally:
    shutil.rmtree(fakes, ignore_errors=True)

# ---------------------------------------------------------------------------------------------
print("scenario: path policy")
with FakeDataDir() as data:
    user = pathlib.Path(tempfile.mkdtemp(prefix="ffv-user-"))
    try:
        clip = user / "clip.mp4"
        clip.write_bytes(b"\x00" * 64)
        root = data.output_root
        root.mkdir(parents=True, exist_ok=True)
        (root / "inbox").mkdir(exist_ok=True)
        (root / "inbox" / "rel.mp4").write_bytes(b"\x00")

        args, err, c = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": "final.mp4"}, data)
        check("a bare output name lands in the output root", err is None and
              os.path.normcase(args["output"]) == os.path.normcase(str(root / "final.mp4")), err and err.message)
        check("the input stays absolute and real", err is None and os.path.normcase(args["input"]) == os.path.normcase(os.path.realpath(clip)))
        args, err, c = outcome("ffmpeg.edit.cut", {"input": "inbox/rel.mp4", "output": "out/a.mp4"}, data)
        check("a relative input resolves under the output root", err is None and
              os.path.normcase(args["input"]) == os.path.normcase(str(root / "inbox" / "rel.mp4")), err and err.message)
        check("a folder made for an output is removed again when the call does not run",
              err is None and not (root / "out").exists())
        r = outcome("ffmpeg.edit.cut", {"input": "https://example.com/a.mp4", "output": "a.mp4"}, data)
        check("a URL input is refused", code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "url", r[1] and r[1].message)
        r = outcome("ffmpeg.edit.cut", {"input": str(clip) + "\nx", "output": "a.mp4"}, data)
        check("a newline in a path is refused", code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "control_character")
        r = outcome("ffmpeg.edit.cut", {"input": "~/definitely-not-here-ffv.mp4", "output": "a.mp4"}, data)
        check("~ expands to the user's home", code_of(r) == "INVALID_ARGUMENT" and reason_of(r) == "not_found"
              and os.path.expanduser("~") in (r[1].extra or {}).get("path", ""), r[1] and r[1].extra)
        r = outcome("ffmpeg.edit.cut", {"input": str(user / "nope.mp4"), "output": "a.mp4"}, data)
        check("a missing input is INVALID_ARGUMENT not_found", code_of(r) == "INVALID_ARGUMENT" and reason_of(r) == "not_found")
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": str(user / "out.mp4")}, data)
        check("an output outside the write roots is refused", code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "outside_write_roots")
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": "../escape.mp4"}, data)
        check("a relative output with .. is refused", code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "relative_parent")
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": "noext"}, data)
        check("an output without an extension is refused", code_of(r) == "INVALID_ARGUMENT")
        for sub in ("vault", "config", "skills"):
            secret = data.root / sub / "x.mp4"
            secret.parent.mkdir(parents=True, exist_ok=True)
            secret.write_bytes(b"\x00")
            r = outcome("ffmpeg.edit.cut", {"input": str(secret), "output": "a.mp4"}, data)
            check(f"an input under <dataDir>/{sub} is refused", code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "sophon_data")
        doc_in = data.root / "documents" / "generated" / "img.png"
        doc_in.parent.mkdir(parents=True, exist_ok=True)
        doc_in.write_bytes(b"\x00")
        r = outcome("ffmpeg.make.insert", {"input": str(doc_in), "output": "still.mp4", "duration": "3"}, data)
        check("an input under <dataDir>/documents is allowed", r[1] is None, r[1] and r[1].message)
        r = outcome("ffmpeg.edit.cut", {"input": str(SKILL / "vendor" / "ffmpeg-skill" / "LICENSE"), "output": "a.mp4"}, data)
        check("a file of the skill itself is refused", code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "skill_home")
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": str(data.root / "documents" / "x.mp4")}, data)
        check("writing elsewhere in documents (outside the root) is refused", code_of(r) == "PATH_NOT_ALLOWED")

        extra_root = user / "exports"
        extra_root.mkdir()
        env = {"FFMPEG_VIDEO_WRITE_ROOTS": str(extra_root)}
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": str(extra_root / "x.mp4")}, data, env)
        check("FFMPEG_VIDEO_WRITE_ROOTS adds a write root", r[1] is None, r[1] and r[1].message)
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": str(extra_root / "x.mp4"), "overwrite": True}, data, env)
        check("overwrite outside the output root is refused", code_of(r) == "PATH_NOT_ALLOWED"
              and reason_of(r) == "overwrite_outside_output_root")
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": "ow.mp4", "overwrite": True}, data)
        check("overwrite inside the output root is accepted", r[1] is None, r[1] and r[1].message)
        r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": str(data.root / "vault" / "x.mp4")}, data,
                    {"FFMPEG_VIDEO_WRITE_ROOTS": str(data.root / "vault")})
        check("a write root inside Sophon's data is ignored", code_of(r) == "PATH_NOT_ALLOWED")

        if WINDOWS or sys.platform == "darwin":
            upper = str(root).upper() if WINDOWS else str(root)
            r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": os.path.join(upper, "case.mp4")}, data)
            check("paths compare case-insensitively on this OS", r[1] is None, r[1] and r[1].message)
        link = root / "link"
        try:
            os.symlink(str(user), str(link), target_is_directory=True)
            linked = True
        except (OSError, NotImplementedError):
            linked = False
        if linked:
            r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": "link/escape.mp4"}, data)
            check("a symlink out of the output root is refused", code_of(r) == "PATH_NOT_ALLOWED")
            os.unlink(str(link)) if not WINDOWS else os.rmdir(str(link))
        else:
            print("skip symlink escape (this account cannot create symlinks)")

        args, err, c = outcome("ffmpeg.layer.caption", {"input": str(clip), "output": "cap.mp4",
                                                         "srt": str(clip) + ":en"}, data)
        check("srt keeps a :LANG suffix after the checked path", err is None and args["srt"].endswith(":en")
              and os.path.normcase(args["srt"][:-3]) == os.path.normcase(os.path.realpath(clip)), err and err.message)
        r = outcome("ffmpeg.make.sequence", {"dir": str(user), "pattern": "../x_%04d.png", "output": "s.mp4"}, data)
        check("sequence.pattern must be a plain name", code_of(r) == "INVALID_ARGUMENT")
        args, err, c = outcome("ffmpeg.mix.loudness", {"input": str(clip), "versions": "youtube"}, data)
        check("loudness versions beside an input outside the roots is refused", err is not None
              and err.code == "PATH_NOT_ALLOWED", err and err.message)

        # render: inline project, paths checked and made absolute, the work folder forced
        args, err, c = outcome("ffmpeg.project.render", {"project_json": {
            "output": "promo/final.mp4", "clips": [{"src": str(clip)}], "audio": {"music": str(clip)}},
            "use_cache": True}, data)
        saved = json.loads(pathlib.Path(args["project"]).read_text(encoding="utf-8")) if args else {}
        check("render: the checked project is saved under <root>/projects", args and
              os.path.normcase(args["project"]).startswith(os.path.normcase(str(root / "projects"))))
        dry, dry_err, c = outcome("ffmpeg.project.render", {"project_json": {"output": "p.mp4", "clips": [{"src": str(clip)}]},
                                                             "dry_run": True}, data)
        check("render dry run: the project goes to the temp folder, not projects/", dry and ".tmp" in dry["project"], dry_err)
        check("render project_json: output lands in the output root", err is None and
              os.path.normcase(saved.get("output", "")) == os.path.normcase(str(root / "promo" / "final.mp4")), err and err.message)
        check("render: --work forced into the call's temp folder, --cache into the root", args and
              "work" in args and ".tmp" in args["work"] and args.get("cache", "").endswith(os.path.join(".cache", "render")))
        r = outcome("ffmpeg.project.render", {"project_json": {"output": str(user / "x.mp4"), "clips": [{"src": str(clip)}]}}, data)
        check("render: a project output outside the roots is refused", code_of(r) == "PATH_NOT_ALLOWED")
        r = outcome("ffmpeg.project.render", {"project_json": {"output": "x.mp4", "clips": [{"src": str(data.root / "vault" / "x.mp4")}]}}, data)
        check("render: a clip under <dataDir>/vault is refused", code_of(r) == "PATH_NOT_ALLOWED")
        r = outcome("ffmpeg.project.render", {"project_json": {"plan_version": 1, "steps": []}}, data)
        check("render: a plan document is refused", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.project.render", {"project_json": "x" * (70 * 1024)}, data)
        check("render: project_json over 64 KB is refused", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.project.render", {"project": str(clip), "project_json": {"output": "a.mp4"}}, data)
        check("render: project and project_json together are refused", code_of(r) == "INVALID_ARGUMENT")

        # batch: output_dir confined, steps checked, jobs capped
        (user / "clips").mkdir()
        args, err, c = outcome("ffmpeg.project.batch", {"folder": str(user / "clips"), "jobs": "8", "recipe_json": {
            "glob": "*.mp4", "steps": [["cut.py", "{in}", "--start", "0", "--end", "1", "-o", "{out}"]]}}, data)
        recipe = json.loads(pathlib.Path(args["recipe"]).read_text(encoding="utf-8")) if args else {}
        check("batch: jobs capped at 2", args and args.get("jobs") == "2", args and args.get("jobs"))
        check("batch: a missing output_dir defaults into the output root", bool(recipe) and
              os.path.normcase(recipe["output_dir"]).startswith(os.path.normcase(str(root / "batch"))), recipe.get("output_dir"))
        r = outcome("ffmpeg.project.batch", {"folder": str(user / "clips"), "recipe_json": {
            "output_dir": str(user / "out"), "steps": [["cut.py", "{in}", "-o", "{out}"]]}}, data)
        check("batch: output_dir outside the roots is refused", code_of(r) == "PATH_NOT_ALLOWED")
        r = outcome("ffmpeg.project.batch", {"folder": str(user / "clips"), "recipe_json": {
            "steps": [["cut.py", "{in}", "--edl", str(user / "x.edl"), "-o", "{out}"]]}}, data)
        check("batch: a step writing a side file is refused", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.project.batch", {"folder": str(user / "clips"), "recipe_json": {
            "steps": [["render.py", str(clip)]]}}, data)
        check("batch: render.py as a step is refused", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.project.batch", {"folder": str(user / "clips"), "recipe_json": {"steps": [["../x.py"]]}}, data)
        check("batch: a step script with a folder is refused", code_of(r) == "INVALID_ARGUMENT")

        args, err, c = outcome("ffmpeg.setup.verify", {"paths": [str(clip)], "quick": True}, data)
        check("verify: --out forced into <root>/verify", err is None and
              os.path.normcase(args["out"]).startswith(os.path.normcase(str(root / "verify"))), err and err.message)

        # credential stores and .env files are refused as inputs, for media and text roles alike
        uhome = pathlib.Path(tempfile.mkdtemp(prefix="ffv-home-")).resolve()  # outside the data folder
        secrets = {"~/.ssh": uhome / ".ssh" / "id_ed25519.png", "~/.aws": uhome / ".aws" / "credentials.srt",
                   "~/.config": uhome / ".config" / "gh" / "hosts.txt", ".env": uhome / "proj" / ".env",
                   ".env.local": uhome / "proj" / ".env.local"}
        for path in secrets.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x")
        henv = {"HOME": str(uhome), "USERPROFILE": str(uhome)}
        for label, path in secrets.items():
            r = outcome("ffmpeg.inspect.probe", {"inputs": [str(path)]}, data, env=henv)
            check(f"an input under {label} is refused (credential_store)",
                  code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "credential_store", r[1] and r[1].message)
        r = outcome("ffmpeg.layer.caption", {"input": str(clip), "output": "c3.mp4", "text": str(secrets["~/.aws"]),
                                             "write_srt": "leak2.srt"}, data, env=henv)
        check("a caption text file under ~/.aws is refused", code_of(r) == "PATH_NOT_ALLOWED"
              and reason_of(r) == "credential_store")
        r = outcome("ffmpeg.inspect.report", {"after": str(clip), "notes": str(secrets[".env"]), "output": "r2.html"},
                    data, env=henv)
        check("report notes from a .env file are refused", code_of(r) == "PATH_NOT_ALLOWED"
              and reason_of(r) == "credential_store")
        args, err, c = outcome("ffmpeg.inspect.probe", {"inputs": [str(clip)]}, data, env=henv)
        check("an ordinary input is still accepted", err is None, err and err.message)
        shutil.rmtree(uhome, ignore_errors=True)

        # network and device spellings: refused before any filesystem call, inputs and outputs alike
        vault = data.root / "vault" / "secret.png"
        vault.parent.mkdir(parents=True, exist_ok=True)
        vault.write_bytes(b"\x00")
        spellings = {"UNC host": "\\\\attacker.example\\s\\a.mp4", "UNC forward slashes": "//attacker.example/s/a.mp4"}
        if WINDOWS:
            plain = str(vault)
            spellings.update({
                "extended-length": "\\\\?\\" + plain, "extended-length forward": "//?/" + plain.replace("\\", "/"),
                "device namespace": "\\\\.\\" + plain, "GLOBALROOT": "\\\\?\\GLOBALROOT\\??\\" + plain,
                "admin share": "\\\\localhost\\" + plain[0] + "$" + plain[2:],
                "admin share by address": "\\\\127.0.0.1\\" + plain[0] + "$" + plain[2:]})
        touched = []
        real_realpath, real_isfile = os.path.realpath, os.path.isfile

        def spy(fn):
            def wrapped(p, *a, **k):
                text = os.fspath(p)
                if len(text) > 1 and text[0] in "\\/" and text[1] in "\\/":
                    touched.append(text)
                return fn(p, *a, **k)
            return wrapped
        for label, spelled in spellings.items():
            os.path.realpath, os.path.isfile = spy(real_realpath), spy(real_isfile)
            try:
                r = outcome("ffmpeg.inspect.probe", {"inputs": [spelled]}, data)
            finally:
                os.path.realpath, os.path.isfile = real_realpath, real_isfile
            check(f"an input in {label} spelling is refused (network_path)", code_of(r) == "PATH_NOT_ALLOWED"
                  and reason_of(r) == "network_path", (spelled, r[1] and r[1].message))
        check("... before any realpath or isfile call on it", not touched, touched[:3])
        r = outcome("ffmpeg.layer.caption", {"input": str(clip), "output": "c.mp4", "text": spellings["UNC host"],
                                             "write_srt": "leak.srt"}, data)
        check("a caption text file in UNC spelling is refused", code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "network_path")
        touched.clear()
        os.path.realpath, os.path.isfile = spy(real_realpath), spy(real_isfile)
        try:
            r = outcome("ffmpeg.layer.caption", {"input": str(clip), "output": "c2.mp4",
                                                 "srt": spellings["UNC host"] + ":en"}, data)
        finally:
            os.path.realpath, os.path.isfile = real_realpath, real_isfile
        check("a caption srt:LANG in UNC spelling is refused (network_path)",
              code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "network_path", r[1] and r[1].message)
        check("... before any realpath or isfile call on it", not touched, touched[:3])
        if WINDOWS:
            r = outcome("ffmpeg.inspect.report", {"after": str(clip), "notes": spellings["extended-length"], "output": "r.html"}, data)
            check("report notes in \\\\?\\ spelling of <dataDir>/vault is refused", code_of(r) == "PATH_NOT_ALLOWED")
            r = outcome("ffmpeg.edit.cut", {"input": str(clip), "output": "\\\\?\\" + str(data.root / "config" / "x.mp4")}, data)
            check("an output in \\\\?\\ spelling is refused", code_of(r) == "PATH_NOT_ALLOWED")
            check("plain_path drops the extended-length prefix", bridge.plain_path("\\\\?\\C:\\x") == "C:\\x"
                  and bridge.plain_path("\\\\?\\UNC\\h\\s\\x") == "\\\\h\\s\\x")

        # batch steps are read the way argparse reads them: only the step tool's own exact options
        media = data.root / "documents" / "batch-in"
        media.mkdir(parents=True, exist_ok=True)
        (media / "a.mp4").write_bytes(b"\x00")
        outside = user / "victim.mp4"

        def batch(steps=None, **recipe):
            body = dict(recipe, steps=steps if steps is not None else [["cut.py", "{in}", "-o", "{out}"]])
            return outcome("ffmpeg.project.batch", {"folder": str(media), "recipe_json": body}, data)
        cut = ["cut.py", "{in}", "--start", "0", "--end", "1"]
        refused_steps = {
            "an attached short value (-oPATH)": cut + ["-o" + str(outside)],
            "an abbreviated option (--outp=PATH)": cut + ["--outp=" + str(outside)],
            "an abbreviated option (--out PATH)": cut + ["--out", str(outside)],
            "an abbreviated --pla": cut + ["--pla=" + str(data.root / "config" / "x.json"), "-o", "{out}"],
            "--overwrite inside a step": cut + ["-o", "{out}", "--overwrite"],
            "an option of another tool": cut + ["--image", str(clip), "-o", "{out}"],
            "-o joined with '='": cut + ["-o={out}"],
            "a value starting with '-' as its own item": ["cut.py", "{in}", "--start", "-x", "-o", "{out}"],
            "{in} inside a longer value": ["overlay.py", "{in}", "--image", "{in}/../../x.png", "-o", "{out}"],
            "a write flag naming {in}": cut + ["-o", "{in}"],
            "a second positional": cut + [str(clip), "-o", "{out}"],
            "loudness versions (writes beside the input)": ["loudness.py", "{in}", "--versions", "youtube", "-o", "{out}"],
        }
        for label, step in refused_steps.items():
            r = batch([step])
            check(f"batch step refused: {label}", r[1] is not None and code_of(r) in ("INVALID_ARGUMENT", "PATH_NOT_ALLOWED"),
                  step)
        r = batch([["overlay.py", "{in}", "--image=" + str(vault), "-o", "{out}"]])
        check("batch: a joined input path (--image=<dataDir>/vault/...) is checked and refused",
              code_of(r) == "PATH_NOT_ALLOWED" and reason_of(r) == "sophon_data", r[1] and r[1].message)
        hops = "/".join([".."] * len(root.relative_to(data.root).parts))
        r = batch([["overlay.py", "{in}", "--image", f"{hops}/vault/secret.png", "-o", "{out}"]])
        check("batch: a relative '..' input climbing into <dataDir>/vault is refused", code_of(r) == "PATH_NOT_ALLOWED"
              and reason_of(r) == "sophon_data", r[1] and r[1].message)
        args, err, c = batch([["cut.py", "{in}", "--start=-1", "--end", "2", "--json", "-o", "{out}"],
                              ["overlay.py", "{in}", "--image", "inbox/rel.mp4", "-o", "{out}"]])
        recipe = json.loads(pathlib.Path(args["recipe"]).read_text(encoding="utf-8")) if args else {}
        check("batch: exact options, a joined negative value and --json are accepted", err is None, err and err.message)
        check("batch: a relative input path is passed absolute (the step runs in another folder)", bool(recipe) and
              os.path.normcase(recipe["steps"][1][3]) == os.path.normcase(str(root / "inbox" / "rel.mp4")), recipe.get("steps"))
        for key, value in (("suffix", "\\..\\..\\..\\..\\..\\evil\\trav"), ("suffix", "/../x"), ("ext", "mp4/../../x"),
                           ("ext", "mp4:x"), ("glob", "../../../vault/*.png"), ("glob", "sub\\*.mp4"),
                           ("glob", "C:*.mp4"), ("glob", "/abs/*.mp4")):
            r = batch(**{key: value})
            check(f"batch: recipe.{key} {value!r} is refused", code_of(r) == "PATH_NOT_ALLOWED", r[1] and r[1].message)
        r = batch(glob="*.mp4", suffix="_final", ext="mov")
        check("batch: a plain glob, suffix and ext are accepted", r[1] is None, r[1] and r[1].message)
        link = media / "linked.mp4"
        try:
            os.symlink(str(data.root / "vault" / "secret.png"), str(link))
            linked = True
        except (OSError, NotImplementedError):
            linked = False
        if linked:
            r = batch(glob="*")
            check("batch: a glob match that links into <dataDir>/vault is refused", code_of(r) == "PATH_NOT_ALLOWED"
                  and reason_of(r) == "sophon_data", r[1] and r[1].message)
            os.unlink(str(link))
        else:
            print("skip batch glob symlink (this account cannot create symlinks)")
    finally:
        shutil.rmtree(user, ignore_errors=True)

# ---------------------------------------------------------------------------------------------
print("scenario: parameters")
with FakeDataDir() as data:
    user = pathlib.Path(tempfile.mkdtemp(prefix="ffv-user-"))
    try:
        clip = user / "clip.mp4"
        clip.write_bytes(b"\x00")
        base = {"input": str(clip), "output": "a.mp4"}
        args, err, c = outcome("ffmpeg.edit.cut", dict(base, tool="ffmpeg.edit.cut", apiKey="k", accessToken="t"), data)
        check("tool, apiKey and accessToken are stripped", err is None and not {"tool", "apiKey", "accessToken"} & set(args))
        r = outcome("ffmpeg.edit.cut", dict(base, bogus=1, other=2), data)
        check("unknown keys are refused by name", code_of(r) == "INVALID_ARGUMENT"
              and r[1].extra.get("unknown") == ["bogus", "other"], r[1] and r[1].message)
        r = outcome("ffmpeg.edit.cut", dict(base, argv=["--plan", "x"]), data)
        check("a removed key (argv) is refused with its reason", code_of(r) == "INVALID_ARGUMENT" and "argv" in r[1].message)
        r = outcome("ffmpeg.edit.cut", dict(base, progress=False, hw=None), data)
        check("a removed key given as false or null is accepted", r[1] is None, r[1] and r[1].message)
        r = outcome("ffmpeg.project.render", {"project_json": {"output": "a.mp4", "clips": [{"src": str(clip)}]}, "work": "x"}, data)
        check("render.work is refused (removed per tool)", code_of(r) == "INVALID_ARGUMENT")
        args, err, c = outcome("ffmpeg.edit.cut", dict(base, smart="true", tolerance="0.5", fast=1), data, steps=("validate",))
        check("coercion: 'true' -> true, '0.5' -> 0.5, 1 -> true", err is None and args["smart"] is True
              and args["tolerance"] == 0.5 and args["fast"] is True, args)
        args, err, c = outcome("ffmpeg.adjust.crop", dict(base, x="10", y=0, width=320.0, height="180"), data, steps=("validate",))
        check("coercion: integers from strings and whole floats", err is None and (args["x"], args["width"], args["height"]) == (10, 320, 180), args)
        r = outcome("ffmpeg.adjust.crop", dict(base, x="ten", y=0, width=1, height=1), data, steps=("validate",))
        check("a non-integer is refused", code_of(r) == "INVALID_ARGUMENT")
        args, err, c = outcome("ffmpeg.inspect.probe", {"inputs": str(clip)}, data)
        check("a scalar becomes a one-item list for an array", err is None and isinstance(args["inputs"], list) and len(args["inputs"]) == 1)
        r = outcome("ffmpeg.edit.cut", dict(base, preset="warp"), data, steps=("validate",))
        check("a value outside the choices is refused", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.edit.join", {"inputs": [str(clip)], "output": "j.mp4", "channels": 2}, data, steps=("validate",))
        check("numeric choices: join.channels 2 is accepted", r[1] is None, r[1] and r[1].message)
        r = outcome("ffmpeg.edit.join", {"inputs": [str(clip)], "output": "j.mp4", "channels": 3}, data, steps=("validate",))
        check("numeric choices: join.channels 3 is refused", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.edit.cut", dict(base, edit_list=True, no_edit_list=True), data, steps=("validate",))
        check("mutually exclusive flags are refused together", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.edit.loop", base, data, steps=("validate",))
        check("one-of-required (loop: times or duration) is enforced", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.edit.cut", {"input": str(clip)}, data, steps=("validate",))
        check("a missing required output is refused", code_of(r) == "INVALID_ARGUMENT" and "output" in r[1].extra.get("missing", []))
        r = outcome("ffmpeg.edit.silence", {"input": str(clip)}, data, steps=("validate",))
        check("conditional required: silence needs output unless list", code_of(r) == "INVALID_ARGUMENT")
        r = outcome("ffmpeg.edit.silence", {"input": str(clip), "list": True}, data, steps=("validate",))
        check("conditional required: silence list needs no output", r[1] is None, r[1] and r[1].message)
        args, err, c = outcome("ffmpeg.edit.cut", dict(base, timeout=10 ** 7), data, steps=("validate",))
        check("timeout is clamped to the call's deadline", err is None and args["timeout"] <= 1800 - 60 - 30, args and args.get("timeout"))
        r = outcome("ffmpeg.edit.cut", dict(base, timeout=0), data, steps=("validate",))
        check("timeout 0 (no limit) is refused", code_of(r) == "INVALID_ARGUMENT")
        args, err, c = outcome("ffmpeg.edit.cut", base, data, steps=("validate",))
        check("a default timeout is always passed", err is None and 1 <= args["timeout"] <= 1800, args and args.get("timeout"))
        defaults = []
        for late in (0.3, 1.7, 95.0):
            with call("ffmpeg.project.render", {"project_json": {"output": "a.mp4", "clips": [{"src": str(clip)}]}}, data) as c:
                c.start -= late
                defaults.append(c.validate()["timeout"])
        check("the default timeout does not move with the elapsed time (render's cache key holds it)",
              len(set(defaults)) == 1 and defaults[0] == 1680, defaults)
        args, err, c = outcome("ffmpeg.inspect.probe", {"inputs": [str(clip)]}, data, steps=("validate",))
        check("probe's per-tool deadline (120 s) bounds its timeout", err is None and args["timeout"] <= 90, args and args.get("timeout"))
        args, err, c = outcome("ffmpeg.project.batch", {"folder": str(user), "recipe_json": {"steps": []}, "jobs": "auto"}, data, steps=("validate",))
        check("batch jobs 'auto' becomes the cap", err is None and args["jobs"] == "2")
    finally:
        shutil.rmtree(user, ignore_errors=True)

# ---------------------------------------------------------------------------------------------
print("scenario: argv parity with the full upstream contract")
PARITY = r'''
import importlib.util, json, sys
sys.dont_write_bytecode = True
vendor, tool_map_path = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("ffvideo_server", vendor + "/mcp/server.py")
server = importlib.util.module_from_spec(spec); sys.modules["ffvideo_server"] = server; spec.loader.exec_module(server)
tool_map = json.load(open(tool_map_path, encoding="utf-8"))
full = {s["name"]: s for s in server._contract.build(detect=False)["tools"]}
pre = {k: e["spec"] for k, e in tool_map["tools"].items() if e.get("spec")}
def values(entry, dash):
    out = {}
    for name, p in entry["params"].items():
        if p.get("source") != "upstream" or name in (entry.get("removed") or {}):
            continue
        kind = p.get("type")
        if kind == "boolean": out[name] = True
        elif kind == "integer": out[name] = 7
        elif kind == "number": out[name] = 2.5
        elif kind == "array": out[name] = ["a1", "-a2"] if dash else ["a1", "a2"]
        else: out[name] = ("-" if dash else "") + "v_" + name
    out["json_brief"] = True
    return out
def argv(specs, key, args):
    server._SPECS.clear(); server._SPECS.update(specs)
    try: return server.build_argv(key, dict(args))
    except Exception as exc: return "error: %s" % exc
mismatch, count, ro = [], 0, []
for key, entry in tool_map["tools"].items():
    if not entry.get("spec"): continue
    if key not in full: mismatch.append([key, "not in the full contract"]); continue
    for dash in (False, True):
        args = values(entry, dash)
        a, b = argv(pre, key, args), argv(full, key, args)
        count += 1
        if a != b: mismatch.append([key, dash, a, b])
    if server._contract.mcp_read_only(entry["spec"]) != server._contract.mcp_read_only(full[key]) or \
       bool(entry.get("read_only")) != server._contract.mcp_read_only(full[key]):
        ro.append(key)
print(json.dumps({"tools": sum(1 for e in tool_map["tools"].values() if e.get("spec")), "cases": count,
                  "mismatch": mismatch[:5], "mismatches": len(mismatch), "read_only": ro}))
'''
proc = subprocess.run([sys.executable, "-I", "-B", "-c", PARITY, str(VENDOR), str(SKILL / "lib" / "tool-map.json")],
                      capture_output=True, text=True, encoding="utf-8", cwd=tempfile.gettempdir(), timeout=300)
try:
    parity = json.loads(proc.stdout.strip().splitlines()[-1])
except (ValueError, IndexError):
    parity = {"error": proc.stderr[-800:]}
check("42 upstream tools compared", parity.get("tools") == 42, parity)
check("build_argv: pre-filled spec == full contract for every tool (plain and dash values)",
      parity.get("mismatches") == 0 and parity.get("cases") == 84, parity.get("mismatch") or parity)
check("mcp_read_only parity (and the tool map's read_only flag)", parity.get("read_only") == [], parity.get("read_only"))
with FakeDataDir() as data:
    user = pathlib.Path(tempfile.mkdtemp(prefix="ffv-user-"))
    try:
        clip = user / "-dash.mp4"
        clip.write_bytes(b"\x00")
        with call("ffmpeg.edit.cut", {"input": str(clip), "output": "a.mp4", "start": "-1"}, data) as c:
            args = c.resolve_paths(c.validate())
            cli = dict(args, json_brief=True)
            argv = c.server.build_argv("cut", cli)
            check("argv: --json and --json-brief, --timeout, -o and the input",
                  "--json" in argv and "--json-brief" in argv and "--timeout" in argv and "-o" in argv and args["input"] in argv, argv)
            check("argv: a value starting with '-' is joined (--start=-1)", "--start=-1" in argv, argv)
    finally:
        shutil.rmtree(user, ignore_errors=True)

# ---------------------------------------------------------------------------------------------
print("scenario: preflight and failure mapping")
with FakeDataDir() as data:
    home = data.install("ffmpeg-video")
    if bridge.well_known_ffmpeg_dirs():
        print("skip DEPENDENCY_MISSING with PATH stripped (FFmpeg is installed in a well-known folder here)")
    else:
        env = sim_env(data, PATH=os.path.dirname(sys.executable) + (os.pathsep + os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32") if WINDOWS else ""))
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.setup.doctor"}, env=env)
        check("doctor with PATH stripped: DEPENDENCY_MISSING", doc and doc.get("code") == "DEPENDENCY_MISSING", out[:300])
        check("... and it still reports the wrapper facts and a fix", doc and doc.get("doctor", {}).get("outputRoot")
              and doc["doctor"].get("problems") and all(p.get("fix") for p in doc["doctor"]["problems"]), out[:300])
        media = data.root / "documents" / "in.mp4"
        media.write_bytes(b"\x00")
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.inspect.probe", "inputs": [str(media)]}, env=env)
        check("a tool call with PATH stripped: DEPENDENCY_MISSING", doc and doc.get("code") == "DEPENDENCY_MISSING", out[:300])

    with call("ffmpeg.edit.cut", {}, data) as c:
        def fake(rc, doc, stderr=""):
            return subprocess.CompletedProcess(["x"], rc, json.dumps(doc) if doc is not None else "", stderr)
        missing = {"status": "failed", "exit_code": 127, "error": {"kind": "missing_tool", "message": "'ffmpeg' was not found on PATH."}}
        check("upstream exit 127 / missing_tool maps to DEPENDENCY_MISSING",
              c.classify(fake(127, missing), missing, 1.0, 64)[0] == "DEPENDENCY_MISSING")
        old = {"status": "failed", "error": {"kind": "missing_tool", "reason": "ffmpeg_unsupported", "message": "FFmpeg 5.1"}}
        check("ffmpeg_unsupported maps to DEPENDENCY_MISSING", c.classify(fake(1, old), old, 1.0, 64)[0] == "DEPENDENCY_MISSING")
        tout = {"status": "failed", "exit_code": 124, "error": {"kind": "timeout", "message": "ffmpeg exceeded the 5 s time limit"}}
        check("a tool's own timeout maps to TIMEOUT", c.classify(fake(124, tout), tout, 6.0, 300)[0] == "TIMEOUT")
        code, message = c.classify(fake(124, tout), tout, 300.0, 300)
        check("a run that reached the ceiling says it hit the wrapper deadline", code == "TIMEOUT" and "wrapper deadline" in message, message)
        code, message = c.classify(fake(2, None, "usage: cut.py\ncut.py: error: argument --start: bad value"), None, 0.5, 64)
        check("argparse exit 2 with no JSON maps to ARGUMENT_REJECTED", code == "ARGUMENT_REJECTED" and "--start" in message, message)
        other = {"status": "failed", "error": {"kind": "ffmpeg", "message": "Conversion failed"}}
        check("any other failure maps to TOOL_FAILED", c.classify(fake(1, other), other, 1.0, 64)[0] == "TOOL_FAILED")

# ---------------------------------------------------------------------------------------------
print("scenario: compaction and the envelope")
big_list = list(range(1000))
compacted = bridge.compact({"rows": big_list, "s": "x" * 5000, "n": float("inf")})
check("a long list keeps the first 40 and the last 10", len(compacted["rows"]) == 51 and compacted["rows"][40] == {"_omitted": 950}
      and compacted["rows"][-1] == 999)
check("a long string is cut at 2,000 characters", compacted["s"].startswith("x" * 2000) and len(compacted["s"]) < 2100)
check("a non-finite number becomes text (valid JSON)", compacted["n"] == "inf")
redacted = bridge.redact_text({"cues": [{"text": "hello"}], "text": "y" * 500, "status": "ok"})
check("brief mode never echoes caption or transcript text", "hello" not in json.dumps(redacted) and "y" * 200 not in json.dumps(redacted))
with FakeDataDir() as data:
    with call("ffmpeg.inspect.scenes", {}, data) as c:
        c.detail = "brief"
        huge = {"status": "completed", "output": None, "verified": True,
                "scenes": [{"start": i, "end": i + 1, "note": "n" * 1900} for i in range(600)]}
        env = c.success(huge)
        size = len(json.dumps(env, ensure_ascii=True, separators=(",", ":")))
        check("a 1 MB result is truncated under the 40K brief cap", env["truncated"] is True and size <= 40000, size)
        check("... and spilled whole to <root>/reports", env["fullResultPath"] and os.path.isfile(env["fullResultPath"])
              and pathlib.Path(env["fullResultPath"]).stat().st_size > 1_000_000)
        check("the success envelope has the documented keys", set(env) == {"ok", "tool", "status", "output", "outputs", "verified",
              "dryRun", "summary", "result", "diagnostics", "truncated", "fullResultPath", "elapsedSeconds", "skill"}, sorted(env))
    fail = bridge.failure("ffmpeg.edit.cut", "TOOL_FAILED", "boom", upstream={"exit_code": 1}, stderr="x")
    check("the failure envelope has the documented keys", set(fail) >= {"ok", "error", "errorKind", "code", "retryable", "hint",
                                                                       "upstream", "stderrTail"} and fail["ok"] is False)

    home = data.install("ffmpeg-video")
    user = pathlib.Path(tempfile.mkdtemp(prefix="ffv-ü-"))
    try:
        cases = [{"tool": "ffmpeg.nope"}, {"tool": "ffmpeg.edit.cut", "input": str(user / "vidéo.mp4"), "output": "a.mp4"},
                 {"tool": "ffmpeg.edit.cut", "input": "https://x/y.mp4", "output": "a.mp4"},
                 {"tool": "ffmpeg.setup.contract", "tool_name": "ffmpeg.nope"}, {"tool": "ffmpeg.edit.cut", "bogus": True}]
        shapes = []
        for params in cases:
            doc, out, err, rc = run_process(data, home, params, env=sim_env(data))
            shapes.append(rc == 0 and len(out.strip().splitlines()) == 1 and out.isascii() and isinstance(doc, dict))
        check("every error path prints exactly one ASCII JSON object and exits 0", all(shapes), shapes)
    finally:
        shutil.rmtree(user, ignore_errors=True)
    leftovers = [p for p in data.output_root.rglob("*")] if data.output_root.exists() else []
    check("error paths leave nothing in the output root but reports", all("reports" in p.parts for p in leftovers),
          [str(p) for p in leftovers][:5])

# ---------------------------------------------------------------------------------------------
print("scenario: contract handler")
with FakeDataDir() as data:
    home = data.install("ffmpeg-video")
    doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.setup.contract"}, env=sim_env(data))
    check("contract without tool_name lists 44 tools and spawns nothing", doc and doc.get("ok") and len(doc["result"]["tools"]) == 44)
    doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.setup.contract", "tool_name": "ffmpeg.layer.caption"}, env=sim_env(data))
    spec = (doc or {}).get("result", {}).get("contract", {})
    check("contract with tool_name returns a trimmed spec", doc and doc.get("ok") and spec.get("name") == "ffmpeg.layer.caption"
          and spec.get("examples") and "rules" in spec and len(out) < 40000, out[:300])

# ---------------------------------------------------------------------------------------------
print("scenario: generator and lock")
proc = subprocess.run([sys.executable, "-B", str(REPO / "build" / "ffmpeg-video" / "generate.py"), "--check"],
                      capture_output=True, text=True, encoding="utf-8")
check("generate.py --check passes", proc.returncode == 0, proc.stdout + proc.stderr)
try:
    bridge.verify_vendor(str(SKILL))
    locked = True
except bridge.BridgeError as exc:
    locked = exc.extra
check("the vendored tree matches vendor.lock.json", locked is True, locked)
check("no __pycache__ was written into the skill", not list(SKILL.rglob("__pycache__")), list(SKILL.rglob("__pycache__"))[:3])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
