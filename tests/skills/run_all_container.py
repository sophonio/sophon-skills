"""Container parity smoke: run inside python:3.13-alpine with the repo mounted at /repo.

Replicates the Sophon runtime's exec-with-params-global model for every skill listed below:
unknown-tool and missing-credentials paths must emit clean JSON errors on Python 3.13/alpine.
ffmpeg-video runs only on the process backend: from the Docker backend's /workspace cwd it must
refuse with BACKEND_UNSUPPORTED, and its entrypoint must give Sophon nothing to pip-install.
craft-reference must answer one read and an unknown tool from /workspace, with nothing to pip-install.
"""
import contextlib
import io
import json
import os
import re
import sys

REPO = "/repo"
PAIRS = [
    ("salesforce", "sf.soql_query"), ("servicenow", "snow.search_records"),
    ("sharepoint", "sp.search_sites"), ("snowflake", "snowflake.list_databases"),
    ("zendesk", "zendesk.list_tickets"), ("outlook-mail", "mail.list_folders"),
    ("entra-id", "entra.search_users"), ("databricks", "databricks.list_warehouses"),
    ("okta", "okta.search_users"), ("azure-devops", "devops.list_builds"),
    ("splunk", "splunk.list_indexes"), ("elasticsearch", "es.cluster_health"),
    ("powerbi", "powerbi.list_workspaces"), ("onedrive", "onedrive.list_folder"),
    ("bitbucket", "bitbucket.list_repos"), ("mongodb-atlas", "atlas.list_projects"),
    ("jenkins", "jenkins.list_jobs"), ("intercom", "intercom.search_conversations"),
    ("freshdesk", "freshdesk.list_tickets"), ("freshservice", "freshservice.list_tickets"),
    ("hubspot", "hubspot.list_owners"), ("pipedrive", "pipedrive.list_deals"),
    ("clickhouse", "clickhouse.list_databases"), ("sonarqube", "sonar.search_projects"),
    ("jira-service-management", "jsm.list_service_desks"), ("planner", "planner.list_plans"),
    ("tableau", "tableau.list_workbooks"), ("hashicorp-vault", "vault.list_mounts"),
    ("dynamics-365", "dynamics.whoami"), ("artifactory", "artifactory.list_repositories"),
    ("tmdb", "tmdb.get_trending"), ("plex", "plex.list_libraries"),
    ("jellyfin", "jellyfin.list_libraries"), ("radarr", "radarr.list_movies"),
    ("sonarr", "sonarr.list_series"), ("seerr", "seerr.list_requests"),
    ("steam", "steam.get_player_summary"), ("twitch", "twitch.get_top_games"),
    ("ticketmaster", "ticketmaster.search_events"), ("lastfm", "lastfm.get_chart_top_artists"),
    ("todoist", "todoist.list_tasks"), ("dataroot", "dataroot.list_organizations"),
]


def run(skill, params, cwd=None):
    src = open(f"{REPO}/skills/{skill}/main.py", encoding="utf-8").read()
    buf = io.StringIO()
    old = os.getcwd()
    if cwd:
        os.makedirs(cwd, exist_ok=True)
        os.chdir(cwd)
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "main.py", "exec"), {"params": params})
    finally:
        os.chdir(old)
    return buf.getvalue().strip()


# PythonImportResolver (src/Sophon.Sandbox): every line matching this is pip-installed unless stdlib
IMPORT_RE = re.compile(r"^(?:import|from)\s+(\w+)")


def pip_names(skill):
    src = open(f"{REPO}/skills/{skill}/main.py", encoding="utf-8").read()
    names = set()
    for line in src.splitlines():
        match = IMPORT_RE.match(line.lstrip())
        if match and not line.lstrip().startswith("#"):
            names.add(match.group(1))
    return sorted(n for n in names if n not in sys.stdlib_module_names)


fails = 0
for skill, tool in PAIRS:
    try:
        unknown = json.loads(run(skill, {"tool": "nope.nope"}))
        nocreds = json.loads(run(skill, {"tool": tool}))
        ok = ("unknown tool" in unknown.get("error", "").lower()
              and "connect" in nocreds.get("error", "").lower())
    except Exception as e:  # noqa: BLE001
        ok, unknown, nocreds = False, {"error": f"{type(e).__name__}: {e}"}, {}
    print(f"{'ok  ' if ok else 'FAIL'} {skill}: {unknown.get('error', '')[:70]}")
    if not ok:
        fails += 1
# ffmpeg-video: the Docker backend runs the script in /workspace, which has no FFmpeg
try:
    unknown = json.loads(run("ffmpeg-video", {"tool": "nope.nope"}, cwd="/workspace"))
    refused = json.loads(run("ffmpeg-video", {"tool": "ffmpeg.setup.doctor"}, cwd="/workspace"))
    ok = ("unknown tool" in unknown.get("error", "").lower()
          and refused.get("code") == "BACKEND_UNSUPPORTED" and refused.get("backend") == "docker"
          and not pip_names("ffmpeg-video"))
except Exception as e:  # noqa: BLE001
    ok, refused = False, {"error": f"{type(e).__name__}: {e}"}
print(f"{'ok  ' if ok else 'FAIL'} ffmpeg-video: {refused.get('code') or refused.get('error', '')[:70]}")
if not ok:
    fails += 1
# craft-reference: topics are embedded in main.py; one read, an unknown tool, nothing to install
try:
    unknown = json.loads(run("craft-reference", {"tool": "nope.nope"}, cwd="/workspace"))
    topic = run("craft-reference", {"tool": "craft.read", "topic": "design-schools", "section": "swiss"}, cwd="/workspace")
    ok = ("unknown tool" in unknown.get("error", "").lower() and unknown.get("code") == "UNKNOWN_TOOL"
          and topic.startswith("[craft-reference ") and "## Swiss" in topic and not pip_names("craft-reference"))
except Exception as e:  # noqa: BLE001
    ok, topic = False, f"{type(e).__name__}: {e}"
print(f"{'ok  ' if ok else 'FAIL'} craft-reference: {topic.splitlines()[0][:70] if topic else ''}")
if not ok:
    fails += 1
total = len(PAIRS) + 2
print(f"python {sys.version.split()[0]} — {total - fails}/{total} passed")
sys.exit(1 if fails else 0)
