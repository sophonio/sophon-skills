"""GitHub Projects (v2) skill — talks to the GitHub GraphQL API with a personal access token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (token).
"""

import json
import urllib.request
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "sophon-github-projects",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def graphql(query, variables=None):
    """Run a GraphQL query/mutation. Returns the `data` object or raises on errors."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(GRAPHQL_URL, data=payload, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"GitHub GraphQL error {e.code}: {detail}") from e
    if body.get("errors"):
        messages = "; ".join(err.get("message", str(err)) for err in body["errors"])
        raise RuntimeError(f"GraphQL: {messages}")
    return body.get("data") or {}


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def owner_root(owner_type):
    return "user" if (owner_type or "organization").lower() == "user" else "organization"


def project_summary(node):
    return {
        "id": node.get("id"),
        "number": node.get("number"),
        "title": node.get("title"),
        "url": node.get("url"),
        "closed": node.get("closed"),
    }


# --- Tool handlers ---------------------------------------------------------

def projects_list():
    owner = params.get("owner", "")
    root = owner_root(params.get("ownerType"))
    limit = clamp(params.get("limit", 20), 20, 100)
    query = f"""
    query($owner: String!, $limit: Int!) {{
      {root}(login: $owner) {{
        projectsV2(first: $limit) {{
          nodes {{ id number title url closed }}
        }}
      }}
    }}
    """
    data = graphql(query, {"owner": owner, "limit": limit})
    holder = data.get(root) or {}
    nodes = ((holder.get("projectsV2") or {}).get("nodes")) or []
    projects = [project_summary(n) for n in nodes if n]
    print(json.dumps({"count": len(projects), "projects": projects}))


def projects_get_items():
    owner = params.get("owner", "")
    root = owner_root(params.get("ownerType"))
    number = int(params.get("number"))
    limit = clamp(params.get("limit", 30), 30, 100)
    query = f"""
    query($owner: String!, $number: Int!, $limit: Int!) {{
      {root}(login: $owner) {{
        projectV2(number: $number) {{
          id
          title
          items(first: $limit) {{
            nodes {{
              id
              type
              content {{
                __typename
                ... on Issue {{ number title state url }}
                ... on PullRequest {{ number title state url }}
                ... on DraftIssue {{ title }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    data = graphql(query, {"owner": owner, "number": number, "limit": limit})
    holder = data.get(root) or {}
    project = holder.get("projectV2")
    if not project:
        raise RuntimeError(f"Project #{number} not found for {owner}")
    nodes = ((project.get("items") or {}).get("nodes")) or []
    items = []
    for n in nodes:
        if not n:
            continue
        content = n.get("content") or {}
        items.append({
            "id": n.get("id"),
            "type": n.get("type"),
            "contentType": content.get("__typename"),
            "number": content.get("number"),
            "title": content.get("title"),
            "state": content.get("state"),
            "url": content.get("url"),
        })
    print(json.dumps({
        "projectId": project.get("id"),
        "title": project.get("title"),
        "count": len(items),
        "items": items,
    }))


def projects_add_draft_issue():
    project_id = params.get("projectId", "")
    title = params.get("title", "")
    body = params.get("body") or ""
    query = """
    mutation($projectId: ID!, $title: String!, $body: String!) {
      addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
        projectItem { id }
      }
    }
    """
    data = graphql(query, {"projectId": project_id, "title": title, "body": body})
    item = ((data.get("addProjectV2DraftIssue") or {}).get("projectItem")) or {}
    print(json.dumps({"itemId": item.get("id")}))


def projects_update_item_status():
    query = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { singleSelectOptionId: $optionId }
      }) {
        projectV2Item { id }
      }
    }
    """
    data = graphql(query, {
        "projectId": params.get("projectId", ""),
        "itemId": params.get("itemId", ""),
        "fieldId": params.get("fieldId", ""),
        "optionId": params.get("optionId", ""),
    })
    item = ((data.get("updateProjectV2ItemFieldValue") or {}).get("projectV2Item")) or {}
    print(json.dumps({"itemId": item.get("id"), "updated": bool(item.get("id"))}))


HANDLERS = {
    "projects.list": projects_list,
    "projects.get_items": projects_get_items,
    "projects.add_draft_issue": projects_add_draft_issue,
    "projects.update_item_status": projects_update_item_status,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not token:
        print(json.dumps({"error": "Missing GitHub credential: connect the GitHub Projects integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
