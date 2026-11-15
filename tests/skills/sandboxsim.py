"""Simulate how Sophon runs a skill tool call, for skills that cannot be tested in-process.

Sophon's process sandbox backend (src/Sophon.Sandbox/ProcessSandboxOrchestrator.cs) writes the
entrypoint text, with a two-line preamble in front (src/Sophon.Skills/SandboxedTool.cs), as
`script.py` into a fresh `<dataDir>/sandbox/workspaces/<32 hex>` folder, runs it there with the
host `python` and the Gateway's environment plus SOPHON_PARAMS, and deletes the folder after.
Only that one file is staged: the rest of the skill stays in `<dataDir>/skills/<root>/<folder>`.

    from sandboxsim import FakeDataDir, run_process, run_exec

    with FakeDataDir() as data:
        home = data.install("ffmpeg-video")
        out = run_process(data, home, {"tool": "ffmpeg.setup.contract"})

`run_process` is the real shape (a child process, preamble + entrypoint, the workspace cwd);
`run_exec` is the container-parity shape run_all_container.py uses (exec with a `params` global).
`resolver_packages` replays PythonImportResolver: what Sophon would pip-install before the call.
"""
import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills"

# SandboxedTool.cs: the preamble Sophon puts in front of a Python entrypoint, byte for byte.
PREAMBLE = "import json, os\nparams = json.loads(os.environ['SOPHON_PARAMS'])\n"

# PythonImportResolver.cs: the import pattern and the Python 3.13 stdlib list it skips.
IMPORT_RE = re.compile(r"^(?:import|from)\s+(\w+)")
STDLIB = set("""
__future__ _thread abc aifc argparse array ast asynchat asyncio asyncore atexit audioop base64 bdb binascii binhex
bisect builtins bz2 calendar cgi cgitb chunk cmath cmd code codecs codeop collections colorsys compileall concurrent
configparser contextlib contextvars copy copyreg cProfile crypt csv ctypes curses dataclasses datetime dbm decimal
difflib dis distutils doctest email encodings enum errno faulthandler fcntl filecmp fileinput fnmatch fractions ftplib
functools gc getopt getpass gettext glob graphlib grp gzip hashlib heapq hmac html http idlelib imaplib imghdr imp
importlib inspect io ipaddress itertools json keyword lib2to3 linecache locale logging lzma mailbox mailcap marshal
math mimetypes mmap modulefinder multiprocessing netrc nis nntplib numbers operator optparse os ossaudiodev pathlib pdb
pickle pickletools pipes pkgutil platform plistlib poplib posix posixpath pprint profile pstats pty pwd py_compile
pyclbr pydoc queue quopri random re readline reprlib resource rlcompleter runpy sched secrets select selectors shelve
shlex shutil signal site smtpd smtplib sndhdr socket socketserver spwd sqlite3 ssl stat statistics string stringprep
struct subprocess sunau symtable sys sysconfig syslog tabnanny tarfile telnetlib tempfile termios test textwrap
threading time timeit tkinter token tokenize tomllib trace traceback tracemalloc tty turtle turtledemo types typing
unicodedata unittest urllib uu uuid venv warnings wave weakref webbrowser winreg winsound wsgiref xdrlib xml xmlrpc
zipapp zipfile zipimport zlib
""".split())

COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "Thumbs.db")


def resolver_packages(code):
    """The top-level module names Sophon would pip-install for this script text."""
    found = []
    for line in code.split("\n"):
        trimmed = line.lstrip()
        if not trimmed or trimmed[0] == "#":
            continue
        match = IMPORT_RE.match(trimmed)
        if match and match.group(1) not in STDLIB and match.group(1) not in found:
            found.append(match.group(1))
    return found


class FakeDataDir:
    """A throwaway Sophon data folder: skills/{installed,bundled,...}, sandbox/workspaces, documents."""

    def __init__(self, root=None):
        self._own = root is None
        self.root = pathlib.Path(root or tempfile.mkdtemp(prefix="sophon-sim-")).resolve()
        for part in ("skills/installed", "skills/bundled", "skills/self-authored", "skills/organization",
                     "sandbox/workspaces", "documents", "vault", "config"):
            (self.root / part).mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self):
        if self._own:
            shutil.rmtree(self.root, ignore_errors=True)

    def install(self, skill, folder=None, root="installed", patch_manifest=None):
        """Copy skills/<skill> into skills/<root>/<folder>, as an installer would."""
        target = self.root / "skills" / root / (folder or skill)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(SKILLS / skill, target, ignore=COPY_IGNORE)
        if patch_manifest:
            path = target / "manifest.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            patch_manifest(doc)
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
        return target

    def workspace(self):
        path = self.root / "sandbox" / "workspaces" / uuid.uuid4().hex
        path.mkdir(parents=True)
        return path

    @property
    def output_root(self):
        return self.root / "documents" / "video" / "ffmpeg-video"


def entry_text(home):
    manifest = json.loads((pathlib.Path(home) / "manifest.json").read_text(encoding="utf-8"))
    return (pathlib.Path(home) / manifest.get("entrypoint", "main.py")).read_text(encoding="utf-8-sig")


def base_env(extra=None, drop=()):
    env = dict(os.environ)
    for name in ("FFMPEG_VIDEO_SKILL_ROOT", "SOPHON_DATA_DIR", "SOPHON__DataDirectory", "PYTHONPATH",
                 "FFMPEG_VIDEO_WRITE_ROOTS", "FFMPEG_VIDEO_PYTHON") + tuple(drop):
        env.pop(name, None)
    env.update(extra or {})
    return env


def run_process(data, home, params, env=None, python=None, cwd=None, timeout=300, keep_workspace=False):
    """Run one call the way the process backend does. Returns (doc or None, stdout, stderr, exit code).

    `cwd` replaces the workspace folder (to simulate the Docker backend's /workspace shape, or an
    unknown one); `env` is the full environment (base_env() by default)."""
    workdir = pathlib.Path(cwd) if cwd else data.workspace()
    script = workdir / "script.py"
    script.write_text(PREAMBLE + entry_text(home), encoding="utf-8", newline="\n")
    child_env = dict(env if env is not None else base_env())
    child_env["SOPHON_PARAMS"] = json.dumps(params)
    try:
        proc = subprocess.run([python or sys.executable, str(script)], cwd=str(workdir), env=child_env,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    finally:
        if not keep_workspace and not cwd:
            shutil.rmtree(workdir, ignore_errors=True)
        elif cwd:
            try:
                script.unlink()
            except OSError:
                pass
    stdout = proc.stdout.decode("utf-8", "replace")
    stderr = proc.stderr.decode("utf-8", "replace")
    doc = None
    lines = stdout.strip().splitlines()
    if lines:
        try:
            doc = json.loads(lines[-1])
        except ValueError:
            doc = None
    return doc, stdout, stderr, proc.returncode


def run_exec(main_path, params, cwd):
    """exec() the entrypoint with a `params` global in `cwd` (run_all_container.py's model)."""
    src = pathlib.Path(main_path).read_text(encoding="utf-8")
    buf = io.StringIO()
    old = os.getcwd()
    os.chdir(cwd)
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "main.py", "exec"), {"params": dict(params)})
    finally:
        os.chdir(old)
    return buf.getvalue().strip()
