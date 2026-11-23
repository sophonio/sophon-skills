# ffmpeg-video: the Sophon entrypoint (a bootstrap; the work happens in lib/bridge.py).
#
# Sophon copies only this file, as script.py, into a throwaway workspace folder and puts two
# lines in front of it that define `params`. This bootstrap therefore has to find the installed
# skill folder on its own, check that it is the same release as this file, and then hand the
# call to lib/bridge.py, under this interpreter when it is Python 3.10+ or under a newer one.
#
# Rules for this file (checked by tests/skills/test_ffmpeg_video.py and the build lint):
# - Python 3.6 syntax, standard library only, no __future__ import (the preamble comes first);
# - comments only, never a docstring or any multi-line string;
# - no line may begin with the import keywords unless it names a standard-library module:
#   Sophon pip-installs whatever such a line names, whether it is code or text;
# - exactly one compact ASCII JSON object on stdout, and the exit code is always 0.
import time
import sys
import os
import re
import json
import hashlib
import subprocess
import importlib.util

START = time.time()
sys.dont_write_bytecode = True

# --- GENERATED CONSTANTS BEGIN ---
# Written by build/ffmpeg-video/generate.py; edit policy.json or manifest.base.json instead.
SKILL_NAME = "ffmpeg-video"
SKILL_VERSION = "1.0.0"
VENDOR_TAG = "v3.9.2"
VENDOR_COMMIT = "3f8ba63cc8eb991c1730d57b0215e6127765399a"
VENDOR_LOCK_SHA256 = "b9bfdd058d2430721fb03e312e782653bb10afb3a389e599288cc85b7c8fa35c"
# sha256 of lib/bridge.py; main.py loads no bridge whose bytes differ (rerun generate.py after editing it)
BRIDGE_SHA256 = "6163bbfa9867516c9e08d5d827d3f68012648920a8c4547dd344c1ae1a4ef3d5"
TOOLS = [
    "ffmpeg.inspect.probe",
    "ffmpeg.inspect.cropdetect",
    "ffmpeg.inspect.check",
    "ffmpeg.inspect.scenes",
    "ffmpeg.inspect.look",
    "ffmpeg.inspect.report",
    "ffmpeg.make.insert",
    "ffmpeg.make.background",
    "ffmpeg.make.sequence",
    "ffmpeg.make.waveform",
    "ffmpeg.edit.cut",
    "ffmpeg.edit.join",
    "ffmpeg.edit.silence",
    "ffmpeg.edit.broll",
    "ffmpeg.edit.multicam",
    "ffmpeg.edit.sync",
    "ffmpeg.edit.grid",
    "ffmpeg.edit.pad",
    "ffmpeg.edit.freeze",
    "ffmpeg.edit.loop",
    "ffmpeg.edit.metadata",
    "ffmpeg.adjust.fit",
    "ffmpeg.adjust.crop",
    "ffmpeg.adjust.color",
    "ffmpeg.adjust.speedramp",
    "ffmpeg.adjust.reverse",
    "ffmpeg.adjust.straighten",
    "ffmpeg.adjust.sphere",
    "ffmpeg.adjust.stabilize",
    "ffmpeg.adjust.deinterlace",
    "ffmpeg.adjust.denoise",
    "ffmpeg.adjust.redact",
    "ffmpeg.layer.caption",
    "ffmpeg.layer.graphics",
    "ffmpeg.layer.overlay",
    "ffmpeg.mix.audio",
    "ffmpeg.mix.loudness",
    "ffmpeg.deliver.export",
    "ffmpeg.deliver.proxy",
    "ffmpeg.project.render",
    "ffmpeg.project.batch",
    "ffmpeg.setup.verify",
    "ffmpeg.setup.doctor",
    "ffmpeg.setup.contract",
]
# --- GENERATED CONSTANTS END ---

