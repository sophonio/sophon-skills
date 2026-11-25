"""API handlers. Each takes a Request and returns (status, body)."""

from dataclasses import dataclass, field


@dataclass
class Request:
    user: str
    params: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)


class Store:
    def __init__(self, entries):
        self.entries = {entry.id: entry for entry in entries}


def list_entries(store, request):
    mine = [entry for entry in store.entries.values() if entry.owner == request.user and not entry.archived]
    return 200, [{"id": entry.id, "project": entry.project, "minutes": entry.minutes} for entry in mine]


def delete_entry(store, request):
    entry = store.entries.get(request.params["id"])
    if entry is None:
        return 404, {"error": "no such entry"}
    del store.entries[entry.id]
    return 204, None


def archive_entry(store, request):
    entry = store.entries.get(request.params["id"])
    if entry is None:
        return 404, {"error": "no such entry"}
    entry.archived = True
    return 200, {"id": entry.id, "archived": True}
