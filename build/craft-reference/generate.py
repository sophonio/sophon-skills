#!/usr/bin/env python3
"""Generate the craft-reference skill's embedded corpus from build/craft-reference/.

Inputs
  build/craft-reference/topics.index.json   the topic registry (hand-written): id, family, title, maxBytes,
                                            originalOrAdapted, sources, usedBy
  build/craft-reference/topics/<family>/<id>.md
                                            one topic per file: front matter (id, summary, reviewed), one
                                            "# " title line, an optional preamble and "## " sections
  build/craft-reference/sources.json        per upstream key: url, commit, label, ideasOnly, creditOnly, notice
                                            (a creditOnly key that is not a repository has no url and commit)
  build/craft-reference/owner-review.json   topics that need the owner's sign-off, and the sign-offs
  build/craft-reference/released.json       ids and section ids of every published version
  skills/craft-reference/manifest.json      the skill version
  build/agent-src/catalog/scan-rules.psd1   the 44 phrase literals (CRAFT-FLAT)
  build/agent-src/family.psd1               the Credits strings (CRAFT-SOURCE, the notices)

Outputs (deterministic; the generator owns their formatting)
  skills/craft-reference/main.py            the block between the GENERATED DOCS markers
  skills/craft-reference/README.md          the table between <!-- topics:begin --> and <!-- topics:end -->
  skills/craft-reference/THIRD_PARTY_NOTICES.md
  build/craft-reference/topics.lock.json    bytes, sha256 and section ids per topic, and the corpus hash

Modes
  (none)       check every rule, then write every output
  --check      check every rule, regenerate in memory and fail when an output on disk differs (CI)
  --summary    print sizes per topic and family, the projected main.py size and stale review months
  --release    with any mode: CRAFT-OWNER and the pin rules of CRAFT-SOURCE become errors

Rules (each problem prints with its id; design docs/plans/2026-11-23-agents-v3-design.md, "Generator rules"):
  CRAFT-REGISTRY CRAFT-FRONT CRAFT-ASCII CRAFT-SIZE CRAFT-HEADING CRAFT-FLAT CRAFT-PROCESS CRAFT-SOURCE
  CRAFT-PERMANENT CRAFT-OWNER CRAFT-RULES

Until the upstreams are pinned (milestone M7), CRAFT-SOURCE reports a source key that sources.json or the
family Credits lack as a note; --release makes it an error.

Standard library only; Python 3.10 or later.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SKILL = REPO / "skills" / "craft-reference"
MAIN_PATH = SKILL / "main.py"
README_PATH = SKILL / "README.md"
NOTICES_PATH = SKILL / "THIRD_PARTY_NOTICES.md"
MANIFEST_PATH = SKILL / "manifest.json"
INDEX_PATH = HERE / "topics.index.json"
TOPICS_DIR = HERE / "topics"
SOURCES_PATH = HERE / "sources.json"
OWNER_PATH = HERE / "owner-review.json"
RELEASED_PATH = HERE / "released.json"
LOCK_PATH = HERE / "topics.lock.json"
SCAN_RULES_PATH = REPO / "build" / "agent-src" / "catalog" / "scan-rules.psd1"
FAMILY_PATH = REPO / "build" / "agent-src" / "family.psd1"
AGENTS_DIR = REPO / "agents"

BEGIN = "# --- GENERATED DOCS BEGIN ---"
END = "# --- GENERATED DOCS END ---"
TABLE_BEGIN = "<!-- topics:begin -->"
TABLE_END = "<!-- topics:end -->"

FAMILIES = ["design", "product", "engineering", "release", "agent"]
PREFIX = {"design": "design-", "product": "product-", "engineering": "eng-", "release": "release-", "agent": "agent-"}
# Agent ids planned for the 3.0 roster that have no agents/<id>/ folder yet (they arrive in M6). A topic id
# never equals an agent id; the folders under agents/ are read as well.
PLANNED_AGENT_IDS = ["agent-engineer", "product-manager", "product-owner", "release-engineer"]

TOPIC_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,47}$")
SECTION_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
FIXED_ID_RE = re.compile(r"\s*\{#([^}]*)\}\s*$")

TOPIC_MAX = 12288
TOPIC_WARN = 8192
CORPUS_MAX = 204800
LISTING_MAX = 8192
MAIN_MAX = 258048
SUMMARY_MAX = 120
# The protocol words of the development family (CRAFT-PROCESS). A topic never carries a status key,
# a verdict word or a question label.
PROCESS_WORDS = ["STATUS:", "VERDICT", "FINDINGS", "NEEDS_CONTEXT", "DONE_WITH_CONCERNS", "BLOCKED",
                 "READ_FIRST", "WRITE_SCOPE", "(Recommended)"]
TIER_COUNTS = {"High": 14, "Medium": 17, "Low": 13}
# The review month that counts as stale (--summary): six months for these, twelve for the rest.
FAST_REFRESH = {"design-generated-defaults", "design-sophon-default", "design-sophon-components"}

HEADER_LINE2 = "Reference data only: tables, checklists and templates."
ORIGINAL_SOURCES = "Sources: original text by Buildersoft LLC."
NOTICE_STATEMENT = ("Ideas and structure re-expressed in new words for Sophon by Buildersoft LLC; "
                    "no upstream file is included.")
MIT_TEXT = """Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


