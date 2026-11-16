"""Inkling API integration for Sophon's injected-credential sandbox."""
import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request

TOOL = params.get("tool", "")
API_KEY = params.get("apiKey", "")
BASE = "https://api.inkling.buildersoft.io/v1"
MAX_PROBLEM_BYTES = 16384
MAX_NOTE_REQUEST_BYTES = 8 * 1024 * 1024
STATUSES = ("not_started", "in_progress", "waiting", "done")
ROLES = ("edit", "view")
SOURCE_TEXT_FIELDS = ("title", "snippet", "published_date")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_problem_fields(exc):
    """Return only bounded, identifier-shaped problem members, never raw text."""
    try:
        raw = exc.read(MAX_PROBLEM_BYTES + 1)
        if len(raw) > MAX_PROBLEM_BYTES:
            return {}
        problem = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(problem, dict):
        return {}
    fields = {}
    for name, pattern in (("code", r"[a-z][a-z0-9_]{0,63}"),
                          ("correlation_id", r"[A-Za-z0-9_-]{1,128}")):
        value = problem.get(name)
        if (isinstance(value, str) and re.fullmatch(pattern, value)
                and API_KEY.casefold() not in value.casefold()):
            fields[name] = value
    return fields


def request(method, path, query=None, body=None, headers=None):
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode({k: str(v).lower() if isinstance(v, bool) else v for k, v in query.items() if v is not None})
    request_headers = {"Authorization": "Bearer " + API_KEY, "Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    data = json.dumps(body, ensure_ascii=True).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        # Do not expose human-readable server text or unrestricted problem members.
        result = {"error": "Inkling API request failed", "status": exc.code}
        retry = exc.headers.get("Retry-After") if exc.headers else None
        if retry and re.fullmatch(r"[0-9]{1,10}", retry) and API_KEY.casefold() not in retry.casefold():
            result["retry_after"] = retry
        result.update(safe_problem_fields(exc))
        try:
            exc.close()
        except Exception:
            pass
        return result
    except (urllib.error.URLError, OSError, ValueError):
        return {"error": "Inkling API request failed"}


def identifier(value):
    if not isinstance(value, str) or not value or value in (".", ".."):
        raise ValueError("id must be a nonempty identifier")
    return urllib.parse.quote(value, safe="")


def optional_query(names):
    return {name: params[name] for name in names if name in params and params[name] is not None}


def body_fields(names):
    return {name: params[name] for name in names if name in params}


def header(name, parameter):
    value = params.get(parameter)
    if value is None:
        return {}
    if not isinstance(value, str) or not 1 <= len(value) <= 255 or any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise ValueError(parameter + " must be 1–255 printable ASCII characters")
    return {name: value}


def check_text_query(query, names):
    for name in names:
        if name in query and not isinstance(query[name], str):
            raise ValueError(name + " must be a string")


def check_limit(query):
    # The API clamps to 1-50 (0 or less means 20); only the type is checked here.
    if "limit" in query and type(query["limit"]) is not int:
        raise ValueError("limit must be an integer")


def check_bool_query(query, name):
    if name in query and type(query[name]) is not bool:
        raise ValueError(name + " must be a boolean")


def check_date(value, name):
    if value is None:
        return
    message = name + " must be a YYYY-MM-DD date or null"
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError(message)
    try:
        datetime.date(int(value[0:4]), int(value[5:7]), int(value[8:10]))
    except ValueError:
        raise ValueError(message)


def check_nullable_string(value, name):
    if value is not None and not isinstance(value, str):
        raise ValueError(name + " must be a string or null")


def check_tags(value):
    if value is None:
        return
    if not isinstance(value, list) or len(value) > 50:
        raise ValueError("tags must be an array of at most 50 strings, or null")
    for tag in value:
        if not isinstance(tag, str) or not tag or "#" in tag:
            raise ValueError("each tag must be a nonempty string without #")


def check_properties(value, update):
    if value is None:
        return
    if not isinstance(value, dict) or set(value) - {"status", "due", "lead"}:
        raise ValueError("properties must be an object with only status, due and lead, or null")
    if value.get("status") is not None and (not isinstance(value["status"], str) or value["status"] not in STATUSES):
        raise ValueError("properties.status must be not_started, in_progress, waiting, done or null")
    check_date(value.get("due"), "properties.due")
    lead = value.get("lead")
    if update:
        if lead is not None and (not isinstance(lead, str) or not lead):
            raise ValueError("properties.lead must be me, a person key or null")
    elif lead is not None and lead != "me":
        raise ValueError("properties.lead must be me or null when creating a note")


def check_sources(value):
    if value is None:
        return
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError("sources must be an array of at most 100 objects, or null")
    seen = set()
    for source in value:
        if not isinstance(source, dict) or set(source) - {"n", "url", *SOURCE_TEXT_FIELDS}:
            raise ValueError("each source must be an object with only n, url, title, snippet and published_date")
        n = source.get("n")
        if type(n) is not int or not 1 <= n <= 999 or n in seen:
            raise ValueError("each source needs a unique integer n from 1 to 999")
        seen.add(n)
        url = source.get("url")
        parsed = urllib.parse.urlsplit(url) if isinstance(url, str) and len(url) <= 2048 else None
        if parsed is None or parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("each source needs an http or https url of at most 2048 characters")
        for name in SOURCE_TEXT_FIELDS:
            check_nullable_string(source.get(name), "source " + name)


def check_share_with(value):
    if value is None:
        return
    if not isinstance(value, list) or len(value) > 9:
        raise ValueError("share_with must be an array of at most 9 objects, or null")
    for person in value:
        if not isinstance(person, dict) or set(person) != {"email", "role"}:
            raise ValueError("each share_with entry must have exactly email and role")
        if not isinstance(person["email"], str) or "@" not in person["email"]:
            raise ValueError("share_with email must be an email address")
        if not isinstance(person["role"], str) or person["role"] not in ROLES:
            raise ValueError("share_with role must be edit or view")


def check_note_size(body):
    if len(json.dumps(body, ensure_ascii=True).encode("utf-8")) > MAX_NOTE_REQUEST_BYTES:
        raise ValueError("note request must be at most 8 MiB")


def list_notes():
    query = optional_query(("limit", "cursor", "q", "tag", "status", "archived"))
    check_limit(query)
    check_text_query(query, ("cursor", "tag"))
    check_bool_query(query, "archived")
    if "q" in query and (not isinstance(query["q"], str) or len(query["q"]) > 200):
        raise ValueError("q must be a string of at most 200 characters")
    if "status" in query and (not isinstance(query["status"], str) or query["status"] not in STATUSES):
        raise ValueError("status must be not_started, in_progress, waiting or done")
    return request("GET", "/notes", query=query)


def list_todos():
    if "limit" in params:
        raise ValueError("list_todos does not accept limit")
    query = optional_query(("view", "tag", "cursor"))
    check_text_query(query, ("tag", "cursor"))
    if not isinstance(query.get("view", "open"), str) or query.get("view", "open") not in ("open", "done", "assigned"):
        raise ValueError("view must be open, done or assigned")
    if "cursor" in query and query.get("view", "open") != "done":
        raise ValueError("cursor is only supported for the done view")
    return request("GET", "/todos", query=query)


def ask():
    body = body_fields(("query", "discussion_id"))
    if not isinstance(body.get("query"), str) or not 1 <= len(body["query"]) <= 4000:
        raise ValueError("query must be 1–4000 characters")
    if body.get("discussion_id") is not None and (not isinstance(body["discussion_id"], str) or not body["discussion_id"]):
        raise ValueError("discussion_id must be a nonempty string or null")
    return request("POST", "/ask", body=body)


def get_answer():
    query = optional_query(("wait",))
    if "wait" in query and (type(query["wait"]) is not int or not 0 <= query["wait"] <= 20):
        raise ValueError("wait must be an integer from 0 to 20")
    return request("GET", "/answers/" + identifier(params.get("id")), query=query)


def check_note_body(body, update):
    check_nullable_string(body.get("body"), "body")
    check_tags(body.get("tags"))
    check_properties(body.get("properties"), update)
    check_sources(body.get("sources"))


def create_note():
    body = body_fields(("title", "body", "tags", "properties", "sources", "share_with"))
    if not isinstance(body.get("title"), str) or not body["title"]:
        raise ValueError("title is required")
    check_note_body(body, False)
    check_share_with(body.get("share_with"))
    check_note_size(body)
    return request("POST", "/notes", body=body, headers=header("Idempotency-Key", "idempotency_key"))


def update_note():
    body = body_fields(("title", "body", "tags", "properties", "sources"))
    if not body:
        raise ValueError("provide at least one note field")
    if "title" in body and body["title"] is not None and (not isinstance(body["title"], str) or not body["title"]):
        raise ValueError("title cannot be empty")
    check_note_body(body, True)
    check_note_size(body)
    headers = header("If-Match", "if_match")
    if "body" in body and not headers:
        raise ValueError("if_match is required when replacing the body")
    return request("PATCH", "/notes/" + identifier(params.get("id")), body=body, headers=headers)


def append_note():
    body = body_fields(("body", "sources"))
    if not isinstance(body.get("body"), str):
        raise ValueError("body is required")
    check_sources(body.get("sources"))
    return request("POST", "/notes/" + identifier(params.get("id")) + "/append", body=body, headers=header("Idempotency-Key", "idempotency_key"))


def check_repeat(value):
    if value is None:
        return
    message = "repeat must be daily, weekdays, weekly-1 to weekly-7, monthly-1 to monthly-31, yearly-MM-DD or null"
    if not isinstance(value, str):
        raise ValueError(message)
    if value in ("daily", "weekdays") or re.fullmatch(r"weekly-[1-7]", value):
        return
    if re.fullmatch(r"monthly-([1-9]|[12][0-9]|3[01])", value):
        return
    found = re.fullmatch(r"yearly-([0-9]{2})-([0-9]{2})", value)
    if found:
        try:
            datetime.date(2000, int(found.group(1)), int(found.group(2)))
            return
        except ValueError:
            pass
    raise ValueError(message)


def create_todo():
    body = body_fields(("text", "note_id", "due", "priority", "repeat"))
    text = body.get("text")
    if not isinstance(text, str) or not 1 <= len(" ".join(text.split())) <= 2000:
        raise ValueError("text must contain 1–2000 characters after whitespace normalization")
    if body.get("note_id") is not None and (not isinstance(body["note_id"], str) or not body["note_id"]):
        raise ValueError("note_id must be a nonempty string or null")
    check_date(body.get("due"), "due")
    if body.get("priority") is not None and (type(body["priority"]) is not int or body["priority"] not in (1, 2)):
        raise ValueError("priority must be 1, 2 or null")
    check_repeat(body.get("repeat"))
    return request("POST", "/todos", body=body, headers=header("Idempotency-Key", "idempotency_key"))


def get_note():
    return request("GET", "/notes/" + identifier(params.get("id")))


def list_discussions():
    query = optional_query(("limit", "cursor", "archived"))
    check_limit(query)
    check_text_query(query, ("cursor",))
    check_bool_query(query, "archived")
    return request("GET", "/discussions", query=query)


def get_discussion():
    return request("GET", "/discussions/" + identifier(params.get("id")))


def archive_note():
    return request("POST", "/notes/" + identifier(params.get("id")) + "/archive")


def complete_todo():
    return request("POST", "/todos/" + identifier(params.get("id")) + "/complete")


def usage():
    return request("GET", "/usage")


HANDLERS = {
    "inkling.usage": usage, "inkling.list_notes": list_notes, "inkling.get_note": get_note,
    "inkling.list_todos": list_todos, "inkling.ask": ask, "inkling.get_answer": get_answer,
    "inkling.list_discussions": list_discussions, "inkling.get_discussion": get_discussion,
    "inkling.create_note": create_note, "inkling.update_note": update_note,
    "inkling.append_note": append_note, "inkling.archive_note": archive_note,
    "inkling.create_todo": create_todo, "inkling.complete_todo": complete_todo,
}

try:
    if TOOL not in HANDLERS:
        result = {"error": "Unknown Inkling tool"}
    elif not isinstance(API_KEY, str) or not API_KEY:
        result = {"error": "Missing Inkling credential: connect the Inkling integration first."}
    else:
        result = HANDLERS[TOOL]()
    print(json.dumps(result))
except ValueError as exc:
    print(json.dumps({"error": str(exc)}))
except Exception:
    print(json.dumps({"error": "Inkling request could not be completed"}))
