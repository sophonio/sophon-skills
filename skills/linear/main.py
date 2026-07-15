"""Linear integration skill — talks to the Linear GraphQL API with a personal API key.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential field (apiKey).

Note: Linear uses a BARE Authorization header (no 'Bearer' prefix).
"""

import json
import re
import urllib.request
import urllib.error

tool_name = params.get("tool", "")
api_key = params.get("apiKey", "")

ENDPOINT = "https://api.linear.app/graphql"
HEADERS = {
    "Authorization": api_key,
    "Content-Type": "application/json",
    "User-Agent": "sophon-linear-skill",
}

# Identifiers look like ENG-123 (team key, dash, number).
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9]+-\d+$")


def graphql(query, variables=None):
    """Execute a GraphQL request and return the `data` object.

    Raises RuntimeError on transport errors or GraphQL-level errors (HTTP 200 with an
    "errors" array).
    """
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Linear API error {e.code}: {detail}") from e
    if body.get("errors"):
        messages = "; ".join(
            err.get("message", "unknown error") for err in body["errors"]
        )
        raise RuntimeError(f"Linear GraphQL error: {messages}")
    return body.get("data") or {}


def issue_summary(node):
    return {
        "id": node.get("id"),
        "identifier": node.get("identifier"),
        "title": node.get("title"),
        "state": (node.get("state") or {}).get("name"),
        "assignee": (node.get("assignee") or {}).get("name"),
        "url": node.get("url"),
    }


def resolve_issue(identifier_or_id):
    """Return the full issue node for a UUID or an IDENT-123 identifier."""
    value = (identifier_or_id or "").strip()
    fields = """
        id
        identifier
        title
        description
        url
        state { name }
        assignee { name }
    """
    if IDENTIFIER_RE.match(value):
        # Identifiers are best resolved by searching; issueSearch matches the identifier text.
        search_query = "query($q: String!) { issueSearch(query: $q, first: 10) { nodes { %s } } }" % fields
        data = graphql(search_query, {"q": value})
        nodes = (data.get("issueSearch") or {}).get("nodes", [])
        for node in nodes:
            if (node.get("identifier") or "").upper() == value.upper():
                return node
        if nodes:
            return nodes[0]
        raise RuntimeError(f"Issue not found: {value}")
    # Treat as a UUID.
    query = "query($id: String!) { issue(id: $id) { %s } }" % fields
    data = graphql(query, {"id": value})
    node = data.get("issue")
    if not node:
        raise RuntimeError(f"Issue not found: {value}")
    return node


def resolve_issue_uuid(identifier_or_id):
    """Return the UUID for a UUID or an IDENT-123 identifier."""
    value = (identifier_or_id or "").strip()
    if IDENTIFIER_RE.match(value):
        return resolve_issue(value)["id"]
    return value


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


# --- Tool handlers ---------------------------------------------------------

def search_issues():
    query_text = params.get("query", "")
    first = clamp(params.get("limit", 25), 25, 100)
    gql = """
    query($q: String!, $first: Int!) {
      issueSearch(query: $q, first: $first) {
        nodes {
          id
          identifier
          title
          state { name }
          assignee { name }
          url
        }
      }
    }
    """
    data = graphql(gql, {"q": query_text, "first": first})
    nodes = (data.get("issueSearch") or {}).get("nodes", [])
    issues = [issue_summary(n) for n in nodes]
    print(json.dumps({"count": len(issues), "issues": issues}))


def get_issue():
    node = resolve_issue(params.get("id", ""))
    print(json.dumps({
        "id": node.get("id"),
        "identifier": node.get("identifier"),
        "title": node.get("title"),
        "description": node.get("description"),
        "state": (node.get("state") or {}).get("name"),
        "assignee": (node.get("assignee") or {}).get("name"),
        "url": node.get("url"),
    }))


def list_teams():
    gql = "query { teams { nodes { id name key } } }"
    data = graphql(gql)
    nodes = (data.get("teams") or {}).get("nodes", [])
    teams = [{"id": n.get("id"), "name": n.get("name"), "key": n.get("key")} for n in nodes]
    print(json.dumps({"count": len(teams), "teams": teams}))


def create_issue():
    issue_input = {
        "teamId": params.get("teamId", ""),
        "title": params.get("title", ""),
    }
    if params.get("description"):
        issue_input["description"] = params["description"]
    if params.get("priority") is not None:
        issue_input["priority"] = int(params["priority"])
    if params.get("assigneeId"):
        issue_input["assigneeId"] = params["assigneeId"]
    gql = """
    mutation($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier url }
      }
    }
    """
    data = graphql(gql, {"input": issue_input})
    result = data.get("issueCreate") or {}
    issue = result.get("issue") or {}
    print(json.dumps({
        "success": result.get("success"),
        "id": issue.get("id"),
        "identifier": issue.get("identifier"),
        "url": issue.get("url"),
    }))


def update_issue():
    issue_id = resolve_issue_uuid(params.get("id", ""))
    issue_input = {}
    if params.get("title") is not None:
        issue_input["title"] = params["title"]
    if params.get("description") is not None:
        issue_input["description"] = params["description"]
    if params.get("stateId"):
        issue_input["stateId"] = params["stateId"]
    if params.get("priority") is not None:
        issue_input["priority"] = int(params["priority"])
    if params.get("assigneeId"):
        issue_input["assigneeId"] = params["assigneeId"]
    if not issue_input:
        raise ValueError("update_issue requires at least one field to change")
    gql = """
    mutation($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) {
        success
        issue { id identifier url }
      }
    }
    """
    data = graphql(gql, {"id": issue_id, "input": issue_input})
    result = data.get("issueUpdate") or {}
    issue = result.get("issue") or {}
    print(json.dumps({
        "success": result.get("success"),
        "id": issue.get("id"),
        "identifier": issue.get("identifier"),
        "url": issue.get("url"),
    }))


def add_comment():
    issue_id = resolve_issue_uuid(params.get("issueId", ""))
    comment_input = {"issueId": issue_id, "body": params.get("body", "")}
    gql = """
    mutation($input: CommentCreateInput!) {
      commentCreate(input: $input) {
        success
        comment { id url }
      }
    }
    """
    data = graphql(gql, {"input": comment_input})
    result = data.get("commentCreate") or {}
    comment = result.get("comment") or {}
    print(json.dumps({
        "success": result.get("success"),
        "id": comment.get("id"),
        "url": comment.get("url"),
    }))


HANDLERS = {
    "linear.search_issues": search_issues,
    "linear.get_issue": get_issue,
    "linear.list_teams": list_teams,
    "linear.create_issue": create_issue,
    "linear.update_issue": update_issue,
    "linear.add_comment": add_comment,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_key:
        print(json.dumps({"error": "Missing Linear credential: connect the Linear integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
