"""Container parity smoke: run inside python:3.13-alpine with the repo mounted at /repo.

Replicates the Sophon runtime's exec-with-params-global model for all 20 wave-5/6 skills:
unknown-tool and missing-credentials paths must emit clean JSON errors on Python 3.13/alpine.
"""
import contextlib
import io
import json
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
]


def run(skill, params):
    src = open(f"{REPO}/skills/{skill}/main.py", encoding="utf-8").read()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(src, "main.py", "exec"), {"params": params})
    return buf.getvalue().strip()


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
print(f"python {sys.version.split()[0]} — {len(PAIRS) - fails}/{len(PAIRS)} passed")
sys.exit(1 if fails else 0)
