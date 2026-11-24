"""Every API route: (method, pattern) -> handler."""

from . import handlers

ROUTES = {
    ("GET", "/entries"): handlers.list_entries,
    ("DELETE", "/entries/{id}"): handlers.delete_entry,
    ("POST", "/entries/{id}/archive"): handlers.archive_entry,
}


def resolve(method, path):
    for (route_method, pattern), handler in ROUTES.items():
        if route_method != method:
            continue
        params = match(pattern, path)
        if params is not None:
            return handler, params
    return None, None


def match(pattern, path):
    expected = pattern.strip("/").split("/")
    actual = path.split("?")[0].strip("/").split("/")
    if len(expected) != len(actual):
        return None
    params = {}
    for want, got in zip(expected, actual):
        if want.startswith("{") and want.endswith("}"):
            params[want[1:-1]] = got
        elif want != got:
            return None
    return params