class Problems:
    def __init__(self, release):
        self.release = release
        self.errors = []
        self.notes = []
        self.warnings = []

    def error(self, rule, where, message):
        self.errors.append("%s %s: %s" % (rule, where, message))

    def pending(self, rule, where, message):
        # An error under --release, a note otherwise.
        if self.release:
            self.error(rule, where, message)
        else:
            self.notes.append("%s %s: %s (an error under --release)" % (rule, where, message))

    def warn(self, rule, where, message):
        self.warnings.append("%s %s: %s" % (rule, where, message))


def rel(path):
    return Path(path).resolve().relative_to(REPO).as_posix()


# ---------------------------------------------------------------------------------------------------------
# PowerShell data files: single-quoted strings under a named key
# ---------------------------------------------------------------------------------------------------------

def _skip_comment(text, i):
    while i < len(text) and text[i] != "\n":
        i += 1
    return i


def _read_quoted(text, i):
    # text[i] is the opening quote; '' is an escaped quote. Returns (value, index after the closing quote).
    out = []
    i += 1
    while i < len(text):
        ch = text[i]
        if ch == "'":
            if i + 1 < len(text) and text[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    raise ValueError("unterminated string")


def psd1_block(text, key, opener):
    """The text of the first `key = @(` or `key = @{` block (opener '(' or '{'), brackets matched outside
    strings and comments; None when absent."""
    match = re.search(r"(?m)^\s*" + re.escape(key) + r"\s*=\s*@" + re.escape(opener), text)
    if not match:
        return None
    closer = ")" if opener == "(" else "}"
    depth = 1
    i = match.end()
    start = i
    while i < len(text):
        ch = text[i]
        if ch == "#":
            i = _skip_comment(text, i)
            continue
        if ch == "'":
            _, i = _read_quoted(text, i)
            continue
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth -= 1
            if depth == 0:
                return text[start:i]
        i += 1
    raise ValueError("unterminated block " + key)


def psd1_strings(block):
    values = []
    i = 0
    while i < len(block):
        ch = block[i]
        if ch == "#":
            i = _skip_comment(block, i)
            continue
        if ch == "'":
            value, i = _read_quoted(block, i)
            values.append(value)
            continue
        i += 1
    return values


def psd1_pairs(block):
    """`name = '...'` pairs of a hashtable block, in order."""
    pairs = []
    i = 0
    name_re = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*'")
    while i < len(block):
        ch = block[i]
        if ch == "#":
            i = _skip_comment(block, i)
            continue
        match = name_re.match(block, i)
        if match and (i == 0 or block[i - 1] in "\n;{ \t"):
            value, i = _read_quoted(block, match.end() - 1)
            pairs.append((match.group(1), value))
            continue
        if ch == "'":
            _, i = _read_quoted(block, i)
            continue
        i += 1
    return pairs


def load_literals(problems):
    text = SCAN_RULES_PATH.read_text(encoding="utf-8")
    p2 = psd1_block(text, "P2", "{")
    tiers = {}
    for tier, want in TIER_COUNTS.items():
        block = psd1_block(p2 or "", tier, "(")
        values = psd1_strings(block) if block is not None else []
        tiers[tier] = values
        if len(values) != want:
            problems.error("CRAFT-RULES", rel(SCAN_RULES_PATH),
                           "found %d %s literals in P2, expected %d" % (len(values), tier, want))
    return [v for tier in TIER_COUNTS for v in tiers[tier]]


def load_credits():
    text = FAMILY_PATH.read_text(encoding="utf-8")
    block = psd1_block(text, "Credits", "{")
    return dict(psd1_pairs(block or ""))


# ---------------------------------------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------------------------------------

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def flat_hits(text, literals):
    low = text.lower()
    return [lit for lit in literals if lit.lower() in low]


def parse_topic(path, entry, problems):
    """Returns {front, parts: [(section id, text)], body} or None when the file cannot be used."""
    where = rel(path)
    data = path.read_bytes()
    bad = [i for i, b in enumerate(data) if not (b == 0x0A or 0x20 <= b <= 0x7E)]
    if bad:
        line = data[:bad[0]].count(b"\n") + 1
        problems.error("CRAFT-ASCII", "%s:%d" % (where, line),
                       "byte 0x%02X; a topic holds 0x0A and 0x20-0x7E only (%d such byte(s))" % (data[bad[0]], len(bad)))
        return None
    text = data.decode("ascii")
    if not text.endswith("\n"):
        problems.error("CRAFT-ASCII", where, "the file must end with one newline")
        return None
    lines = text.split("\n")[:-1]
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        problems.error("CRAFT-FRONT", "%s:1" % where, "front matter between two --- lines is missing")
        return None
    close = lines.index("---", 1)
    front = {}
    for n, line in enumerate(lines[1:close], start=2):
        key, sep, value = line.partition(": ")
        if not sep or key in front:
            problems.error("CRAFT-FRONT", "%s:%d" % (where, n), "front matter lines are 'key: value', each key once")
            continue
        front[key] = value
    if sorted(front) != ["id", "reviewed", "summary"]:
        problems.error("CRAFT-FRONT", "%s:1" % where, "front matter holds exactly id, summary and reviewed (got %s)" % ", ".join(sorted(front)))
    if front.get("id") != path.stem:
        problems.error("CRAFT-FRONT", "%s:2" % where, "id '%s' differs from the file name" % front.get("id"))
    if len(front.get("summary", "")) > SUMMARY_MAX or not front.get("summary"):
        problems.error("CRAFT-FRONT", where, "summary must be 1-%d bytes (has %d)" % (SUMMARY_MAX, len(front.get("summary", ""))))
    if not MONTH_RE.match(front.get("reviewed", "")):
        problems.error("CRAFT-FRONT", where, "reviewed '%s' is not YYYY-MM" % front.get("reviewed"))

    body = lines[close + 1:]
    first = close + 2
    parts = [["", []]]
    titles = 0
    seen = set()
    fence = False
    for n, line in enumerate(body, start=first):
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("# "):
            titles += 1
            if n != first:
                problems.error("CRAFT-HEADING", "%s:%d" % (where, n), "the '# ' title line comes first after the front matter")
        if not fence and line.startswith("## "):
            heading = line[3:]
            fixed = FIXED_ID_RE.search(heading)
            if fixed:
                sid = fixed.group(1)
                line = "## " + heading[:fixed.start()]
            else:
                sid = slug(heading)
            if not SECTION_ID_RE.match(sid):
                problems.error("CRAFT-HEADING", "%s:%d" % (where, n),
                               "section id '%s' does not match ^[a-z][a-z0-9-]{1,31}$; end the heading with {#<id>}" % sid)
            if sid in seen:
                problems.error("CRAFT-HEADING", "%s:%d" % (where, n), "section id '%s' repeats" % sid)
            seen.add(sid)
            parts.append([sid, []])
        for word in PROCESS_WORDS:
            if word in line:
                problems.error("CRAFT-PROCESS", "%s:%d" % (where, n), "the protocol word '%s'; a topic holds reference data only" % word)
        parts[-1][1].append(line + "\n")
    if titles != 1:
        problems.error("CRAFT-HEADING", where, "a topic has exactly one '# ' title line (found %d)" % titles)
    out = [(sid, "".join(chunk)) for sid, chunk in parts]
    whole = "".join(t for _, t in out)
    return {"front": front, "parts": out, "body": whole, "sha256": hashlib.sha256(data).hexdigest()}


def agent_ids():
    ids = set(PLANNED_AGENT_IDS)
    if AGENTS_DIR.is_dir():
        ids.update(p.name for p in AGENTS_DIR.iterdir() if p.is_dir())
    return ids


def load_json(path, problems, rule, default):
    if not path.exists():
        problems.error(rule, rel(path), "the file is missing")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        problems.error(rule, rel(path), "not valid JSON: %s" % exc)
        return default


def check_registry(registry, problems):
    where = rel(INDEX_PATH)
    if not isinstance(registry, list) or not registry:
        problems.error("CRAFT-REGISTRY", where, "the registry is a non-empty array")
        return []
    keys = ["id", "family", "title", "maxBytes", "originalOrAdapted", "sources", "usedBy"]
    agents = agent_ids()
    seen = set()
    good = []
    total = 0
    for n, entry in enumerate(registry):
        if not isinstance(entry, dict) or sorted(entry) != sorted(keys):
            problems.error("CRAFT-REGISTRY", where, "entry %d must hold exactly %s" % (n, ", ".join(keys)))
            continue
        tid = entry["id"]
        if not isinstance(tid, str) or not TOPIC_ID_RE.match(tid):
            problems.error("CRAFT-REGISTRY", where, "id '%s' does not match ^[a-z][a-z0-9-]{2,47}$" % tid)
            continue
        if tid in seen:
            problems.error("CRAFT-REGISTRY", where, "id '%s' is listed twice" % tid)
        seen.add(tid)
        if entry["family"] not in FAMILIES:
            problems.error("CRAFT-REGISTRY", where, "'%s': family '%s' is not one of %s" % (tid, entry["family"], ", ".join(FAMILIES)))
            continue
        if not tid.startswith(PREFIX[entry["family"]]):
            problems.error("CRAFT-REGISTRY", where, "'%s' lacks the family prefix %s" % (tid, PREFIX[entry["family"]]))
        if tid in agents:
            problems.error("CRAFT-REGISTRY", where, "'%s' equals an agent id" % tid)
        size = entry["maxBytes"]
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > TOPIC_MAX:
            problems.error("CRAFT-REGISTRY", where, "'%s': maxBytes %r must be 1-%d" % (tid, size, TOPIC_MAX))
        else:
            total += size
        title = entry["title"]
        if not isinstance(title, str) or not title or any(not (0x20 <= ord(c) <= 0x7E) for c in title):
            problems.error("CRAFT-REGISTRY", where, "'%s': title must be non-empty printable ASCII" % tid)
        if entry["originalOrAdapted"] not in ("original", "adapted"):
            problems.error("CRAFT-REGISTRY", where, "'%s': originalOrAdapted is original or adapted" % tid)
        for key in ("sources", "usedBy"):
            if not isinstance(entry[key], list) or any(not isinstance(v, str) for v in entry[key]):
                problems.error("CRAFT-REGISTRY", where, "'%s': %s is an array of strings" % (tid, key))
        good.append(entry)
    if total > CORPUS_MAX:
        problems.error("CRAFT-REGISTRY", where, "maxBytes sum to %d, above the corpus limit %d" % (total, CORPUS_MAX))
    files = {}
    if TOPICS_DIR.is_dir():
        for path in sorted(TOPICS_DIR.rglob("*")):
            if path.is_file():
                files[path.relative_to(TOPICS_DIR).as_posix()] = path
    expected = {"%s/%s.md" % (e["family"], e["id"]) for e in good}
    for name in sorted(set(files) - expected):
        problems.error("CRAFT-REGISTRY", rel(files[name]), "a topic file without a registry entry (or in the wrong family folder)")
    for name in sorted(expected - set(files)):
        problems.error("CRAFT-REGISTRY", "build/craft-reference/topics/" + name, "the registry entry has no topic file")
    return good


def source_line(entry, sources):
    if entry["originalOrAdapted"] != "adapted":
        return ORIGINAL_SOURCES
    labels = []
    for key in entry["sources"]:
        info = sources.get(key) if isinstance(sources, dict) else None
        label = info.get("label") if isinstance(info, dict) else None
        labels.append(label if isinstance(label, str) and label else key)
    return "Sources: " + "; ".join(labels) + "."


def check_sources(registry, sources, credits, problems):
    where = rel(INDEX_PATH)
    if not isinstance(sources, dict):
        problems.error("CRAFT-SOURCE", rel(SOURCES_PATH), "sources.json is an object keyed by source key")
        sources = {}
    unpinned = {}
    uncredited = {}
    for entry in registry:
        tid = entry["id"]
        if entry["originalOrAdapted"] == "adapted" and not entry["sources"]:
            problems.error("CRAFT-SOURCE", where, "'%s' is adapted and names no source" % tid)
        if entry["originalOrAdapted"] == "original" and entry["sources"]:
            problems.error("CRAFT-SOURCE", where, "'%s' is original and names a source" % tid)
        for key in entry["sources"]:
            info = sources.get(key)
            if not isinstance(info, dict):
                unpinned.setdefault(key, []).append(tid)
            elif info.get("ideasOnly"):
                problems.error("CRAFT-SOURCE", where, "'%s' names source '%s', which is ideasOnly" % (tid, key))
            if key not in credits:
                uncredited.setdefault(key, []).append(tid)
    # Before the upstreams are pinned these are one note each; under --release one error per key.
    for what, keys in (("sources.json does not pin", unpinned), ("the family Credits lack", uncredited)):
        if problems.release:
            for key in sorted(keys, key=str.lower):
                problems.error("CRAFT-SOURCE", where, "%s source '%s' (topics %s)" % (what, key, ", ".join(keys[key])))
        elif keys:
            problems.notes.append("CRAFT-SOURCE %s: %s %d source key(s) yet: %s (an error under --release)" % (
                where, what, len(keys), ", ".join(sorted(keys, key=str.lower))))
    for key, info in sorted(sources.items()):
        here = "%s (%s)" % (rel(SOURCES_PATH), key)
        if not isinstance(info, dict):
            problems.error("CRAFT-SOURCE", here, "an entry is an object")
            continue
        # A creditOnly source that is not a repository (heuristic names cited by name) has no url and commit.
        bare = info.get("creditOnly") is True and "url" not in info and "commit" not in info
        url = info.get("url", "")
        if not bare and (not isinstance(url, str) or not url.startswith("https://github.com/")):
            problems.error("CRAFT-SOURCE", here, "url must be on https://github.com/")
        if not bare and (not isinstance(info.get("commit"), str) or not COMMIT_RE.match(info["commit"])):
            problems.error("CRAFT-SOURCE", here, "commit must be 40 hex digits")
        label = info.get("label", "")
        if not isinstance(label, str) or not label or any(not (0x20 <= ord(c) <= 0x7E) for c in label):
            problems.error("CRAFT-SOURCE", here, "label must be non-empty printable ASCII")
    return sources


# ---------------------------------------------------------------------------------------------------------
# What the skill returns (mirrors the handlers in main.py; the tests compare both)
# ---------------------------------------------------------------------------------------------------------

def compact(doc):
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":"))