MIN_PYTHON = (3, 10)
# Not self-authored: agents write there, and a released copy of this skill never lives there.
SKILL_ROOTS = ("installed", "bundled", "organization")
WORKSPACE_RE = re.compile(r"^(.+?)[\\/]+sandbox[\\/]+workspaces[\\/]+[0-9A-Fa-f]{32}[\\/]*$")

BACKEND_HINT = (
    "Desktop: make Docker unreachable for Sophon (stop Docker Desktop), set "
    "SOPHON__Sandbox__AllowProcessFallback=true and restart the Gateway; this lowers isolation "
    "for every skill. Server: run docker-compose.pro.prebuilt.yml with a Gateway image that adds "
    "FFmpeg 6.1+. Python 3.10+ and FFmpeg must be on the Gateway's PATH."
)
BACKEND_MESSAGES = {
    "docker": ("ffmpeg-video runs only on Sophon's process sandbox backend; this call ran in the "
               "Docker sandbox, which has no FFmpeg and cannot reach your files."),
    "unknown": ("ffmpeg-video runs only on Sophon's process sandbox backend; this call ran in a "
                "working folder that is not a Sophon sandbox workspace, so the skill cannot find "
                "its installed files."),
}
ERROR_KINDS = {"INTERNAL_ERROR": "internal"}


