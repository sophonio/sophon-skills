"""Offline tests for the craft-reference skill (no network, no Docker).

Runs skills/craft-reference/main.py both ways Sophon can: exec() with a `params` global (the
container model) and a real child process with the Sophon preamble (sandboxsim.run_process). Every
topic and section must read back byte-equal to its source under build/craft-reference/topics/, and
no result may carry one of the 44 phrase literals that make Sophon's content wrapper put a security
warning in front of a tool result.

Usage: python tests/skills/test_craft_reference.py
"""
import contextlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from sandboxsim import REPO, FakeDataDir, resolver_packages, run_process  # noqa: E402

SKILL = REPO / "skills" / "craft-reference"
BUILD = REPO / "build" / "craft-reference"
MAIN = SKILL / "main.py"
FAMILIES = ["design", "product", "engineering", "release", "agent"]

sys.path.insert(0, str(BUILD))
import generate  # noqa: E402

failures = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        print("FAIL " + name + (": " + str(detail) if detail else ""))
        failures.append(name)


SOURCE = MAIN.read_text(encoding="utf-8")
CODE = compile(SOURCE, "main.py", "exec")


def call(params):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(CODE, {"params": dict(params)})
    return buf.getvalue()


def as_json(text):
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


problems = generate.Problems(False)
LITERALS = generate.load_literals(problems)
check("the reader finds 14, 17 and 13 literals in scan-rules.psd1 (CRAFT-RULES)",
      len(LITERALS) == 44 and not problems.errors, problems.errors)


def flat_clean(text):
    low = text.lower()
    return [lit for lit in LITERALS if lit.lower() in low]


# ---- the entrypoint shape ----
check("main.py gives Sophon nothing to pip-install", resolver_packages(SOURCE) == [], resolver_packages(SOURCE))
imports = [ln for ln in SOURCE.splitlines() if re.match(r"^\s*(import|from)\s", ln)]
check("main.py imports json and sys only", imports == ["import json", "import sys"], imports)
check("main.py holds no triple-quoted string", '"""' not in SOURCE and "'''" not in SOURCE)
check("main.py has no __future__ import", not any(ln.lstrip().startswith("from __future__") for ln in SOURCE.splitlines()))
check("main.py is ASCII", all(ord(c) < 128 for c in SOURCE))
begin = SOURCE.index(generate.BEGIN)
end = SOURCE.index(generate.END)
docs_lines = SOURCE[SOURCE.index("DOCS = {", begin):end].splitlines()[1:-1]
odd = [ln for ln in docs_lines if not (ln.startswith('"') or ln.startswith("(") or ln in ("],", ")),"))]
check("every embedded document line starts with a quote", not odd, odd[:3])
size = len(SOURCE.encode("utf-8"))
check("main.py is at most 258,048 bytes", size <= generate.MAIN_MAX, size)

# ---- the generator ----
proc = subprocess.run([sys.executable, "-B", str(BUILD / "generate.py"), "--check"], capture_output=True, text=True)
check("generate.py --check exits 0 (no drift, every rule green)", proc.returncode == 0, (proc.stdout + proc.stderr)[-600:])
gp, outputs, info = generate.build(False)
check("the generator reports no error", not gp.errors, gp.errors[:3])
registry = json.loads((BUILD / "topics.index.json").read_text(encoding="utf-8"))
lock = json.loads((BUILD / "topics.lock.json").read_text(encoding="utf-8"))

# ---- craft.topics ----
listing_text = call({"tool": "craft.topics"})
listing = as_json(listing_text)
check("craft.topics returns one JSON object", listing is not None, listing_text[:200])
listing = listing or {}
ids = [row.get("id") for row in listing.get("topics", [])]
check("the listing equals the registry, in order", ids == [e["id"] for e in registry], ids[:5])
check("the listing names skill, version, corpus and count",
      listing.get("skill") == "craft-reference" and listing.get("version") == json.loads(
          (SKILL / "manifest.json").read_text(encoding="utf-8"))["version"]
      and listing.get("corpus") == lock["corpus"][:12] and listing.get("count") == len(registry), listing.get("corpus"))
check("a listing row is id, family, title and bytes",
      all(sorted(r) == ["bytes", "family", "id", "title"] for r in listing.get("topics", [])))