def listing(skill_version, corpus, index, family=None):
    rows = []
    for row in index:
        if family is not None and row["family"] != family:
            continue
        item = {"id": row["id"], "family": row["family"], "title": row["title"], "bytes": row["bytes"]}
        if family is not None:
            item.update({"summary": row["summary"], "sections": row["sections"], "origin": row["origin"],
                         "reviewed": row["reviewed"]})
        rows.append(item)
    return compact({"skill": "craft-reference", "version": skill_version, "corpus": corpus[:12],
                    "count": len(rows), "topics": rows})


def header(skill_version, row, section, size):
    what = "whole topic" if section is None else "section " + section
    return ("[craft-reference %s] %s | %s | %d bytes | reviewed %s\n%s\n%s\n\n"
            % (skill_version, row["id"], what, size, row["reviewed"], HEADER_LINE2, row["sources"]))


# ---------------------------------------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------------------------------------

def render_block(skill_version, corpus, index, docs):
    out = [BEGIN,
           "# Written by build/craft-reference/generate.py from build/craft-reference/; never edit by hand.",
           "# Every document line is one physical line that starts with a quote (the import scan reads every line).",
           'SKILL_NAME = "craft-reference"',
           "SKILL_VERSION = %s" % json.dumps(skill_version),
           "CORPUS_SHA256 = %s" % json.dumps(corpus),
           "INDEX = ["]
    for row in index:
        out.append(json.dumps(row, ensure_ascii=True, separators=(", ", ": ")) + ",")
    out.append("]")
    out.append("DOCS = {")
    for row in index:
        out.append("%s: [" % json.dumps(row["id"]))
        for sid, text in docs[row["id"]]:
            out.append("(%s, (" % json.dumps(sid))
            for line in text.splitlines(keepends=True):
                out.append(json.dumps(line, ensure_ascii=True))
            out.append(")),")
        out.append("],")
    out.append("}")
    out.append(END)
    return "\n".join(out)


