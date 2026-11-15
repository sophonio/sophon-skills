#!/usr/bin/env python3
"""Generate the ffmpeg-video skill's tool surface from the vendored ffmpeg-skill contract.

Inputs
  skills/ffmpeg-video/vendor/ffmpeg-skill/   byte-identical upstream files (Sync-FfmpegSkill.ps1)
  skills/ffmpeg-video/vendor.lock.json       their sha256 lock
  build/ffmpeg-video/manifest.base.json      the manifest's top-level fields
  build/ffmpeg-video/policy.json             group, risk, "Use when" line, path roles and rules per tool
  build/ffmpeg-video/smoke-args.json         one minimal call per tool (validated here, run by the media tests)

Outputs (all deterministic; the generator owns their formatting)
  skills/ffmpeg-video/manifest.json          manifest.base.json + tools[]
  skills/ffmpeg-video/lib/tool-map.json      everything lib/bridge.py needs per tool
  skills/ffmpeg-video/vendor.lock.json       its "generated" entry (the tool map's sha256)
  skills/ffmpeg-video/README.md              the table between <!-- tools:begin --> and <!-- tools:end -->
  skills/ffmpeg-video/main.py                the block between the GENERATED CONSTANTS markers

Modes
  (none)          regenerate every output
  --check         regenerate in memory and fail when any output on disk differs (CI)
  --summary       print the tool surface, the path classification and the diff against the
                  tool map on disk; fail on any policy problem. With --write-lock it also writes.
  --write-lock    rebuild vendor.lock.json's upstream block and files[] from the vendor folder
                  (needs --repo, --tag, --commit), then regenerate
  --scan-imports DIR
                  AST import scan of an upstream tree (Sync-FfmpegSkill.ps1 runs it on the staged
                  files): any non-stdlib, non-local import outside a try block fails

The upstream contract is built with the vendored scripts/_contract.py (`build(detect=False)`, no
FFmpeg needed) in a child interpreter started with -I -B and a scrubbed environment, so the result
does not depend on this machine and no __pycache__ lands in vendor/.

Standard library only; Python 3.10 or later.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SKILL = REPO / "skills" / "ffmpeg-video"
VENDOR_REL = "vendor/ffmpeg-skill"
VENDOR = SKILL / VENDOR_REL
LOCK_PATH = SKILL / "vendor.lock.json"
TOOL_MAP_REL = "lib/tool-map.json"
TOOL_MAP_PATH = SKILL / TOOL_MAP_REL
MANIFEST_PATH = SKILL / "manifest.json"
README_PATH = SKILL / "README.md"
MAIN_PATH = SKILL / "main.py"
BASE_PATH = HERE / "manifest.base.json"
POLICY_PATH = HERE / "policy.json"
SMOKE_PATH = HERE / "smoke-args.json"

TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*(\.[a-z0-9_-]+)*$")
TOOL_NAME_MAX = 64
GROUP_MAX = 15
DESCRIPTION_MAX = 600
PARAM_DESCRIPTION_MAX = 360
RISKS = ("none", "low", "medium", "high", "critical")
README_BEGIN = "<!-- tools:begin -->"
README_END = "<!-- tools:end -->"
MAIN_BEGIN = "# --- GENERATED CONSTANTS BEGIN ---"
MAIN_END = "# --- GENERATED CONSTANTS END ---"
# Zero-width, bidi-control and other invisible characters a scanner flags; never shipped in text.
HIDDEN_CHARS = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\ufe0f]")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Heuristics for "this string parameter may be a path": a hit must be classified by the tool's own
# policy (a path role or an explicit literal); a global literal is not enough.
PATHY_NAME = re.compile(
    r"(^|_)(input|inputs|output|outputs|file|files|path|paths|dir|dirs|folder|project|recipe|list|srt|ass|lut|"
    r"image|images|video|logo|brand|music|effects|replace|cues|chapters|edl|sheet|timemap|words|notes|commands|pack|"
    r"after|before|compare|insert|reference|second|sources|report|out|work|cache|init|assets|model|source|text|"
    r"timeline|log|write)(_|$)")
PATHY_DESC = re.compile(
    r"\b(file|files|path|paths|directory|folder|dir)\b|\.(json|srt|ass|png|jpg|cube|txt|md|ttf|otf|mp4|mov|wav)\b",
    re.IGNORECASE)

GENERIC_OUTPUT = re.compile(r"^output (file|video)( \(default: [^)]*\))?$")

CHILD_CONTRACT = r"""
import json, sys
sys.dont_write_bytecode = True
scripts, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, scripts)
import _contract
built = _contract.build(detect=False)
doc = {
    "contract_version": built["contract_version"],
    "skill_version": built["skill"]["version"],
    "removed": built["removed"],
    "deprecated": built["deprecated"],
    "mcp_json_exempt": list(_contract.MCP_JSON_EXEMPT),
    "tools": [{"spec": t, "read_only": bool(_contract.mcp_read_only(t))} for t in built["tools"]],
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, ensure_ascii=False)
"""


class GenerationError(Exception):
    """A problem that stops generation; every problem found is collected before raising."""

    def __init__(self, problems: List[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


# ----------------------------------------------------------------------------- small helpers

def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def json_text(doc: Any, indent: Optional[int] = 2, ascii_only: bool = False) -> str:
    return json.dumps(doc, indent=indent, ensure_ascii=ascii_only) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_text_lf(path: Path) -> str:
    """Text as stored (no newline translation), so a CRLF file is reported, not silently fixed."""
    return path.read_bytes().decode("utf-8")


def clean_text(text: str) -> str:
    text = text.replace("%%", "%")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit - 3)]
    space = cut.rfind(" ")
    if space > limit // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:-") + "..."


def human_list(items: List[str], joiner: str = "or") -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {joiner} " + items[-1]


def wire_name(name: str) -> str:
    return name.replace(".", "_")


# ----------------------------------------------------------------------------- vendor lock

def vendor_disk_files() -> List[str]:
    """Every file under vendor/, as skill-root-relative forward-slash paths, ordinal order."""
    vendor_root = SKILL / "vendor"
    found: List[str] = []
    if not vendor_root.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(vendor_root):
        dirnames.sort()
        for name in filenames:
            full = Path(dirpath) / name
            found.append(full.relative_to(SKILL).as_posix())
    return sorted(found)


def lock_files_from_disk() -> List[Dict[str, Any]]:
    entries = []
    for rel in vendor_disk_files():
        data = (SKILL / rel).read_bytes()
        entries.append({"path": rel, "sha256": sha256_bytes(data), "bytes": len(data)})
    return entries


def verify_lock(lock: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    if lock.get("schemaVersion") != 1:
        problems.append("vendor.lock.json: schemaVersion must be 1")
    upstream = lock.get("upstream") or {}
    for key in ("repo", "tag", "commit", "version"):
        if not isinstance(upstream.get(key), str) or not upstream.get(key):
            problems.append(f"vendor.lock.json: upstream.{key} is missing")
    if not re.fullmatch(r"[0-9a-f]{40}", str(upstream.get("commit", ""))):
        problems.append("vendor.lock.json: upstream.commit must be a full 40-character sha")
    if str(upstream.get("tag", "")).lstrip("v") != upstream.get("version"):
        problems.append("vendor.lock.json: upstream.version must equal the tag without its leading v")
    listed = lock.get("files") or []
    paths = [e.get("path") for e in listed]
    if paths != sorted(paths):
        problems.append("vendor.lock.json: files[] is not sorted by ordinal path")
    if len(set(paths)) != len(paths):
        problems.append("vendor.lock.json: files[] lists a path twice")
    on_disk = set(vendor_disk_files())
    for entry in listed:
        rel = entry.get("path", "")
        if not rel.startswith(VENDOR_REL + "/"):
            problems.append(f"vendor.lock.json: {rel} is not under {VENDOR_REL}/")
            continue
        full = SKILL / rel
        if not full.is_file():
            problems.append(f"vendor.lock.json: {rel} is listed but missing on disk")
            continue
        data = full.read_bytes()
        if sha256_bytes(data) != entry.get("sha256") or len(data) != entry.get("bytes"):
            problems.append(f"vendor.lock.json: {rel} does not match its sha256/bytes (edited or corrupted)")
    for rel in sorted(on_disk - set(paths)):
        problems.append(f"vendor.lock.json: {rel} exists under vendor/ but is not locked")
    return problems


# ----------------------------------------------------------------------------- upstream contract

def load_contract() -> Dict[str, Any]:
    scripts = VENDOR / "scripts"
    if not (scripts / "_contract.py").is_file():
        raise GenerationError([f"{scripts / '_contract.py'} not found: run Sync-FfmpegSkill.ps1 first"])
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("FFMPEG_", "PYTHON", "_FFMPEG"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    with tempfile.TemporaryDirectory(prefix="ffvideo-gen-") as tmp:
        out = Path(tmp) / "contract.json"
        proc = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", CHILD_CONTRACT, str(scripts), str(out)],
                              cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=300)
        if proc.returncode != 0 or not out.is_file():
            tail = "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-15:])
            raise GenerationError([f"building the vendored contract failed (exit {proc.returncode}):\n{tail}"])
        doc = read_json(out)
    stray = [p for p in VENDOR.rglob("__pycache__")]
    if stray:
        raise GenerationError([f"the contract build left {stray[0]} under vendor/; remove it"])
    return doc


# ----------------------------------------------------------------------------- surface model

def property_description(name: str, upstream_prop: Dict[str, Any], borrowed: Dict[Tuple[str, str], str],
                         allow_borrow: bool) -> str:
    text = clean_text(upstream_prop.get("description") or "")
    if not text and allow_borrow:
        text = borrowed.get((name, upstream_prop["type"]), "")
    return text


def collect_borrowed(specs: Dict[str, Dict[str, Any]]) -> Dict[Tuple[str, str], str]:
    """A description for a (param name, type) that some tool leaves empty, taken from the first
    tool (by name) that describes it. Never used for path params: their role hint says enough."""
    found: Dict[Tuple[str, str], str] = {}
    for name in sorted(specs):
        for key, prop in specs[name]["input_schema"]["properties"].items():
            desc = clean_text(prop.get("description") or "")
            if desc and (key, prop["type"]) not in found:
                found[(key, prop["type"])] = desc
    return found


def join_sentences(*parts: str) -> str:
    """Join description fragments, ending each with a full stop so appended notes read cleanly."""
    out = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if out and out[-1] not in ".!?":
            out += "."
        out = (out + " " + part) if out else part
    return out


def rule_applies_text(rule: Dict[str, Any]) -> str:
    parts = []
    if rule.get("whenAny"):
        parts.append("when " + human_list(rule["whenAny"]) + " is given")
    if rule.get("whenNone"):
        parts.append("unless " + human_list(rule["whenNone"]) + " is given")
    return " ".join(parts)


class Surface:
    """The whole generated surface: manifest tools, tool map, README rows and constants."""

    def __init__(self, base: Dict[str, Any], policy: Dict[str, Any], contract: Dict[str, Any],
                 lock: Dict[str, Any]):
        self.base = base
        self.policy = policy
        self.contract = contract
        self.lock = lock
        self.problems: List[str] = []
        self.specs = {t["spec"]["name"]: t["spec"] for t in contract["tools"]}
        self.read_only = {t["spec"]["name"]: t["read_only"] for t in contract["tools"]}
        self.borrowed = collect_borrowed(self.specs)
        self.classification: Dict[str, Dict[str, str]] = {}
        self.manifest_tools: List[Dict[str, Any]] = []
        self.tool_map: Dict[str, Any] = {}
        self.readme_rows: List[Tuple[str, str, str]] = []
        self.order: List[Tuple[str, str]] = []  # (key, full name)

    # -- checks on the upstream contract ------------------------------------------------------

    def check_contract(self) -> None:
        expect = self.policy["upstreamExpect"]
        major = str(self.contract["contract_version"]).split(".")[0]
        if major != str(expect["contractMajor"]):
            self.problems.append(f"upstream contract_version {self.contract['contract_version']} has major {major}, "
                                 f"policy expects {expect['contractMajor']}: review the new contract first")
        removed_now = [d["what"] for d in self.contract["removed"]]
        if removed_now != expect["removed"]:
            self.problems.append("upstream `removed` list changed: review it, then update policy.json upstreamExpect.removed")
        deprecated_now = [d.get("what") for d in self.contract["deprecated"]]
        if deprecated_now != expect["deprecated"]:
            self.problems.append("upstream `deprecated` list changed: review it, then update policy.json upstreamExpect.deprecated")
        upstream_version = self.lock.get("upstream", {}).get("version")
        if self.contract["skill_version"] != upstream_version:
            self.problems.append(f"vendored package.json version {self.contract['skill_version']} != lock version {upstream_version}")
        policy_tools = set(self.policy["tools"])
        upstream_tools = set(self.specs)
        for name in sorted(upstream_tools - policy_tools):
            self.problems.append(f"upstream tool `{name}` has no entry in policy.json tools")
        for name in sorted(policy_tools - upstream_tools):
            self.problems.append(f"policy.json tool `{name}` is not an upstream tool any more")
        for name in sorted(set(self.policy["wrapperTools"]) & upstream_tools):
            self.problems.append(f"wrapper tool `{name}` collides with an upstream tool of the same name")
        for name in self.contract["mcp_json_exempt"]:
            if name in self.policy["tools"] and "jsonMode" not in self.policy["tools"][name]:
                self.problems.append(f"`{name}` is in MCP_JSON_EXEMPT: policy must state its jsonMode (add or native)")

    # -- one upstream tool ----------------------------------------------------------------------

    def build_upstream_tool(self, key: str) -> None:
        pol = self.policy["tools"][key]
        spec = self.specs[key]
        schema = spec["input_schema"]
        props: Dict[str, Dict[str, Any]] = schema["properties"]
        full_name = f"ffmpeg.{pol['group']}.{key}"
        roles = self.policy["pathRoles"]
        problems = self.problems

        removed: Dict[str, str] = {}
        for param, reason in self.policy["dropEverywhere"].items():
            if param in props:
                removed[param] = reason
        if self.read_only[key]:
            for param, reason in self.policy["readOnlyDrop"].items():
                if param in props:
                    removed[param] = reason
        for param, reason in (pol.get("removed") or {}).items():
            if param not in props:
                problems.append(f"{key}: policy removes `{param}`, which upstream does not have")
            removed[param] = reason
        exposed = [p for p in props if p not in removed]

        # wrapper params
        wrapper_defs = self.policy["wrapperParams"]
        extras = list(self.policy["wrapperParamsEverywhere"]) + list(pol.get("extraParams") or [])
        for extra in extras:
            if extra not in wrapper_defs:
                problems.append(f"{key}: extra param `{extra}` is not defined in wrapperParams")
            if extra in props:
                problems.append(f"{key}: wrapper param `{extra}` collides with an upstream param")

        # path classification
        paths: Dict[str, str] = dict(pol.get("paths") or {})
        literals = set(pol.get("literals") or [])
        global_literals = set(self.policy["globalLiterals"])
        for param, role in paths.items():
            if role not in roles:
                problems.append(f"{key}: `{param}` has unknown path role `{role}`")
            if param not in exposed:
                problems.append(f"{key}: policy gives a path role to `{param}`, which is not an exposed param")
        for param in literals:
            if param not in exposed:
                problems.append(f"{key}: policy lists `{param}` as a literal, but it is not an exposed param")
            if param in paths:
                problems.append(f"{key}: `{param}` is both a path and a literal")
        classification: Dict[str, str] = {}
        for param in exposed:
            prop = props[param]
            if prop["type"] not in ("string", "array"):
                continue
            if prop.get("enum") and prop["type"] == "string" and param not in paths:
                classification[param] = "enum"
                continue
            desc = clean_text(prop.get("description") or "")
            pathy = bool(PATHY_NAME.search(param) or PATHY_DESC.search(desc) or prop.get("cli") == "positional")
            if param in paths:
                classification[param] = paths[param]
            elif param in literals:
                classification[param] = "literal"
            elif pathy:
                problems.append(f"{key}: path-like parameter `{param}` ({prop['type']}) is not classified in "
                                f"policy.json (give it a path role or list it under literals)")
            elif param in global_literals:
                classification[param] = "literal (global)"
            else:
                problems.append(f"{key}: string parameter `{param}` is not classified in policy.json "
                                f"(path role, tool literal or globalLiterals)")
        self.classification[key] = classification

        # required
        optional = set(pol.get("optional") or [])
        required = [p for p in schema.get("required", []) if p in exposed and p not in optional]
        for param in pol.get("required") or []:
            if param not in exposed:
                problems.append(f"{key}: policy requires `{param}`, which is not an exposed param")
            elif param not in required:
                required.append(param)
        order_index = {p: i for i, p in enumerate(exposed)}
        required.sort(key=lambda p: order_index[p])
        conditional = list(pol.get("conditionalRequired") or [])
        cond_params = set()
        for rule in conditional:
            for field in [rule["param"]] + list(rule.get("whenAny") or []) + list(rule.get("whenNone") or []):
                if field not in exposed and field not in extras:
                    problems.append(f"{key}: conditionalRequired names `{field}`, which is not an exposed param")
            if rule["param"] in required:
                problems.append(f"{key}: `{rule['param']}` is both required and conditionally required")
            cond_params.add(rule["param"])

        # a writing tool must name its output explicitly (or the policy says why not)
        out_roles = [p for p, r in paths.items() if r in ("out_file", "out_dir")]
        if not self.read_only[key] and "output" in exposed and "output" not in required \
                and "output" not in cond_params and not pol.get("outputNotRequired"):
            problems.append(f"{key}: writing tool does not require `output`; require it, make it conditional, "
                            f"or set outputNotRequired with a reason")
        if self.read_only[key] and out_roles:
            problems.append(f"{key}: read-only tool has output path roles {out_roles}")

        # choices, mutual exclusion, one-of-required
        choices: Dict[str, List[Any]] = {}
        for param in exposed:
            if props[param].get("enum"):
                choices[param] = list(props[param]["enum"])
        for extra in extras:
            if wrapper_defs.get(extra, {}).get("enum"):
                choices[extra] = list(wrapper_defs[extra]["enum"])
        all_params = exposed + extras
        mutex = [[p for p in g if p in all_params] for g in schema.get("mutually_exclusive", [])]
        mutex = [g for g in mutex if len(g) >= 2] + [list(g) for g in (pol.get("mutuallyExclusive") or [])]
        one_of = [[p for p in g if p in all_params] for g in schema.get("one_of_required", [])]
        one_of = [g for g in one_of if g] + [list(g) for g in (pol.get("oneOfRequired") or [])]
        for group in mutex + one_of:
            for param in group:
                if param not in all_params:
                    problems.append(f"{key}: rule group names `{param}`, which is not an exposed param")
        mutex_partners: Dict[str, List[str]] = {}
        for group in mutex:
            for param in group:
                mutex_partners.setdefault(param, [])
                mutex_partners[param] += [p for p in group if p != param and p not in mutex_partners[param]]

        # constraints and other bridge rules
        constraints = dict(pol.get("constraints") or {})
        for param in constraints:
            if param not in all_params:
                problems.append(f"{key}: constraint on `{param}`, which is not an exposed param")
        beside = dict(pol.get("writesBesideInput") or {})
        for param, input_param in beside.items():
            if param not in exposed or input_param not in exposed:
                problems.append(f"{key}: writesBesideInput `{param}` -> `{input_param}` names an unknown param")
        nested = dict(pol.get("nested") or {})
        for param in nested:
            if param not in all_params:
                problems.append(f"{key}: nested-path hint on `{param}`, which is not an exposed param")

        # manifest parameters
        overrides = dict(self.policy["commonDescriptions"])
        overrides.update(pol.get("descriptions") or {})
        properties: Dict[str, Any] = {}
        types: Dict[str, Any] = {}
        for param in exposed:
            prop = props[param]
            out: Dict[str, Any] = {"type": prop["type"]}
            if prop["type"] == "array":
                out["items"] = dict(prop.get("items") or {"type": "string"})
            base_desc = overrides.get(param) or property_description(param, prop, self.borrowed,
                                                                     allow_borrow=param not in paths)
            notes: List[str] = []
            if param in paths and param not in overrides:
                # the wrapper requires an explicit output, so upstream's "(default: <name>_x.<ext>)" is moot
                if paths[param] == "out_file" and GENERIC_OUTPUT.match(base_desc):
                    base_desc = ""
                if base_desc:
                    base_desc = base_desc[0].upper() + base_desc[1:]
                base_desc = join_sentences(roles[paths[param]]["hint"], base_desc)
            enum = prop.get("enum")
            if enum:
                if all(isinstance(v, str) for v in enum):
                    out["enum"] = list(enum)
                else:
                    notes.append("One of: " + ", ".join(str(v) for v in enum) + ".")
            if param in mutex_partners:
                notes.append("Not with: " + ", ".join(mutex_partners[param]) + ".")
            if param in constraints and constraints[param].get("text"):
                notes.append(constraints[param]["text"])
            suffix = join_sentences(*notes)
            room = PARAM_DESCRIPTION_MAX - (len(suffix) + 2 if suffix else 0)
            desc = join_sentences(clip(base_desc, room), suffix)
            if desc:
                out["description"] = desc
            default = prop.get("default")
            if default is not None and param not in paths and self.default_fits(prop["type"], default):
                out["default"] = default
            properties[param] = out
            types[param] = {"type": prop["type"], "source": "upstream"}
            if prop["type"] == "array":
                types[param]["items"] = out["items"]["type"]
        for extra in extras:
            definition = wrapper_defs[extra]
            out = {k: v for k, v in definition.items() if k in ("type", "enum", "items", "default")}
            desc = (pol.get("descriptions") or {}).get(extra) or definition["description"]
            if extra in mutex_partners:
                desc = join_sentences(desc, "Not with: " + ", ".join(mutex_partners[extra]) + ".")
            out["description"] = desc
            properties[extra] = out
            types[extra] = {"type": definition["type"], "source": "wrapper"}

        # tool description
        summary = clean_text(pol.get("summary") or spec["description"])
        rules: List[str] = []
        for group in one_of:
            rules.append("Needs one of: " + ", ".join(group) + ".")
        for rule in conditional:
            rules.append(f"{rule['param']} is required {rule_applies_text(rule)}.")
        writes = pol.get("writes") or self.writes_text(key, paths, required, cond_params)
        description = join_sentences(summary, pol["useWhen"], *rules, writes)
        self.check_description(full_name, description)

        parameters = {"type": "object", "properties": properties, "required": required, "additionalProperties": False}
        if not required:
            del parameters["required"]
        self.manifest_tools.append({"name": full_name, "description": description, "riskLevel": pol["risk"],
                                    "parameters": parameters})

        # tool map
        json_mode = pol.get("jsonMode") or "flag"
        if not spec.get("supports_json"):
            json_mode = "none"
        self.tool_map[key] = {
            "name": full_name,
            "group": pol["group"],
            "script": spec["executable"],
            "handler": pol.get("handler"),
            "deadline": pol.get("deadline"),
            "risk": pol["risk"],
            "read_only": self.read_only[key],
            "json": json_mode,
            "brief": bool(spec.get("supports_json_brief")),
            "defaultDetail": "brief",
            "supportsDryRun": bool(spec.get("supports_dry_run")),
            "dryRunExecution": spec.get("dry_run", {}).get("ffmpeg_execution"),
            "spec": {
                "name": spec["name"],
                "mcp": {"positional": list(spec["mcp"]["positional"]),
                        "argument_exceptions": dict(spec["mcp"]["argument_exceptions"])},
                "input_schema": {"properties": {p: {"cli": props[p]["cli"]} for p in props}},
                "produces_artifact": bool(spec["produces_artifact"]),
                "mutates_input": bool(spec["mutates_input"]),
            },
            "params": types,
            "required": required,
            "conditionalRequired": conditional,
            "paths": paths,
            "choices": choices,
            "mutuallyExclusive": mutex,
            "oneOfRequired": one_of,
            "constraints": constraints,
            "writesBesideInput": beside,
            "nested": nested,
            "removed": removed,
        }
        self.readme_rows.append((full_name, pol["risk"], summary))
        self.order.append((key, full_name))

    @staticmethod
    def default_fits(kind: str, value: Any) -> bool:
        if kind == "string":
            return isinstance(value, str)
        if kind == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if kind == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if kind == "boolean":
            return isinstance(value, bool)
        if kind == "array":
            return isinstance(value, list) and len(value) > 0
        return False

    def writes_text(self, key: str, paths: Dict[str, str], required: List[str], conditional: set) -> str:
        primary = [p for p, r in paths.items() if r in ("out_file", "out_dir")]
        side = [p for p, r in paths.items() if r == "out_side_file"]
        if not primary and not side:
            return "Writes: nothing."
        parts = []
        if primary:
            parts.append(human_list(primary, "and"))
        if side:
            parts.append(("side files when named: " if primary else "only the side files you name: ")
                         + ", ".join(side))
        return "Writes: " + "; ".join(parts) + ". Relative output paths land in the output root."

    def check_description(self, name: str, text: str) -> None:
        if len(text) > DESCRIPTION_MAX:
            self.problems.append(f"{name}: description is {len(text)} characters (max {DESCRIPTION_MAX}); "
                                 f"shorten useWhen or set a summary in policy.json")
        if HIDDEN_CHARS.search(text) or CONTROL_CHARS.search(text):
            self.problems.append(f"{name}: description contains a hidden or control character")

    # -- wrapper tools --------------------------------------------------------------------------

    def build_wrapper_tool(self, key: str) -> None:
        pol = self.policy["wrapperTools"][key]
        full_name = f"ffmpeg.{pol['group']}.{key}"
        wrapper_defs = self.policy["wrapperParams"]
        properties: Dict[str, Any] = {}
        types: Dict[str, Any] = {}
        choices: Dict[str, List[Any]] = {}
        for extra in pol.get("params") or []:
            if extra not in wrapper_defs:
                self.problems.append(f"{key}: param `{extra}` is not defined in wrapperParams")
                continue
            definition = wrapper_defs[extra]
            out = {k: v for k, v in definition.items() if k in ("type", "enum", "items", "default")}
            out["description"] = (pol.get("descriptions") or {}).get(extra) or definition["description"]
            properties[extra] = out
            types[extra] = {"type": definition["type"], "source": "wrapper"}
            if definition.get("enum"):
                choices[extra] = list(definition["enum"])
        if "tool_name" in properties:
            choices["tool_name"] = sorted(list(self.specs) + [f"ffmpeg.{self.policy['tools'][n]['group']}.{n}"
                                                              for n in self.specs if n in self.policy["tools"]])
        description = join_sentences(clean_text(pol["summary"]), pol["useWhen"], pol["writes"])
        self.check_description(full_name, description)
        parameters = {"type": "object", "properties": properties, "additionalProperties": False}
        self.manifest_tools.append({"name": full_name, "description": description, "riskLevel": pol["risk"],
                                    "parameters": parameters})
        self.tool_map[key] = {
            "name": full_name,
            "group": pol["group"],
            "script": pol["script"],
            "handler": pol["handler"],
            "deadline": pol.get("deadline"),
            "risk": pol["risk"],
            "read_only": True,
            "json": "add",
            "brief": False,
            "defaultDetail": "brief",
            "supportsDryRun": False,
            "dryRunExecution": None,
            "spec": None,
            "params": types,
            "required": [],
            "conditionalRequired": [],
            "paths": {},
            "choices": choices,
            "mutuallyExclusive": [],
            "oneOfRequired": [],
            "constraints": {},
            "writesBesideInput": {},
            "nested": {},
            "removed": {},
        }
        self.readme_rows.append((full_name, pol["risk"], clean_text(pol["summary"])))
        self.order.append((key, full_name))

    # -- whole surface --------------------------------------------------------------------------

    def build(self) -> None:
        self.check_contract()
        groups = self.policy["groupOrder"]
        entries: List[Tuple[int, int, str, bool]] = []
        for idx, (key, pol) in enumerate(self.policy["tools"].items()):
            if key in self.specs:
                entries.append((groups.index(pol["group"]) if pol["group"] in groups else 99, idx, key, False))
            if pol.get("group") not in groups:
                self.problems.append(f"{key}: group `{pol.get('group')}` is not in groupOrder")
            if pol.get("risk") not in RISKS:
                self.problems.append(f"{key}: risk `{pol.get('risk')}` is not valid")
            if key in self.specs:
                if self.read_only[key] and pol.get("risk") != "none":
                    self.problems.append(f"{key}: read-only upstream tool should have risk none")
                if not self.read_only[key] and pol.get("risk") == "none":
                    self.problems.append(f"{key}: a tool that writes files cannot have risk none")
        offset = len(self.policy["tools"])
        for idx, (key, pol) in enumerate(self.policy["wrapperTools"].items()):
            entries.append((groups.index(pol["group"]) if pol["group"] in groups else 99, offset + idx, key, True))
        entries.sort()
        for _, _, key, is_wrapper in entries:
            if is_wrapper:
                self.build_wrapper_tool(key)
            else:
                self.build_upstream_tool(key)

        names = [t["name"] for t in self.manifest_tools]
        if len(names) != len(set(names)):
            self.problems.append("duplicate tool names")
        wires = [wire_name(n) for n in names]
        if len(wires) != len(set(wires)):
            self.problems.append("two tool names collide after '.' -> '_'")
        counts: Dict[str, int] = {}
        for name in names:
            if not TOOL_NAME_RE.match(name) or len(name) > TOOL_NAME_MAX:
                self.problems.append(f"tool name `{name}` does not match the tool-name rule")
            group = ".".join(name.split(".")[:2])
            counts[group] = counts.get(group, 0) + 1
        for group, count in counts.items():
            if count > GROUP_MAX:
                self.problems.append(f"group {group} has {count} tools (max {GROUP_MAX}; the tool index collapses it)")
        for tool in self.manifest_tools:
            if "tool" in tool["parameters"]["properties"]:
                self.problems.append(f"{tool['name']}: has a parameter named `tool` (Sophon overwrites it)")
            self.check_schema_subset(tool["name"], tool["parameters"])

    def check_schema_subset(self, name: str, node: Any, path: str = "parameters") -> None:
        if isinstance(node, dict):
            for bad in ("$ref", "oneOf", "anyOf", "allOf", "not"):
                if bad in node:
                    self.problems.append(f"{name}: {path} uses `{bad}`")
            if "type" in node and not isinstance(node["type"], str):
                self.problems.append(f"{name}: {path} has a non-string type")
            if node.get("type") == "array" and "items" not in node:
                self.problems.append(f"{name}: {path} is an array without items")
            if "enum" in node and not all(isinstance(v, str) for v in node["enum"]):
                self.problems.append(f"{name}: {path} has a non-string enum")
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    for prop, sub in value.items():
                        self.check_schema_subset(name, sub, f"{path}.{prop}")
                elif key == "items":
                    self.check_schema_subset(name, value, f"{path}.items")

    # -- rendered outputs -----------------------------------------------------------------------

    def tool_map_doc(self) -> Dict[str, Any]:
        upstream = self.lock["upstream"]
        return {
            "schemaVersion": 1,
            "generator": "build/ffmpeg-video/generate.py",
            "skill": {"name": self.base["name"], "version": self.base["version"]},
            "upstream": {"repo": upstream["repo"], "tag": upstream["tag"], "commit": upstream["commit"],
                         "version": upstream["version"], "contractVersion": self.contract["contract_version"]},
            "mcpJsonExempt": list(self.contract["mcp_json_exempt"]),
            "legend": self.policy["toolMapLegend"],
            "pathRoles": {role: d["meaning"] for role, d in self.policy["pathRoles"].items()},
            "removedEverywhere": dict(self.policy["dropEverywhere"]),
            "byName": {full: key for key, full in self.order},
            "tools": {key: self.tool_map[key] for key, _ in self.order},
        }

    def manifest_doc(self) -> Dict[str, Any]:
        doc = dict(self.base)
        doc.pop("tools", None)
        doc["tools"] = self.manifest_tools
        return doc

    def readme_block(self) -> str:
        lines = [README_BEGIN,
                 "",
                 "| Tool | Risk | What it does |",
                 "|---|---|---|"]
        for name, risk, summary in self.readme_rows:
            lines.append(f"| `{name}` | {risk} | {clip(summary, 200).replace('|', '/')} |")
        lines.append("")
        lines.append(f"{len(self.readme_rows)} tools. Tools at risk `none` or `low` show no approval card; "
                     "`medium` tools ask once per call.")
        lines.append(README_END)
        return "\n".join(lines)

    def main_block(self, lock_sha: str) -> str:
        upstream = self.lock["upstream"]
        lines = [MAIN_BEGIN,
                 "# Written by build/ffmpeg-video/generate.py; edit policy.json or manifest.base.json instead.",
                 f"SKILL_NAME = {json.dumps(self.base['name'])}",
                 f"SKILL_VERSION = {json.dumps(self.base['version'])}",
                 f"VENDOR_TAG = {json.dumps(upstream['tag'])}",
                 f"VENDOR_COMMIT = {json.dumps(upstream['commit'])}",
                 f"VENDOR_LOCK_SHA256 = {json.dumps(lock_sha)}",
                 "TOOLS = ["]
        for _, full in self.order:
            lines.append(f"    {json.dumps(full)},")
        lines.append("]")
        lines.append(MAIN_END)
        return "\n".join(lines)


# ----------------------------------------------------------------------------- marker files

def replace_block(text: str, begin: str, end: str, block: str, label: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
        raise GenerationError([f"{label}: expected exactly one `{begin}` ... `{end}` block"])
    start = text.index(begin)
    stop = text.index(end) + len(end)
    return text[:start] + block + text[stop:]


def render_marker_file(path: Path, begin: str, end: str, block: str, label: str) -> str:
    if not path.exists():
        return block + "\n"
    text = read_text_lf(path)
    return replace_block(text, begin, end, block, label)


# ----------------------------------------------------------------------------- smoke args

def check_smoke(surface: Surface, smoke: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    calls = smoke.get("calls") or {}
    by_name = {t["name"]: t for t in surface.manifest_tools}
    for name in by_name:
        if name not in calls:
            problems.append(f"smoke-args.json: no call for {name}")
    for name, call in calls.items():
        if name not in by_name:
            problems.append(f"smoke-args.json: {name} is not a tool")
            continue
        props = by_name[name]["parameters"]["properties"]
        args = call.get("args") or {}
        for key in args:
            if key not in props:
                problems.append(f"smoke-args.json: {name} passes unknown param `{key}`")
        for key in by_name[name]["parameters"].get("required", []):
            if key not in args:
                problems.append(f"smoke-args.json: {name} misses required `{key}`")
        if call.get("dryRun") and "dry_run" not in props:
            problems.append(f"smoke-args.json: {name} is marked dryRun but has no dry_run param")
        if call.get("dryRun") and args.get("dry_run") is not True:
            problems.append(f"smoke-args.json: {name} is marked dryRun but does not pass dry_run: true")
    return problems


# ----------------------------------------------------------------------------- summary / diff

def print_summary(surface: Surface, old_map: Optional[Dict[str, Any]]) -> None:
    print(f"tools: {len(surface.manifest_tools)}")
    counts: Dict[str, List[str]] = {}
    for tool in surface.manifest_tools:
        group = ".".join(tool["name"].split(".")[:2])
        counts.setdefault(group, []).append(f"{tool['name'].split('.')[-1]}({tool['riskLevel']})")
    for group, items in counts.items():
        print(f"  {group} [{len(items)}]: {', '.join(items)}")
    risks: Dict[str, int] = {}
    for tool in surface.manifest_tools:
        risks[tool["riskLevel"]] = risks.get(tool["riskLevel"], 0) + 1
    print("risk: " + ", ".join(f"{k} {v}" for k, v in sorted(risks.items())))
    longest = max(surface.manifest_tools, key=lambda t: len(t["description"]))
    print(f"longest description: {longest['name']} ({len(longest['description'])} chars)")
    print("path classification (string/array params):")
    for key, _ in surface.order:
        cls = surface.classification.get(key)
        if not cls:
            continue
        rows = [f"{p}={r}" for p, r in cls.items() if r not in ("enum", "literal (global)")]
        glob = [p for p, r in cls.items() if r == "literal (global)"]
        print(f"  {key}: {', '.join(rows) or '-'}" + (f"  [global literals: {', '.join(glob)}]" if glob else ""))
    if old_map is None:
        print("surface diff: no previous lib/tool-map.json")
        return
    new_tools = surface.tool_map_doc()["tools"]
    old_tools = old_map.get("tools", {})
    diff: List[str] = []
    for key in sorted(set(new_tools) - set(old_tools)):
        diff.append(f"+ tool {new_tools[key]['name']}")
    for key in sorted(set(old_tools) - set(new_tools)):
        diff.append(f"- tool {old_tools[key]['name']}")
    for key in sorted(set(new_tools) & set(old_tools)):
        new, old = new_tools[key], old_tools[key]
        if new["name"] != old.get("name"):
            diff.append(f"~ {key}: renamed {old.get('name')} -> {new['name']}")
        if new["risk"] != old.get("risk"):
            diff.append(f"~ {new['name']}: risk {old.get('risk')} -> {new['risk']}")
        new_params, old_params = set(new["params"]), set(old.get("params", {}))
        for p in sorted(new_params - old_params):
            diff.append(f"+ {new['name']}.{p}")
        for p in sorted(old_params - new_params):
            diff.append(f"- {new['name']}.{p}")
        for p in sorted(set(new["paths"]) | set(old.get("paths", {}))):
            if new["paths"].get(p) != old.get("paths", {}).get(p):
                diff.append(f"~ {new['name']}.{p}: path role {old.get('paths', {}).get(p)} -> {new['paths'].get(p)}")
        if new.get("choices") != old.get("choices"):
            diff.append(f"~ {new['name']}: choices changed")
    print("surface diff against lib/tool-map.json on disk:")
    for line in diff or ["  (none)"]:
        print(f"  {line}")


# ----------------------------------------------------------------------------- import scan

def scan_imports(root: Path, optional_allowed: List[str]) -> int:
    files = sorted(list((root / "mcp").glob("*.py")) + list((root / "scripts").rglob("*.py")))
    if not files:
        print(f"scan-imports: no Python files under {root}", file=sys.stderr)
        return 1
    local = {p.stem for p in (root / "scripts").glob("*.py")}
    local |= {p.name for p in (root / "scripts").iterdir() if p.is_dir() and (p / "__init__.py").is_file()}
    stdlib = set(sys.stdlib_module_names)
    errors: List[str] = []
    warnings: List[str] = []
    notes: List[str] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_bytes().decode("utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: does not parse as UTF-8 Python: {exc}")
            continue
        parents: Dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        for node in ast.walk(tree):
            modules: List[str] = []
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules = [node.module]
            for module in modules:
                top = module.split(".")[0]
                if top in ("socket", "urllib", "http", "ssl", "ftplib", "smtplib", "telnetlib", "xmlrpc"):
                    warnings.append(f"{rel}:{node.lineno}: network module `{module}`")
                if top in stdlib or top in local:
                    continue
                guarded = False
                cursor: ast.AST = node
                while cursor in parents:
                    cursor = parents[cursor]
                    if isinstance(cursor, ast.Try):
                        guarded = True
                        break
                if guarded and top in optional_allowed:
                    notes.append(f"{rel}:{node.lineno}: optional import `{module}` (allowed, inside try)")
                elif guarded:
                    warnings.append(f"{rel}:{node.lineno}: optional non-stdlib import `{module}` (inside try)")
                else:
                    errors.append(f"{rel}:{node.lineno}: non-stdlib import `{module}`")
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                        warnings.append(f"{rel}:{node.lineno}: subprocess call with shell= set")
    for line in notes:
        print(f"note: {line}")
    for line in warnings:
        print(f"WARN: {line}")
    for line in errors:
        print(f"ERROR: {line}")
    print(f"scan-imports: {len(files)} files, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


# ----------------------------------------------------------------------------- main

def generate(args: argparse.Namespace) -> int:
    base = read_json(BASE_PATH)
    policy = read_json(POLICY_PATH)
    smoke = read_json(SMOKE_PATH)
    problems: List[str] = []

    if args.write_lock:
        if not (args.repo and args.tag and args.commit):
            raise GenerationError(["--write-lock needs --repo, --tag and --commit"])
        version = read_json(VENDOR / "package.json")["version"]
        lock = {"schemaVersion": 1,
                "upstream": {"repo": args.repo, "tag": args.tag, "commit": args.commit, "version": version},
                "files": lock_files_from_disk(),
                "generated": []}
    else:
        if not LOCK_PATH.is_file():
            raise GenerationError(["vendor.lock.json is missing: run Sync-FfmpegSkill.ps1"])
        lock = read_json(LOCK_PATH)
    problems += verify_lock(lock)

    contract = load_contract()
    surface = Surface(base, policy, contract, lock)
    surface.build()
    problems += surface.problems
    problems += check_smoke(surface, smoke)
    if base.get("name") != "ffmpeg-video":
        problems.append("manifest.base.json: name must be ffmpeg-video")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(base.get("version", ""))):
        problems.append("manifest.base.json: version must be MAJOR.MINOR.PATCH")

    old_map = read_json(TOOL_MAP_PATH) if TOOL_MAP_PATH.is_file() else None
    if args.summary:
        print_summary(surface, old_map)

    if problems:
        raise GenerationError(problems)

    tool_map_text = json_text(surface.tool_map_doc(), indent=1)
    lock_out = dict(lock)
    lock_out["generated"] = [{"path": TOOL_MAP_REL, "sha256": sha256_bytes(tool_map_text.encode("utf-8"))}]
    lock_text = json_text(lock_out, indent=2, ascii_only=True)
    lock_sha = sha256_bytes(lock_text.encode("utf-8"))
    outputs = {
        TOOL_MAP_PATH: tool_map_text,
        LOCK_PATH: lock_text,
        MANIFEST_PATH: json_text(surface.manifest_doc(), indent=2),
        README_PATH: render_marker_file(README_PATH, README_BEGIN, README_END, surface.readme_block(), "README.md"),
        MAIN_PATH: render_marker_file(MAIN_PATH, MAIN_BEGIN, MAIN_END, surface.main_block(lock_sha), "main.py"),
    }

    if args.check:
        stale = []
        for path, text in outputs.items():
            if not path.is_file() or path.read_bytes() != text.encode("utf-8"):
                stale.append(path.relative_to(REPO).as_posix())
        if stale:
            print("generate.py --check: out of date (run python -B build/ffmpeg-video/generate.py):")
            for rel in stale:
                print(f"  {rel}")
            return 1
        print(f"generate.py --check: up to date ({len(surface.manifest_tools)} tools, "
              f"vendor {lock['upstream']['tag']} {lock['upstream']['commit'][:12]}, "
              f"{len(lock['files'])} locked files)")
        return 0

    if args.summary and not args.write_lock:
        return 0

    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        data = text.encode("utf-8")
        if not path.is_file() or path.read_bytes() != data:
            path.write_bytes(data)
            print(f"wrote {path.relative_to(REPO).as_posix()}")
    print(f"generated {len(surface.manifest_tools)} tools")
    return 0


def main() -> int:
    if sys.version_info < (3, 10):
        print("generate.py needs Python 3.10 or later", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser(description="Generate the ffmpeg-video tool surface from the vendored contract.")
    ap.add_argument("--check", action="store_true", help="fail when a generated file is out of date; write nothing")
    ap.add_argument("--summary", action="store_true", help="print the surface, the path classification and the diff")
    ap.add_argument("--write-lock", action="store_true", help="rebuild vendor.lock.json from the vendor folder")
    ap.add_argument("--repo", help="upstream repository URL (with --write-lock)")
    ap.add_argument("--tag", help="upstream tag (with --write-lock)")
    ap.add_argument("--commit", help="upstream commit (with --write-lock)")
    ap.add_argument("--scan-imports", metavar="DIR", help="AST import scan of an upstream tree, then exit")
    args = ap.parse_args()
    if args.scan_imports:
        policy = read_json(POLICY_PATH)
        return scan_imports(Path(args.scan_imports), list(policy.get("optionalImports") or []))
    if args.check and args.write_lock:
        ap.error("--check and --write-lock cannot be combined")
    try:
        return generate(args)
    except GenerationError as exc:
        print("generate.py: failed:", file=sys.stderr)
        for line in exc.problems:
            print(f"  - {line}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
