"""ffmpeg-video runtime: one Sophon tool call -> one vendored ffmpeg-skill script run.

main.py (the bootstrap Sophon runs) finds the installed skill folder, checks it is this release
and calls run() here, in-process on Python 3.10+ or through `bridge.py --stdin` under a newer
interpreter. run() never raises and always returns one result document (the envelope):

  success  {ok, tool, status, output, outputs, verified, dryRun, summary, result, diagnostics,
            truncated, fullResultPath, elapsedSeconds, skill}
  failure  {ok: false, tool, error, errorKind, code, retryable, hint, upstream, stderrTail, ...}

What happens in between, in order:
  1. the vendored tree is hashed against vendor.lock.json (VENDOR_CORRUPT on any drift);
  2. the call gets a temp folder <outputRoot>/.tmp/<uuid> (its cwd, TMP and TEMP) and a deadline
     D = sandbox.timeoutSeconds - 60 read from the installed manifest;
  3. the child environment is built (UTF-8, offline ASR models, PATH plus well-known FFmpeg
     folders, FFMPEG_SKILL_READ_ONLY for the read-only tools);
  4. preflight: ffmpeg and ffprobe 6.1+ on that PATH, free disk space;
  5. the arguments are validated against lib/tool-map.json (types, choices, exclusions, path roles
     and write roots), then the special handlers (render, batch, verify, doctor, contract) run;
  6. the vendored mcp/server.py build_argv() turns them into argv, with server._SPECS filled from
     the tool map, and the vendored _common.run_tool() runs the script under the deadline;
  7. cleanup (a failed run's own partial outputs, never a file upstream reports as written and
     kept or one another process put there, this run's hidden siblings and dead locks, the temp
     folder), then the envelope, compacted and capped, with an oversize result spilled to
     <outputRoot>/reports/.

Standard library only. Nothing here writes inside the skill folder.
"""
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid

SKILL_NAME = "ffmpeg-video"
VENDOR_REL = "vendor/ffmpeg-skill"
OUTPUT_PARTS = ("documents", "video", "ffmpeg-video")
DEFAULT_TIMEOUT_SECONDS = 1800
DEADLINE_MARGIN = 60          # D = S - 60: room for the child's stop, cleanup and printing
FFMPEG_TIMEOUT_MARGIN = 30    # the default --timeout stays this far inside the call's deadline
MTIME_SLACK = 2               # seconds: a coarse file clock (FAT, HFS+) may date a new file just before the run
MIN_FFMPEG = (6, 1)
MIN_FREE_MB = 2048
INLINE_JSON_MAX = 64 * 1024
DOCUMENT_MAX = 1024 * 1024
BRIEF_CAP = 40000
FULL_CAP = 120000
LIST_MAX, LIST_HEAD, LIST_TAIL = 50, 40, 10
STRING_MAX = 2000
STDERR_LINES, STDERR_LINE_MAX = 12, 300
STRIPPED_KEYS = ("tool", "apiKey", "accessToken")
WRAPPER_PARAMS = ("detail", "project_json", "recipe_json", "use_cache", "tool_name")
SCRUBBED_ENV = ("FFMPEG_SKILL_MCP_FULL", "_FFMPEG_SKILL_OWNED", "PYTHONPATH", "PYTHONSTARTUP",
                "PYTHONINSPECT", "FFMPEG_SKILL_READ_ONLY", "FFMPEG_SKILL_HW", "_FFMPEG_SKILL_HW_EXPLICIT",
                "FFMPEG_SKILL_TIMEOUT", "SOPHON_PARAMS")
KEPT_SIBLINGS = (".ffskill-audit.jsonl", ".ffskill_cache.json")
TEXT_KEYS = ("text", "transcript", "words", "cues", "lines")
LIFTED_KEYS = ("status", "output", "verified", "dry_run", "summary", "warnings", "notes", "exit_code")
CASE_INSENSITIVE = os.name == "nt" or sys.platform == "darwin"
URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")
# Credential stores refused as inputs for every tool (relative to the user's home, then env folders).
SECRET_HOME_ENTRIES = (".ssh", ".aws", ".azure", ".gnupg", ".docker", ".kube", ".config", ".netrc",
                       ".git-credentials", ".npmrc", ".pypirc", ".pgpass", ".vault-token",
                       os.path.join("Library", "Keychains"))
SECRET_ENV_ENTRIES = (("APPDATA", ("Microsoft",)), ("LOCALAPPDATA", ("Microsoft", "Credentials")),
                      ("LOCALAPPDATA", ("Microsoft", "Vault")))
LANG_SUFFIX_RE = re.compile(r"^(.*[^:]):([A-Za-z]{2,3}(?:-[A-Za-z0-9]{1,8})*)$")
TRUE_WORDS = ("true", "yes", "on", "1")
FALSE_WORDS = ("false", "no", "off", "0")
BATCH_REFUSED_FLAGS = ("--plan", "--watch", "--work", "--keep", "--audit-log", "--cache", "--progress")
BATCH_REFUSED_SCRIPTS = ("batch.py", "render.py", "verify.py")
STEP_SWITCHES = ("--json",)   # options a step may carry that no tool-map parameter names (batch adds --json anyway)
STEP_REFUSED_PARAMS = {"overwrite": "set the batch's own overwrite parameter instead"}
NUMBER_RE = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
EXT_RE = re.compile(r"[A-Za-z0-9]{1,8}")
KEPT_REASONS = ("output_exists", "output_locked")  # upstream refused before writing: the file there is not this run's

ERRORS = {
    # code: (errorKind, retryable, default hint)
    "BACKEND_UNSUPPORTED": ("backend_unsupported", False, None),
    "PYTHON_UNSUPPORTED": ("python_unsupported", False, None),
    "DEPENDENCY_MISSING": ("dependency_missing", False,
                           "Install FFmpeg 6.1+ (it includes ffprobe), make sure the Gateway's PATH reaches it, "
                           "restart the Gateway and run ffmpeg.setup.doctor."),
    "VENDOR_NOT_FOUND": ("vendor_not_found", False, "Reinstall or update the ffmpeg-video skill."),
    "VENDOR_CORRUPT": ("vendor_corrupt", True,
                       "The installed skill files were changed: reinstall or update the ffmpeg-video skill."),
    "INVALID_ARGUMENT": ("invalid_argument", False,
                         "Fix the named parameters; ffmpeg.setup.contract with tool_name shows the full rules."),
    "ARGUMENT_REJECTED": ("argument_rejected", False,
                          "The tool refused a value; see stderrTail and ffmpeg.setup.contract with tool_name."),
    "PATH_NOT_ALLOWED": ("path_not_allowed", False,
                         "Read media from your own folders or the output root, and write under the output root "
                         "(a relative output path lands there); ffmpeg.setup.doctor shows outputRoot."),
    "INSUFFICIENT_DISK": ("insufficient_disk", False, "Free disk space on the output volume and try again."),
    "TIMEOUT": ("timeout", False,
                "Long jobs must finish inside the skill's time limit: render with use_cache (re-renders reuse "
                "finished stages), set fast: true, edit a proxy (ffmpeg.deliver.proxy) or a shorter section."),
    "TOOL_FAILED": ("tool_failed", False, "See upstream.error for what the tool reported."),
    "INTERNAL_ERROR": ("internal", False, "Run ffmpeg.setup.doctor; if this persists, reinstall the skill."),
}

INSTALL_HINTS = {
    "Windows": "winget install Gyan.FFmpeg (or choco install ffmpeg), then restart the Sophon Gateway",
    "Darwin": "brew install ffmpeg (a launchd Gateway also needs /opt/homebrew/bin on its PATH), then restart the Gateway",
    "Linux": "sudo apt install ffmpeg (Ubuntu 24.04+ / Debian 13+ ship 6.1 or later), then restart the Gateway",
}
UPGRADE_HINTS = {
    "Windows": "winget upgrade Gyan.FFmpeg, then restart the Sophon Gateway",
    "Darwin": "brew upgrade ffmpeg, then restart the Gateway",
    "Linux": "use a distribution whose ffmpeg package is 6.1+ (Ubuntu 24.04, Debian 13) or a static 6.1+ build "
             "ahead of the old one on PATH, then restart the Gateway",
}