def splice(text, begin, end, block, where, problems):
    start = text.find(begin)
    stop = text.find(end)
    if start < 0 or stop < start:
        problems.error("CRAFT-SIZE", where, "the markers %s and %s are missing" % (begin, end))
        return text
    return text[:start] + block + text[stop + len(end):]


def render_table(registry, index):
    by_id = {row["id"]: row for row in index}
    lines = [TABLE_BEGIN, "",
             "| Id | Family | Title | Sections | Bytes | Origin |", "|---|---|---|---|---|---|"]
    for entry in registry:
        row = by_id.get(entry["id"])
        if row is None:
            continue
        lines.append("| `%s` | %s | %s | %d | %d of %d | %s |" % (
            row["id"], row["family"], row["title"], len(row["sections"]), row["bytes"], entry["maxBytes"], row["origin"]))
    lines += ["", TABLE_END]
    return "\n".join(lines)


def render_notices(registry, sources, credits):
    users = {}
    for entry in registry:
        if entry["originalOrAdapted"] != "adapted":
            continue
        for key in entry["sources"]:
            users.setdefault(key, []).append(entry["id"])
    out = ["# Third-party notices", "",
           "Generated by build/craft-reference/generate.py; never edit by hand.", "",
           "Every topic of craft-reference is written in Buildersoft LLC's own words. A topic marked adapted follows",
           "the structure or substance of the upstreams below closely enough that we acknowledge them. No upstream",
           "file is included in this skill.", ""]
    mit = False
    for key in sorted(users, key=str.lower):
        info = sources.get(key) if isinstance(sources.get(key), dict) else {}
        credit = credits.get(key)
        out.append("## %s" % key)
        out.append("")
        out.append("- Credit: %s" % (credit if credit else "recorded when the source is pinned, before its topic text is written"))
        if info.get("url") and info.get("commit"):
            out.append("- Source: %s at commit %s" % (info["url"], info["commit"]))
        elif info.get("creditOnly") is True:
            out.append("- Source: not a repository; cited by name only")
        else:
            out.append("- Source: not pinned yet; this version holds stub text only for its topics")
        out.append("- Topics: %s" % ", ".join("`%s`" % t for t in users[key]))
        if info.get("creditOnly"):
            out.append("- Credit only: names are used, no text or structure is adapted.")
        out.append("")
        if isinstance(info.get("notice"), str) and info["notice"].strip():
            out += ["Upstream NOTICE:", "", "```", info["notice"].strip(), "```", ""]
        out.append(NOTICE_STATEMENT)
        out.append("")
        if credit and "MIT" in credit:
            mit = True
    if mit:
        out += ["## MIT License", "", "The MIT-licensed upstreams above are used under these terms:", "", MIT_TEXT.rstrip("\n"), ""]
    return "\n".join(out).rstrip("\n") + "\n"


