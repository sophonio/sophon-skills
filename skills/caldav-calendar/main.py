"""CalDAV calendar integration skill.

Talks to any CalDAV server (iCloud, Fastmail, Nextcloud, Google app-password, ...) using the
pure-python `caldav` client and the `icalendar` parser/builder. `params` is injected as a global by
the Sophon runtime and carries the tool name, the tool arguments, and the connection-card credential
fields (url, username, password).
"""

import json
import uuid
from datetime import datetime, date, timedelta, timezone

import caldav
import icalendar

tool_name = params.get("tool", "")
url = params.get("url", "")
username = params.get("username", "")
password = params.get("password", "")


# --- Helpers ---------------------------------------------------------------

def connect():
    """Open a CalDAV client and return the principal."""
    client = caldav.DAVClient(url=url, username=username, password=password)
    return client.principal()


def find_calendar(principal, selector):
    """Locate a calendar by name or URL. Falls back to the first calendar when selector is empty."""
    calendars = principal.calendars()
    if not calendars:
        raise RuntimeError("No calendars found on this CalDAV account.")
    if not selector:
        return calendars[0]
    for cal in calendars:
        if str(cal.url) == selector:
            return cal
    for cal in calendars:
        name = getattr(cal, "name", None) or (cal.get_display_name() if hasattr(cal, "get_display_name") else None)
        if name and str(name) == selector:
            return cal
    raise RuntimeError(f"Calendar not found: {selector}")


def parse_dt(value, all_day=False):
    """Parse an ISO 8601 string into a date (all-day) or datetime."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Empty date/time value")
    date_only = "T" not in value and len(value) <= 10
    if all_day or date_only:
        return date.fromisoformat(value[:10])
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        if value.endswith("Z"):
            return datetime.fromisoformat(value[:-1]).replace(tzinfo=timezone.utc)
        raise ValueError(f"Unable to parse date/time: {value}")


def iso_or_str(dt):
    """Render a date/datetime for JSON output."""
    if dt is None:
        return None
    inner = getattr(dt, "dt", dt)
    if hasattr(inner, "isoformat"):
        return inner.isoformat()
    return str(inner)


def get_vevent(event):
    """Return the first VEVENT component of a caldav event, or None."""
    ical = event.icalendar_instance
    for comp in ical.walk("VEVENT"):
        return comp
    return None


def event_to_dict(event):
    """Convert a caldav event into a serializable dict."""
    comp = get_vevent(event)
    if comp is None:
        return None
    return {
        "uid": str(comp.get("uid")) if comp.get("uid") is not None else None,
        "summary": str(comp.get("summary")) if comp.get("summary") is not None else None,
        "start": iso_or_str(comp.get("dtstart")),
        "end": iso_or_str(comp.get("dtend")),
        "location": str(comp.get("location")) if comp.get("location") is not None else None,
        "description": str(comp.get("description")) if comp.get("description") is not None else None,
        "url": str(event.url) if getattr(event, "url", None) else None,
    }


# --- Tool handlers ---------------------------------------------------------

def list_calendars():
    principal = connect()
    out = []
    for cal in principal.calendars():
        name = getattr(cal, "name", None)
        if not name and hasattr(cal, "get_display_name"):
            try:
                name = cal.get_display_name()
            except Exception:
                name = None
        out.append({"name": str(name) if name else None, "url": str(cal.url)})
    print(json.dumps({"count": len(out), "calendars": out}))


def list_events():
    principal = connect()
    cal = find_calendar(principal, params.get("calendar"))

    start = parse_dt(params["start"]) if params.get("start") else datetime.now(timezone.utc)
    end = parse_dt(params["end"]) if params.get("end") else (
        (start if isinstance(start, datetime) else datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc))
        + timedelta(days=30)
    )

    try:
        results = cal.search(start=start, end=end, event=True, expand=True)
    except Exception:
        # Older servers/clients: fall back to date_search.
        results = cal.date_search(start=start, end=end, expand=True)

    events = []
    for ev in results:
        d = event_to_dict(ev)
        if d:
            events.append(d)
    events.sort(key=lambda e: e.get("start") or "")
    print(json.dumps({"count": len(events), "events": events}))


def create_event():
    principal = connect()
    cal = find_calendar(principal, params.get("calendar"))

    all_day = bool(params.get("allDay"))
    uid = str(uuid.uuid4())

    vevent = icalendar.Event()
    vevent.add("uid", uid)
    vevent.add("summary", params.get("summary", ""))
    vevent.add("dtstart", parse_dt(params.get("start", ""), all_day))
    vevent.add("dtend", parse_dt(params.get("end", ""), all_day))
    vevent.add("dtstamp", datetime.now(timezone.utc))
    if params.get("description"):
        vevent.add("description", params["description"])
    if params.get("location"):
        vevent.add("location", params["location"])

    cal_obj = icalendar.Calendar()
    cal_obj.add("prodid", "-//Sophon//CalDAV Calendar Skill//EN")
    cal_obj.add("version", "2.0")
    cal_obj.add_component(vevent)

    cal.save_event(cal_obj.to_ical().decode("utf-8"))
    print(json.dumps({"uid": uid, "created": True}))


def update_event():
    principal = connect()
    cal = find_calendar(principal, params.get("calendar"))
    uid = params.get("uid", "")

    event = cal.event_by_uid(uid)
    ical = event.icalendar_instance
    comp = None
    for c in ical.walk("VEVENT"):
        comp = c
        break
    if comp is None:
        raise RuntimeError(f"Event {uid} has no VEVENT component.")

    def replace(field, value):
        if field in comp:
            del comp[field]
        comp.add(field, value)

    if params.get("summary") is not None:
        replace("summary", params["summary"])
    if params.get("start") is not None:
        replace("dtstart", parse_dt(params["start"]))
    if params.get("end") is not None:
        replace("dtend", parse_dt(params["end"]))
    if params.get("description") is not None:
        replace("description", params["description"])
    if params.get("location") is not None:
        replace("location", params["location"])

    event.data = ical.to_ical().decode("utf-8")
    event.save()
    print(json.dumps({"uid": uid, "updated": True}))


def delete_event():
    principal = connect()
    cal = find_calendar(principal, params.get("calendar"))
    uid = params.get("uid", "")
    event = cal.event_by_uid(uid)
    event.delete()
    print(json.dumps({"uid": uid, "deleted": True}))


HANDLERS = {
    "caldav.list_calendars": list_calendars,
    "caldav.list_events": list_events,
    "caldav.create_event": create_event,
    "caldav.update_event": update_event,
    "caldav.delete_event": delete_event,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not url or not username or not password:
        print(json.dumps({"error": "Missing CalDAV credential: connect the CalDAV Calendar integration first."}))
    else:
        handler()
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": str(e)}))