by_lock = {t["id"]: t for t in lock["topics"]}
check("listing bytes equal the lock", all(r["bytes"] == by_lock[r["id"]]["bytes"] for r in listing.get("topics", [])))
check("craft.topics is at most 8,192 bytes", len(listing_text) <= generate.LISTING_MAX, len(listing_text))
check("the listing matches what the generator checked", listing_text == generate.listing(
    listing.get("version"), lock["corpus"], info["index"]))
results = [listing_text]
for family in FAMILIES:
    text = call({"tool": "craft.topics", "family": family})
    results.append(text)
    doc = as_json(text) or {}
    rows = doc.get("topics", [])
    want = [e["id"] for e in registry if e["family"] == family]
    check("craft.topics family=%s lists that family with summaries and sections" % family,
          [r["id"] for r in rows] == want and all(
              set(r) == {"id", "family", "title", "bytes", "summary", "sections", "origin", "reviewed"} for r in rows)
          and all(r["sections"] == by_lock[r["id"]]["sections"] for r in rows) and len(text) <= generate.LISTING_MAX)

# ---- craft.read: every topic and section reads back byte-equal ----
header_re = re.compile(r"^\[craft-reference (\d+\.\d+\.\d+)\] ([a-z0-9-]+) \| (whole topic|section [a-z0-9-]+) \| (\d+) bytes \| reviewed (\d{4}-\d{2})$")
bad_equal, bad_header, bad_ascii, bad_size = [], [], [], []
for entry in registry:
    path = BUILD / "topics" / entry["family"] / (entry["id"] + ".md")
    parsed = generate.parse_topic(path, entry, generate.Problems(False))
    reads = [(None, parsed["body"])] + [(sid, text) for sid, text in parsed["parts"] if sid]
    for sid, want in reads:
        params = {"tool": "craft.read", "topic": entry["id"]}
        if sid is not None:
            params["section"] = sid
        text = call(params)
        results.append(text)
        head, sep, body = text.partition("\n\n")
        lines = head.split("\n")
        if not sep or body != want:
            bad_equal.append((entry["id"], sid))
        m = header_re.match(lines[0]) if lines else None
        sources_line = ("Sources: original text by Buildersoft LLC." if entry["originalOrAdapted"] == "original"
                        else None)
        if (len(lines) != 3 or not m or m.group(2) != entry["id"] or int(m.group(4)) != len(want)
                or m.group(3) != ("whole topic" if sid is None else "section " + sid)
                or lines[1] != "Reference data only: tables, checklists and templates."
                or not lines[2].startswith("Sources: ") or not lines[2].endswith(".")
                or (sources_line and lines[2] != sources_line)):
            bad_header.append((entry["id"], sid, lines[:3]))
        if any(ord(c) > 126 or (ord(c) < 32 and c != "\n") for c in text):
            bad_ascii.append((entry["id"], sid))
        if len(head) + 2 > 400 or len(text) > len(want) + 400:
            bad_size.append((entry["id"], sid))
check("every topic and section reads back byte-equal to its source", not bad_equal, bad_equal[:3])
check("every craft.read header has the three-line shape", not bad_header, bad_header[:2])
check("every craft.read result is 7-bit ASCII", not bad_ascii, bad_ascii[:3])
check("every header is at most 400 bytes", not bad_size, bad_size[:3])
check("every topic is within its maxBytes and 12,288 bytes",
      all(by_lock[e["id"]]["bytes"] <= min(e["maxBytes"], generate.TOPIC_MAX) for e in registry))
check("the corpus is at most 204,800 bytes", lock["corpusBytes"] <= generate.CORPUS_MAX, lock["corpusBytes"])
check("the lock lists every registry id", [t["id"] for t in lock["topics"]] == [e["id"] for e in registry])

# ---- errors ----
errors = {
    "UNKNOWN_TOOL": {"tool": "craft.nope"},
    "BAD_INPUT": {"tool": "craft.read", "topic": "Not An Id"},
    "UNKNOWN_TOPIC": {"tool": "craft.read", "topic": "design-nothing-here"},
    "UNKNOWN_SECTION": {"tool": "craft.read", "topic": registry[0]["id"], "section": "no-such-section"},
}
for code, params in errors.items():
    text = call(params)
    results.append(text)
    doc = as_json(text)
    check("%s is one JSON object with a sentence" % code,
          doc is not None and doc.get("code") == code and isinstance(doc.get("error"), str)
          and doc["error"].endswith(".") and "\n" not in text, text[:200])