class BridgeError(Exception):
    """A refusal or failure that becomes the failure envelope."""

    def __init__(self, code, message, hint=None, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.extra = extra


# ----------------------------------------------------------------------------- small helpers

def one_line(text, limit=500):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def tail_lines(text):
    lines = [ln for ln in str(text or "").strip().splitlines() if ln.strip()][-STDERR_LINES:]
    return "\n".join(ln[:STDERR_LINE_MAX] for ln in lines)


def stamp():
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_json_file(path, limit=DOCUMENT_MAX, what="file"):
    try:
        size = os.path.getsize(path)
        if size > limit:
            raise BridgeError("INVALID_ARGUMENT", f"{what} {path} is {size} bytes; the limit is {limit}")
        with open(path, "rb") as handle:
            return json.loads(handle.read().decode("utf-8-sig"))
    except BridgeError:
        raise
    except (OSError, ValueError) as exc:
        raise BridgeError("INVALID_ARGUMENT", f"cannot read {what} {path}: {one_line(exc, 200)}") from None


def norm(path):
    path = os.path.normpath(path)
    return os.path.normcase(path).lower() if CASE_INSENSITIVE else path


def within(path, root):
    r"""True when `path` is `root` or inside it (separator-aware, case-insensitive on Windows and macOS).

    Paths that cannot be compared (different drives, or a \\?\ or UNC spelling against a drive
    letter) are not inside, so a protection check must not rest on this alone: path_text and
    real_path refuse network and device spellings first and compare plain_path() forms."""
    a, b = norm(path), norm(root)
    try:
        return os.path.commonpath([a, b]) == b
    except ValueError:
        return False  # different drives


def double_separator(text):
    r"""A UNC (\\host\share, //host/share) or device (\\?\..., \\.\...) spelling."""
    return len(text) >= 2 and text[0] in "\\/" and text[1] in "\\/"


def plain_path(path):
    r"""`path` without the extended-length prefix realpath can return (\\?\C:\x -> C:\x,
    \\?\UNC\host\x -> \\host\x), so it compares with the plain spellings of the roots."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path


def truthy(value):
    return value is not None and value is not False and value != "" and value != []


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def plain_number(value):
    return int(value) if isinstance(value, float) and value.is_integer() else value


def caseless_glob(pattern):
    """upstream batch.py's caseless_glob(): every letter outside a [...] class in either case, so the
    files checked here are the files batch.py will find on a case-sensitive filesystem too."""
    out, in_class, first = [], False, -1
    for i, ch in enumerate(pattern):
        if in_class:
            out.append(ch)
            if ch == "]" and i > first:
                in_class = False
        elif ch == "[":
            first = i + 2 if pattern[i + 1:i + 2] == "!" else i + 1
            in_class = "]" in pattern[first + 1:]
            out.append(ch if in_class else "[[]")
        elif ch.isalpha() and ch.lower() != ch.upper():
            out.append(f"[{ch.lower()}{ch.upper()}]")
        else:
            out.append(ch)
    return "".join(out)


# ----------------------------------------------------------------------------- vendor tree

def verify_vendor(home):
    """Hash every locked file (and the generated tool map) and refuse any unlocked code file."""
    lock_path = os.path.join(home, "vendor.lock.json")
    try:
        with open(lock_path, "rb") as handle:
            lock = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise BridgeError("VENDOR_CORRUPT", f"vendor.lock.json is unreadable: {one_line(exc, 200)}")
    problems = []
    listed = set()
    for entry in list(lock.get("files") or []) + list(lock.get("generated") or []):
        rel = str(entry.get("path", ""))
        listed.add(rel)
        full = os.path.join(home, *rel.split("/"))
        try:
            with open(full, "rb") as handle:
                data = handle.read()
        except OSError:
            problems.append(f"{rel}: missing")
            continue
        if sha256_bytes(data) != entry.get("sha256") or ("bytes" in entry and len(data) != entry["bytes"]):
            problems.append(f"{rel}: changed")
    vendor = os.path.join(home, *VENDOR_REL.split("/"))
    for folder, dirs, files in os.walk(vendor):
        for name in files:
            rel = os.path.relpath(os.path.join(folder, name), home).replace(os.sep, "/")
            if rel not in listed and os.path.splitext(name)[1].lower() in (".py", ".pyc", ".pyo", ".pth", ".so", ".pyd", ".dll"):
                problems.append(f"{rel}: not in vendor.lock.json")
    if problems:
        raise BridgeError("VENDOR_CORRUPT", f"the vendored ffmpeg-skill files do not match vendor.lock.json ({len(problems)} problems)",
                          problems=problems[:20])
    return lock


_SERVER = {}


def load_server(home):
    """The vendored mcp/server.py as module ffvideo_server, with _SPECS filled from the tool map."""
    path = os.path.join(home, *VENDOR_REL.split("/"), "mcp", "server.py")
    key = norm(path)
    if key in _SERVER:
        return _SERVER[key]
    spec = importlib.util.spec_from_file_location("ffvideo_server", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ffvideo_server"] = module
    spec.loader.exec_module(module)
    _SERVER[key] = module
    return module


def prefill_specs(server, tool_map):
    server._SPECS.clear()
    for key, entry in tool_map["tools"].items():
        if entry.get("spec"):
            server._SPECS[key] = entry["spec"]


# ----------------------------------------------------------------------------- PATH and preflight

def well_known_ffmpeg_dirs():
    """Folders FFmpeg installers use that a service's PATH often lacks; only those holding ffmpeg."""
    found = []
    system = platform.system()
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        choco = os.environ.get("ChocolateyInstall", r"C:\ProgramData\chocolatey")
        candidates = [os.path.join(local, "Microsoft", "WinGet", "Links"),
                      os.path.join(program_files, "ffmpeg", "bin"),
                      os.path.join(choco, "bin"),
                      os.path.join(os.path.expanduser("~"), "scoop", "shims")]
        packages = os.path.join(local, "Microsoft", "WinGet", "Packages")
        try:
            for name in sorted(os.listdir(packages)):
                if name.lower().startswith("gyan.ffmpeg"):
                    base = os.path.join(packages, name)
                    for sub in sorted(os.listdir(base)):
                        candidates.append(os.path.join(base, sub, "bin"))
        except OSError:
            pass
        exe = "ffmpeg.exe"
    elif system == "Darwin":
        candidates, exe = ["/opt/homebrew/bin", "/usr/local/bin"], "ffmpeg"
    else:
        candidates, exe = ["/usr/local/bin", "/usr/bin", "/snap/bin"], "ffmpeg"
    for folder in candidates:
        if folder and os.path.isfile(os.path.join(folder, exe)) and folder not in found:
            found.append(folder)
    return found


def child_path():
    entries = [e for e in os.environ.get("PATH", "").split(os.pathsep) if e]
    first = os.environ.get("FFMPEG_VIDEO_FFMPEG_DIR")
    if first:
        entries.insert(0, os.path.expanduser(first))
    keys = {norm(e) for e in entries}
    for folder in well_known_ffmpeg_dirs():
        if norm(folder) not in keys:
            entries.append(folder)
            keys.add(norm(folder))
    return os.pathsep.join(entries)


def read_ff_version(exe, env):
    """(major, minor) from `<exe> -version`, None when it does not say (a git build), or 'error'."""
    try:
        proc = subprocess.run([exe, "-version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, encoding="utf-8", errors="replace", timeout=20, env=env)
    except (OSError, subprocess.SubprocessError, ValueError):
        return "error", ""
    first = (proc.stdout or "").strip().splitlines()[:1]
    line = first[0] if first else ""
    match = re.search(r"version\s+n?(\d+)\.(\d+)", line)
    return ((int(match.group(1)), int(match.group(2))) if match else None), line


# ----------------------------------------------------------------------------- the call

class Call:
    def __init__(self, tool, params, home, data_dir, start, cwd0, backend, reexec=None):
        self.tool = tool
        self.raw = dict(params or {})
        self.home = os.path.abspath(home)
        self.data_dir = os.path.abspath(data_dir) if data_dir else None
        self.start = float(start or time.time())
        self.cwd0 = cwd0
        self.backend = backend or "process"
        self.reexec = reexec
        self.tmp = None
        self.created_dirs = []
        self.outputs = []          # (param, path, kind, existed_when_resolved)
        self.pre_run = {}          # output file -> it existed when the child started
        self.began = None          # when the child started (None: no tool ran)
        self.doc = None            # the child's result document
        self.watch_dirs = set()    # folders whose new .ffskill siblings this run may leave
        self.notes = []
        self._secret_roots = None
        self.dry_run = False
        self.ok = False
        self.output_root = None
        self.write_roots = []

    # -- setup ------------------------------------------------------------------------------

    def setup(self):
        self.lock = verify_vendor(self.home)
        map_path = os.path.join(self.home, "lib", "tool-map.json")
        with open(map_path, "rb") as handle:
            self.map = json.loads(handle.read().decode("utf-8"))
        self.key = self.map["byName"].get(self.tool)
        if not self.key:
            raise BridgeError("VENDOR_CORRUPT", f"{self.tool} is not in lib/tool-map.json")
        self.entry = self.map["tools"][self.key]
        try:
            with open(os.path.join(self.home, "manifest.json"), "rb") as handle:
                manifest = json.loads(handle.read().decode("utf-8-sig"))
        except (OSError, ValueError):
            manifest = {}
        self.version = manifest.get("version") or self.map["skill"]["version"]
        self.sandbox_seconds = int((manifest.get("sandbox") or {}).get("timeoutSeconds") or DEFAULT_TIMEOUT_SECONDS)
        self.deadline = max(1, self.sandbox_seconds - DEADLINE_MARGIN)
        tool_limit = self.entry.get("deadline")
        self.tool_deadline = min(self.deadline, tool_limit) if tool_limit else self.deadline

        if not self.data_dir:
            raise BridgeError("INTERNAL_ERROR", "no Sophon data folder was found")
        self.real_data_dir = plain_path(os.path.realpath(self.data_dir))
        self.real_home = plain_path(os.path.realpath(self.home))
        self.output_root = plain_path(os.path.realpath(os.path.join(self.data_dir, *OUTPUT_PARTS)))
        os.makedirs(self.output_root, exist_ok=True)
        self.write_roots = [self.output_root] + self.extra_write_roots()

        tmp_base = os.path.join(self.output_root, ".tmp")
        self.sweep_tmp(tmp_base)
        self.tmp = os.path.join(tmp_base, uuid.uuid4().hex)
        os.makedirs(self.tmp)
        os.chdir(self.tmp)
        self.env = self.child_env()

    def extra_write_roots(self):
        roots = []
        for raw in (os.environ.get("FFMPEG_VIDEO_WRITE_ROOTS") or "").split(os.pathsep):
            raw = raw.strip()
            if not raw:
                continue
            path = plain_path(os.path.realpath(os.path.expanduser(raw)))
            if not os.path.isabs(os.path.expanduser(raw)) or not os.path.isdir(path):
                self.notes.append(f"FFMPEG_VIDEO_WRITE_ROOTS entry {raw!r} is not an existing absolute folder; ignored")
            elif self.protected_reason(path):
                self.notes.append(f"FFMPEG_VIDEO_WRITE_ROOTS entry {raw!r} is inside Sophon's own data; ignored")
            else:
                roots.append(path)
        return roots

    def sweep_tmp(self, base):
        horizon = time.time() - 2 * self.sandbox_seconds
        try:
            names = os.listdir(base)
        except OSError:
            return
        for name in names:
            path = os.path.join(base, name)
            try:
                if os.path.getmtime(path) < horizon:
                    shutil.rmtree(path, ignore_errors=True)
            except OSError:
                pass

    def child_env(self):
        scrubbed = {name.upper() for name in SCRUBBED_ENV}
        env = {k: v for k, v in os.environ.items() if k.upper() not in scrubbed}
        env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
                   TMP=self.tmp, TEMP=self.tmp, TMPDIR=self.tmp, PATH=child_path())
        if os.environ.get("FFMPEG_VIDEO_ALLOW_MODEL_DOWNLOAD") != "1":
            env["HF_HUB_OFFLINE"] = "1"
        return env

    def elapsed(self):
        return time.time() - self.start

    def remaining(self):
        return self.tool_deadline - self.elapsed()

    def made_dir(self, path):
        """os.makedirs, remembering each folder created so a dry or failed run can remove it."""
        missing = []
        probe = path
        while probe and not os.path.isdir(probe):
            missing.append(probe)
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        os.makedirs(path, exist_ok=True)
        self.created_dirs.extend(reversed(missing))

    # -- preflight ---------------------------------------------------------------------------

    def find_ff(self):
        found = {}
        for name in ("ffmpeg", "ffprobe"):
            exe = shutil.which(name, path=self.env["PATH"])
            version, line = read_ff_version(exe, self.env) if exe else (None, "")
            found[name] = {"path": exe, "version": version, "line": line}
        return found

    def ff_problems(self, found):
        problems = []
        system = platform.system()
        missing = [n for n in ("ffmpeg", "ffprobe") if not found[n]["path"]]
        if missing:
            problems.append({"code": "ffmpeg_missing",
                             "problem": f"{' and '.join(missing)} not found on the Gateway's PATH",
                             "fix": INSTALL_HINTS.get(system, "install FFmpeg 6.1+ and put it on the Gateway's PATH")})
        for name in ("ffmpeg", "ffprobe"):
            version = found[name]["version"]
            if isinstance(version, tuple) and version < MIN_FFMPEG:
                problems.append({"code": "ffmpeg_too_old",
                                 "problem": f"{name} {version[0]}.{version[1]} is older than 6.1",
                                 "fix": UPGRADE_HINTS.get(system, "install FFmpeg 6.1 or later")})
            elif version == "error":
                problems.append({"code": "ffmpeg_unrunnable", "problem": f"{found[name]['path']} -version did not run",
                                 "fix": "reinstall FFmpeg or point FFMPEG_VIDEO_FFMPEG_DIR at a working build"})
        return problems

    def free_mb(self):
        try:
            return shutil.disk_usage(self.output_root).free // (1024 * 1024)
        except OSError:
            return None

    def min_free_mb(self):
        try:
            return int(os.environ.get("FFMPEG_VIDEO_MIN_FREE_MB") or MIN_FREE_MB)
        except ValueError:
            return MIN_FREE_MB

    def preflight(self):
        found = self.find_ff()
        problems = self.ff_problems(found)
        if problems:
            raise BridgeError("DEPENDENCY_MISSING", problems[0]["problem"], problems[0]["fix"], problems=problems)
        self.ff = found
        return found

    def check_disk(self):
        free = self.free_mb()
        need = self.min_free_mb()
        if free is not None and free < need:
            raise BridgeError("INSUFFICIENT_DISK", f"only {free} MB free on the output volume ({self.output_root}); "
                                                   f"at least {need} MB is needed", freeMb=free, requiredMb=need)

    # -- argument validation -----------------------------------------------------------------

    def invalid(self, message, **extra):
        return BridgeError("INVALID_ARGUMENT", message, **extra)

    def coerce(self, name, kind, value, items="string"):
        if kind == "array":
            values = value if isinstance(value, list) else [value]
            return [self.coerce(name, items or "string", v) for v in values]
        if kind == "boolean":
            if isinstance(value, bool):
                return value
            if is_number(value) and value in (0, 1):
                return bool(value)
            if isinstance(value, str) and value.strip().lower() in TRUE_WORDS + FALSE_WORDS:
                return value.strip().lower() in TRUE_WORDS
        elif kind == "integer":
            if is_number(value) and float(value).is_integer() and math.isfinite(value):
                return int(value)
            if isinstance(value, str) and re.fullmatch(r"\s*[+-]?\d+\s*", value):
                return int(value)
        elif kind == "number":
            if is_number(value) and math.isfinite(value):
                return plain_number(value)
            if isinstance(value, str):
                try:
                    number = float(value)
                except ValueError:
                    number = None
                if number is not None and math.isfinite(number):
                    return plain_number(number)
        elif kind == "string":
            if isinstance(value, str):
                return value
            if is_number(value) and math.isfinite(value):
                return str(plain_number(value))
            if isinstance(value, (dict, list)) and name.endswith("_json"):
                return json.dumps(value)
        else:
            return value
        raise self.invalid(f"{name}: expected {kind}, got {type(value).__name__} {one_line(json.dumps(value, default=str), 80)}")

    def check_choice(self, name, value, allowed):
        values = value if isinstance(value, list) else [value]
        for v in values:
            ok = False
            for choice in allowed:
                if isinstance(choice, str) and str(v) == choice:
                    ok = True
                elif is_number(choice) and not isinstance(v, bool):
                    try:
                        ok = float(v) == float(choice)
                    except (TypeError, ValueError):
                        ok = False
                if ok:
                    break
            if not ok:
                shown = ", ".join(str(c) for c in allowed[:40])
                raise self.invalid(f"{name}: {v!r} is not one of {shown}")

    def validate(self):
        entry = self.entry
        params = entry["params"]
        removed = entry.get("removed") or {}
        given = {k: v for k, v in self.raw.items() if k not in STRIPPED_KEYS and v is not None}

        refused = {k: removed[k] for k in given if k in removed and truthy(given[k])}
        if refused:
            raise self.invalid("not accepted here: " + "; ".join(f"{k} ({why})" for k, why in sorted(refused.items())),
                               refused=refused)
        unknown = sorted(k for k in given if k not in params and k not in removed)
        if unknown:
            raise self.invalid(f"unknown parameter(s) for {self.tool}: {', '.join(unknown)}",
                               unknown=unknown, allowed=sorted(params))
        args = {}
        for name, value in given.items():
            if name in removed:
                continue  # a removed key given as false/empty: nothing to refuse
            spec = params[name]
            args[name] = self.coerce(name, spec.get("type"), value, spec.get("items"))
        for name, allowed in (entry.get("choices") or {}).items():
            if name in args and truthy(args[name]):
                self.check_choice(name, args[name], allowed)

        missing = [n for n in entry.get("required") or [] if not truthy(args.get(n))]
        for rule in entry.get("conditionalRequired") or []:
            when_any, when_none = rule.get("whenAny"), rule.get("whenNone")
            applies = (not when_any or any(truthy(args.get(n)) for n in when_any)) and \
                      (not when_none or not any(truthy(args.get(n)) for n in when_none))
            if applies and not truthy(args.get(rule["param"])) and rule["param"] not in missing:
                missing.append(rule["param"])
        if missing:
            raise self.invalid(f"missing required parameter(s): {', '.join(missing)}", missing=missing)
        for group in entry.get("mutuallyExclusive") or []:
            hit = [n for n in group if truthy(args.get(n))]
            if len(hit) > 1:
                raise self.invalid(f"{' and '.join(hit)} cannot be used together")
        for group in entry.get("oneOfRequired") or []:
            if not any(truthy(args.get(n)) for n in group):
                raise self.invalid(f"give one of: {', '.join(group)}")
        for name, rule in (entry.get("constraints") or {}).items():
            if name in args and truthy(args[name]):
                args[name] = self.apply_constraint(name, rule, args[name])

        self.detail = args.pop("detail", None) or entry.get("defaultDetail") or "brief"
        self.dry_run = bool(args.get("dry_run"))
        if "timeout" in params:
            args["timeout"] = self.clamp_timeout(args.get("timeout"))
        return args

    def apply_constraint(self, name, rule, value):
        kind = rule.get("kind")
        if kind == "relative_name":
            if re.search(r"[\\/]", str(value)) or ".." in str(value) or ":" in str(value):
                raise self.invalid(f"{name}: {rule.get('text') or 'a plain file name pattern'}")
        elif kind == "jobs_cap":
            cap = int(rule.get("max") or 1)
            text = str(value).strip().lower()
            if text == "auto":
                return str(cap)
            if not re.fullmatch(r"\d+", text) or int(text) < 1:
                raise self.invalid(f"{name}: a positive whole number or 'auto'")
            if int(text) > cap:
                self.notes.append(f"{name} lowered from {text} to {cap}")
            return str(min(int(text), cap))
        return value

    def timeout_ceiling(self):
        """The longest per-command --timeout of this tool: fixed by its deadline alone, in whole minutes.

        It must not depend on the moment of the call: render.py hashes --timeout into every stage's
        cache key, so a value that moved with the elapsed time made use_cache and from_stage miss on
        every call. The call's real deadline is enforced around the child (run_tool's per_call)."""
        ceiling = min(float(DEFAULT_TIMEOUT_SECONDS), float(self.tool_deadline - FFMPEG_TIMEOUT_MARGIN))
        if ceiling >= 60:
            ceiling = ceiling // 60 * 60
        return plain_number(max(1.0, ceiling))

    def clamp_timeout(self, value):
        ceiling = self.timeout_ceiling()
        if value is None:
            return ceiling
        if not is_number(value) or value <= 0:
            raise self.invalid("timeout must be a positive number of seconds (0, no limit, is not allowed here)")
        if value > ceiling:
            self.notes.append(f"timeout lowered from {plain_number(value)} to {ceiling} s (the call's deadline)")
            return ceiling
        return plain_number(value)

    # -- paths -------------------------------------------------------------------------------

    def protected_reason(self, real):
        if within(real, self.real_home):
            return "skill_home"
        if self.data_dir and within(real, self.real_data_dir) and not within(real, os.path.join(self.real_data_dir, "documents")):
            return "sophon_data"
        return None

    def secret_roots(self):
        if self._secret_roots is None:
            user = os.path.expanduser("~")
            roots = [os.path.join(user, name) for name in SECRET_HOME_ENTRIES]
            for var, parts in SECRET_ENV_ENTRIES:
                base = os.environ.get(var)
                if base:
                    roots.append(os.path.join(base, *parts))
            self._secret_roots = [plain_path(os.path.realpath(root)) for root in roots]
        return self._secret_roots

    def secret_reason(self, real):
        """Well-known credential stores and .env files are never media, captions or notes."""
        name = os.path.basename(real).lower()
        if name == ".env" or name.startswith(".env."):
            return "credential_store"
        if any(within(real, root) for root in self.secret_roots()):
            return "credential_store"
        return None

    def refuse_path(self, name, value, reason, why):
        return BridgeError("PATH_NOT_ALLOWED", f"{name}: {why}", reason=reason, param=name, path=str(value))

    def path_text(self, name, value):
        if not isinstance(value, str) or not value.strip():
            raise self.invalid(f"{name}: expected a file path")
        if "\x00" in value or "\n" in value or "\r" in value:
            raise self.refuse_path(name, value.strip(), "control_character", "a path cannot hold NUL or line breaks")
        if URL_RE.match(value.strip()):
            raise self.refuse_path(name, value, "url", "URLs are not accepted; give a local file path (nothing is downloaded)")
        text = os.path.expanduser(value.strip())
        if double_separator(text) and not self.in_write_root(text):
            # Checked before any filesystem call: looking at a UNC path makes Windows open an SMB
            # session to that host (sending the account's credentials), and a \\?\ or \\.\ device
            # spelling of a local path slips past the folder comparisons.
            raise self.refuse_path(name, value, "network_path",
                                   "network (UNC) and device paths are not accepted; give a local path")
        return text

    def in_write_root(self, path):
        return any(within(path, root) for root in self.write_roots)

    def real_path(self, name, value, full):
        """realpath in its plain spelling; a link that leads to a network or device path is refused."""
        real = plain_path(os.path.realpath(full))
        if double_separator(real) and not self.in_write_root(real):
            raise self.refuse_path(name, value, "network_path",
                                   "the path leads to a network (UNC) or device path, which is not accepted")
        return real

    def input_path(self, name, value, kind="file", base=None):
        text = self.path_text(name, value)
        full = text if os.path.isabs(text) else os.path.join(base or self.output_root, text)
        real = self.real_path(name, value, full)
        reason = self.protected_reason(real)
        if reason == "skill_home":
            raise self.refuse_path(name, value, reason, "files of the ffmpeg-video skill itself cannot be used as media")
        if reason == "sophon_data":
            raise self.refuse_path(name, value, reason, "Sophon's own data folder is off limits (only its documents folder is readable)")
        if self.secret_reason(real) and not self.in_write_root(real) and not (
                self.data_dir and within(real, os.path.join(self.real_data_dir, "documents"))):
            raise self.refuse_path(name, value, "credential_store",
                                   "credential and key folders (.ssh, .aws, .config, ...) and .env files cannot be used as inputs")
        exists = os.path.isfile(real) if kind == "file" else os.path.isdir(real) if kind == "dir" else os.path.exists(real)
        if not exists:
            what = {"file": "file", "dir": "folder"}.get(kind, "file or folder")
            raise self.invalid(f"{name}: {what} not found: {real}", reason="not_found", param=name, path=real)
        return real

    def output_path(self, name, value, kind="file", base=None):
        text = self.path_text(name, value)
        if os.path.isabs(text):
            full = text
        else:
            if ".." in re.split(r"[\\/]+", text):
                raise self.refuse_path(name, value, "relative_parent", "a relative output path cannot use '..'")
            full = os.path.join(base or self.output_root, text)
        real = self.real_path(name, value, full)
        if not self.in_write_root(real):
            raise self.refuse_path(name, value, "outside_write_roots",
                                   f"outputs must be written under the output root {self.output_root}"
                                   + (" or FFMPEG_VIDEO_WRITE_ROOTS" if len(self.write_roots) > 1 else ""))
        reason = self.protected_reason(real)
        if reason:
            raise self.refuse_path(name, value, reason, "cannot write into Sophon's own data or the skill folder")
        if kind == "dir":
            if os.path.exists(real) and not os.path.isdir(real):
                raise self.invalid(f"{name}: {real} exists and is not a folder")
            folder = real
        else:
            if not os.path.splitext(real)[1]:
                raise self.invalid(f"{name}: an output file needs an extension (.mp4, .png, ...): {real}")
            if os.path.isdir(real):
                raise self.invalid(f"{name}: {real} is a folder; name a file")
            folder = os.path.dirname(real)
        if not os.path.isdir(folder):
            if within(folder, self.output_root):
                self.made_dir(folder)
            else:
                raise self.invalid(f"{name}: the folder {folder} does not exist (folders are created only under the output root)")
        self.outputs.append((name, real, kind, os.path.lexists(real)))
        self.watch_dirs.add(folder)
        return real

    def resolve_role(self, name, role, value, rule=None, base=None):
        if role in ("in_files", "in_paths"):
            items = value if isinstance(value, list) else [value]
            kind = "file" if role == "in_files" else "any"
            return [self.input_path(name, v, kind, base) for v in items]
        if role == "in_file":
            if rule and rule.get("kind") == "lang_suffix":
                # path_text first: it refuses UNC and device spellings before any filesystem probe
                # (an isfile on \\host\share makes Windows open an SMB session to that host).
                text = self.path_text(name, value)
                match = LANG_SUFFIX_RE.match(text)
                if match:
                    self.path_text(name, match.group(1))
                    full = text if os.path.isabs(text) else os.path.join(base or self.output_root, text)
                    if not os.path.isfile(full):
                        return self.input_path(name, match.group(1), "file", base) + ":" + match.group(2)
            return self.input_path(name, value, "file", base)
        if role == "in_dir":
            return self.input_path(name, value, "dir", base)
        if role in ("out_file", "out_side_file"):
            return self.output_path(name, value, "file", base)
        if role == "out_dir":
            return self.output_path(name, value, "dir", base)
        return value

    def resolve_paths(self, args, roles=None):
        roles = dict(self.entry.get("paths") or {}) if roles is None else roles
        constraints = self.entry.get("constraints") or {}
        for name, role in roles.items():
            if name in args and truthy(args[name]):
                args[name] = self.resolve_role(name, role, args[name], constraints.get(name))
        for name, input_name in (self.entry.get("writesBesideInput") or {}).items():
            if truthy(args.get(name)) and args.get(input_name):
                folder = os.path.dirname(str(args[input_name]))
                if not any(within(folder, root) for root in self.write_roots):
                    raise self.refuse_path(name, folder, "outside_write_roots",
                                           f"{name} writes next to {input_name}, and {folder} is outside the write roots; "
                                           "copy the input into the output root first")
                self.watch_dirs.add(folder)
                self.outputs.append((name, folder, "beside", True))
        for name, kind in (self.entry.get("nested") or {}).items():
            if kind == "brand_json" and truthy(args.get(name)):
                self.check_brand(name, args[name])
        return args

    def check_overwrite(self, args):
        if truthy(args.get("overwrite")):
            for name, path, kind, _ in self.outputs:
                if not within(path, self.output_root):
                    raise self.refuse_path(name, path, "overwrite_outside_output_root",
                                           f"overwrite is honoured only inside the output root {self.output_root}")

    def check_brand(self, name, path):
        brand = read_json_file(path, what="brand file")
        if not isinstance(brand, dict):
            raise self.invalid(f"{name}: {path} is not a JSON object")
        base = os.path.dirname(path)
        for key in self.server._common.decision.BRAND_FILE_KEYS:
            if isinstance(brand.get(key), str) and brand[key]:
                self.input_path(f"{name}.{key}", brand[key], "file", base)

    # -- special handlers --------------------------------------------------------------------

    def inline_document(self, name, text):
        if not isinstance(text, str):
            raise self.invalid(f"{name}: expected a JSON object (as an object or a string)")
        if len(text.encode("utf-8")) > INLINE_JSON_MAX:
            raise self.invalid(f"{name} is over {INLINE_JSON_MAX // 1024} KB; write it to a file with fs.write and pass its path")
        try:
            doc = json.loads(text)
        except ValueError as exc:
            raise self.invalid(f"{name} is not valid JSON: {one_line(exc, 200)}") from None
        if not isinstance(doc, dict):
            raise self.invalid(f"{name} must be a JSON object")
        return doc

    def save_document(self, prefix, doc):
        """Write a normalised project or recipe: the output root's projects/ folder, or the temp folder on a dry run."""
        folder = self.tmp if self.dry_run else os.path.join(self.output_root, "projects")
        if not os.path.isdir(folder):
            self.made_dir(folder)
        path = os.path.join(folder, f"{prefix}-{stamp()}.json")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(doc, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return path

    def project_nodes(self, proj, section):
        found = [proj]
        for part in (section.split(".") if section else []):
            name, many = (part[:-2], True) if part.endswith("[]") else (part, False)
            nxt = []
            for node in found:
                value = node.get(name) if isinstance(node, dict) else None
                if many:
                    nxt.extend(value if isinstance(value, list) else [])
                elif isinstance(value, dict):
                    nxt.append(value)
            found = nxt
        return found

    def normalise_project(self, proj, base, label, require_output=True):
        """Check every path a render project names (outputs confined, inputs readable) and make them absolute."""
        if "plan_version" in proj:
            raise self.invalid(f"{label} is a plan document; plans are not supported (use dry_run to preview a render)")
        if require_output and not truthy(proj.get("output")):
            raise self.invalid(f"{label}: the project needs an output path (a relative one lands in the output root)")
        for section, key in self.server._common.decision.PROJECT_PATH_KEYS:
            for node in self.project_nodes(proj, section):
                value = node.get(key) if isinstance(node, dict) else None
                if not isinstance(value, str) or not value:
                    continue
                where = f"{label}.{(section + '.') if section else ''}{key}"
                if section is None and key == "output":
                    node[key] = self.output_path(where, value, "file", base)
                elif section is None and key == "brand":
                    node[key] = self.input_path(where, value, "file", base)
                    self.check_brand(where, node[key])
                else:
                    node[key] = self.input_path(where, value, "file", base)
        return proj

    def prepare_render(self, args):
        project_json = args.pop("project_json", None)
        use_cache = args.pop("use_cache", None)
        template = args.get("template")
        pack = bool(template) and ("," in str(template) or str(template).strip().lower() == "all")
        roles = dict(self.entry.get("paths") or {})
        roles.pop("project", None)
        if pack:
            roles["output"] = "out_dir"
        if template:
            if project_json is not None:
                raise self.invalid("project_json and template cannot be used together (template mode takes the footage as project)")
            if truthy(args.get("project")):
                args["project"] = self.input_path("project", args["project"], "file")
        self.resolve_paths(args, roles)
        renders = not (truthy(args.get("init")) or truthy(args.get("list_templates")))
        if not template and renders:
            if project_json is not None:
                proj = self.inline_document("project_json", project_json)
                proj = self.normalise_project(proj, self.output_root, "project_json")
            elif truthy(args.get("project")):
                source = self.input_path("project", args["project"], "file")
                proj = read_json_file(source, what="project")
                if not isinstance(proj, dict):
                    raise self.invalid(f"project: {source} is not a JSON object")
                proj = self.normalise_project(proj, os.path.dirname(source), "project")
            else:
                proj = None
            if proj is not None:
                args["project"] = self.save_document("render", proj)
        writes_only_side = any(truthy(args.get(k)) for k in ("write_project", "export_timeline"))
        if renders and not pack and not writes_only_side and truthy(args.get("project")):
            stop_after = args.get("stop_after")
            if stop_after and stop_after != "export" and not self.dry_run:
                work = os.path.join(self.output_root, "previews", stamp())
                self.notes.append(f"stop_after {stop_after}: the preview stage files are kept in {work}")
            else:
                work = os.path.join(self.tmp, "work")
            args["work"] = work
            if use_cache:
                cache = os.path.join(self.output_root, ".cache", "render")
                os.makedirs(cache, exist_ok=True)
                args["cache"] = cache
        elif use_cache:
            self.notes.append("use_cache applies to a single project render; ignored")
        return args

    def prepare_batch(self, args):
        recipe_json = args.pop("recipe_json", None)
        roles = dict(self.entry.get("paths") or {})
        roles.pop("recipe", None)
        self.resolve_paths(args, roles)
        if recipe_json is not None:
            recipe = self.inline_document("recipe_json", recipe_json)
            base = self.output_root
        else:
            source = self.input_path("recipe", args["recipe"], "file")
            recipe = read_json_file(source, what="recipe")
            if not isinstance(recipe, dict):
                raise self.invalid(f"recipe: {source} is not a JSON object")
            base = os.path.dirname(source)
        self.check_recipe_names(recipe)
        if truthy(args.get("folder")):
            self.check_batch_matches(args["folder"], recipe.get("glob") or "*")
        if truthy(recipe.get("project")):
            project = self.input_path("recipe.project", recipe["project"], "file", base)
            proj = read_json_file(project, what="recipe.project")
            if not isinstance(proj, dict):
                raise self.invalid(f"recipe.project: {project} is not a JSON object")
            proj.pop("output", None)  # batch names each item's output itself
            checked = self.normalise_project(proj, os.path.dirname(project), "recipe.project", require_output=False)
            recipe["project"] = self.save_document("batch-project", checked)
        steps = recipe.get("steps")
        if steps is not None:
            if not isinstance(steps, list):
                raise self.invalid("recipe.steps must be a list of steps, each a list of strings")
            for i, step in enumerate(steps):
                self.check_step(i, step, base)
        outdir = recipe.get("output_dir")
        if truthy(outdir):
            recipe["output_dir"] = self.output_path("recipe.output_dir", outdir, "dir")
        else:
            recipe["output_dir"] = self.output_path("recipe.output_dir", os.path.join("batch", stamp()), "dir")
        args["recipe"] = self.save_document("batch-recipe", recipe)
        return args

    def check_recipe_names(self, recipe):
        """glob, suffix and ext become parts of the paths upstream builds (folder/glob and
        output_dir/<stem><suffix>.<ext>): none of them may climb out of its folder."""
        for key in ("glob", "suffix", "ext"):
            if recipe.get(key) is not None and not isinstance(recipe[key], str):
                raise self.invalid(f"recipe.{key} must be a string")
        glob = recipe.get("glob") or ""
        if glob and ("\\" in glob or ":" in glob or "\x00" in glob or glob.startswith("/") or os.path.isabs(glob)
                     or ".." in glob.split("/")):
            raise self.refuse_path("recipe.glob", glob, "glob_outside_folder",
                                   "the glob matches names inside the batch folder, like *.mp4 or sub/*.mov "
                                   "(no '..', drive, root, backslash or ':')")
        suffix = recipe.get("suffix") or ""
        if re.search(r"[\\/:\x00]", suffix) or ".." in suffix:
            raise self.refuse_path("recipe.suffix", suffix, "suffix_not_a_name",
                                   "the suffix is part of a file name, like _final (no folder separators, ':' or '..')")
        ext = recipe.get("ext") or ""
        if ext and not EXT_RE.fullmatch(ext):
            raise self.refuse_path("recipe.ext", ext, "ext_not_a_name",
                                   "the extension is letters and digits only, like mp4 (at most 8)")

    def check_batch_matches(self, folder, glob):
        """Check every file the glob matches as an input, the way upstream will find it: a link
        inside the folder may lead into Sophon's data or onto a network share."""
        try:
            for match in pathlib.Path(folder).glob(caseless_glob(glob)):
                if match.is_file():
                    self.input_path("recipe.glob", str(match), "file")
        except (OSError, ValueError, NotImplementedError) as exc:
            raise self.invalid(f"recipe.glob: {glob!r} cannot be matched in {folder}: {one_line(exc, 200)}") from None

    def step_contract(self, script, where):
        """The tool-map entry of a step's script, its options (flag -> parameter) and its positionals."""
        for entry in self.map["tools"].values():
            spec = entry.get("spec") or {}
            if entry.get("script") == f"scripts/{script}" and spec:
                break
        else:
            raise self.invalid(f"{where}: {script} is not one of the ffmpeg-video tool scripts")
        params = entry["params"]
        flags = {}
        for name, prop in ((spec.get("input_schema") or {}).get("properties") or {}).items():
            cli = prop.get("cli")
            if isinstance(cli, list) and (params.get(name) or {}).get("source") == "upstream":
                flags.update((flag, name) for flag in cli)
        positional = [name for name in (spec.get("mcp") or {}).get("positional") or [] if name in params]
        return entry, flags, positional

    def check_step(self, i, step, base):
        """Read a step the way argparse will, allowing only what the step's own tool accepts.

        Options are spelled in full and exactly: argparse would read an abbreviation (--outp) or an
        attached value (-oPATH) as another option. A value that starts with '-' is joined to its
        option (--start=-1). Every file a step writes is {out}; every path it reads is checked and
        passed absolute, since the step runs in another folder; {in} and {out} stand alone."""
        where = f"recipe.steps[{i}]"
        if not isinstance(step, list) or not step or not all(isinstance(t, str) for t in step):
            raise self.invalid(f"{where} must be a non-empty list of strings")
        script = step[0]
        if re.search(r"[\\/]", script) or not script.endswith(".py") or script.startswith("_"):
            raise self.invalid(f"{where}: the first item names one of the tool scripts, like cut.py")
        if script in BATCH_REFUSED_SCRIPTS:
            raise self.invalid(f"{where}: {script} cannot run as a batch step (use recipe.project for a render)")
        entry, flags, positional = self.step_contract(script, where)
        tokens, out, j, slot, after_dashes = step[1:], [], 0, 0, False
        while j < len(tokens):
            token, at = tokens[j], f"{where}[{j + 1}]"
            if token == "--" and not after_dashes:
                after_dashes = True
                out.append(token)
                j += 1
                continue
            if token.startswith("-") and not after_dashes and not NUMBER_RE.fullmatch(token):
                flag, joined, value = token.partition("=")
                name = self.step_option(at, script, flag, flags, entry)
                if name is None or entry["params"][name].get("type") == "boolean":
                    if joined:
                        raise self.invalid(f"{at}: {flag} is a switch and takes no value")
                    out.append(token)
                    j += 1
                    continue
                if joined:
                    if not flag.startswith("--"):
                        raise self.invalid(f"{at}: give {flag} and its value as two items (or the long option with '=')")
                    out.append(f"{flag}={self.step_value(at, name, value, entry, base)}")
                    j += 1
                    continue
                if j + 1 >= len(tokens):
                    raise self.invalid(f"{at}: {flag} needs a value")
                value = tokens[j + 1]
                if value.startswith("-") and not NUMBER_RE.fullmatch(value):
                    raise self.invalid(f"{at}: a value starting with '-' goes joined to its option ({flag}=VALUE)")
                out += [flag, self.step_value(f"{where}[{j + 2}]", name, value, entry, base)]
                j += 2
                continue
            if slot >= len(positional):
                raise self.invalid(f"{at}: {script} takes no further value here: {token!r}")
            name = positional[slot]
            out.append(self.step_value(at, name, token, entry, base))
            if entry["params"][name].get("type") != "array":
                slot += 1
            j += 1
        step[1:] = out

    def step_option(self, at, script, flag, flags, entry):
        """The parameter an option names (None for a harmless switch), or a refusal."""
        if flag in BATCH_REFUSED_FLAGS:
            raise self.invalid(f"{at}: {flag} is not accepted in a batch step")
        if flag in STEP_SWITCHES:
            return None
        name = flags.get(flag)
        if name is None:
            raise self.invalid(f"{at}: {flag} is not an option of {script}; spell options in full "
                               "(ffmpeg.setup.contract with tool_name lists them)")
        if name in STEP_REFUSED_PARAMS:
            raise self.invalid(f"{at}: {flag} is not accepted in a batch step; {STEP_REFUSED_PARAMS[name]}")
        if name in (entry.get("writesBesideInput") or {}):
            raise self.invalid(f"{at}: {flag} writes next to the step's input, which a batch cannot confine")
        return name

    def step_value(self, at, name, value, entry, base):
        role = (entry.get("paths") or {}).get(name)
        rule = (entry.get("constraints") or {}).get(name)
        if value in ("{in}", "{out}"):
            if value == "{in}" and role and role.startswith("out_"):
                raise self.invalid(f"{at}: {name} may only name {{out}}")
            return value
        if "{in}" in value or "{out}" in value:
            raise self.invalid(f"{at}: {{in}} and {{out}} stand alone as a value, not inside {value!r}")
        if role and role.startswith("out_"):
            raise self.invalid(f"{at}: {name} may only name {{out}}; a step writes nothing but its output, "
                               "which batch places in output_dir")
        if role and role.startswith("in_"):
            if role in ("in_file", "in_files"):
                real = self.resolve_role(at, "in_file", value, rule, base)  # one item of a list at a time
            else:
                real = self.input_path(at, value, "dir" if role == "in_dir" else "any", base)
            if (entry.get("nested") or {}).get(name) == "brand_json":
                self.check_brand(at, real)
            return real
        if rule and rule.get("kind") == "relative_name":
            self.apply_constraint(at, rule, value)
        if self.names_a_path(value, base):
            return self.input_path(at, value, "any", base)
        return value

    def names_a_path(self, value, base):
        """Whether the value of a parameter that is not a path still reads as one: then it is checked as one."""
        text = os.path.expanduser(value)
        if os.path.isabs(text) or double_separator(text) or ".." in re.split(r"[\\/]+", text):
            return True
        if os.name == "nt" and re.match(r"[A-Za-z]:", text):
            return True  # C:name is relative to that drive's current folder, not the step's
        return bool(re.search(r"[\\/]", text)) and os.path.exists(os.path.join(base, text))

    def prepare_verify(self, args):
        self.resolve_paths(args)
        out = os.path.join(self.output_root, "verify", stamp())
        args["out"] = self.output_path("out", out, "dir")
        return args

    # -- running ----------------------------------------------------------------------------

    def snapshot_siblings(self):
        names = {}
        stems = self.output_stems()
        for folder in self.watch_dirs:
            try:
                names[folder] = {n for n in os.listdir(folder) if ".ffskill" in n and self.ours(n, stems)}
            except OSError:
                names[folder] = set()
        return names

    def output_stems(self):
        stems = set()
        for _, path, kind, _ in self.outputs:
            if kind == "file":
                base = os.path.basename(path)
                stems.add(base)
                stems.add(os.path.splitext(base)[0])
        return stems

    def ours(self, name, stems):
        if any(name.endswith(k) for k in KEPT_SIBLINGS):
            return False
        if not stems:
            return True
        return any(name.startswith(f".{s}.ffskill") for s in stems)

    def run_script(self, args):
        server = self.server
        cli = {k: v for k, v in args.items() if k not in WRAPPER_PARAMS}
        if self.entry.get("json") == "add":
            cli["json"] = True
        if self.detail == "brief" and self.entry.get("brief"):
            cli["json_brief"] = True
        argv = server.build_argv(self.key, cli)
        script = os.path.join(self.home, *VENDOR_REL.split("/"), *self.entry["script"].split("/"))
        env = dict(self.env)
        if server._contract.mcp_read_only(self.entry["spec"]):
            env[server._contract.READ_ONLY_ENV] = "1"
        if "timeout" in cli:
            env["FFMPEG_SKILL_TIMEOUT"] = str(cli["timeout"])
        remaining = self.remaining()
        if remaining < 5:
            raise BridgeError("TIMEOUT", f"{self.tool} had no time left before the call's deadline", timeoutSeconds=self.tool_deadline)
        per_call = max(1.0, (remaining - 60) / 4)
        ceiling = server._common.runner.child_limit(per_call)
        before = self.snapshot_siblings()
        # what is at each output path as the child starts: a file that appeared after the paths were
        # resolved (another call finishing) is not this run's to remove
        self.pre_run = {path: os.path.lexists(path) for _, path, kind, _ in self.outputs if kind == "file"}
        self.began = time.time()
        proc = server._common.run_tool([script] + argv, per_call=per_call, env=env)
        ran = time.time() - self.began
        return proc, ran, ceiling, before

    def parse_stdout(self, text):
        text = (text or "").strip()
        if not text:
            return None
        for candidate in (text, text.splitlines()[-1]):
            if candidate.startswith("{"):
                try:
                    doc = json.loads(candidate)
                    return doc if isinstance(doc, dict) else None
                except ValueError:
                    continue
        start = text.rfind("\n{")
        if start >= 0:
            try:
                doc = json.loads(text[start + 1:])
                return doc if isinstance(doc, dict) else None
            except ValueError:
                return None
        return None

    def classify(self, proc, doc, ran, ceiling):
        rc = proc.returncode
        err = doc.get("error") if isinstance(doc, dict) and isinstance(doc.get("error"), dict) else {}
        kind, reason = err.get("kind"), err.get("reason")
        message = one_line((err.get("message") or "").splitlines()[0] if err.get("message") else "", 400)
        if rc == 124 and ceiling and ran >= ceiling - 1:
            return "TIMEOUT", (f"{self.tool} hit the wrapper deadline ({round(ceiling)} s left of the call's "
                               f"{self.tool_deadline} s) and was stopped")
        if kind == "timeout" or rc == 124:
            return "TIMEOUT", message or f"{self.tool} timed out"
        if kind == "missing_tool" or reason == "ffmpeg_unsupported" or rc == 127:
            return "DEPENDENCY_MISSING", message or "FFmpeg is missing or too old"
        if doc is None and rc == 2:
            lines = tail_lines(proc.stderr).splitlines()
            return "ARGUMENT_REJECTED", one_line(lines[-1] if lines else "the tool refused its arguments", 400)
        return "TOOL_FAILED", message or f"{self.tool} failed (exit {rc})"

    # -- cleanup -----------------------------------------------------------------------------

    def upstream_error(self):
        doc = self.doc if isinstance(self.doc, dict) else {}
        return doc.get("error") if isinstance(doc.get("error"), dict) else {}

    def claimed_outputs(self):
        """Files upstream's failure document reports as written and kept, that are on disk: the output
        of a render whose check stage failed (the file is finished), a stopped run's kept deliverable."""
        doc = self.doc if isinstance(self.doc, dict) else {}
        paths = []
        for key in ("output", "kept"):
            value = doc.get(key)
            for path in value if isinstance(value, list) else [value]:
                if isinstance(path, str) and path and os.path.isfile(path) and path not in paths:
                    paths.append(path)
        return paths

    def locked_by_other(self, path):
        """Whether a live process other than this one holds upstream's lock on `path`."""
        lock = os.path.join(os.path.dirname(path), f".{os.path.basename(path)}.ffskill-lock")
        try:
            with open(lock, encoding="utf-8", errors="replace") as handle:
                pid = int(handle.read().strip() or "0")
        except (OSError, ValueError):
            return False
        return pid > 0 and pid != os.getpid() and not self.server._common.runner._pid_dead(pid)

    def partial_outputs(self):
        """The output files a failed run leaves that are its own partials, to remove.

        Only files the child could have written: absent when it started and modified since, inside
        the write roots, not claimed by upstream as written and kept, and not locked by another live
        process. Nothing when no tool ran, when upstream refused before writing (output_exists,
        output_locked: the file there belongs to someone else) or when the delivery itself was
        written and only its verification failed."""
        if self.ok or self.began is None:
            return []
        err = self.upstream_error()
        if err.get("kind") == "verification" or err.get("reason") in KEPT_REASONS:
            return []
        claimed = {norm(path) for path in self.claimed_outputs()}
        partials = []
        for _, path, kind, _ in self.outputs:
            if kind != "file" or self.pre_run.get(path, True) or norm(path) in claimed or path in partials:
                continue
            try:
                fresh = os.path.isfile(path) and os.path.getmtime(path) >= self.began - MTIME_SLACK
            except OSError:
                fresh = False
            if fresh and self.in_write_root(path) and not self.locked_by_other(path):
                partials.append(path)
        return partials

    def kept_outputs(self):
        """A failed run's new output files that stay on disk (named in the failure envelope as `kept`)."""
        if self.began is None:
            return []
        partials = set(self.partial_outputs())
        kept = [path for _, path, kind, _ in self.outputs
                if kind == "file" and not self.pre_run.get(path, True) and path not in partials and os.path.isfile(path)]
        for path in self.claimed_outputs():
            if path not in kept and self.in_write_root(plain_path(os.path.realpath(path))):
                kept.append(path)
        return kept

    def cleanup(self, before):
        for path in self.partial_outputs():
            try:
                os.remove(path)
            except OSError:
                pass
        if before is not None:
            stems = self.output_stems()
            pid_dead = self.server._common.runner._pid_dead
            for folder in self.watch_dirs:
                try:
                    now = {n for n in os.listdir(folder) if ".ffskill" in n and self.ours(n, stems)}
                except OSError:
                    continue
                for name in sorted(now - before.get(folder, set())):
                    path = os.path.join(folder, name)
                    if name.endswith(".ffskill-lock"):
                        try:
                            with open(path, encoding="utf-8", errors="replace") as handle:
                                pid = int((handle.read().strip() or "0"))
                        except (OSError, ValueError):
                            pid = 0
                        if pid > 0 and not pid_dead(pid):
                            continue
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path, ignore_errors=True)
                        else:
                            os.remove(path)
                    except OSError:
                        pass

    def finish(self):
        """Always: leave the temp folder, remove it, and remove folders a dry or failed run created."""
        for target in (self.cwd0, self.output_root, os.path.expanduser("~")):
            if target and os.path.isdir(target):
                try:
                    os.chdir(target)
                    break
                except OSError:
                    continue
        if self.tmp:
            # Windows refuses to delete a folder a dying child still has open (or as its cwd): retry briefly
            for _ in range(6):
                shutil.rmtree(self.tmp, ignore_errors=True)
                if not os.path.lexists(self.tmp):
                    break
                time.sleep(0.25)
            try:
                os.rmdir(os.path.dirname(self.tmp))  # .tmp itself, when no other call is using it
            except OSError:
                pass
        if self.dry_run or not self.ok:
            for folder in reversed(self.created_dirs):
                try:
                    os.rmdir(folder)
                except OSError:
                    pass

    # -- envelopes ---------------------------------------------------------------------------

    def skill_info(self):
        upstream = (getattr(self, "lock", None) or {}).get("upstream") or {}
        return {"version": getattr(self, "version", None), "upstream": upstream.get("version")}

    def success(self, doc, status="completed"):
        doc = doc if isinstance(doc, dict) else {}
        outputs = []
        for _, path, kind, _ in self.outputs:
            if kind == "file" and os.path.isfile(path) and path not in outputs:
                outputs.append(path)
        output = doc.get("output")
        if isinstance(output, str) and os.path.isfile(output) and output not in outputs:
            outputs.insert(0, output)
        result = {k: v for k, v in doc.items() if k not in LIFTED_KEYS}
        diagnostics = {}
        for key in ("warnings", "notes"):
            if doc.get(key):
                diagnostics[key] = doc[key]
        if self.notes:
            diagnostics["wrapper"] = list(self.notes)
        envelope = {"ok": True, "tool": self.tool, "status": doc.get("status") or status,
                    "output": output if isinstance(output, str) else None, "outputs": [] if self.dry_run else outputs,
                    "verified": doc.get("verified"), "dryRun": bool(doc.get("dry_run", self.dry_run)),
                    "summary": doc.get("summary"), "result": result, "diagnostics": diagnostics,
                    "truncated": False, "fullResultPath": None,
                    "elapsedSeconds": round(self.elapsed(), 1), "skill": self.skill_info()}
        return self.cap(envelope, doc)

    def cap(self, envelope, full_doc):
        brief = getattr(self, "detail", "brief") != "full"
        result = envelope["result"]
        if brief:
            result = redact_text(result)
        envelope["result"] = compact(result)
        envelope["diagnostics"] = compact(envelope["diagnostics"])
        limit = BRIEF_CAP if brief else FULL_CAP
        if len(json.dumps(envelope, ensure_ascii=True, separators=(",", ":"))) > limit:
            path = self.spill(full_doc)
            keep = {k: full_doc[k] for k in ("status", "output", "verified", "error", "summary") if k in full_doc}
            envelope["result"] = compact(keep)
            envelope["diagnostics"] = compact({k: v[:5] if isinstance(v, list) else v
                                               for k, v in envelope["diagnostics"].items()})
            envelope["truncated"] = True
            envelope["fullResultPath"] = path
        return envelope

    def spill(self, doc):
        folder = os.path.join(self.output_root, "reports")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{self.key}-{stamp()}.json")
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(doc, handle, indent=1, ensure_ascii=False, default=str)
            return path
        except OSError:
            return None


def redact_text(value, depth=0):
    """Brief mode never echoes caption or transcript text back into the conversation."""
    if depth > 20:
        return value
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in TEXT_KEYS and isinstance(item, str) and len(item) > 120:
                out[key] = f"[{len(item)} characters omitted; detail: full shows them]"
            elif key in TEXT_KEYS and isinstance(item, list) and item and all(isinstance(i, (str, dict)) for i in item):
                out[key] = f"[{len(item)} items omitted; detail: full shows them]"
            else:
                out[key] = redact_text(item, depth + 1)
        return out
    if isinstance(value, list):
        return [redact_text(item, depth + 1) for item in value]
    return value


def compact(value, depth=0):
    """Trim lists over 50 items to the first 40 and last 10, and strings to 2,000 characters."""
    if depth > 30:
        return "[nested too deep]"
    if isinstance(value, dict):
        return {str(k): compact(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        if len(value) > LIST_MAX:
            omitted = len(value) - LIST_HEAD - LIST_TAIL
            value = value[:LIST_HEAD] + [{"_omitted": omitted}] + value[-LIST_TAIL:]
        return [compact(v, depth + 1) for v in value]
    if isinstance(value, str) and len(value) > STRING_MAX:
        return value[:STRING_MAX] + f"... [{len(value) - STRING_MAX} more characters]"
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def failure(tool, code, message, hint=None, upstream=None, stderr=None, **extra):
    kind, retryable, default_hint = ERRORS.get(code, ERRORS["INTERNAL_ERROR"])
    doc = {"ok": False, "tool": tool, "error": one_line(message, 600), "errorKind": kind, "code": code,
           "retryable": retryable, "hint": hint or default_hint, "upstream": upstream, "stderrTail": stderr or ""}
    for key, value in extra.items():
        doc[key] = compact(value)
    return doc


# ----------------------------------------------------------------------------- handlers that spawn no tool

def contract_summary(call):
    tools = []
    for key, entry in call.map["tools"].items():
        tools.append({"name": entry["name"], "group": entry["group"], "risk": entry["risk"],
                      "readOnly": entry.get("read_only"), "dryRun": entry.get("supportsDryRun"),
                      "required": entry.get("required") or [], "handler": entry.get("handler")})
    groups = {}
    for t in tools:
        groups[t["group"]] = groups.get(t["group"], 0) + 1
    return {"tools": tools, "groups": groups, "upstream": call.map.get("upstream"),
            "notes": ["Call ffmpeg.setup.contract with tool_name for one tool's full rules and examples.",
                      "Media paths are absolute, or relative to the output root that ffmpeg.setup.doctor reports."]}


def wrapper_rules(entry):
    keys = ("required", "conditionalRequired", "choices", "mutuallyExclusive", "oneOfRequired", "paths",
            "constraints", "writesBesideInput", "removed")
    return {k: entry[k] for k in keys if entry.get(k)}


def run_contract(call, args):
    name = args.get("tool_name")
    if not truthy(name):
        return call.success({"status": "completed", **contract_summary(call)})
    key = call.map["byName"].get(name) or (name if name in call.map["tools"] else None)
    if not key:
        raise call.invalid(f"tool_name: {name!r} is not one of the ffmpeg-video tools", allowed=sorted(call.map["byName"]))
    entry = call.map["tools"][key]
    spec = {"name": entry["name"], "upstreamName": key, "group": entry["group"], "risk": entry["risk"],
            "readOnly": entry.get("read_only"), "supportsDryRun": entry.get("supportsDryRun"),
            "rules": wrapper_rules(entry)}
    if entry.get("spec"):
        script = os.path.join(call.home, *VENDOR_REL.split("/"), "scripts", "_contract.py")
        proc = run_child(call, [sys.executable, "-B", script, "contract", "--json", "--static", "--tool", key],
                         min(60.0, max(5.0, call.remaining())))
        doc = call.parse_stdout(proc.stdout)
        tool = ((doc or {}).get("tools") or [None])[0]
        if not isinstance(tool, dict):
            raise BridgeError("INTERNAL_ERROR", f"the upstream contract for {key} could not be read",
                              stderr=tail_lines(proc.stderr))
        for field in ("description", "inputs", "outputs", "examples", "dry_run", "verification", "reencode_note",
                      "idempotency_hint", "capabilities", "requirements"):
            if field in tool:
                spec[field] = tool[field]
        if call.detail == "full":
            props = (tool.get("input_schema") or {}).get("properties") or {}
            spec["parameters"] = {k: v for k, v in props.items() if k in entry["params"]}
        spec["resultKeys"] = sorted(((tool.get("output_schema") or {}).get("properties") or {}).keys())
    return call.success({"status": "completed", "contract": spec})


def run_child(call, argv, limit):
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              encoding="utf-8", errors="replace", env=call.env, timeout=limit)
    except subprocess.TimeoutExpired:
        raise BridgeError("TIMEOUT", f"{call.tool} did not finish within {round(limit)} s") from None


def run_doctor(call):
    found = call.find_ff()
    problems = call.ff_problems(found)
    free = call.free_mb()
    if free is not None and free < call.min_free_mb():
        problems.append({"code": "low_disk", "problem": f"only {free} MB free on the output volume",
                         "fix": f"free at least {call.min_free_mb()} MB on the drive holding {call.output_root}"})
    facts = {"backend": call.backend, "dataDir": call.data_dir, "skillHome": call.home, "outputRoot": call.output_root,
             "writeRoots": call.write_roots,
             "vendor": {k: (call.lock.get("upstream") or {}).get(k) for k in ("tag", "commit", "version")},
             "sandboxTimeoutSeconds": call.sandbox_seconds, "deadlineSeconds": call.deadline,
             "childPython": {"executable": sys.executable, "version": platform.python_version(),
                             "reexec": " ".join(call.reexec) if call.reexec else None},
             "ffmpeg": {"path": found["ffmpeg"]["path"], "version": found["ffmpeg"]["line"] or None},
             "ffprobe": {"path": found["ffprobe"]["path"], "version": found["ffprobe"]["line"] or None},
             "freeDiskMb": free}
    blocking = [p for p in problems if p["code"] in ("ffmpeg_missing", "ffmpeg_too_old", "ffmpeg_unrunnable")]
    if blocking:
        facts.update(ready=False, problems=problems)
        raise BridgeError("DEPENDENCY_MISSING", blocking[0]["problem"], blocking[0]["fix"], doctor=facts)
    script = os.path.join(call.home, *VENDOR_REL.split("/"), "scripts", "_contract.py")
    proc = run_child(call, [sys.executable, "-B", script, "doctor", "--json"], min(120.0, max(5.0, call.remaining())))
    doc = call.parse_stdout(proc.stdout)
    if not isinstance(doc, dict):
        problems.append({"code": "doctor_failed", "problem": "the upstream doctor printed no report",
                         "fix": "see stderrTail; reinstall the skill if this persists"})
        upstream = {"stderrTail": tail_lines(proc.stderr)}
    else:
        names = {key: e["name"] for key, e in call.map["tools"].items()}
        unusable = [{"tool": names.get(n, n), "usable": t.get("usable"), "fix": t.get("fix")}
                    for n, t in sorted((doc.get("tools") or {}).items()) if isinstance(t, dict) and t.get("usable") != "yes"]
        upstream = {"ok": doc.get("ok"), "version": doc.get("version"), "missingRequired": doc.get("missing") or [],
                    "missingOptionalCount": len(doc.get("missing_optional") or []), "unknown": doc.get("unknown") or [],
                    "unsupported": doc.get("unsupported") or [],
                    "securityWarnings": (doc.get("ffmpeg_security") or {}).get("warnings") or [],
                    "fonts": (doc.get("fonts") or {}).get("detail"), "unusableTools": unusable}
        for line in doc.get("unsupported") or []:
            problems.append({"code": "unsupported", "problem": one_line(line, 300), "fix": "upgrade Python or FFmpeg as it says"})
        if doc.get("missing"):
            problems.append({"code": "capabilities_missing",
                             "problem": "this FFmpeg build lacks required parts: " + ", ".join(doc["missing"][:12]),
                             "fix": "install a full FFmpeg build (see upstream.unusableTools for per-tool fixes)"})
    facts.update(ready=not problems, problems=problems, upstream=upstream)
    return call.success({"status": "completed", "summary": {"ready": not problems, "outputRoot": call.output_root},
                         **facts})


# ----------------------------------------------------------------------------- entry points

def run(tool, params, home, data_dir, start=None, cwd0=None, backend="process", reexec=None):
    """One call, start to finish. Never raises; returns the envelope."""
    call = Call(tool, params, home, data_dir, start, cwd0, backend, reexec)
    before = None
    try:
        call.setup()
        call.server = load_server(call.home)
        prefill_specs(call.server, call.map)
        handler = call.entry.get("handler")
        if handler == "contract":
            call.detail = "brief"
            args = {k: v for k, v in call.raw.items() if k not in STRIPPED_KEYS and v is not None}
            unknown = sorted(k for k in args if k not in call.entry["params"])
            if unknown:
                raise call.invalid(f"unknown parameter(s) for {tool}: {', '.join(unknown)}", unknown=unknown)
            call.detail = args.get("detail") if args.get("detail") in ("brief", "full") else "brief"
            envelope = run_contract(call, args)
            call.ok = True
            return envelope
        if handler == "doctor":
            call.validate()
            envelope = run_doctor(call)
            call.ok = True
            return envelope
        args = call.validate()
        if handler == "render":
            args = call.prepare_render(args)
        elif handler == "batch":
            args = call.prepare_batch(args)
        elif handler == "verify":
            args = call.prepare_verify(args)
        else:
            call.resolve_paths(args)
        call.check_overwrite(args)
        call.preflight()
        if not call.dry_run and not call.entry.get("read_only"):
            call.check_disk()
        proc, ran, ceiling, before = call.run_script(args)
        doc = call.parse_stdout(proc.stdout)
        call.doc = doc
        failed = proc.returncode != 0 or (isinstance(doc, dict) and doc.get("status") == "failed")
        if not failed:
            call.ok = True
            if doc is None:
                doc = {"status": "completed", "stdout": tail_lines(proc.stdout)}
            return call.success(doc)
        code, message = call.classify(proc, doc, ran, ceiling)
        err = (doc or {}).get("error") if isinstance((doc or {}).get("error"), dict) else None
        upstream = {"exit_code": proc.returncode, "error": compact(err)} if err or doc else {"exit_code": proc.returncode}
        extra = {}
        if isinstance(doc, dict):
            rest = {k: v for k, v in doc.items() if k not in ("error", "commands", "status", "exit_code")}
            if rest:
                extra["result"] = compact(redact_text(rest)) if call.detail != "full" else compact(rest)
        hint = (err or {}).get("hint") if code == "TOOL_FAILED" else None
        kept = call.kept_outputs()
        if kept:
            extra["kept"] = kept  # written and left on disk, e.g. a render whose check stage failed
        envelope = failure(tool, code, message, one_line(hint, 600) if hint else None, upstream, tail_lines(proc.stderr), **extra)
        if len(json.dumps(envelope)) > (FULL_CAP if call.detail == "full" else BRIEF_CAP):
            envelope.pop("result", None)
            envelope["fullResultPath"] = call.spill(doc)
            envelope["truncated"] = True
        return envelope
    except BridgeError as exc:
        return failure(tool, exc.code, exc.message, exc.hint, **exc.extra)
    except Exception as exc:  # noqa: BLE001 - every failure becomes an envelope
        where = traceback.extract_tb(exc.__traceback__)[-1:] if exc.__traceback__ else []
        at = f" at {os.path.basename(where[0].filename)}:{where[0].lineno}" if where else ""
        return failure(tool, "INTERNAL_ERROR", f"{type(exc).__name__}: {one_line(exc, 300)}{at}")
    finally:
        try:
            if getattr(call, "server", None) is not None:
                call.cleanup(before)
        except Exception:  # noqa: BLE001 - cleanup is best effort
            pass
        call.finish()


def main():
    """`bridge.py --stdin`: the re-exec path main.py takes under Python < 3.10."""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        doc = run(payload["tool"], payload.get("params") or {}, payload["home"], payload.get("data_dir"),
                  payload.get("start"), payload.get("cwd0"), payload.get("backend") or "process", payload.get("reexec"))
    except Exception as exc:  # noqa: BLE001
        doc = failure(None, "INTERNAL_ERROR", f"bridge.py --stdin: {type(exc).__name__}: {one_line(exc, 300)}")
    sys.stdout.write(json.dumps(doc, ensure_ascii=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__" and "--stdin" in sys.argv[1:]:
    sys.dont_write_bytecode = True
    sys.exit(main())