def corpus_hash(index, docs):
    digest = hashlib.sha256()
    for row in index:
        body = "".join(t for _, t in docs[row["id"]])
        digest.update(("%s %s\n" % (row["id"], hashlib.sha256(body.encode("ascii")).hexdigest())).encode("ascii"))
    return digest.hexdigest()


def build(release):
    problems = Problems(release)
    literals = load_literals(problems)
    credits = load_credits()
    registry = check_registry(load_json(INDEX_PATH, problems, "CRAFT-REGISTRY", []), problems)
    sources = check_sources(registry, load_json(SOURCES_PATH, problems, "CRAFT-SOURCE", {}), credits, problems)
    manifest = load_json(MANIFEST_PATH, problems, "CRAFT-REGISTRY", {})
    skill_version = manifest.get("version", "0.0.0") if isinstance(manifest, dict) else "0.0.0"

    index = []
    docs = {}
    shas = {}
    for entry in registry:
        path = TOPICS_DIR / entry["family"] / (entry["id"] + ".md")
        if not path.exists():
            continue
        topic = parse_topic(path, entry, problems)
        if topic is None:
            continue
        size = len(topic["body"].encode("ascii"))
        where = rel(path)
        if isinstance(entry["maxBytes"], int) and size > entry["maxBytes"]:
            problems.error("CRAFT-SIZE", where, "%d bytes, above its maxBytes %d" % (size, entry["maxBytes"]))
        elif size > TOPIC_WARN:
            problems.warn("CRAFT-SIZE", where, "%d bytes, above %d; consider a section split" % (size, TOPIC_WARN))
        for sid, text in topic["parts"]:
            for lit in flat_hits(text, literals):
                problems.error("CRAFT-FLAT", where, "the phrase literal '%s' (section '%s'); reword it" % (lit, sid or "(preamble)"))
        row = {"id": entry["id"], "family": entry["family"], "title": entry["title"], "bytes": size,
               "summary": topic["front"].get("summary", ""), "sections": [s for s, _ in topic["parts"] if s],
               "origin": entry["originalOrAdapted"], "reviewed": topic["front"].get("reviewed", ""),
               "sources": source_line(entry, sources)}
        for key in ("title", "summary", "sources"):
            for lit in flat_hits(row[key], literals):
                problems.error("CRAFT-FLAT", where, "the phrase literal '%s' in its %s" % (lit, key))
        index.append(row)
        docs[entry["id"]] = topic["parts"]
        shas[entry["id"]] = topic["sha256"]

    total = sum(row["bytes"] for row in index)
    if total > CORPUS_MAX:
        problems.error("CRAFT-SIZE", rel(TOPICS_DIR), "the corpus is %d bytes, above %d" % (total, CORPUS_MAX))
    corpus = corpus_hash(index, docs)

    # Every listing and header the skill can return, checked for size and phrase literals.
    for family in [None] + FAMILIES:
        text = listing(skill_version, corpus, index, family)
        if len(text) > LISTING_MAX:
            problems.error("CRAFT-SIZE", "craft.topics", "the listing%s is %d bytes, above %d" % (
                "" if family is None else " of family " + family, len(text), LISTING_MAX))
        for lit in flat_hits(text, literals):
            problems.error("CRAFT-FLAT", "craft.topics", "the phrase literal '%s' in a listing" % lit)
    for row in index:
        for sid, text in [(None, None)] + list(docs[row["id"]]):
            if sid == "":
                continue
            size = row["bytes"] if sid is None else len(text)
            for lit in flat_hits(header(skill_version, row, sid, size), literals):
                problems.error("CRAFT-FLAT", "craft.read %s" % row["id"], "the phrase literal '%s' in a header" % lit)

    # CRAFT-PERMANENT: every released id and section id still exists.
    released = load_json(RELEASED_PATH, problems, "CRAFT-PERMANENT", {"versions": []})
    by_id = {row["id"]: row for row in index}
    for version in released.get("versions", []) if isinstance(released, dict) else []:
        for tid, sections in (version.get("topics") or {}).items():
            if tid not in by_id:
                problems.error("CRAFT-PERMANENT", rel(RELEASED_PATH), "%s published topic '%s', which no longer exists" % (version.get("version"), tid))
                continue
            for sid in sections:
                if sid not in by_id[tid]["sections"]:
                    problems.error("CRAFT-PERMANENT", rel(RELEASED_PATH), "%s published section '%s' of '%s', which no longer exists" % (version.get("version"), sid, tid))

    # CRAFT-OWNER: a listed topic needs a sign-off for its current sha256 (an error under --release only).
    owner = load_json(OWNER_PATH, problems, "CRAFT-OWNER", {"topics": [], "signoffs": []})
    signed = {(s.get("topic"), s.get("sha256")) for s in owner.get("signoffs", []) if isinstance(s, dict)}
    for tid in owner.get("topics", []):
        if tid not in shas:
            problems.error("CRAFT-OWNER", rel(OWNER_PATH), "lists '%s', which is not a topic" % tid)
        elif (tid, shas[tid]) not in signed:
            problems.pending("CRAFT-OWNER", rel(OWNER_PATH), "'%s' has no owner sign-off for sha256 %s" % (tid, shas[tid][:12]))

    outputs = {}
    if MAIN_PATH.exists():
        main = splice(MAIN_PATH.read_text(encoding="utf-8"), BEGIN, END, render_block(skill_version, corpus, index, docs),
                      rel(MAIN_PATH), problems)
        outputs[MAIN_PATH] = main
        if len(main.encode("utf-8")) > MAIN_MAX:
            problems.error("CRAFT-SIZE", rel(MAIN_PATH), "%d bytes, above %d" % (len(main.encode("utf-8")), MAIN_MAX))
        handlers = main.replace(render_block(skill_version, corpus, index, docs), "")
        for lit in flat_hits(handlers, literals):
            problems.error("CRAFT-FLAT", rel(MAIN_PATH), "the phrase literal '%s' in the handlers (error sentences)" % lit)
    else:
        problems.error("CRAFT-SIZE", rel(MAIN_PATH), "the entrypoint is missing")
    if README_PATH.exists():
        outputs[README_PATH] = splice(README_PATH.read_text(encoding="utf-8"), TABLE_BEGIN, TABLE_END,
                                      render_table(registry, index), rel(README_PATH), problems)
    else:
        problems.error("CRAFT-SIZE", rel(README_PATH), "the README is missing")
    outputs[NOTICES_PATH] = render_notices(registry, sources, credits)
    lock = {"generatedBy": "build/craft-reference/generate.py", "skillVersion": skill_version, "corpus": corpus,
            "corpusBytes": total,
            "topics": [{"id": row["id"], "bytes": row["bytes"], "sha256": shas[row["id"]], "sections": row["sections"]}
                       for row in index]}
    outputs[LOCK_PATH] = json.dumps(lock, indent=2, ensure_ascii=True) + "\n"
    return problems, outputs, {"index": index, "registry": registry, "total": total, "corpus": corpus}