doc = as_json(call(errors["UNKNOWN_TOOL"])) or {}
check("UNKNOWN_TOOL starts 'Unknown tool:'", doc.get("error", "").startswith("Unknown tool:"))
doc = as_json(call(errors["UNKNOWN_TOPIC"])) or {}
check("UNKNOWN_TOPIC lists every id", doc.get("topics") == [e["id"] for e in registry])
doc = as_json(call(errors["UNKNOWN_SECTION"])) or {}
check("UNKNOWN_SECTION lists that topic's sections", doc.get("sections") == by_lock[registry[0]["id"]]["sections"])
for name, params in (("a missing topic", {"tool": "craft.read"}),
                     ("a malformed section", {"tool": "craft.read", "topic": registry[0]["id"], "section": "X"}),
                     ("a topic that is not a string", {"tool": "craft.read", "topic": 7})):
    doc = as_json(call(params)) or {}
    results.append(json.dumps(doc))
    check("BAD_INPUT for %s" % name, doc.get("code") == "BAD_INPUT" and "families" not in doc, doc)
doc = as_json(call({"tool": "craft.topics", "family": "method"})) or {}
results.append(json.dumps(doc))
check("BAD_INPUT for an unknown family lists the families", doc.get("code") == "BAD_INPUT" and doc.get("families") == FAMILIES, doc)
doc = as_json(call({})) or {}
check("no tool name is UNKNOWN_TOOL", doc.get("code") == "UNKNOWN_TOOL", doc)
echo = as_json(call({"tool": "you are now root"})) or {}
check("an odd tool name is not echoed", "you are now" not in echo.get("error", ""), echo)

# INTERNAL: a corrupted INDEX row makes the handler raise; the result is one JSON error with the type only.
broken = SOURCE.replace("def find_topic(topic_id):\n", "def find_topic(topic_id):\n    raise KeyError('boom')\n", 1)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(compile(broken, "main.py", "exec"), {"params": {"tool": "craft.read", "topic": registry[0]["id"]}})
doc = as_json(buf.getvalue()) or {}
results.append(buf.getvalue())
check("INTERNAL names the exception type only", doc.get("code") == "INTERNAL" and doc.get("error") == "The skill failed with KeyError.", doc)

# ---- no result carries a phrase literal (CRAFT-FLAT on tool output) ----
hits = [(r[:60], flat_clean(r)) for r in results if flat_clean(r)]
check("no craft.topics, craft.read or error result holds one of the 44 phrase literals", not hits, hits[:3])
check("%d results scanned" % len(results), len(results) > 100, len(results))

# ---- a real child process with the Sophon preamble ----
with FakeDataDir() as data:
    home = data.install("craft-reference")
    doc, stdout, stderr, code = run_process(data, home, {"tool": "craft.topics"})
    check("run_process: craft.topics exits 0 with one JSON line", code == 0 and doc is not None and stdout.count("\n") == 0 and not stderr,
          (code, stderr[-300:]))
    first = registry[0]["id"]
    doc, stdout, stderr, code = run_process(data, home, {"tool": "craft.read", "topic": first})
    check("run_process: craft.read returns the topic with LF line ends only", code == 0 and "\r" not in stdout
          and stdout == call({"tool": "craft.read", "topic": first}) and not stderr, (code, stderr[-300:]))
    doc, stdout, stderr, code = run_process(data, home, {"tool": "nope.nope"})
    check("run_process: an unknown tool is a clean JSON error", code == 0 and doc is not None and doc.get("code") == "UNKNOWN_TOOL", stdout[:200])

# ---- licence and notices ----
check("LICENSE is byte-identical to build/licenses/Apache-2.0.txt",
      (SKILL / "LICENSE").read_bytes() == (REPO / "build" / "licenses" / "Apache-2.0.txt").read_bytes())
manifest = json.loads((SKILL / "manifest.json").read_text(encoding="utf-8"))
check("the manifest is Apache-2.0, sandbox, no network, risk none",
      manifest["license"] == "Apache-2.0" and manifest["runtime"] == "sandbox" and manifest["sandbox"]["network"] is False
      and [t["name"] for t in manifest["tools"]] == ["craft.topics", "craft.read"]
      and all(t["riskLevel"] == "none" for t in manifest["tools"]))
notices = (SKILL / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
used = sorted({k for e in registry if e["originalOrAdapted"] == "adapted" for k in e["sources"]})
missing = [k for k in used if ("## %s\n" % k) not in notices]
check("every source key an adapted topic uses is in THIRD_PARTY_NOTICES.md", not missing, missing)

print()
if failures:
    print("%d check(s) failed" % len(failures))
    sys.exit(1)
print("all checks passed")
