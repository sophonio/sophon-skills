"""Google Personal skill — Gmail via IMAP/SMTP, Calendar via CalDAV.

For @gmail.com personal accounts using App Passwords.
No OAuth or Google Cloud Console required.
"""

import json
import imaplib
import smtplib
import email
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parsedate_to_datetime, formatdate, make_msgid
from datetime import datetime, timedelta, timezone

import caldav

# params is injected by the sandbox runtime via SOPHON_PARAMS
tool_name = params.get("tool", "")
email_address = params.get("email", "")
app_password = params.get("appPassword", "")

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
CALDAV_URL = "https://apidata.googleusercontent.com/caldav/v2/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def decode_header_value(value):
    """Decode an RFC 2047 encoded header value to a plain string."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return "".join(parts)


def detect_html(text):
    """Return True if the text appears to contain HTML markup."""
    stripped = text.strip().lower()
    return (
        stripped.startswith("<!doctype html")
        or stripped.startswith("<html")
        or "<br" in stripped
        or "<p>" in stripped
    )


def extract_body(msg):
    """Extract plain text and HTML body from an email message."""
    text_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
            except Exception:
                continue
            if content_type == "text/plain" and not text_body:
                text_body = decoded
            elif content_type == "text/html" and not html_body:
                html_body = decoded
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    html_body = decoded
                else:
                    text_body = decoded
        except Exception:
            pass
    return text_body, html_body


def list_attachments(msg):
    """Return a list of attachment metadata dicts from an email message."""
    attachments = []
    if not msg.is_multipart():
        return attachments
    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" not in disposition and "inline" not in disposition:
            continue
        content_type = part.get_content_type()
        if content_type in ("text/plain", "text/html") and "attachment" not in disposition:
            continue
        filename = part.get_filename()
        if filename:
            filename = decode_header_value(filename)
        size = len(part.get_payload(decode=True) or b"")
        attachments.append({
            "filename": filename or "unnamed",
            "contentType": content_type,
            "size": size,
        })
    return attachments


def parse_email_message(msg):
    """Parse an email.message.Message into a dict with headers, body, and attachments."""
    date_str = msg.get("Date", "")
    try:
        parsed_date = parsedate_to_datetime(date_str).isoformat()
    except Exception:
        parsed_date = date_str

    text_body, html_body = extract_body(msg)
    attachments = list_attachments(msg)

    return {
        "from": decode_header_value(msg.get("From", "")),
        "to": decode_header_value(msg.get("To", "")),
        "cc": decode_header_value(msg.get("Cc", "")),
        "subject": decode_header_value(msg.get("Subject", "")),
        "date": parsed_date,
        "messageId": msg.get("Message-ID", ""),
        "body": text_body,
        "bodyHtml": html_body,
        "attachments": attachments,
    }


def parse_email_headers(msg):
    """Parse only header fields from an email message (no body)."""
    date_str = msg.get("Date", "")
    try:
        parsed_date = parsedate_to_datetime(date_str).isoformat()
    except Exception:
        parsed_date = date_str

    return {
        "from": decode_header_value(msg.get("From", "")),
        "to": decode_header_value(msg.get("To", "")),
        "subject": decode_header_value(msg.get("Subject", "")),
        "date": parsed_date,
        "messageId": msg.get("Message-ID", ""),
    }


# ---------------------------------------------------------------------------
# IMAP / SMTP connections
# ---------------------------------------------------------------------------

def connect_imap():
    """Connect and authenticate to Gmail IMAP, returning the IMAP4_SSL object."""
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
    imap.login(email_address, app_password)
    return imap


def connect_smtp():
    """Connect and authenticate to Gmail SMTP with STARTTLS, returning the SMTP object."""
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(email_address, app_password)
    return server


# ---------------------------------------------------------------------------
# Email tools
# ---------------------------------------------------------------------------

def mail_list():
    """List recent inbox emails."""
    max_results = int(params.get("maxResults", 10))
    imap = None
    try:
        imap = connect_imap()
        imap.select("INBOX", readonly=True)

        status, msg_ids = imap.search(None, "ALL")
        if status != "OK" or not msg_ids[0]:
            print(json.dumps({"total": 0, "emails": []}))
            return

        id_list = msg_ids[0].split()
        recent_ids = id_list[-max_results:]
        recent_ids.reverse()

        emails = []
        for msg_id in recent_ids:
            status, msg_data = imap.fetch(msg_id, "(BODY.PEEK[HEADER])")
            if status != "OK" or not msg_data[0]:
                continue
            raw_header = msg_data[0][1]
            msg = email.message_from_bytes(raw_header)
            emails.append(parse_email_headers(msg))

        imap.close()
        print(json.dumps({"total": len(emails), "emails": emails}))
    except imaplib.IMAP4.error as e:
        print(json.dumps({"error": f"IMAP error: {e}"}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to list emails: {e}"}))
    finally:
        if imap:
            try:
                imap.logout()
            except Exception:
                pass


def mail_read():
    """Read a specific email by Message-ID."""
    message_id = params.get("messageId", "")
    if not message_id:
        print(json.dumps({"error": "Missing required parameter: messageId"}))
        return

    imap = None
    try:
        imap = connect_imap()
        imap.select("INBOX", readonly=True)

        # Search by Message-ID header
        status, msg_ids = imap.search(None, "HEADER", "Message-ID", message_id)
        if status != "OK" or not msg_ids[0]:
            # Try without angle brackets if not found
            clean_id = message_id.strip("<>")
            status, msg_ids = imap.search(None, "HEADER", "Message-ID", f"<{clean_id}>")
            if status != "OK" or not msg_ids[0]:
                print(json.dumps({"error": f"Email not found with Message-ID: {message_id}"}))
                return

        msg_num = msg_ids[0].split()[0]
        status, msg_data = imap.fetch(msg_num, "(BODY[])")
        if status != "OK" or not msg_data[0]:
            print(json.dumps({"error": "Failed to fetch email content"}))
            return

        raw_msg = msg_data[0][1]
        msg = email.message_from_bytes(raw_msg)
        result = parse_email_message(msg)

        imap.close()
        print(json.dumps(result))
    except imaplib.IMAP4.error as e:
        print(json.dumps({"error": f"IMAP error: {e}"}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to read email: {e}"}))
    finally:
        if imap:
            try:
                imap.logout()
            except Exception:
                pass


def mail_search():
    """Search emails by query using Gmail IMAP extensions."""
    query = params.get("query", "")
    max_results = int(params.get("maxResults", 10))

    if not query:
        print(json.dumps({"error": "Missing required parameter: query"}))
        return

    imap = None
    try:
        imap = connect_imap()
        imap.select("INBOX", readonly=True)

        # Try Gmail X-GM-RAW extension for full Gmail search syntax
        try:
            status, msg_ids = imap.search(None, "X-GM-RAW", f'"{query}"')
        except imaplib.IMAP4.error:
            # Fallback to standard IMAP SUBJECT search
            status, msg_ids = imap.search(None, "SUBJECT", f'"{query}"')

        if status != "OK" or not msg_ids[0]:
            print(json.dumps({"total": 0, "emails": []}))
            return

        id_list = msg_ids[0].split()
        recent_ids = id_list[-max_results:]
        recent_ids.reverse()

        emails = []
        for msg_id in recent_ids:
            status, msg_data = imap.fetch(msg_id, "(BODY.PEEK[HEADER])")
            if status != "OK" or not msg_data[0]:
                continue
            raw_header = msg_data[0][1]
            msg = email.message_from_bytes(raw_header)
            emails.append(parse_email_headers(msg))

        imap.close()
        print(json.dumps({"total": len(emails), "emails": emails}))
    except imaplib.IMAP4.error as e:
        print(json.dumps({"error": f"IMAP error: {e}"}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to search emails: {e}"}))
    finally:
        if imap:
            try:
                imap.logout()
            except Exception:
                pass


def mail_send():
    """Send a new email via SMTP."""
    to = params.get("to", "")
    subject = params.get("subject", "")
    body = params.get("body", "")

    if not to or not subject or not body:
        print(json.dumps({"error": "Missing required parameters: to, subject, body"}))
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = email_address
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")

    if detect_html(body):
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with connect_smtp() as server:
            server.send_message(msg)
        print(json.dumps({
            "status": "sent",
            "to": to,
            "subject": subject,
            "messageId": msg["Message-ID"],
        }))
    except smtplib.SMTPAuthenticationError as e:
        print(json.dumps({"error": f"SMTP authentication failed: {e.smtp_code} {e.smtp_error}"}))
    except smtplib.SMTPException as e:
        print(json.dumps({"error": f"SMTP error: {e}"}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to send email: {e}"}))


def mail_reply():
    """Reply to an email by Message-ID."""
    message_id = params.get("messageId", "")
    body = params.get("body", "")
    reply_all = params.get("replyAll", False)

    if not message_id or not body:
        print(json.dumps({"error": "Missing required parameters: messageId, body"}))
        return

    # Fetch the original email to build proper reply headers
    imap = None
    try:
        imap = connect_imap()
        imap.select("INBOX", readonly=True)

        status, msg_ids = imap.search(None, "HEADER", "Message-ID", message_id)
        if status != "OK" or not msg_ids[0]:
            clean_id = message_id.strip("<>")
            status, msg_ids = imap.search(None, "HEADER", "Message-ID", f"<{clean_id}>")
            if status != "OK" or not msg_ids[0]:
                print(json.dumps({"error": f"Original email not found: {message_id}"}))
                return

        msg_num = msg_ids[0].split()[0]
        status, msg_data = imap.fetch(msg_num, "(BODY.PEEK[HEADER])")
        if status != "OK" or not msg_data[0]:
            print(json.dumps({"error": "Failed to fetch original email headers"}))
            return

        original = email.message_from_bytes(msg_data[0][1])
        imap.close()
        imap.logout()
        imap = None

        # Build reply recipients
        original_from = decode_header_value(original.get("From", ""))
        original_to = decode_header_value(original.get("To", ""))
        original_cc = decode_header_value(original.get("Cc", ""))
        original_subject = decode_header_value(original.get("Subject", ""))
        original_msg_id = original.get("Message-ID", "")
        original_references = original.get("References", "")

        # Reply-To takes precedence over From
        reply_to_addr = decode_header_value(original.get("Reply-To", "")) or original_from

        # Build recipient list
        to_addr = reply_to_addr
        cc_addr = ""
        if reply_all:
            # Combine original To and Cc, excluding ourselves
            all_recipients = set()
            for addr_str in [original_to, original_cc]:
                if addr_str:
                    for addr in addr_str.split(","):
                        addr = addr.strip()
                        if addr and email_address.lower() not in addr.lower():
                            all_recipients.add(addr)
            # Remove the reply-to address from CC (it's already in To)
            all_recipients.discard(reply_to_addr)
            if all_recipients:
                cc_addr = ", ".join(all_recipients)

        # Build subject with Re: prefix
        subject = original_subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        # Build references header
        references = original_references
        if references:
            references = f"{references} {original_msg_id}"
        else:
            references = original_msg_id

        # Compose reply
        msg = MIMEMultipart("alternative")
        msg["From"] = email_address
        msg["To"] = to_addr
        if cc_addr:
            msg["Cc"] = cc_addr
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="gmail.com")
        msg["In-Reply-To"] = original_msg_id
        msg["References"] = references

        if detect_html(body):
            msg.attach(MIMEText(body, "html", "utf-8"))
        else:
            msg.attach(MIMEText(body, "plain", "utf-8"))

        with connect_smtp() as server:
            server.send_message(msg)

        print(json.dumps({
            "status": "sent",
            "to": to_addr,
            "cc": cc_addr,
            "subject": subject,
            "inReplyTo": original_msg_id,
            "messageId": msg["Message-ID"],
        }))
    except smtplib.SMTPAuthenticationError as e:
        print(json.dumps({"error": f"SMTP authentication failed: {e.smtp_code} {e.smtp_error}"}))
    except smtplib.SMTPException as e:
        print(json.dumps({"error": f"SMTP error: {e}"}))
    except imaplib.IMAP4.error as e:
        print(json.dumps({"error": f"IMAP error: {e}"}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to reply to email: {e}"}))
    finally:
        if imap:
            try:
                imap.logout()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# CalDAV connection
# ---------------------------------------------------------------------------

def connect_caldav():
    """Connect to Google CalDAV and return the client."""
    return caldav.DAVClient(
        url=CALDAV_URL,
        username=email_address,
        password=app_password,
    )


def get_default_calendar(client):
    """Get the primary (default) calendar from the CalDAV client."""
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise Exception("No calendars found for this account")
    # Return first calendar (primary)
    return calendars[0]


def event_to_dict(event):
    """Convert a caldav Event to a serializable dict."""
    try:
        vevent = event.vobject_instance.vevent
    except Exception:
        return None

    def get_dt(prop):
        """Extract a datetime value from a vobject property."""
        try:
            val = getattr(vevent, prop, None)
            if val is None:
                return None
            dt = val.value
            if hasattr(dt, "isoformat"):
                return dt.isoformat()
            return str(dt)
        except Exception:
            return None

    def get_text(prop):
        """Extract a text value from a vobject property."""
        try:
            val = getattr(vevent, prop, None)
            if val is None:
                return ""
            return str(val.value)
        except Exception:
            return ""

    return {
        "id": get_text("uid"),
        "summary": get_text("summary"),
        "start": get_dt("dtstart"),
        "end": get_dt("dtend"),
        "description": get_text("description"),
        "location": get_text("location"),
        "url": str(event.url) if hasattr(event, "url") else "",
    }


# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------

def calendar_list():
    """List upcoming calendar events."""
    max_results = int(params.get("maxResults", 10))
    days = int(params.get("days", 7))

    try:
        client = connect_caldav()
        calendar = get_default_calendar(client)

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)

        results = calendar.date_search(start=now, end=end, expand=True)

        events = []
        for event in results:
            event_dict = event_to_dict(event)
            if event_dict:
                events.append(event_dict)

        # Sort by start time
        events.sort(key=lambda e: e.get("start") or "")

        # Limit results
        events = events[:max_results]

        print(json.dumps({"total": len(events), "events": events}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to list calendar events: {e}"}))


def calendar_create():
    """Create a new calendar event."""
    summary = params.get("summary", "")
    start = params.get("start", "")
    end = params.get("end", "")
    description = params.get("description", "")
    location = params.get("location", "")

    if not summary or not start or not end:
        print(json.dumps({"error": "Missing required parameters: summary, start, end"}))
        return

    event_uid = str(uuid.uuid4())

    # Build iCalendar data
    vcal_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sophon//Google Personal Skill//EN",
        "BEGIN:VEVENT",
        f"UID:{event_uid}",
        f"DTSTART:{_format_ical_datetime(start)}",
        f"DTEND:{_format_ical_datetime(end)}",
        f"SUMMARY:{_escape_ical(summary)}",
    ]
    if description:
        vcal_lines.append(f"DESCRIPTION:{_escape_ical(description)}")
    if location:
        vcal_lines.append(f"LOCATION:{_escape_ical(location)}")
    vcal_lines.append(f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    vcal_lines.extend(["END:VEVENT", "END:VCALENDAR"])

    ical_data = "\r\n".join(vcal_lines) + "\r\n"

    try:
        client = connect_caldav()
        calendar = get_default_calendar(client)
        event = calendar.save_event(ical_data)

        result = event_to_dict(event)
        if result is None:
            result = {
                "id": event_uid,
                "summary": summary,
                "start": start,
                "end": end,
                "description": description,
                "location": location,
            }
        result["status"] = "created"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": f"Failed to create calendar event: {e}"}))


def calendar_update():
    """Update an existing calendar event by UID."""
    event_id = params.get("eventId", "")
    if not event_id:
        print(json.dumps({"error": "Missing required parameter: eventId"}))
        return

    try:
        client = connect_caldav()
        calendar = get_default_calendar(client)

        # Search a wide range to find the event
        now = datetime.now(timezone.utc)
        start_range = now - timedelta(days=365)
        end_range = now + timedelta(days=365)

        results = calendar.date_search(start=start_range, end=end_range, expand=False)

        target_event = None
        for event in results:
            try:
                vevent = event.vobject_instance.vevent
                uid = str(vevent.uid.value)
                if uid == event_id:
                    target_event = event
                    break
            except Exception:
                continue

        if target_event is None:
            print(json.dumps({"error": f"Event not found with ID: {event_id}"}))
            return

        # Update properties on the vobject
        vevent = target_event.vobject_instance.vevent

        new_summary = params.get("summary")
        new_start = params.get("start")
        new_end = params.get("end")
        new_description = params.get("description")
        new_location = params.get("location")

        if new_summary is not None:
            vevent.summary.value = new_summary
        if new_start is not None:
            vevent.dtstart.value = _parse_datetime(new_start)
        if new_end is not None:
            vevent.dtend.value = _parse_datetime(new_end)
        if new_description is not None:
            if hasattr(vevent, "description"):
                vevent.description.value = new_description
            else:
                vevent.add("description").value = new_description
        if new_location is not None:
            if hasattr(vevent, "location"):
                vevent.location.value = new_location
            else:
                vevent.add("location").value = new_location

        target_event.save()

        result = event_to_dict(target_event)
        if result is None:
            result = {"id": event_id}
        result["status"] = "updated"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": f"Failed to update calendar event: {e}"}))


def calendar_delete():
    """Delete a calendar event by UID."""
    event_id = params.get("eventId", "")
    if not event_id:
        print(json.dumps({"error": "Missing required parameter: eventId"}))
        return

    try:
        client = connect_caldav()
        calendar = get_default_calendar(client)

        # Search a wide range to find the event
        now = datetime.now(timezone.utc)
        start_range = now - timedelta(days=365)
        end_range = now + timedelta(days=365)

        results = calendar.date_search(start=start_range, end=end_range, expand=False)

        target_event = None
        for event in results:
            try:
                vevent = event.vobject_instance.vevent
                uid = str(vevent.uid.value)
                if uid == event_id:
                    target_event = event
                    break
            except Exception:
                continue

        if target_event is None:
            print(json.dumps({"error": f"Event not found with ID: {event_id}"}))
            return

        target_event.delete()
        print(json.dumps({"status": "deleted", "id": event_id}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to delete calendar event: {e}"}))


def calendar_search():
    """Search calendar events by text in summary/description."""
    query = params.get("query", "")
    max_results = int(params.get("maxResults", 10))
    days = int(params.get("days", 30))

    if not query:
        print(json.dumps({"error": "Missing required parameter: query"}))
        return

    try:
        client = connect_caldav()
        calendar = get_default_calendar(client)

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)

        results = calendar.date_search(start=now, end=end, expand=True)

        query_lower = query.lower()
        events = []
        for event in results:
            event_dict = event_to_dict(event)
            if event_dict is None:
                continue
            # Match against summary and description
            summary = (event_dict.get("summary") or "").lower()
            description = (event_dict.get("description") or "").lower()
            if query_lower in summary or query_lower in description:
                events.append(event_dict)

        events.sort(key=lambda e: e.get("start") or "")
        events = events[:max_results]

        print(json.dumps({"total": len(events), "events": events}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to search calendar events: {e}"}))


# ---------------------------------------------------------------------------
# iCalendar format helpers
# ---------------------------------------------------------------------------

def _escape_ical(text):
    """Escape special characters for iCalendar text values."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _format_ical_datetime(iso_str):
    """Convert an ISO 8601 datetime string to iCalendar DTSTART/DTEND format."""
    try:
        dt = _parse_datetime(iso_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y%m%dT%H%M%SZ")
        return dt.strftime("%Y%m%dT%H%M%S")
    except Exception:
        # Return as-is if parsing fails — let CalDAV server handle it
        return iso_str


def _parse_datetime(iso_str):
    """Parse an ISO 8601 string to a datetime object."""
    # Handle common ISO formats
    iso_str = iso_str.strip()
    # Try standard fromisoformat (Python 3.11+ handles Z suffix)
    try:
        return datetime.fromisoformat(iso_str)
    except ValueError:
        pass
    # Handle Z suffix for older Python
    if iso_str.endswith("Z"):
        return datetime.fromisoformat(iso_str[:-1]).replace(tzinfo=timezone.utc)
    raise ValueError(f"Unable to parse datetime: {iso_str}")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

TOOL_DISPATCH = {
    "google.mail_list": mail_list,
    "google.mail_read": mail_read,
    "google.mail_search": mail_search,
    "google.mail_send": mail_send,
    "google.mail_reply": mail_reply,
    "google.calendar_list": calendar_list,
    "google.calendar_create": calendar_create,
    "google.calendar_update": calendar_update,
    "google.calendar_delete": calendar_delete,
    "google.calendar_search": calendar_search,
}

handler = TOOL_DISPATCH.get(tool_name)
if handler:
    try:
        handler()
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error in {tool_name}: {e}"}))
else:
    print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