def emit(doc):
    sys.stdout.write(json.dumps(doc, ensure_ascii=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def failure(tool, code, message, hint, retryable=False, extra=None):
    doc = {"ok": False, "tool": tool, "error": message,
           "errorKind": ERROR_KINDS.get(code, code.lower()), "code": code,
           "retryable": retryable, "hint": hint}
    if extra:
        doc.update(extra)
    return doc


def current_dir():
    try:
        return os.getcwd()
    except OSError:
        return ""


def detect_backend(cwd):
    # The Docker backend runs the script in /workspace; the process backend in
    # <dataDir>/sandbox/workspaces/<32 hex>. /.dockerenv is no signal: the Pro prebuilt
    # deployment runs the process backend inside a container.
    flat = cwd.replace("\\", "/").rstrip("/")
    if flat == "/workspace" or flat.startswith("/workspace/"):
        return "docker", None
    match = WORKSPACE_RE.match(cwd)
    if match:
        return "process", match.group(1)
    if os.environ.get("FFMPEG_VIDEO_SKILL_ROOT"):
        return "process", None
    return "unknown", None


def home_dir():
    return os.path.expanduser("~")


def data_dir_candidates(from_cwd):
    found = []
    if from_cwd:
        found.append(("cwd", from_cwd))
    value = os.environ.get("SOPHON_DATA_DIR")
    if value:
        found.append(("SOPHON_DATA_DIR", value))
    for name in ("SOPHON__DataDirectory", "Sophon__DataDirectory"):
        value = os.environ.get(name)
        if value:
            found.append((name, os.path.expanduser(value)))
    if sys.platform.startswith("linux") and os.environ.get("SOPHON_OS") == "1":
        xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(home_dir(), ".local", "share")
        found.append(("XDG_DATA_HOME", os.path.join(xdg, "sophon")))
    found.append(("home", os.path.join(home_dir(), ".sophon")))
    return [(source, os.path.abspath(path)) for source, path in found]


def resolve_data_dir(from_cwd):
    candidates = data_dir_candidates(from_cwd)
    for source, path in candidates:
        if os.path.isdir(os.path.join(path, "skills")):
            return path, source
    return candidates[0][1], candidates[0][0]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8-sig"))


def check_home(path):
    # None when `path` is this release of the skill, otherwise why it is not.
    if not os.path.isdir(path):
        return "not a folder"
    lock = os.path.join(path, "vendor.lock.json")
    manifest = os.path.join(path, "manifest.json")
    if not os.path.isfile(lock):
        return "no vendor.lock.json"
    if not os.path.isfile(manifest):
        return "no manifest.json"
    try:
        doc = read_manifest(manifest)
    except (OSError, ValueError) as exc:
        return "manifest.json is unreadable (%s)" % exc
    if not isinstance(doc, dict) or doc.get("name") != SKILL_NAME:
        return "manifest name is not %s" % SKILL_NAME
    if doc.get("version") != SKILL_VERSION:
        return "version %s, this call is %s" % (doc.get("version"), SKILL_VERSION)
    try:
        digest = sha256_file(lock)
    except OSError as exc:
        return "vendor.lock.json is unreadable (%s)" % exc
    if digest != VENDOR_LOCK_SHA256:
        return "vendor.lock.json does not match this release (sha256 %s)" % digest[:12]
    bridge = os.path.join(path, "lib", "bridge.py")
    if not os.path.isfile(bridge):
        return "lib/bridge.py is missing"
    try:
        digest = sha256_file(bridge)
    except OSError as exc:
        return "lib/bridge.py is unreadable (%s)" % exc
    if digest != BRIDGE_SHA256:
        return "lib/bridge.py does not match this release (sha256 %s)" % digest[:12]
    return None


def list_folders(base):
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    return [os.path.join(base, name) for name in names if os.path.isdir(os.path.join(base, name))]


def home_candidates(data_dir):
    seen = set()
    found = []

    def add(source, path):
        key = os.path.normcase(os.path.abspath(path))
        if key not in seen:
            seen.add(key)
            found.append((source, os.path.abspath(path)))

    value = os.environ.get("FFMPEG_VIDEO_SKILL_ROOT")
    if value:
        add("FFMPEG_VIDEO_SKILL_ROOT", os.path.expanduser(value))
    if data_dir:
        add("installed", os.path.join(data_dir, "skills", "installed", SKILL_NAME))
        for root in SKILL_ROOTS:
            for path in list_folders(os.path.join(data_dir, "skills", root)):
                add(root, path)
    # `sophon dev install` always copies into ~/.sophon, whatever SOPHON_DATA_DIR says
    for path in list_folders(os.path.join(home_dir(), ".sophon", "skills", "installed")):
        add("dev-install", path)
    return found


def find_home(data_dir):
    tried = []
    skipped = 0
    for source, path in home_candidates(data_dir):
        reason = check_home(path)
        if reason is None:
            return path, tried, skipped
        if reason in ("no vendor.lock.json", "not a folder") and source not in ("FFMPEG_VIDEO_SKILL_ROOT", "installed"):
            skipped += 1
            continue
        tried.append({"path": path, "source": source, "reason": reason})
    return None, tried, skipped


def path_entries():
    return [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]


def python_candidates():
    found = []
    value = os.environ.get("FFMPEG_VIDEO_PYTHON")
    if value:
        found.append([value])
    windows = os.name == "nt"
    if windows:
        found.append(["py", "-3"])
    minors = list(range(14, MIN_PYTHON[1] - 1, -1))
    folders = path_entries() + ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
    for folder in folders:
        for minor in minors:
            name = "python3.%d" % minor + (".exe" if windows else "")
            path = os.path.join(folder, name)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                found.append([path])
    if windows:
        bases = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python"),
                 os.environ.get("ProgramFiles", ""), "C:\\"]
        for base in bases:
            for minor in minors:
                path = os.path.join(base, "Python3%d" % minor, "python.exe")
                if base and os.path.isfile(path):
                    found.append([path])
    return found


def python_qualifies(command):
    probe = command + ["-c", "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 3)"]
    try:
        proc = subprocess.run(probe, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=5)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def find_python():
    tried = []
    for command in python_candidates():
        if command in tried:
            continue
        tried.append(command)
        if python_qualifies(command):
            return command, tried
    return None, tried


def stderr_tail(data):
    lines = data.decode("utf-8", "replace").strip().splitlines()[-12:]
    return "\n".join(line[:300] for line in lines)


def run_reexec(tool, command, home, payload):
    bridge = os.path.join(home, "lib", "bridge.py")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(command + ["-B", "-X", "utf8", bridge, "--stdin"],
                          input=json.dumps(payload).encode("utf-8"), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env)
    lines = proc.stdout.decode("utf-8", "replace").strip().splitlines()
    if lines:
        try:
            doc = json.loads(lines[-1])
            if isinstance(doc, dict):
                return doc
        except ValueError:
            pass
    return failure(tool, "INTERNAL_ERROR",
                   "lib/bridge.py under %s printed no result (exit %s)" % (" ".join(command), proc.returncode),
                   "Run ffmpeg.setup.doctor; if this persists, reinstall the skill.",
                   extra={"stderrTail": stderr_tail(proc.stderr)})


def load_bridge(home):
    # Run exactly the bytes whose hash matches, not whatever the file holds a moment later.
    path = os.path.join(home, "lib", "bridge.py")
    with open(path, "rb") as handle:
        source = handle.read()
    if hashlib.sha256(source).hexdigest() != BRIDGE_SHA256:
        raise RuntimeError("lib/bridge.py changed after it was verified")
    spec = importlib.util.spec_from_loader("ffvideo_bridge", loader=None, origin=path)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = path
    sys.modules["ffvideo_bridge"] = module
    exec(compile(source, path, "exec"), module.__dict__)
    return module


def main(raw):
    if raw is None:
        raw = json.loads(os.environ.get("SOPHON_PARAMS") or "{}")
    params = dict(raw) if isinstance(raw, dict) else {}
    tool = params.pop("tool", None)
    if not isinstance(tool, str) or tool not in TOOLS:
        return {"error": "Unknown tool: %s" % (tool,)}

    cwd = current_dir()
    backend, from_cwd = detect_backend(cwd)
    if backend != "process":
        return failure(tool, "BACKEND_UNSUPPORTED", BACKEND_MESSAGES[backend], BACKEND_HINT,
                       extra={"backend": backend})

    data_dir, data_source = resolve_data_dir(from_cwd)
    home, tried, skipped = find_home(data_dir)
    if home is None:
        return failure(tool, "VENDOR_NOT_FOUND",
                       "cannot find the installed ffmpeg-video %s folder (lock %s)" % (SKILL_VERSION, VENDOR_LOCK_SHA256[:12]),
                       "Reinstall or update the ffmpeg-video skill. A development copy can be named "
                       "with the FFMPEG_VIDEO_SKILL_ROOT environment variable of the Gateway.",
                       extra={"dataDir": data_dir, "dataDirSource": data_source,
                              "candidates": tried, "otherSkillFolders": skipped})

    payload = {"tool": tool, "params": params, "home": home, "data_dir": data_dir,
               "start": START, "cwd0": cwd, "backend": backend}
    if sys.version_info >= MIN_PYTHON:
        return load_bridge(home).run(**payload)

    command, tried_pythons = find_python()
    if command is None:
        found = "%d.%d.%d" % tuple(sys.version_info[:3])
        return failure(tool, "PYTHON_UNSUPPORTED",
                       "ffmpeg-video needs Python 3.10 or later; Sophon ran Python %s and no newer "
                       "interpreter was found" % found,
                       "Install Python 3.10+ and put it first on the Gateway's PATH (as python or "
                       "python3), or point the FFMPEG_VIDEO_PYTHON environment variable of the "
                       "Gateway at it, then restart the Gateway.",
                       extra={"python": found, "tried": [" ".join(c) for c in tried_pythons]})
    payload["reexec"] = command
    return run_reexec(tool, command, home, payload)


try:
    RESULT = main(globals().get("params"))
except Exception as exc:  # noqa: BLE001 - the one place every failure becomes a result
    RESULT = failure(None, "INTERNAL_ERROR", "ffmpeg-video bootstrap failed: %s: %s" % (type(exc).__name__, exc),
                     "Run ffmpeg.setup.doctor; if this persists, reinstall the skill.")
emit(RESULT)