def months_between(month, today):
    year, mon = (int(x) for x in month.split("-"))
    return (today.year - year) * 12 + (today.month - mon)


def summary(info, outputs, problems):
    registry = {e["id"]: e for e in info["registry"]}
    today = datetime.date.today()
    print("%-28s %-12s %8s %8s %4s  %s" % ("topic", "family", "bytes", "max", "secs", "reviewed"))
    fam_bytes = {f: 0 for f in FAMILIES}
    fam_max = {f: 0 for f in FAMILIES}
    for row in info["index"]:
        cap = registry[row["id"]]["maxBytes"]
        fam_bytes[row["family"]] += row["bytes"]
        fam_max[row["family"]] += cap
        print("%-28s %-12s %8d %8d %4d  %s" % (row["id"], row["family"], row["bytes"], cap, len(row["sections"]), row["reviewed"]))
        if MONTH_RE.match(row["reviewed"]):
            limit = 6 if row["id"] in FAST_REFRESH else 12
            if months_between(row["reviewed"], today) > limit:
                problems.warn("CRAFT-STALE", row["id"], "reviewed %s is older than %d months" % (row["reviewed"], limit))
    for family in FAMILIES:
        print("family %-12s %8d of %8d allocated" % (family, fam_bytes[family], fam_max[family]))
    print("corpus %d of %d bytes, %d topics, hash %s" % (info["total"], CORPUS_MAX, len(info["index"]), info["corpus"][:12]))
    if MAIN_PATH in outputs:
        print("main.py %d of %d bytes" % (len(outputs[MAIN_PATH].encode("utf-8")), MAIN_MAX))


def main():
    parser = argparse.ArgumentParser(description="Generate the craft-reference skill from build/craft-reference/.")
    parser.add_argument("--check", action="store_true", help="fail when a generated file differs (writes nothing)")
    parser.add_argument("--summary", action="store_true", help="print sizes and review months (writes nothing)")
    parser.add_argument("--release", action="store_true", help="CRAFT-OWNER and the CRAFT-SOURCE pins become errors")
    args = parser.parse_args()

    problems, outputs, info = build(args.release)
    if args.summary:
        summary(info, outputs, problems)
    for note in problems.notes:
        print("note " + note)
    for warning in problems.warnings:
        print("WARN " + warning)
    if problems.errors:
        for error in problems.errors:
            print("ERROR " + error)
        print("generate.py: %d error(s); nothing written" % len(problems.errors))
        return 1
    if args.summary:
        return 0
    drift = []
    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            drift.append(rel(path))
            if not args.check:
                path.write_text(text, encoding="utf-8", newline="\n")
    if args.check:
        if drift:
            for name in drift:
                print("DRIFT " + name)
            print("generate.py --check: %d file(s) differ; run python -B build/craft-reference/generate.py" % len(drift))
            return 1
        print("generate.py --check: OK (%d topics, %d bytes, corpus %s, %d note(s))" % (
            len(info["index"]), info["total"], info["corpus"][:12], len(problems.notes)))
        return 0
    print("generate.py: wrote %s" % (", ".join(drift) if drift else "nothing (no change)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
